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

    def __init__(self, calendars):
        self.logger = logging.getLogger('maginkcal')
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
            if event['allday'] is True:
                # Force start and end times to be the same
                event['startDatetime'] = event['endDatetime']
            event['endDatetime'] = self.adjust_end_time(event['endDatetime'], localTZ)
            event['isUpdated'] = self.is_recent_updated(event['updatedDatetime'], thresholdHours)
            event['isMultiday'] = self.is_multiday(event['startDatetime'], event['endDatetime'])

         #Sort eventList because the event will be sorted in "calendar order" instead of hours order
        return sorted(events, key=lambda k: k['startDatetime'])

if __name__ == "__main__":
    import sys
    import os
    here = os.path.dirname(__file__)
    sys.path.append(os.path.join(here, '..'))

    from config import Config
    from pprint import pprint
    from pytz import timezone

    config = Config()

    displayTZ = timezone(config.displayTZ)
    calStartDate = dt.date(2024, 9, 1)
    calEndDate = calStartDate + dt.timedelta(days=(5 * 7 - 1))
    calStartDatetime = displayTZ.localize(dt.datetime.combine(calStartDate, dt.datetime.min.time()))
    calEndDatetime = displayTZ.localize(dt.datetime.combine(calEndDate, dt.datetime.max.time()))

    icalService = IcalHelper(calendars=config.get("calendars", []))
    eventList = icalService.retrieve_events(calStartDatetime, 
        calEndDatetime, displayTZ, config.thresholdHours)

    pprint(eventList)
