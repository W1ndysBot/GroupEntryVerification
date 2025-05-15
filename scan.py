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

from app.api import send_group_msg, set_group_kick

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

# 最大警告次数
MAX_WARNING_COUNT = 4


class ScanVerification:
    """扫描未验证用户并发送警告的类"""

    def __init__(self):
        """初始化扫描验证类"""
        self.user_verification = self._load_user_verification()
        self.verification_questions = self._load_verification_questions()
        self.warning_record = self._load_warning_record()

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

    def _save_warning_record(self):
        """保存警告记录"""
        os.makedirs(os.path.dirname(WARNING_RECORD_FILE), exist_ok=True)
        try:
            with open(WARNING_RECORD_FILE, "w", encoding="utf-8") as f:
                json.dump(dict(self.warning_record), f, ensure_ascii=False, indent=4)
        except Exception as e:
            logging.error(f"保存警告记录失败: {e}")

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

        if not pending_users:
            await send_group_msg(websocket, group_id, "本群暂无未验证的用户")
            return False

        # 构建警告消息
        warning_msg = ""
        for user in pending_users:
            # 增加警告次数
            user_key = f"{user['user_id']}_{group_id}"
            self.warning_record[user_key] += 1

            # 获取当前警告次数
            current_warning_count = self.warning_record[user_key]

            # 添加到警告消息
            warning_msg += f"[CQ:at,qq={user['user_id']}] 请及时私聊我【{user['expression']}】的答案完成验证，当前警告第{current_warning_count}次，警告到达{MAX_WARNING_COUNT}次将会被踢群\n"

        # 发送合并警告消息
        if warning_msg:
            await send_group_msg(websocket, group_id, warning_msg.strip())

            # 保存警告记录
            self._save_warning_record()

            # 检查是否有用户需要被踢出
            await self.check_and_kick_users(websocket, group_id)

            return True

        return False

    async def check_and_kick_users(self, websocket, group_id):
        """检查并踢出被警告超过三次的用户"""
        kicked_users = []

        for key, count in list(self.warning_record.items()):
            if count >= MAX_WARNING_COUNT and "_" in key:
                user_id, gid = key.split("_")
                if gid == group_id:
                    # 踢出用户
                    try:
                        await set_group_kick(websocket, group_id, user_id)
                        kicked_users.append(user_id)

                        # 从警告记录中移除
                        del self.warning_record[key]

                        # 从验证状态中移除
                        user_key = f"{user_id}_{group_id}"
                        if user_key in self.user_verification:
                            self.user_verification[user_key]["status"] = "kicked"
                            with open(
                                USER_VERIFICATION_FILE, "w", encoding="utf-8"
                            ) as f:
                                json.dump(
                                    self.user_verification,
                                    f,
                                    ensure_ascii=False,
                                    indent=4,
                                )

                        logging.info(
                            f"用户 {user_id} 被警告超过 {MAX_WARNING_COUNT} 次，已被踢出群 {group_id}"
                        )
                    except Exception as e:
                        logging.error(f"踢出用户 {user_id} 失败: {e}")

        # 如果有用户被踢出，发送通知
        if kicked_users:
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
