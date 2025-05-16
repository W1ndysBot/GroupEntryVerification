"""
用于扫描未验证的用户
"""

import os
import json
import logging
from collections import defaultdict

# 将路径添加到sys.path
import sys
import os

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from app.api import send_group_msg, set_group_kick, send_private_msg

# 数据存储路径
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "GroupEntryVerification",
)

# 用户验证状态文件
USER_VERIFICATION_FILE = os.path.join(DATA_DIR, "user_verification.json")
# 验证题目文件
VERIFICATION_QUESTIONS_FILE = os.path.join(DATA_DIR, "verification_questions.json")
# 警告记录文件
WARNING_RECORD_FILE = os.path.join(DATA_DIR, "warning_record.json")
# 达到警告上限用户记录文件
REACHED_LIMIT_FILE = os.path.join(DATA_DIR, "reached_limit.json")

# 最大警告次数
MAX_WARNING_COUNT = 4


class ScanVerification:
    """扫描未验证用户并发送警告的类"""

    def __init__(self):
        """初始化扫描验证类"""
        self.user_verification = self._load_user_verification()
        self.verification_questions = self._load_verification_questions()
        self.warning_record = self._load_warning_record()
        self.reached_limit = self._load_reached_limit()

    def _load_user_verification(self):
        """加载用户验证状态"""
        if not os.path.exists(USER_VERIFICATION_FILE):
            return {}
        try:
            with open(USER_VERIFICATION_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"加载用户验证状态失败: {e}")
            return {}

    def _load_verification_questions(self):
        """加载用户验证问题"""
        if not os.path.exists(VERIFICATION_QUESTIONS_FILE):
            return {}
        try:
            with open(VERIFICATION_QUESTIONS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"加载验证问题失败: {e}")
            return {}

    def _load_warning_record(self):
        """加载警告记录"""
        if not os.path.exists(WARNING_RECORD_FILE):
            return defaultdict(int)
        try:
            with open(WARNING_RECORD_FILE, "r", encoding="utf-8") as f:
                # 使用defaultdict确保新用户的警告次数默认为0
                return defaultdict(int, json.load(f))
        except Exception as e:
            logging.error(f"加载警告记录失败: {e}")
            return defaultdict(int)

    def _load_reached_limit(self):
        """加载达到警告上限的用户记录"""
        if not os.path.exists(REACHED_LIMIT_FILE):
            return {}
        try:
            with open(REACHED_LIMIT_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"加载达到警告上限用户记录失败: {e}")
            return {}

    def _save_warning_record(self):
        """保存警告记录"""
        os.makedirs(os.path.dirname(WARNING_RECORD_FILE), exist_ok=True)
        try:
            with open(WARNING_RECORD_FILE, "w", encoding="utf-8") as f:
                json.dump(dict(self.warning_record), f, ensure_ascii=False, indent=4)
        except Exception as e:
            logging.error(f"保存警告记录失败: {e}")

    def _save_reached_limit(self):
        """保存达到警告上限的用户记录"""
        os.makedirs(os.path.dirname(REACHED_LIMIT_FILE), exist_ok=True)
        try:
            with open(REACHED_LIMIT_FILE, "w", encoding="utf-8") as f:
                json.dump(self.reached_limit, f, ensure_ascii=False, indent=4)
        except Exception as e:
            logging.error(f"保存达到警告上限用户记录失败: {e}")

    def get_pending_users(self, group_id):
        """获取指定群中所有未验证的用户"""
        pending_users = []

        for key, value in self.user_verification.items():
            if "_" in key and value.get("status") == "pending":
                user_id, gid = key.split("_")
                if gid == group_id:
                    # 检查是否有对应的验证问题
                    expression = None
                    if key in self.verification_questions:
                        expression = self.verification_questions[key].get("expression")
                    elif f"{user_id}_{group_id}" in self.verification_questions:
                        expression = self.verification_questions[
                            f"{user_id}_{group_id}"
                        ].get("expression")

                    if expression:
                        pending_users.append(
                            {
                                "user_id": user_id,
                                "expression": expression,
                                "remaining_attempts": value.get(
                                    "remaining_attempts", 3
                                ),
                            }
                        )

        return pending_users

    async def warn_pending_users(self, websocket, group_id):
        """警告未验证的用户"""
        pending_users = self.get_pending_users(group_id)

        # 先处理上次达到警告上限的用户
        await self.check_and_kick_users(websocket, group_id)

        # 如果没有未验证用户，直接返回False
        if not pending_users:
            return False

        # 构建警告消息
        warning_msg = ""
        about_to_kick_msg = ""
        about_to_kick_users = []

        for user in pending_users:
            # 增加警告次数
            user_key = f"{user['user_id']}_{group_id}"
            self.warning_record[user_key] += 1

            # 获取当前用户的警告次数
            current_warning_count = self.warning_record[user_key]

            # 如果用户达到警告上限，添加到即将踢出的列表
            if current_warning_count >= MAX_WARNING_COUNT:
                if group_id not in self.reached_limit:
                    self.reached_limit[group_id] = []
                if user["user_id"] not in self.reached_limit[group_id]:
                    self.reached_limit[group_id].append(user["user_id"])
                    about_to_kick_users.append(user["user_id"])
                    about_to_kick_msg += f"[CQ:at,qq={user['user_id']}] "

            # 添加到警告消息
            warning_msg += f"[CQ:at,qq={user['user_id']}] 请及时私聊我【{user['expression']}】的答案完成验证 (警告: {current_warning_count}/{MAX_WARNING_COUNT})\n"

        warning_msg += f"超过{MAX_WARNING_COUNT}次警告将在下次扫描时被踢群"

        # 发送合并警告消息
        if warning_msg:
            await send_group_msg(websocket, group_id, warning_msg.strip())

        # 如果有即将被踢出的用户，发送即将踢出的消息
        if about_to_kick_msg:
            kick_warning = (
                f"{about_to_kick_msg}因多次未完成验证，下次扫描时将被踢出群聊！"
            )
            await send_group_msg(websocket, group_id, kick_warning)

            # 同时通知管理员
            from app.config import owner_id

            for admin_id in owner_id:
                user_ids = ", ".join(about_to_kick_users)
                admin_notice = f"群 {group_id} 中的用户 {user_ids} 已达到警告上限，下次扫描时将被踢出群聊。"
                await send_private_msg(websocket, admin_id, admin_notice)

        # 保存警告记录和达到警告上限的用户记录
        self._save_warning_record()
        self._save_reached_limit()

        return True

    async def check_and_kick_users(self, websocket, group_id):
        """检查并踢出上次扫描时已达到警告上限的用户"""
        if group_id not in self.reached_limit or not self.reached_limit[group_id]:
            return False

        kicked_users = []
        for user_id in self.reached_limit[group_id]:
            # 踢出用户
            try:
                await set_group_kick(websocket, group_id, user_id)
                kicked_users.append(user_id)

                # 从警告记录中移除
                user_key = f"{user_id}_{group_id}"
                if user_key in self.warning_record:
                    del self.warning_record[user_key]

                # 从验证状态中移除
                if user_key in self.user_verification:
                    self.user_verification[user_key]["status"] = "kicked"
                    with open(USER_VERIFICATION_FILE, "w", encoding="utf-8") as f:
                        json.dump(
                            self.user_verification,
                            f,
                            ensure_ascii=False,
                            indent=4,
                        )

                # 从验证问题中移除
                verification_questions = self._load_verification_questions()
                if user_key in verification_questions:
                    del verification_questions[user_key]
                    with open(VERIFICATION_QUESTIONS_FILE, "w", encoding="utf-8") as f:
                        json.dump(
                            verification_questions, f, ensure_ascii=False, indent=4
                        )

                logging.info(
                    f"用户 {user_id} 被警告超过 {MAX_WARNING_COUNT} 次，已被踢出群 {group_id}"
                )
            except Exception as e:
                logging.error(f"踢出用户 {user_id} 失败: {e}")

        # 清空该群组的达到警告上限用户列表
        if kicked_users:
            self.reached_limit[group_id] = []
            self._save_reached_limit()

            # 如果有用户被踢出，发送通知
            users_str = "，".join(kicked_users)
            await send_group_msg(
                websocket,
                group_id,
                f"以下用户因多次未完成验证已被踢出群聊：{users_str}",
            )

            # 保存更新的警告记录
            self._save_warning_record()

            return True

        return False
