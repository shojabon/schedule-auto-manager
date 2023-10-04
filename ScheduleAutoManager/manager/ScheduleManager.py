from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ScheduleAutoManager import ScheduleAutoManager


class ScheduleManager:

    def __init__(self, main: ScheduleAutoManager):
        self.main = main


