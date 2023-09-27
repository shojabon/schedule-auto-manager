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
