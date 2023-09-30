from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ScheduleAutoManager import ScheduleAutoManager


class FlexTask:

    def __init__(self, data: dict, main: ScheduleAutoManager):
        self.data = data
        self.main = main

    def get_id(self):
        return self.data["id"]

    def get_name(self) -> str:
        return str(self.data["properties"]["名前"]["title"][0]["text"]["content"])

    def get_date_data(self):
        return self.data["properties"]["日付"]["date"]

    def get_start_date(self):
        if self.get_date_data()["start"] is None:
            return None
        return datetime.datetime.fromisoformat(self.get_date_data()["start"])

    def get_end_date(self):
        if self.get_date_data()["end"] is None:
            return self.get_start_date()
        return datetime.datetime.fromisoformat(self.get_date_data()["end"])

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
