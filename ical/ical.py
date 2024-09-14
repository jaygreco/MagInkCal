#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This is where we retrieve events from the iCloud Calendar. Before doing so, make sure you have both the
credentials.json in the same folder as this file.
"""

import datetime as dt
import icalevents.icalevents as ical
import json
import os.path
import pathlib
import logging


class IcalHelper:

    def __init__(self):
        self.logger = logging.getLogger('maginkcal')
        # Initialise the Google Calendar using the provided credentials and token
        SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']
        self.currPath = str(pathlib.Path(__file__).parent.absolute())

        creds = None
        if os.path.exists(self.currPath + '/credentials.json'):
            with open(self.currPath + '/credentials.json', 'rb') as fo:
                creds = json.load(fo)

        self.calendars = creds.get("calendars", [])

    def list_calendars(self):
        # helps to retrieve ID for calendars within the account
        # calendar IDs added to config.json will then be queried for retrieval of events
        if not self.calendars:
            self.logger.info('No calendars found.')
        for calendar in self.calendars:
            summary = calendar['summary']
            cal_id = calendar['id']
            self.logger.info("%s\t%s" % (summary, cal_id))

    def to_datetime(self, isoDatetime, localTZ):
        # replace Z with +00:00 is a workaround until datetime library decides what to do with the Z notation
        toDatetime = dt.datetime.fromisoformat(isoDatetime.replace('Z', '+00:00'))
        return toDatetime.astimezone(localTZ)

    def is_recent_updated(self, updatedTime, thresholdHours):
        # consider events updated within the past X hours as recently updated
        utcnow = dt.datetime.now(dt.timezone.utc)
        diff = (utcnow - updatedTime).total_seconds() / 3600  # get difference in hours
        return diff < thresholdHours

    def adjust_end_time(self, endTime, localTZ):
        # check if end time is at 00:00 of next day, if so set to max time for day before
        if endTime.hour == 0 and endTime.minute == 0 and endTime.second == 0:
            newEndtime = localTZ.localize(
                dt.datetime.combine(endTime.date() - dt.timedelta(days=1), dt.datetime.max.time()))
            return newEndtime
        else:
            return endTime

    def is_multiday(self, start, end):
        # check if event stretches across multiple days
        return start.date() != end.date()

    def map_keys(self, key_map, d):
        for old_key, new_key in key_map:
            d[new_key] = d.pop(old_key)

        return d


    def retrieve_events(self, startDatetime, endDatetime, localTZ, thresholdHours):
        # Call the Google Calendar API and return a list of events that fall within the specified dates
        eventList = []

        minTimeStr = startDatetime.isoformat()
        maxTimeStr = endDatetime.isoformat()

        self.logger.info('Retrieving events between ' + minTimeStr + ' and ' + maxTimeStr + '...')
        events_result = []
        for cal in self.calendars:
            events_result.extend(
                ical.events(url=cal["id"], 
                    start=startDatetime, end=endDatetime,
                    fix_apple=True, sort=True, tzinfo=displayTZ)
                )

        key_map = [
            ("all_day", "allday"),
            ("end", "endDatetime"),
            ("start", "startDatetime"),
            ("last_modified", "updatedDatetime")
        ]
        events = [self.map_keys(key_map, vars(e)) for e in events_result]

        if not events:
            self.logger.info('No upcoming events found.')

        for event in events:
            event['endDatetime'] = self.adjust_end_time(event['endDatetime'], localTZ)
            event['isUpdated'] = self.is_recent_updated(event['updatedDatetime'], thresholdHours)
            event['isMultiday'] = self.is_multiday(event['startDatetime'], event['endDatetime'])

         #Sort eventList because the event will be sorted in "calendar order" instead of hours order
        return sorted(events, key=lambda k: k['startDatetime'])

if __name__ == "__main__":
    from pprint import pprint
    from pytz import timezone

    displayTZ = timezone("America/Los_Angeles")
    thresholdHours = 24
    calStartDate = dt.date(2024, 9, 1)
    calEndDate = calStartDate + dt.timedelta(days=(5 * 7 - 1))
    calStartDatetime = displayTZ.localize(dt.datetime.combine(calStartDate, dt.datetime.min.time()))
    calEndDatetime = displayTZ.localize(dt.datetime.combine(calEndDate, dt.datetime.max.time()))

    icalService = IcalHelper()
    eventList = icalService.retrieve_events(calStartDatetime, 
        calEndDatetime, displayTZ, thresholdHours)

    pprint(eventList)