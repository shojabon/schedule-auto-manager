from __future__ import annotations

import datetime
import time
from typing import TYPE_CHECKING
from notion_client import Client
from tqdm import tqdm

from ScheduleAutoManager.data_class.FlexTask import FlexTask

if TYPE_CHECKING:
    from ScheduleAutoManager import ScheduleAutoManager


class NotionManager:

    def __init__(self, main: ScheduleAutoManager):
        self.main = main
        self.notion = Client(auth=main.config["notion"]["apiKey"])
        self.database_id = main.config["notion"]["databaseId"]

        self.task_cache = {}

        # self.update_database()

    def upsert_data(self, task_id: str, new_data: dict):
        task = self.get_task(task_id)
        comparing_old = {}
        force_update = False
        for key in self.main.config["notion"]["checkingFields"]:
            if task is None or key not in task.data["properties"]:
                force_update = True
                continue
            comparing_old[key] = task.data["properties"][key]

        comparing_new = {}
        for key in self.main.config["notion"]["checkingFields"]:
            if key not in new_data["properties"]:
                force_update = True
                continue
            comparing_new[key] = new_data["properties"][key]

        if not force_update and comparing_old == comparing_new and task.data["archived"] == new_data["archived"]:
            return False

        res = self.main.mongo["scheduleAutoManager"]["notion_tasks"].update_one({"id": task_id}, {"$set": new_data}, upsert=True)
        if task_id in self.task_cache:
            del self.task_cache[task_id]
        return True

    def update_database(self, start_from: str = None, page_size: int = 10):
        query_result = None
        for x in range(5):
            try:
                query_result = self.notion.databases.query(
                    database_id=self.database_id,
                    sorts=[
                        {
                            "property": "最終更新日時",
                            "direction": "descending"
                        }
                    ],
                    start_cursor=start_from,
                    page_size=page_size,
                )
                break
            except Exception as e:
                time.sleep(3)
                continue

        if query_result is None:
            raise Exception("Failed to query database")
        results = query_result["results"]

        updated_tasks = []
        last_task = None
        for task in results:
            updated_tasks.append(self.upsert_data(task["id"], task))
            last_task = task

        # if last page is updated, recursively update
        if len(results) == page_size and updated_tasks[-1]:
            self.update_database(start_from=last_task["id"], page_size=page_size*2)

    def delete_unnecessary_tasks(self):
        task_ids = []
        for task_db in self.main.mongo["scheduleAutoManager"]["notion_tasks"].find({}, {"id": 1}):
            task = self.get_task(task_db["id"])
            if task is None:
                continue
            if task.get_status() != "削除":
                continue
            task_ids.append(task_db["id"])

        for task_id in tqdm(task_ids, desc="Deleting unnecessary tasks"):
            try:
                self.notion.pages.update(
                    page_id=task_id,
                    archived=True
                )
                self.main.mongo["scheduleAutoManager"]["notion_tasks"].delete_one({"id": task_id})
                if task_id in self.task_cache:
                    del self.task_cache[task_id]
            except:
                print(f"Failed to delete task {task_id}")

    def get_task(self, task_id: str) -> FlexTask | None:
        if task_id in self.task_cache:
            return self.task_cache[task_id]
        task = self.main.mongo["scheduleAutoManager"]["notion_tasks"].find_one({"id": task_id})
        if task is None:
            return None
        task_object = FlexTask(task, self.main)
        self.task_cache[task_id] = task_object
        return self.task_cache[task_id]

    def get_all_tasks(self) -> list[FlexTask]:
        result = []
        task_ids = self.main.mongo["scheduleAutoManager"]["notion_tasks"].find({}, {"id": 1})
        for task_id in task_ids:
            result.append(self.get_task(task_id["id"]))
        return result

    def get_active_tasks(self):
        tasks = []
        for task in self.get_all_tasks():
            if task.get_status() != "未完了":
                continue
            now = datetime.datetime.now(task.get_start_date().astimezone().tzinfo)
            if not (task.get_start_date() <= now <= task.get_end_date()):
                continue
            tasks.append(task)
        return tasks

