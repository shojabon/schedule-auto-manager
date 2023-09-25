from __future__ import annotations
from typing import TYPE_CHECKING
from notion_client import Client

if TYPE_CHECKING:
    from ScheduleAutoManager import ScheduleAutoManager


class NotionManager:

    def __init__(self, main: ScheduleAutoManager):
        self.main = main
        self.notion = Client(auth=main.config["notion"]["apiKey"])
        self.database_id = main.config["notion"]["databaseId"]

        self.update_database()

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
            if mongo_push_result["nModified"] == 1:
                updated_tasks.append(True)
            elif "upserted" in mongo_push_result:
                updated_tasks.append(True)
            else:
                updated_tasks.append(False)

            last_task = task

        # if last page is updated, recursively update
        if len(results) == page_size and updated_tasks[-1]:
            self.update_database(start_from=last_task["id"], page_size=page_size*2)
