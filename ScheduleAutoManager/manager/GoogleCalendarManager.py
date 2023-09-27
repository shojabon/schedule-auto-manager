from __future__ import annotations
from typing import TYPE_CHECKING

import google
from googleapiclient.discovery import build

if TYPE_CHECKING:
    from ScheduleAutoManager import ScheduleAutoManager


class GoogleCalendarManager:

    def __init__(self, main: ScheduleAutoManager):
        self.main = main
        credentials, project = google.auth.load_credentials_from_file('config/mat-project-341415-7328c1f3e2c8.json',
                                                                      scopes=[
                                                                          'https://www.googleapis.com/auth/calendar'])

        self.service = build('calendar', 'v3', credentials=credentials)

    def update_database(self, calendar_id: str, page_token: str = None, page_size: int = 25):
        query_result = self.service.events().list(calendarId=calendar_id,
                                                  singleEvents=True,
                                                  orderBy='updated',
                                                  maxResults=page_size,
                                                  pageToken=page_token,
                                                  ).execute()

        results = query_result["items"]
        #
        updated_tasks = []
        for task in results:
            mongo_push_result = self.main.mongo["scheduleAutoManager"]["google_calendar_tasks"].update_one({"id": task["id"]},
                                                                                                   {"$set": task},
                                                                                                   upsert=True).raw_result
            if mongo_push_result["nModified"] == 1:
                updated_tasks.append(True)
            elif "upserted" in mongo_push_result:
                updated_tasks.append(True)
            else:
                updated_tasks.append(False)
        #
        # # if last page is updated, recursively update
        if len(results) == page_size and updated_tasks[-1]:
            self.update_database(calendar_id=calendar_id, page_token=query_result.get("nextPageToken"), page_size=page_size)