#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This is where we retrieve events from the iCloud Calendar. Before doing so, make sure you have both the
credentials.json in the same folder as this file.
"""

import datetime as dt
import logging
import os.path
import pathlib
import pytz

import icalevents.icalevents as ical


class IcalHelper:

    def __init__(self, calendars):
        self.logger = logging.getLogger(__name__)
        self.currPath = str(pathlib.Path(__file__).parent.absolute())
        self.calendars = calendars

    def list_calendars(self):
        # helps to retrieve ID for calendars within the account
        # calendar IDs added to config.json will then be queried for retrieval of events
        if not self.calendars:
            self.logger.info('No calendars found.')
        for calendar in self.calendars:
            summary = calendar['summary']
            cal_id = calendar['id']
            self.logger.info("%s\t%s" % (summary, cal_id))

    def is_recent_updated(self, event, thresholdHours):
        # consider events updated within the past X hours as recently updated
        utcnow = dt.datetime.now(dt.timezone.utc)
        diff = (utcnow - event['updatedDatetime']).total_seconds() / 3600
        event['isUpdated'] = diff < thresholdHours

        return event

    def normalize_allday_time(self, event, localTZ):
        if event['allday']:
            utc_start = event['startDatetime'].astimezone(pytz.utc)
            utc_end = event['endDatetime'].astimezone(pytz.utc)

            # check if end time is at 00:00 of next day, if so set to max time for day before
            if utc_end.hour == 0 and utc_end.minute == 0 and utc_end.second == 0:
                newEndtime = dt.datetime.combine(utc_end.date() - dt.timedelta(days=1), dt.datetime.max.time())
                utc_end = newEndtime

            event['startDatetime'] = utc_start.replace(tzinfo=localTZ)
            event['endDatetime'] = utc_end.replace(tzinfo=localTZ)

        return event

    def is_multiday(self, event):
        # check if event stretches across multiple days
        event['isMultiday'] = event['startDatetime'].date() != event['endDatetime'].date()

        return event

    def map_keys(self, key_map, d):
        for old_key, new_key in key_map:
            d[new_key] = d.pop(old_key)
        return d

    def retrieve_events(self, startDatetime, endDatetime, localTZ, thresholdHours):
        # Call the Google Calendar API and return a list of events that fall within the specified dates
        eventList = []

        minTimeStr = startDatetime.isoformat()
        maxTimeStr = endDatetime.isoformat()

        self.logger.info('Retrieving events between ' +
                         minTimeStr + ' and ' + maxTimeStr + '...')
        events_result = []
        for cal in self.calendars:
            events_result.extend(
                ical.events(url=cal["id"],
                            start=startDatetime, end=endDatetime,
                            fix_apple=True, sort=True, tzinfo=localTZ)
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
            # Floating (all-day) events are always in UTC, which should be converted to the local time
            # i.e. UTC 00:00 --> PST 00:00
            event = self.normalize_allday_time(event, localTZ)
            event = self.is_recent_updated(event, thresholdHours)
            event = self.is_multiday(event)

         # Sort eventList because the event will be sorted in "calendar order" instead of hours order
        return sorted(events, key=lambda k: k['startDatetime'])


if __name__ == "__main__":
    import os
    import sys
    here = os.path.dirname(__file__)
    sys.path.append(os.path.join(here, '..'))

    from pprint import pprint
    from pytz import timezone
    from config import Config

    config = Config()
    logging.basicConfig(level=logging.INFO)

    displayTZ = timezone(config.displayTZ)
    calStartDate = dt.date(2024, 9, 1)
    calEndDate = calStartDate + dt.timedelta(days=(5 * 7 - 1))
    calStartDatetime = displayTZ.localize(
        dt.datetime.combine(calStartDate, dt.datetime.min.time()))
    calEndDatetime = displayTZ.localize(
        dt.datetime.combine(calEndDate, dt.datetime.max.time()))

    icalService = IcalHelper(calendars=config.get("calendars", []))
    eventList = icalService.retrieve_events(calStartDatetime,
                                            calEndDatetime, displayTZ, config.thresholdHours)

    pprint(eventList)
