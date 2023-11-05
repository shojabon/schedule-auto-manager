from __future__ import annotations

import datetime
import hashlib
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

    def upsert_data(self, task_id: str, new_data: dict, force_push_update=False):
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

        if force_push_update:
            force_update = True

        if not force_update and comparing_old == comparing_new and task.data["archived"] == new_data["archived"]:
            return False

        res = self.main.mongo["scheduleAutoManager"]["notion_tasks"].update_one({"id": task_id}, {"$set": new_data},
                                                                                upsert=True)
        if task_id in self.task_cache:
            del self.task_cache[task_id]

        task = self.get_task(task_id)
        if task is not None:
            task.mark_as_completed_in_google_calendar()

        return True

    def push_score_to_database(self):

        calculated_end_date_map = self.get_calculated_end_date()
        differing_data_tasks = []

        for task in self.get_active_tasks():
            if task.get_determined_end_date_data() != task.get_determined_end_date():
                differing_data_tasks.append(task)
                print(task.get_name(), task.get_determined_end_date_data(), task.get_determined_end_date())
                continue
            calculated_end_date = calculated_end_date_map[
                task.get_id()] if task.get_id() in calculated_end_date_map else task.get_determined_end_date()
            if task.get_calculated_end_date_data() != calculated_end_date:
                differing_data_tasks.append(task)
                continue

        for task in tqdm(differing_data_tasks, desc="Pushing score to database"):
            for x in range(5):
                try:
                    print("Pushing score to database: " + task.get_name())
                    self.notion.pages.update(
                        page_id=task.get_id(),
                        archived=False,
                        properties={
                            "重要度スコア": {
                                "number": task.get_score()
                            },
                            "みなし終わり日": {
                                "date": {
                                    "time_zone": "Asia/Tokyo",
                                    "start": task.get_determined_end_date().strftime("%Y-%m-%dT%H:%M:%SZ")
                                }
                            },
                            "計算終わり日": {
                                "date": {
                                    "time_zone": "Asia/Tokyo",
                                    "start": calculated_end_date_map[task.get_id()].strftime(
                                        "%Y-%m-%dT%H:%M:%SZ") if task.get_id() in calculated_end_date_map else task.get_determined_end_date().strftime(
                                        "%Y-%m-%dT%H:%M:%SZ")
                                }
                            }
                        }
                    )
                    break
                except Exception as e:
                    print(e)
                    time.sleep(3)
                    continue
        # self.main.config["notion"]["scoreUpdateKey"] = score_update_key
        # self.main.save_config()

    def update_database(self, start_from: str = None, page_size: int = 10, task_filter: dict = None):
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
                    filter=task_filter
                )
                break
            except Exception as e:
                print(e)
                time.sleep(3)
                continue

        if query_result is None:
            raise Exception("Failed to query database")
        results = query_result["results"]

        updated_tasks = []
        last_task = None
        for task in results:
            result = self.upsert_data(task["id"], task)
            updated_tasks.append(result)
            # print(f"Updated task {task['id']} with result {result}")
            last_task = task

        # if last page is updated, recursively update
        if len(results) == page_size and updated_tasks[-1]:
            self.update_database(start_from=last_task["id"], page_size=page_size * 2)

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
            if task.get_date_data() is None:
                continue
            now = datetime.datetime.now(task.get_start_date().astimezone().tzinfo)
            if not (task.get_start_date() <= now):
                continue
            tasks.append(task)
        return tasks

    # ======== Task Batching ========

    def get_duration_of_task_completed_today(self):
        tasks = self.get_all_tasks()
        total_duration = 0
        for task in tasks:
            completed_time = task.get_completed_time()
            if completed_time is None:
                continue
            if completed_time.date() != datetime.datetime.now().date():
                continue
            total_duration += task.get_duration()
        return total_duration

    def get_calculated_end_date(self):
        result = {}
        # tasks = self.get_active_tasks()
        # tasks.reverse()
        #
        # tasks.sort(key=lambda x: x.get_determined_end_date())
        #
        # task_duration_completed_today = self.get_duration_of_task_completed_today()
        #
        # base_date = 0
        # total_minutes = 0
        # for task in tasks:
        #     offset = task_duration_completed_today if base_date == 0 else 0
        #     if total_minutes > 6 * 60 - offset:
        #         base_date += 1
        #         total_minutes = 0
        #     total_minutes += task.get_duration()
        #     result[task.get_id()] = datetime.datetime.today() + datetime.timedelta(days=base_date)
        #     # set timezone to JST
        #     result[task.get_id()] = result[task.get_id()].astimezone(tz=datetime.timezone(datetime.timedelta(hours=9)))
        #     # set time to 0:00
        #     result[task.get_id()] = result[task.get_id()].replace(hour=0, minute=0, second=0, microsecond=0)

        return result

    def push_determined_end_date(self):
        active_batched_tasks = self.get_batched_active_tasks()
        for project_id in active_batched_tasks.keys():
            for batch in active_batched_tasks[project_id]:
                last_task = batch[-1]
                for idx, task in enumerate(batch):
                    task.set_metadata("determinedEndDate", last_task.get_ideal_end_date() - datetime.timedelta(minutes=len(batch) - idx))

    def get_batched_active_tasks(self) -> dict[str, list[list[FlexTask]]]:
        result = {}

        batched_tasks_by_project = self.get_batched_tasks_by_project()
        for project_id in batched_tasks_by_project.keys():
            result[project_id] = []
            for batch in batched_tasks_by_project[project_id]:
                if len([task for task in batch if task.get_status() == "未完了"]) == 0:
                    continue
                result[project_id].append(batch)

        return result

    def get_batched_tasks_by_project(self):
        result = {}

        project_tasks = self.get_tasks_by_project()

        for project_id in project_tasks.keys():
            project_id = str(project_id)
            result[project_id] = []
            tasks = project_tasks[project_id]

            batch = []

            def batch_total_duration():
                return sum([task.get_duration() for task in batch])

            for task in tasks:
                batch.append(task)
                if batch_total_duration() >= 90:
                    result[project_id].append(batch)
                    batch = []

            if len(batch) > 0:
                result[project_id].append(batch)

        return result

    def get_tasks_by_project(self):
        result = {}

        for task in self.get_active_tasks():
            if task.get_end_date() is None:
                continue
            project_tasks = task.get_project_tasks()
            first_task_id = project_tasks[0]
            if first_task_id not in result:
                result[first_task_id] = [self.get_task(task_id) for task_id in project_tasks]

        return result
