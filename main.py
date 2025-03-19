# script/GroupEntryVerification/main.py

import logging
import os
import sys
import re
import json
import random
import time
import operator

# 添加项目根目录到sys.path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from app.config import *
from app.api import *
from app.switch import load_switch, save_switch


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


# 查看功能开关状态
def load_function_status(group_id):
    return load_switch(group_id, "GroupEntryVerification")


# 保存功能开关状态
def save_function_status(group_id, status):
    save_switch(group_id, "GroupEntryVerification", status)


# 生成数学表达式和答案
def generate_math_expression():
    """生成一个丰富多样且易于计算的数学表达式和答案"""
    # 选择表达式类型：1=简单二元运算，2=三元运算，3=带括号运算
    expr_type = random.randint(1, 3)

    if expr_type == 1:
        # 简单二元运算 (a op b)
        return generate_simple_expression()
    elif expr_type == 2:
        # 三元运算 (a op b op c)
        return generate_three_term_expression()
    else:
        # 带括号运算 ((a op b) op c 或 a op (b op c))
        return generate_parentheses_expression()


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


def generate_three_term_expression():
    """生成三元表达式 (a op1 b op2 c)"""
    # 选择两个运算符，确保易于计算
    ops = ["+", "-", "*"]
    weights = [0.4, 0.3, 0.3]  # 加法更常见，使计算简单
    op1 = random.choices(ops, weights=weights)[0]
    op2 = random.choices(ops, weights=weights)[0]

    # 生成数字（确保结果易于计算）
    if op1 in ["+", "-"]:
        a = random.randint(1, 20)
    else:
        a = random.randint(2, 6)

    if op2 in ["+", "-"]:
        c = random.randint(1, 20)
    else:
        c = random.randint(2, 6)

    if op1 == "*" and op2 == "*":
        # 避免两个乘法导致结果过大
        b = random.randint(2, 4)
    else:
        b = random.randint(1, 10)

    # 构建表达式
    expression = f"{a} {op1} {b} {op2} {c}"

    # 计算结果（从左到右）
    if op1 == "+":
        temp = a + b
    elif op1 == "-":
        temp = a - b
    else:
        temp = a * b

    if op2 == "+":
        result = temp + c
    elif op2 == "-":
        result = temp - c
    else:
        result = temp * c

    return expression, result


def generate_parentheses_expression():
    """生成带括号的表达式"""
    # 选择括号位置：1=左侧括号 (a op1 b) op2 c, 2=右侧括号 a op1 (b op2 c)
    bracket_pos = random.randint(1, 2)

    # 选择操作符
    simple_ops = ["+", "-"]
    all_ops = ["+", "-", "*"]

    # 确保括号内的运算简单，括号外优先选择加减
    if bracket_pos == 1:
        op1 = random.choice(simple_ops)
        op2 = random.choice(all_ops)
    else:
        op1 = random.choice(all_ops)
        op2 = random.choice(simple_ops)

    # 生成易于计算的数字
    a = random.randint(2, 20)
    b = random.randint(2, 20)
    c = random.randint(2, 10)

    # 构建表达式
    if bracket_pos == 1:
        expression = f"({a} {op1} {b}) {op2} {c}"

        # 计算结果
        if op1 == "+":
            temp = a + b
        elif op1 == "-":
            temp = a - b
        else:
            temp = a * b

        if op2 == "+":
            result = temp + c
        elif op2 == "-":
            result = temp - c
        else:
            result = temp * c
    else:
        expression = f"{a} {op1} ({b} {op2} {c})"

        # 计算结果
        if op2 == "+":
            temp = b + c
        elif op2 == "-":
            temp = b - c
        else:
            temp = b * c

        if op1 == "+":
            result = a + temp
        elif op1 == "-":
            result = a - temp
        else:
            result = a * temp

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
        if raw_message == "gevf":
            await toggle_function_status(websocket, group_id, message_id, authorized)
            return
        # 检查功能是否开启
        if load_function_status(group_id):
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
                            await send_private_msg(
                                websocket,
                                user_id,
                                f"恭喜你通过了验证！你现在可以在群【{group_id}】中正常发言了。",
                            )

                            # 更新状态
                            user_verification[user_group_key]["status"] = "verified"
                            save_user_verification_status(user_verification)
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
                                await send_private_msg(
                                    websocket,
                                    user_id,
                                    f"回答错误！你还有{remaining_attempts}次机会。请重新计算：{expression}",
                                )
                            else:
                                # 尝试次数用完，踢出群聊
                                await set_group_kick(websocket, group_id, user_id)
                                await send_private_msg(
                                    websocket,
                                    user_id,
                                    f"很抱歉，你已用完所有尝试机会，你将被踢出群【{group_id}】。",
                                )

                                # 更新状态
                                user_verification[user_group_key]["status"] = "failed"
                                save_user_verification_status(user_verification)
                    except ValueError:
                        # 用户输入的不是数字
                        await send_private_msg(
                            websocket,
                            user_id,
                            f"请输入一个数字作为答案。你的计算式是：{expression}",
                        )

                    return  # 处理完一个验证请求后返回
    except Exception as e:
        logging.error(f"处理GroupEntryVerification私聊消息失败: {e}")
        await send_private_msg(
            websocket,
            msg.get("user_id"),
            "处理GroupEntryVerification私聊消息失败，错误信息：" + str(e),
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

        # 发送私聊验证消息
        await send_private_msg(
            websocket,
            user_id,
            f"你在群【{group_id}】需要进行人机验证，请回复下面计算结果，你将有{MAX_ATTEMPTS}次机会，如果全部错误将会被踢出群聊\n你的计算式是：{expression}",
        )

        # 保存用户验证状态
        user_verification = load_user_verification_status()
        user_verification[f"{user_id}_{group_id}"] = {
            "status": "pending",
            "remaining_attempts": MAX_ATTEMPTS,
            "timestamp": time.time(),
        }
        save_user_verification_status(user_verification)

        logging.info(f"已向用户 {user_id} 发送群 {group_id} 的入群验证")

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
        if echo and echo.startswith("xxx"):
            # 回调处理逻辑
            pass
    except Exception as e:
        logging.error(f"处理GroupEntryVerification回调事件失败: {e}")
        await send_group_msg(
            websocket,
            msg.get("group_id"),
            f"处理GroupEntryVerification回调事件失败，错误信息：{str(e)}",
        )
        return


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
