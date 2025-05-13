import os
import json


class DelMessage:
    def __init__(self, message_id):
        self.message_id = message_id
        self.DATA_DIR = os.path.join(
            os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            ),
            "data",
            "GroupEntryVerification",
        )
        self.data_file = os.path.join(self.DATA_DIR, "message_id_list.json")

    def load_message_id_list(self):
        """
        加载消息ID列表

        从文件中读取消息ID列表，如果文件不存在则创建一个空列表

        返回:
            list: 消息ID列表
        """
        # 检查文件是否存在，如果不存在则创建空列表
        if not os.path.exists(self.data_file):
            os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
            with open(self.data_file, "w") as f:
                json.dump([], f)
            return []

        with open(self.data_file, "r") as f:
            message_id_list = json.load(f)
        return message_id_list

    def save_message_id_list(self, message_id_list):
        """
        保存消息ID列表

        将消息ID列表保存到文件中

        参数:
            message_id_list (list): 要保存的消息ID列表
        """
        # 确保目录存在
        os.makedirs(os.path.dirname(self.data_file), exist_ok=True)
        with open(self.data_file, "w") as f:
            json.dump(message_id_list, f)

    def add_message_id_list(self):
        """
        添加当前消息ID到列表

        将当前实例的消息ID添加到消息ID列表中并保存
        """
        message_id_list = self.load_message_id_list()
        message_id_list.append(self.message_id)
        self.save_message_id_list(message_id_list)

    def del_message_id_list(self):
        """
        从列表中删除当前消息ID

        如果当前实例的消息ID存在于列表中，则将其删除并保存更新后的列表
        """
        message_id_list = self.load_message_id_list()
        if self.message_id in message_id_list:
            message_id_list.remove(self.message_id)
            self.save_message_id_list(message_id_list)
