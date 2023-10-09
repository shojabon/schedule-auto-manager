from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ScheduleAutoManager import ScheduleAutoManager


class GoogleCalendarFixedTask:

    def __init__(self, data: dict, main: ScheduleAutoManager):
        self.main = main
        self.data = data


