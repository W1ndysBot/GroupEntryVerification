# script/GroupEntryVerification/main.py

import logging
import os
import sys
import json
import random
import time
import operator
import asyncio

# 添加项目根目录到sys.path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from app.config import *
from app.api import *
from app.switch import load_switch, save_switch
from app.scripts.GroupEntryVerification.del_message import DelMessage

# 数据存储路径，实际开发时，请将GroupEntryVerification替换为具体的数据存放路径
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "GroupEntryVerification",
)

# 用户验证状态文件
USER_VERIFICATION_FILE = os.path.join(DATA_DIR, "user_verification.json")
# 验证题目文件
VERIFICATION_QUESTIONS_FILE = os.path.join(DATA_DIR, "verification_questions.json")

# 最大尝试次数
MAX_ATTEMPTS = 3
# 禁言时间（30天，单位：秒）
BAN_DURATION = 30 * 24 * 60 * 60

# 管理员审核命令
ADMIN_APPROVE_CMD = "批准"  # 批准命令
ADMIN_REJECT_CMD = "拒绝"  # 拒绝命令


# 查看功能开关状态
def load_function_status(group_id):
    return load_switch(group_id, "GroupEntryVerification")


# 保存功能开关状态
def save_function_status(group_id, status):
    save_switch(group_id, "GroupEntryVerification", status)


# 生成数学表达式和答案
def generate_math_expression():
    """生成一个简单的加减乘除二元数学表达式和答案"""
    return generate_simple_expression()


def generate_simple_expression():
    """生成简单的二元表达式"""
    operations = {
        "+": operator.add,
        "-": operator.sub,
        "*": operator.mul,
        "/": operator.truediv,
    }

    # 选择运算符
    op = random.choice(list(operations.keys()))

    # 生成数字（简单且容易计算）
    if op == "+":
        a = random.randint(1, 50)
        b = random.randint(1, 50)
    elif op == "-":
        a = random.randint(10, 100)
        b = random.randint(1, a)  # 确保结果为正数
    elif op == "*":
        a = random.randint(2, 12)
        b = random.randint(2, 12)  # 乘法表范围内
    elif op == "/":
        b = random.randint(2, 10)  # 避免除以0和1
        a = b * random.randint(1, 10)  # 确保能整除

    # 计算结果
    result = operations[op](a, b)

    # 对于除法，确保结果是整数
    if op == "/" and result != int(result):
        result = round(result, 2)  # 保留两位小数

    expression = f"{a} {op} {b}"
    return expression, result


# 保存用户验证状态
def save_user_verification_status(user_verification):
    """保存用户验证状态到文件"""
    with open(USER_VERIFICATION_FILE, "w", encoding="utf-8") as f:
        json.dump(user_verification, f, ensure_ascii=False, indent=4)


# 加载用户验证状态
def load_user_verification_status():
    """从文件加载用户验证状态"""
    if not os.path.exists(USER_VERIFICATION_FILE):
        return {}

    try:
        with open(USER_VERIFICATION_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"加载用户验证状态失败: {e}")
        return {}


# 保存验证题目
def save_verification_question(user_id, group_id, expression, answer):
    """保存用户的验证题目和答案"""
    questions = load_verification_questions()
    key = f"{user_id}_{group_id}"

    questions[key] = {
        "expression": expression,
        "answer": answer,
        "timestamp": time.time(),
    }

    with open(VERIFICATION_QUESTIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(questions, f, ensure_ascii=False, indent=4)


# 加载验证题目
def load_verification_questions():
    """从文件加载验证题目"""
    if not os.path.exists(VERIFICATION_QUESTIONS_FILE):
        return {}

    try:
        with open(VERIFICATION_QUESTIONS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logging.error(f"加载验证题目失败: {e}")
        return {}


# 获取用户验证题目和答案
def get_user_verification_question(user_id, group_id):
    """获取特定用户在特定群的验证题目和答案"""
    questions = load_verification_questions()
    key = f"{user_id}_{group_id}"

    if key in questions:
        return questions[key]["expression"], float(questions[key]["answer"])
    return None, None


# 处理元事件，用于启动时确保数据目录存在
async def handle_meta_event(websocket, msg):
    """处理元事件"""
    os.makedirs(DATA_DIR, exist_ok=True)


# 处理开关状态
async def toggle_function_status(websocket, group_id, message_id, authorized):
    if not authorized:
        await send_group_msg(
            websocket,
            group_id,
            f"[CQ:reply,id={message_id}]❌❌❌你没有权限对GroupEntryVerification功能进行操作,请联系管理员。",
        )
        return

    if load_function_status(group_id):
        save_function_status(group_id, False)
        await send_group_msg(
            websocket,
            group_id,
            f"[CQ:reply,id={message_id}]🚫🚫🚫GroupEntryVerification功能已关闭",
        )
    else:
        save_function_status(group_id, True)
        await send_group_msg(
            websocket,
            group_id,
            f"[CQ:reply,id={message_id}]✅✅✅GroupEntryVerification功能已开启",
        )


# 群消息处理函数
async def handle_group_message(websocket, msg):
    """处理群消息"""
    # 确保数据目录存在
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        user_id = str(msg.get("user_id"))
        group_id = str(msg.get("group_id"))
        raw_message = str(msg.get("raw_message"))
        message_id = str(msg.get("message_id"))
        authorized = user_id in owner_id

        # 处理开关命令
        if raw_message == "gev":
            await toggle_function_status(websocket, group_id, message_id, authorized)
            return
        # 检查功能是否开启
        if load_function_status(group_id):
            # 检查用户是否未验证
            user_verification = load_user_verification_status()
            user_group_key = f"{user_id}_{group_id}"
            if (
                user_group_key in user_verification
                and user_verification[user_group_key].get("status") == "pending"
            ):
                # 如果用户未验证，撤回消息并禁言
                await delete_msg(websocket, message_id)
                await set_group_ban(websocket, group_id, user_id, BAN_DURATION)
                expression, _ = get_user_verification_question(user_id, group_id)
                # 发送提示消息
                if expression:
                    await send_group_msg(
                        websocket,
                        group_id,
                        f"[CQ:at,qq={user_id}] 您尚未完成入群验证，消息已被撤回并禁言30天。请私聊我回答问题完成验证：{expression}",
                    )
                else:
                    await send_group_msg(
                        websocket,
                        group_id,
                        f"[CQ:at,qq={user_id}] 您尚未完成入群验证，消息已被撤回并禁言30天。请私聊机器人完成验证。",
                    )
                return  # 阻止后续处理

            # 其他群消息处理逻辑
            pass
    except Exception as e:
        logging.error(f"处理GroupEntryVerification群消息失败: {e}")
        await send_group_msg(
            websocket,
            group_id,
            "处理GroupEntryVerification群消息失败，错误信息：" + str(e),
        )
        return


# 私聊消息处理函数
async def handle_private_message(websocket, msg):
    """处理私聊消息"""
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        user_id = str(msg.get("user_id"))
        raw_message = str(msg.get("raw_message"))

        # 检查是否是管理员命令
        if user_id in owner_id:
            # 处理管理员批准命令
            if raw_message.startswith(ADMIN_APPROVE_CMD):
                await handle_admin_approve(websocket, user_id, raw_message)
                return

            # 处理管理员拒绝命令
            elif raw_message.startswith(ADMIN_REJECT_CMD):
                await handle_admin_reject(websocket, user_id, raw_message)
                return

        # 加载用户验证状态
        user_verification = load_user_verification_status()

        # 检查该用户是否需要验证
        for key in list(user_verification.keys()):
            if key.startswith(f"{user_id}_"):
                user_group_key = key
                group_id = user_group_key.split("_")[1]

                # 如果用户正在等待验证
                if user_verification[user_group_key]["status"] == "pending":
                    expression, correct_answer = get_user_verification_question(
                        user_id, group_id
                    )

                    if expression is None:
                        continue

                    # 尝试将用户输入转换为数字进行比较
                    try:
                        user_answer = float(raw_message.strip())

                        # 判断答案是否正确
                        if (
                            expression is not None
                            and correct_answer is not None
                            and abs(user_answer - correct_answer) < 0.01
                        ):  # 允许小误差
                            # 回答正确，解除禁言
                            await set_group_ban(websocket, group_id, user_id, 0)
                            # 在群里通知验证成功
                            await send_group_msg(
                                websocket,
                                group_id,
                                f"[CQ:at,qq={user_id}] 恭喜你通过了验证！现在可以正常发言了。",
                            )

                            # 更新状态
                            user_verification[user_group_key]["status"] = "verified"
                            save_user_verification_status(user_verification)

                            # 撤回存储的验证消息
                            del_message = DelMessage()
                            message_id_list = del_message.load_message_id_list()
                            for message_id in message_id_list:
                                await delete_msg(websocket, message_id)

                        else:
                            # 回答错误，减少尝试次数
                            remaining_attempts = (
                                user_verification[user_group_key]["remaining_attempts"]
                                - 1
                            )
                            user_verification[user_group_key][
                                "remaining_attempts"
                            ] = remaining_attempts
                            save_user_verification_status(user_verification)

                            if remaining_attempts > 0:
                                # 在群里通知剩余次数
                                await send_group_msg(
                                    websocket,
                                    group_id,
                                    f"[CQ:at,qq={user_id}] 回答错误！你还有{remaining_attempts}次机会。请重新计算：{expression}",
                                )
                            else:
                                # 尝试次数用完，踢出群聊
                                await set_group_kick(websocket, group_id, user_id)
                                # 在群里通知踢出原因
                                await send_group_msg(
                                    websocket,
                                    group_id,
                                    f"用户 {user_id} 验证失败，已被踢出群聊。",
                                )

                                # 更新状态
                                user_verification[user_group_key]["status"] = "failed"
                                save_user_verification_status(user_verification)
                    except ValueError:
                        # 用户输入的不是数字，在群里提醒
                        await send_group_msg(
                            websocket,
                            group_id,
                            f"[CQ:at,qq={user_id}] 请私聊我一个数字作为答案。你的计算式是：{expression}",
                        )

                    return  # 处理完一个验证请求后返回
    except Exception as e:
        logging.error(f"处理GroupEntryVerification私聊消息失败: {e}")
        # 错误信息也转移到群里
        if "group_id" in locals():
            await send_group_msg(
                websocket,
                group_id,
                f"处理用户 {user_id} 的验证消息失败，错误信息：{str(e)}",
            )
        return


# 群通知处理函数
async def handle_group_notice(websocket, msg):
    """处理群通知"""
    # 确保数据目录存在
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        user_id = str(msg.get("user_id"))
        group_id = str(msg.get("group_id"))
        notice_type = str(msg.get("notice_type"))
        sub_type = str(msg.get("sub_type", ""))

        # 检查功能是否开启
        if not load_function_status(group_id):
            return

        # 检测新成员入群事件
        if notice_type == "group_increase":
            await process_new_member(websocket, user_id, group_id)

    except Exception as e:
        logging.error(f"处理GroupEntryVerification群通知失败: {e}")
        await send_group_msg(
            websocket,
            group_id,
            "处理GroupEntryVerification群通知失败，错误信息：" + str(e),
        )
        return


# 处理新成员入群
async def process_new_member(websocket, user_id, group_id):
    """处理新成员入群验证"""
    try:
        # 禁言新成员30天
        await set_group_ban(websocket, group_id, user_id, BAN_DURATION)

        # 生成数学表达式和答案
        expression, answer = generate_math_expression()

        # 保存验证题目和答案
        save_verification_question(user_id, group_id, expression, answer)

        # 在群里发送验证消息
        await send_group_msg(
            websocket,
            group_id,
            f"[CQ:at,qq={user_id}] 欢迎加入本群！请私聊我回复下面计算结果完成验证，你将有{MAX_ATTEMPTS}次机会，如果全部错误将会被踢出群聊\n你的计算式是：{expression}",
        )

        # 保存用户验证状态
        user_verification = load_user_verification_status()
        user_verification[f"{user_id}_{group_id}"] = {
            "status": "pending",
            "remaining_attempts": MAX_ATTEMPTS,
        }
        save_user_verification_status(user_verification)

        logging.info(f"已向用户 {user_id} 发送群 {group_id} 的入群验证")

        # 通知管理员有新成员加入，并私发计算式和答案
        for admin_id in owner_id:
            await send_private_msg(
                websocket,
                admin_id,
                f"新成员 {user_id} 加入了群 {group_id}，等待验证。\n"
                f"计算式：{expression}\n"
                f"答案：{answer}\n"
                f"您可以发送以下命令手动处理：\n"
                f"{ADMIN_APPROVE_CMD} {group_id} {user_id} (批准)\n"
                f"{ADMIN_REJECT_CMD} {group_id} {user_id} (拒绝)",
            )
            await asyncio.sleep(1)
            await send_private_msg(
                websocket,
                admin_id,
                f"{ADMIN_APPROVE_CMD} {group_id} {user_id}",
            )
            await asyncio.sleep(1)
            await send_private_msg(
                websocket,
                admin_id,
                f"{ADMIN_REJECT_CMD} {group_id} {user_id}",
            )
    except Exception as e:
        logging.error(f"处理新成员入群验证失败: {e}")
        await send_group_msg(
            websocket,
            group_id,
            f"处理新成员 {user_id} 入群验证失败，错误信息：{str(e)}",
        )


# 请求事件处理函数
async def handle_request_event(websocket, msg):
    """处理请求事件"""
    try:
        request_type = msg.get("request_type")

        # 处理加群请求
        if request_type == "group":
            group_id = str(msg.get("group_id"))
            user_id = str(msg.get("user_id"))

            # 如果是加群请求，同意加群，后续在入群通知中进行验证
            if msg.get("sub_type") == "add":
                # 此处仅记录，不进行处理，等待用户入群后再处理
                logging.info(
                    f"收到用户 {user_id} 加入群 {group_id} 的请求，将在入群后进行验证"
                )

    except Exception as e:
        logging.error(f"处理GroupEntryVerification请求事件失败: {e}")
        return


# 回应事件处理函数
async def handle_response(websocket, msg):
    """处理回调事件"""
    try:
        echo = msg.get("echo")
        data = msg.get("data")
        if not echo:  # 如果没有echo内容，直接返回
            return

        # 定义需要追踪的验证过程中的消息特征短语
        # 这些消息是用户验证过程中机器人发送的提示或指令
        verification_phrases_to_track = [
            "请私聊我一个数字作为答案",  # 用户输入非数字时的提示
            "欢迎加入本群！请私聊我回复下面计算结果完成验证",  # 新用户入群的验证提示
            "您尚未完成入群验证",  # 用户未验证发言时的提示 (涵盖两种具体提示)
            "回答错误！你还有",  # 用户回答错误后的提示
            "验证失败，已被踢出群聊",  # 用户多次回答错误被踢出的提示
        ]

        found_match = False
        for phrase in verification_phrases_to_track:
            if phrase in echo:
                found_match = True
                break

        if found_match:
            # 如果 echo 中包含任意一个追踪的短语，
            # 则认为这是一条验证过程中的消息，使用 DelMessage 进行记录。
            del_message = DelMessage()
            del_message.add_message_id_list(data.get("message_id"))

    except Exception as e:
        logging.error(f"处理GroupEntryVerification回调事件失败: {e}")
        return


# 添加管理员批准命令处理函数
async def handle_admin_approve(websocket, admin_id, command):
    """处理管理员批准命令"""
    try:
        # 确保是验证功能的命令
        if not command.startswith(ADMIN_APPROVE_CMD):
            return

        # 解析命令参数
        parts = command.strip().split()
        if len(parts) < 3:
            await send_private_msg(
                websocket,
                admin_id,
                f"验证功能命令格式错误，正确格式：{ADMIN_APPROVE_CMD} 群号 QQ号",
            )
            return

        # 只取前三个部分，忽略后面可能的额外文本
        _, group_id, user_id = parts[0:3]

        # 加载用户验证状态
        user_verification = load_user_verification_status()
        user_group_key = f"{user_id}_{group_id}"

        # 检查用户是否在等待验证
        if (
            user_group_key not in user_verification
            or user_verification[user_group_key]["status"] != "pending"
        ):
            await send_private_msg(
                websocket, admin_id, f"用户 {user_id} 不在群 {group_id} 的验证队列中"
            )
            return

        # 解除用户禁言
        await set_group_ban(websocket, group_id, user_id, 0)

        # 在群里通知用户已被批准
        await send_group_msg(
            websocket,
            group_id,
            f"[CQ:at,qq={user_id}] 管理员手动通过了你的验证，现在可以正常发言了。",
        )

        # 更新用户状态
        user_verification[user_group_key]["status"] = "verified"
        save_user_verification_status(user_verification)
        # 撤回存储的验证消息
        del_message = DelMessage()
        message_id_list = del_message.load_message_id_list()
        for message_id in message_id_list:
            await delete_msg(websocket, message_id)
        # 通知管理员操作成功
        await send_private_msg(
            websocket, admin_id, f"已批准用户 {user_id} 在群 {group_id} 的验证"
        )

        logging.info(f"管理员 {admin_id} 批准了用户 {user_id} 在群 {group_id} 的验证")

    except Exception as e:
        logging.error(f"处理管理员批准命令失败: {e}")
        await send_private_msg(
            websocket, admin_id, f"处理批准命令失败，错误信息：{str(e)}"
        )


# 添加管理员拒绝命令处理函数
async def handle_admin_reject(websocket, admin_id, command):
    """处理管理员拒绝命令"""
    try:
        # 确保是验证功能的命令
        if not command.startswith(ADMIN_REJECT_CMD):
            return

        # 解析命令参数
        parts = command.strip().split()
        if len(parts) < 3:
            await send_private_msg(
                websocket,
                admin_id,
                f"验证功能命令格式错误，正确格式：{ADMIN_REJECT_CMD} 群号 QQ号",
            )
            return

        # 只取前三个部分，忽略后面可能的额外文本
        _, group_id, user_id = parts[0:3]

        # 加载用户验证状态
        user_verification = load_user_verification_status()
        user_group_key = f"{user_id}_{group_id}"

        # 在群里通知用户已被拒绝
        await send_group_msg(
            websocket,
            group_id,
            f"[CQ:at,qq={user_id}] 管理员拒绝了你的验证，你将被踢出群聊。",
        )

        # 踢出用户
        await set_group_kick(websocket, group_id, user_id)

        # 更新用户状态
        user_verification[user_group_key]["status"] = "rejected"
        save_user_verification_status(user_verification)

        # 通知管理员操作成功
        await send_private_msg(
            websocket,
            admin_id,
            f"已拒绝用户 {user_id} 在群 {group_id} 的验证并将其踢出",
        )

        logging.info(f"管理员 {admin_id} 拒绝了用户 {user_id} 在群 {group_id} 的验证")

    except Exception as e:
        logging.error(f"处理管理员拒绝命令失败: {e}")
        await send_private_msg(
            websocket, admin_id, f"处理拒绝命令失败，错误信息：{str(e)}"
        )


# 统一事件处理入口
async def handle_events(websocket, msg):
    """统一事件处理入口"""
    post_type = msg.get("post_type", "response")  # 添加默认值
    try:

        # 处理回调事件
        if msg.get("status") == "ok":
            await handle_response(websocket, msg)
            return

        post_type = msg.get("post_type")

        # 处理元事件
        if post_type == "meta_event":
            await handle_meta_event(websocket, msg)

        # 处理消息事件
        elif post_type == "message":
            message_type = msg.get("message_type")
            if message_type == "group":
                await handle_group_message(websocket, msg)
            elif message_type == "private":
                await handle_private_message(websocket, msg)

        # 处理通知事件
        elif post_type == "notice":
            await handle_group_notice(websocket, msg)

        # 处理请求事件
        elif post_type == "request":
            await handle_request_event(websocket, msg)

    except Exception as e:
        error_type = {
            "message": "消息",
            "notice": "通知",
            "request": "请求",
            "meta_event": "元事件",
        }.get(post_type, "未知")

        logging.error(f"处理GroupEntryVerification{error_type}事件失败: {e}")

        # 发送错误提示
        if post_type == "message":
            message_type = msg.get("message_type")
            if message_type == "group":
                await send_group_msg(
                    websocket,
                    msg.get("group_id"),
                    f"处理GroupEntryVerification{error_type}事件失败，错误信息：{str(e)}",
                )
            elif message_type == "private":
                await send_private_msg(
                    websocket,
                    msg.get("user_id"),
                    f"处理GroupEntryVerification{error_type}事件失败，错误信息：{str(e)}",
                )
