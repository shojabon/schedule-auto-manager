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
