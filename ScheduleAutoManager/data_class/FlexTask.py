from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ScheduleAutoManager import ScheduleAutoManager


class FlexTask:

    def __init__(self, data: dict, main: ScheduleAutoManager):
        self.data = data
        self.main: ScheduleAutoManager = main

    def get_id(self):
        return self.data["id"]

    def get_name(self) -> str:
        return str(self.data["properties"]["名前"]["title"][0]["text"]["content"])

    def get_date_data(self):
        return self.data["properties"]["日付"]["date"]

    def get_start_date(self):
        if self.get_date_data() is None:
            return None
        result = datetime.datetime.fromisoformat(self.get_date_data()["start"])
        # if no timezone info, assume JST
        if result.tzinfo is None:
            result = result.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=9)))
        return result

    def get_end_date(self):
        if self.get_date_data() is None:
            return None
        if self.get_date_data()["end"] is None:
            return self.get_start_date()
        result = datetime.datetime.fromisoformat(self.get_date_data()["end"])
        # if no timezone info, assume JST
        if result.tzinfo is None:
            result = result.replace(tzinfo=datetime.timezone(datetime.timedelta(hours=9)))
        return result

    def days_left(self):
        if self.get_end_date() is None:
            return None
        return (self.get_end_date() - datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9)))).days

    def get_zones(self) -> list[str]:
        zones = []
        for zone in self.data["properties"]["タスクゾーン"]["multi_select"]:
            zones.append(zone["name"])
        return zones

    def get_duration(self):
        duration = self.data["properties"]["タスク時間"]["number"]
        if duration is None:
            return 60
        return duration

    def get_insurance_rate(self):
        rate = self.data["properties"]["保険率"]["number"]
        if rate is None:
            return 0.7
        return rate

    def get_status(self):
        return self.data["properties"]["ステータス"]["status"]["name"]

    def get_required_tasks(self):
        required_tasks = []
        for task in self.data["properties"]["完了必須タスク"]["relation"]:
            required_tasks.append(task["id"])
        return required_tasks

    def get_parent_tasks(self):
        parent_tasks = []
        for task in self.data["properties"]["親タスク"]["relation"]:
            parent_tasks.append(task["id"])
        return parent_tasks


    def get_project_tasks(self):
        project_tasks = []
        if len(self.get_parent_tasks()) != 0:
            previous_task_id = self.get_parent_tasks()[0]
            while True:
                previous_task = self.main.notion_manager.get_task(previous_task_id)
                if previous_task is None:
                    break
                project_tasks.append(previous_task_id)
                if len(previous_task.get_parent_tasks()) == 0:
                    break
                previous_task_id = previous_task.get_parent_tasks()[0]

        project_tasks.reverse()
        project_tasks.append(self.get_id())

        if len(self.get_required_tasks()) != 0:
            previous_task_id = self.get_required_tasks()[0]
            while True:
                previous_task = self.main.notion_manager.get_task(previous_task_id)
                if previous_task is None:
                    break
                project_tasks.append(previous_task_id)
                if len(previous_task.get_required_tasks()) == 0:
                    break
                previous_task_id = previous_task.get_required_tasks()[0]

        project_tasks.reverse()
        return project_tasks

    def get_project_tasks_count(self):
        return len(self.get_project_tasks())


    def get_project_tasks_index(self):
        return self.get_project_tasks().index(self.get_id())

    def get_score(self):
        if self.get_start_date() is None:
            return 0
        now = datetime.datetime.now()
        # set timezone to self.get_start_date() timezone
        now = now.astimezone(self.get_start_date().astimezone().tzinfo)
        days_past = (now - self.get_start_date()).days

        days_duration = (self.get_end_date() - self.get_start_date()).days
        if days_duration == 0:
            days_duration = 0.1

        minutes_duration = (self.get_end_date() - self.get_start_date()).total_seconds() / 60
        if minutes_duration == 0:
            minutes_duration = 0.1

        score = ((days_past + 2) / (days_duration * self.get_insurance_rate() * ((self.get_project_tasks_index() + 1)/self.get_project_tasks_count()))) + 1 / (minutes_duration/60/24+1)
        return score

    def get_determined_end_date(self):
        if self.get_end_date() is None:
            return None
        duration_minutes = (self.get_end_date() - self.get_start_date()).total_seconds() / 60
        duration_minutes = duration_minutes * self.get_insurance_rate()
        duration_minutes = duration_minutes * ((self.get_project_tasks_index() + 1)/self.get_project_tasks_count())
        return self.get_start_date() + datetime.timedelta(minutes=duration_minutes)


    def mark_as_completed_in_google_calendar(self):
        completed_record = self.main.mongo["scheduleAutoManager"]["completed_tasks"].find_one({"taskId": self.get_id()})
        status = None
        if completed_record is not None:
            status = completed_record["status"]

        if status == "完了":
            return

        if self.get_status() != "完了":
            return

        self.main.mongo["scheduleAutoManager"]["completed_tasks"].update_one({"taskId": self.get_id()}, {"$set": {"status": "完了", "name": self.get_name(), "datetime": datetime.datetime.now()}}, upsert=True)
        print("marking as completed in google calendar", self.get_name())
        self.main.google_calendar_manager.create_calendar_schedule(
            self.main.google_calendar_manager.get_calendar_id("marker"),
            self.get_name(),
            datetime.datetime.now() - datetime.timedelta(minutes=1),
            1,
            self.get_id() + "-google-calendar-marker"
        )
