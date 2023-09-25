import json

from pymongo import MongoClient

from ScheduleAutoManager.data_class.GoogleCalendarManager import GoogleCalendarManager
from ScheduleAutoManager.data_class.NotionManager import NotionManager


class ScheduleAutoManager:

    def __init__(self):
        config_file = open("config/config.json")
        self.config = json.loads(config_file.read())
        config_file.close()

        self.mongo = MongoClient(self.config["mongodb"])

        self.notion_manager = NotionManager(self)
        self.google_calendar_manager = GoogleCalendarManager(self)
