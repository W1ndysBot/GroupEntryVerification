import os
import json


class DelMessage:
    def __init__(self):
        self.DATA_DIR = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
            "data",
            "GroupEntryVerification",
        )
        self.data_file = os.path.join(self.DATA_DIR, "message_id_list.json")
        os.makedirs(self.DATA_DIR, exist_ok=True)

    def load_data(self):
        """
        加载消息ID数据

        从文件中读取消息ID数据 (格式: {group_id: {user_id: [message_id, ...]}})
        如果文件不存在、为空或格式错误，则创建一个空字典并覆盖原文件。

        返回:
            dict: 消息ID数据字典
        """
        if not os.path.exists(self.data_file):
            # 文件不存在，创建空字典并保存
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump({}, f)
            return {}

        try:
            with open(self.data_file, "r", encoding="utf-8") as f:
                # 处理文件为空的情况
                content = f.read()
                if not content:
                    # 文件为空，返回空字典，并用空字典覆盖（如果需要保持一致性）
                    with open(self.data_file, "w", encoding="utf-8") as f_write:
                        json.dump({}, f_write)
                    return {}
                message_data = json.loads(content)  # 使用 loads 从已读内容加载

            if not isinstance(message_data, dict):
                # 文件内容不是字典，视为无效数据，返回空字典并覆盖原文件
                with open(self.data_file, "w", encoding="utf-8") as f:
                    json.dump({}, f)
                return {}
            return message_data
        except json.JSONDecodeError:
            # JSON 格式错误，返回空字典并覆盖原文件
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump({}, f)
            return {}

    def save_data(self, message_data):
        """
        保存消息ID数据

        将消息ID数据字典保存到文件中

        参数:
            message_data (dict): 要保存的消息ID数据字典
        """
        with open(self.data_file, "w", encoding="utf-8") as f:
            json.dump(message_data, f, indent=4)

    def add_message(self, group_id: str, user_id: str, message_id):
        """
        添加消息ID到指定群组和用户的列表

        参数:
            group_id (str): 群组ID
            user_id (str): 用户ID
            message_id (any): 要添加的消息ID
        """
        message_data = self.load_data()

        group_id_str = str(group_id)
        user_id_str = str(user_id)

        if group_id_str not in message_data:
            message_data[group_id_str] = {}

        if user_id_str not in message_data[group_id_str]:
            message_data[group_id_str][user_id_str] = []

        if message_id not in message_data[group_id_str][user_id_str]:
            message_data[group_id_str][user_id_str].append(message_id)

        self.save_data(message_data)

    def remove_message(self, group_id: str, user_id: str, message_id):
        """
        从指定群组和用户的列表中删除消息ID

        参数:
            group_id (str): 群组ID
            user_id (str): 用户ID
            message_id (any): 要删除的消息ID
        """
        message_data = self.load_data()

        group_id_str = str(group_id)
        user_id_str = str(user_id)

        if (
            group_id_str in message_data
            and user_id_str in message_data[group_id_str]
            and message_id in message_data[group_id_str][user_id_str]
        ):
            message_data[group_id_str][user_id_str].remove(message_id)

            # 可选: 清理空列表和空字典
            if not message_data[group_id_str][user_id_str]:  # 如果用户消息列表为空
                del message_data[group_id_str][user_id_str]
            if not message_data[group_id_str]:  # 如果群组用户字典为空
                del message_data[group_id_str]

            self.save_data(message_data)

    def get_user_messages(self, group_id: str, user_id: str) -> list:
        """
        获取指定群组和用户的所有消息ID

        参数:
            group_id (str): 群组ID
            user_id (str): 用户ID

        返回:
            list: 消息ID列表，如果找不到则返回空列表
        """
        message_data = self.load_data()
        group_id_str = str(group_id)
        user_id_str = str(user_id)
        return message_data.get(group_id_str, {}).get(user_id_str, [])

    def get_all_messages_by_group(self, group_id: str) -> dict:
        """
        获取指定群组下所有用户及其消息ID

        参数:
            group_id (str): 群组ID

        返回:
            dict: 用户ID到消息ID列表的映射，如果找不到群组则返回空字典
        """
        message_data = self.load_data()
        group_id_str = str(group_id)
        return message_data.get(group_id_str, {})


# 示例用法 (可选，用于测试)
# if __name__ == '__main__':
#     handler = DelMessage()
#
#     # 清理旧数据文件（如果存在）
#     if os.path.exists(handler.data_file):
#         os.remove(handler.data_file)
#
#     print("初始数据:", handler.load_data())
#
#     handler.add_message("group1", "userA", 1001)
#     handler.add_message("group1", "userA", 1002)
#     handler.add_message("group1", "userB", 2001)
#     handler.add_message("group2", "userA", 3001)
#
#     print("添加后数据:", handler.load_data())
#
#     print("UserA messages in group1:", handler.get_user_messages("group1", "userA"))
#     print("All messages in group1:", handler.get_all_messages_by_group("group1"))
#
#     handler.remove_message("group1", "userA", 1001)
#     print("移除1001后:", handler.load_data())
#
#     handler.remove_message("group2", "userA", 3001) # 这将移除userA和group2
#     print("移除3001后 (group2应被清理):", handler.load_data())
#
#     handler.remove_message("group1", "userB", 2001) # 这将移除userB和group1
#     print("移除2001后 (userB和group1应被清理):", handler.load_data())
#
#     handler.add_message("new_group", "new_user", 9999)
#     print("再次添加:", handler.load_data())
