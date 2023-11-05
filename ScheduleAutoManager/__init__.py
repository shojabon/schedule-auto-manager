import datetime
import json
import threading
import time
from threading import Thread

from pymongo import MongoClient
from tqdm import tqdm

from ScheduleAutoManager.manager.GoogleCalendarManager import GoogleCalendarManager
from ScheduleAutoManager.manager.NotionManager import NotionManager


class ScheduleAutoManager:

    def execute_every_minute(self):
        while not self.stop_event.is_set():
            try:
                self.notion_manager.update_database(task_filter={
                    "property": "最終更新者",
                    "people": {
                        "contains": self.config["notion"]["userId"]
                    }
                })
                self.notion_manager.update_database()
                self.notion_manager.delete_unnecessary_tasks()
                self.notion_manager.push_determined_end_date()
                self.notion_manager.push_score_to_database()
                self.google_calendar_manager.update_all_databases()

                # Sleep in 1 second intervals, checking for the stop event each time
                for _ in range(60):
                    if self.stop_event.is_set():
                        break
                    time.sleep(1)

            except Exception as e:
                print(e)

    def __init__(self):
        config_file = open("config/config.json", encoding="utf-8")
        self.config = json.loads(config_file.read())
        config_file.close()

        self.mongo = MongoClient(self.config["mongodb"])

        self.notion_manager = NotionManager(self)
        self.google_calendar_manager = GoogleCalendarManager(self)

        self.stop_event = threading.Event()

        # start execute every minute thread
        self.execute_minute_thread = Thread(target=self.execute_every_minute)
        self.execute_minute_thread.start()

        # for task in self.notion_manager.get_active_tasks():
        #     print(task.get_name(), task.get_determined_end_date())

    def stop(self):
        self.stop_event.set()
        self.execute_minute_thread.join()

    def save_config(self):
        config_file = open("config/config.json", "w", encoding="utf-8")
        config_file.write(json.dumps(self.config, indent=4, ensure_ascii=False))
        config_file.close()
