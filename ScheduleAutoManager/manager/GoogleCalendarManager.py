from __future__ import annotations

import datetime
from typing import TYPE_CHECKING

import google
from googleapiclient.discovery import build
from tqdm import tqdm

if TYPE_CHECKING:
    from ScheduleAutoManager import ScheduleAutoManager


class GoogleCalendarManager:

    def __init__(self, main: ScheduleAutoManager):
        self.main = main
        credentials, project = google.auth.load_credentials_from_file('config/mat-project-341415-7328c1f3e2c8.json',
                                                                      scopes=[
                                                                          'https://www.googleapis.com/auth/calendar'])

        self.service = build('calendar', 'v3', credentials=credentials)

        # self.update_all_databases()
        # self.create_calendar_schedule(calendar_id="shojabon@gmail.com", name="test2", start=datetime.datetime.now() + datetime.timedelta(minutes=30), duration=30, unique_id="testa")
        # self.delete_calendar_schedule(calendar_id="shojabon@gmail.com", unique_id="testa")
        # self.update_database("shojabon@gmail.com")
        # self.delete_calendar_schedule(calendar_id="shojabon@gmail.com", event_id="jmvhiqsroua6imc9c1icgcs1jk")
    def update_database(self, calendar_id: str, page_token: str = None, page_size: int = 25):
        min_updated_time = datetime.datetime.now() - datetime.timedelta(days=10)
        min_updated_time_rfc3339 = min_updated_time.isoformat()+"-09:00"
        query_result = self.service.events().list(calendarId=calendar_id,
                                                  singleEvents=True,
                                                  orderBy="updated",
                                                  maxResults=page_size,
                                                  pageToken=page_token,
                                                  showDeleted=True,
                                                  updatedMin=min_updated_time_rfc3339
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

    def update_all_databases(self):
        for calendar_id in tqdm(self.main.config["googleCalendar"]["calendarMap"].values(), desc="Updating Google Calendar"):
            self.update_database(calendar_id=calendar_id)

    def create_calendar_schedule(self, calendar_id: str, name: str, start: datetime.datetime, duration: int, unique_id: str = None):
        if unique_id is not None:
            result = self.main.mongo["scheduleAutoManager"]["google_calendar_unique_ids"].find_one({"unique_id": unique_id})
            if result is not None:
                self.delete_calendar_schedule(calendar_id=calendar_id, event_id=result["event_id"])
        end = start + datetime.timedelta(minutes=duration)
        event = {
            'summary': name,
            'start': {
                'dateTime': start.isoformat(),
                'timeZone': 'Asia/Tokyo',
            },
            'end': {
                'dateTime': end.isoformat(),
                'timeZone': 'Asia/Tokyo',
            },
        }
        event = self.service.events().insert(calendarId=calendar_id, body=event).execute()
        self.main.mongo["scheduleAutoManager"]["google_calendar_tasks"].update_one({"id": event["id"]}, {"$set": event}, upsert=True)
        if unique_id is not None:
            self.main.mongo["scheduleAutoManager"]["google_calendar_unique_ids"].update_one({"unique_id": unique_id}, {"$set": {"unique_id": unique_id,"event_id": event["id"]}}, upsert=True)

    def delete_calendar_schedule(self, calendar_id: str, event_id: str=None, unique_id: str = None):
        if unique_id is not None:
            result = self.main.mongo["scheduleAutoManager"]["google_calendar_unique_ids"].find_one({"unique_id": unique_id})
            if result is not None:
                event_id = result["event_id"]
        self.service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        self.main.mongo["scheduleAutoManager"]["google_calendar_tasks"].update_one({"id": event_id}, {"$set": {"status": "cancelled"}}, upsert=True)
        if unique_id is not None:
            self.main.mongo["scheduleAutoManager"]["google_calendar_unique_ids"].delete_one({"unique_id": unique_id})

    def get_calendar_id(self, alias: str):
        if alias not in self.main.config["googleCalendar"]["calendarMap"]:
            raise ValueError(f"Calendar alias {alias} not found")
        return self.main.config["googleCalendar"]["calendarMap"][alias]

