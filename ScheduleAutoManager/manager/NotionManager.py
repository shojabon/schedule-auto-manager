from __future__ import annotations
from typing import TYPE_CHECKING
from notion_client import Client

from ScheduleAutoManager.data_class.FlexTask import FlexTask

if TYPE_CHECKING:
    from ScheduleAutoManager import ScheduleAutoManager


class NotionManager:

    def __init__(self, main: ScheduleAutoManager):
        self.main = main
        self.notion = Client(auth=main.config["notion"]["apiKey"])
        self.database_id = main.config["notion"]["databaseId"]

        self.task_cache = {}

        self.update_database()

        print(self.get_task("0610ea52-d1b6-409f-8589-0812d9c77d95").get_date())

    def update_database(self, start_from: str = None, page_size: int = 10):
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

        results = query_result["results"]

        updated_tasks = []
        last_task = None
        for task in results:
            # upsert to mongodb
            mongo_push_result = self.main.mongo["scheduleAutoManager"]["notion_tasks"].update_one({"id": task["id"]},
                                                                                                  {"$set": task},
                                                                                                  upsert=True).raw_result
            if mongo_push_result["nModified"] == 1 or "upserted" in mongo_push_result:
                updated_tasks.append(True)
                if task["id"] in self.task_cache:
                    del self.task_cache[task["id"]]
            else:
                updated_tasks.append(False)
            last_task = task

        print(updated_tasks)

        # if last page is updated, recursively update
        if len(results) == page_size and updated_tasks[-1]:
            self.update_database(start_from=last_task["id"], page_size=page_size*2)

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
