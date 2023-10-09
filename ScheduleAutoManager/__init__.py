import json

from pymongo import MongoClient

from ScheduleAutoManager.manager.GoogleCalendarManager import GoogleCalendarManager
from ScheduleAutoManager.manager.NotionManager import NotionManager


class ScheduleAutoManager:

    def __init__(self):
        config_file = open("config/config.json", encoding="utf-8")
        self.config = json.loads(config_file.read())
        config_file.close()

        self.mongo = MongoClient(self.config["mongodb"])

        self.notion_manager = NotionManager(self)
        self.google_calendar_manager = GoogleCalendarManager(self)

        # task = self.notion_manager.get_task("0c07dc72-4fa5-4b32-b965-112ee7c6df7f")
        # keys = task.data["properties"].keys()
        # print(task.get_name(), task.get_insurance_rate(), task.get_score())
        # for x in keys:
        #     print(x)

        # self.notion_manager.update_database()
        # self.notion_manager.delete_unnecessary_tasks()
        # #
        # self.notion_manager.push_score_to_database()
        # #
        # tasks = {}
        #
        # for task in self.notion_manager.get_active_tasks():
        #     tasks[task.get_name()] = (task.get_score(), task.days_left())
        #
        # tasks = sorted(tasks.items(), key=lambda x: x[1], reverse=True)
        # for task in tasks:
        #     print(task[0], task[1])

        # print(len(self.notion_manager.get_active_tasks()))

    def save_config(self):
        config_file = open("config/config.json", "w", encoding="utf-8")
        config_file.write(json.dumps(self.config, indent=4, ensure_ascii=False))
        config_file.close()
