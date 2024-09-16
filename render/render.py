#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This script essentially generates a HTML file of the calendar I wish to display. It then fires cutycapt using xvfb
sized to the resolution of the eInk display and takes a screenshot. This screenshot will then be processed
to extract the grayscale and red portions, which are then sent to the eInk display for updating.

This might sound like a convoluted way to generate the calendar, but I'm doing so mainly because (i) it's easier to
format the calendar exactly the way I want it using HTML/CSS, and (ii) I can better delink the generation of the
calendar and refreshing of the eInk display. In the future, I might choose to generate the calendar on a separate
RPi device, while using a ESP32 or PiZero purely to just retrieve the image from a file host and update the screen.
"""

# TODO: sort
# TODO: this doesn't quite work when doing nested imports
# Add root to path so modules in the parent directory are accessible
import sys
import os
here = os.path.dirname(__file__)
sys.path.append(os.path.join(here, '..'))

from time import sleep
from datetime import timedelta, datetime, date
from epd_hidapi.host.image import resize_image, extract_image
from template import template as t
import pathlib
import logging
import shutil
from subprocess import call


class RenderHelper:
    def __init__(self, width, height, angle):
        self.logger = logging.getLogger('maginkcal')
        self.currPath = str(pathlib.Path(__file__).parent.absolute())
        self.imageWidth = width
        self.imageHeight = height
        self.rotateAngle = angle

    def get_screenshot(self, uri, outfile):
        # Yeah, I know. subprocess.call() with shell=True is bad, but this
        # isn't open to the internet and I control all the inputs.
        # TODO: adapt this for panel size, also dealing with the CSS file
        call(f"xvfb-run --server-args='-screen 0, 768x960x24' \
        cutycapt --url={uri} --min-width=768 --min-height=960 \
        --out={outfile} ", shell=True)

        self.logger.info('Screenshot captured and saved to file.')

    def get_day_in_cal(self, startDate, eventDate):
        delta = eventDate - startDate
        return delta.days

    def get_short_time(self, datetimeObj, is24hour=False):
        datetime_str = ''
        if is24hour:
            datetime_str = '{}:{:02d}'.format(datetimeObj.hour, datetimeObj.minute)
        else:
            if datetimeObj.minute > 0:
                datetime_str = '.{:02d}'.format(datetimeObj.minute)

            if datetimeObj.hour == 0:
                datetime_str = '12{}A'.format(datetime_str)
            elif datetimeObj.hour == 12:
                datetime_str = '12{}P'.format(datetime_str)
            elif datetimeObj.hour > 12:
                datetime_str = '{}{}P'.format(str(datetimeObj.hour % 12), datetime_str)
            else:
                datetime_str = '{}{}A'.format(str(datetimeObj.hour), datetime_str)
        return datetime_str

    def process_inputs(self, calDict):
        # calDict = {'events': eventList, 'calStartDate': calStartDate, 'today': currDate, 'lastRefresh': currDatetime, 'batteryLevel': batteryLevel}

        # retrieve calendar configuration
        # TODO: why pass these instead of loading them directly?
        maxEventsPerDay = calDict['maxEventsPerDay']
        batteryDisplayMode = calDict['batteryDisplayMode']
        dayOfWeekText = calDict['dayOfWeekText']
        weekStartDay = calDict['weekStartDay']
        is24hour = calDict['is24hour']

        # TODO: there is a better way to do this
        # first setup list to represent the 5 weeks in our calendar
        calList = []
        for i in range(35):
            calList.append([])

        # for each item in the eventList, add them to the relevant day in our calendar list
        for event in calDict['events']:
            idx = self.get_day_in_cal(calDict['calStartDate'], event['startDatetime'].date())
            if idx >= 0:
                calList[idx].append(event)
            if event['isMultiday']:
                idx = self.get_day_in_cal(calDict['calStartDate'], event['endDatetime'].date())
                if idx < len(calList):
                    calList[idx].append(event)

        # TODO: extract today's events as well

        # TODO: debug
        # from pprint import pprint
        # pprint(event_list)

        # Read html template
        with open(self.currPath + '/calendar_template.html', 'r') as file:
            calendar_template = file.read()

        # Insert month header
        month_name = str(calDict['today'].month)

        # Insert battery icon
        # batteryDisplayMode - 0: do not show / 1: always show / 2: show when battery is low
        battLevel = calDict['batteryLevel']

        if batteryDisplayMode == 0:
            battText = 'batteryHide'
        elif batteryDisplayMode == 1:
            if battLevel >= 80:
                battText = 'battery80'
            elif battLevel >= 60:
                battText = 'battery60'
            elif battLevel >= 40:
                battText = 'battery40'
            elif battLevel >= 20:
                battText = 'battery20'
            else:
                battText = 'battery0'

        elif batteryDisplayMode == 2 and battLevel < 20.0:
            battText = 'battery0'
        elif batteryDisplayMode == 2 and battLevel >= 20.0:
            battText = 'batteryHide'

        # Populate the day of week row
        l = []
        for d in range(0, 7):
            l.append(t('li', c='font-weight-bold text-uppercase', body=dayOfWeekText[(d + weekStartDay) % 7]))
        cal_days_of_week = '\n'.join(l)

        # Populate the date and events
        cal_events = []
        todays_events = []
        for i, entry in enumerate(calList):
            # TODO: can we do this without i? maybe?
            currDate = calDict['calStartDate'] + timedelta(days=i)
            dayOfMonth = currDate.day

            text_style = ""
            badge_style = "badge-dark"

            if currDate == calDict['today']:
                c = "datecircle"
            elif currDate.month != calDict['today'].month:
                text_style = "text-muted"
                badge_style = "badge-light"
                c = f"date {text_style}"
            else:
                c = "date"

            events = []
            for event in entry:
                event_time = self.get_short_time(event['startDatetime'], is24hour)
                # TODO: clever way to apply styles?

                if event['isUpdated']:
                    text_style = "text-danger"
                    badge_style = "badge-danger"

                if event['isMultiday'] and event['startDatetime'].date() == currDate:
                    event_summary = t('b', body="&rarr;") + event['summary']
                elif event['isMultiday']and event['startDatetime'].date() != currDate:
                    event_summary = t('b', body="&larr;") + event['summary']
                else:
                    event_summary = event['summary']

                time_badge = "" if event['allday'] else t('span', c=f'badge {badge_style}', body=event_time)
                events.append(
                    t('div', c=f'event {text_style}', body=(
                        time_badge, " ", 
                        t('i', body=event_summary)
                        )
                    )
                )

            # Remove events above the maximum and add "+x more"
            if len(events) > maxEventsPerDay:
                event_summary = f"+{len(events) - maxEventsPerDay} more..."
                events = events[:maxEventsPerDay]
                events.append(
                    t('div', c='event text-muted', body=(t('i', body=event_summary)))
                )

            # Add the day's events
            cal_events.append(
                t('li', body=(
                    t('div', c=c, body=dayOfMonth),
                    "".join(events)
                    )
                )
            )

            if currDate == calDict['today']:
                # Also add to today's events
                todays_events = events

        # Join is faster/more memory efficient than += for strings
        cal_events_text = '\n'.join(cal_events)

        # Append the bottom and write the file
        htmlFile = open(self.currPath + '/calendar.html', "w")
        htmlFile.write(calendar_template.format(month=month_name,
            battText=battText, days_of_week=cal_days_of_week,
            events_month=cal_events_text, events_today="\n".join(todays_events)))
        htmlFile.close()

        self.get_screenshot(f"file://{self.currPath}/calendar.html", f"{self.currPath}/calendar.png")

        # TODO: hacky test -- clip pixels after resizing to nearest instead
        resize_image(f"{self.currPath}/calendar.png", 768, 960)

        # TODO:
        # return calBlackImage, calRedImage
        return ([], [])

if __name__ == "__main__":
    import pickle

    events = pickle.loads(b'\x80\x04\x95\x0b\x03\x00\x00\x00\x00\x00\x00]\x94(}\x94(\x8c\x07summary\x94\x8c"Stay at Belmont Shore Beach Studio\x94\x8c\x06allday\x94\x88\x8c\rstartDatetime\x94\x8c\x08datetime\x94\x8c\x08datetime\x94\x93\x94C\n\x07\xe8\x08\x1e\x00\x00\x00\x00\x00\x00\x94\x8c\x04pytz\x94\x8c\x02_p\x94\x93\x94(\x8c\x13America/Los_Angeles\x94J\x90\x9d\xff\xffM\x10\x0e\x8c\x03PDT\x94t\x94R\x94\x86\x94R\x94\x8c\x0bendDatetime\x94h\x08C\n\x07\xe8\t\x02\x17;;\x0fB?\x94h\x10\x86\x94R\x94\x8c\x0fupdatedDatetime\x94h\x08C\n\x07\xe8\t\x02\x0b\x024\x08\xb6x\x94h\x10\x86\x94R\x94\x8c\tisUpdated\x94\x89\x8c\nisMultiday\x94\x88u}\x94(h\x02\x8c\rCSA Fruit Box\x94h\x04\x89h\x05h\x08C\n\x07\xe8\t\x04\x0e\x1e\x00\x00\x00\x00\x94h\x10\x86\x94R\x94h\x13h\x08C\n\x07\xe8\t\x04\x0e\x1e\x00\x00\x00\x00\x94h\x10\x86\x94R\x94h\x17h\x08C\n\x07\xe8\x04\x15\x15\x16&\x06\x06\xf8\x94h\x10\x86\x94R\x94h\x1b\x89h\x1c\x89u}\x94(h\x02\x8c\rCSA Fruit Box\x94h\x04\x89h\x05h\x08C\n\x07\xe8\t\x0b\x0e\x1e\x00\x00\x00\x00\x94h\x10\x86\x94R\x94h\x13h\x08C\n\x07\xe8\t\x0b\x0e\x1e\x00\x00\x00\x00\x94h\x10\x86\x94R\x94h\x17h\x08C\n\x07\xe8\x04\x15\x15\x16&\x06\x06\xf8\x94h\x10\x86\x94R\x94h\x1b\x89h\x1c\x89u}\x94(h\x02\x8c\rCSA Fruit Box\x94h\x04\x89h\x05h\x08C\n\x07\xe8\t\x12\x0e\x1e\x00\x00\x00\x00\x94h\x10\x86\x94R\x94h\x13h\x08C\n\x07\xe8\t\x12\x0e\x1e\x00\x00\x00\x00\x94h\x10\x86\x94R\x94h\x17h\x08C\n\x07\xe8\x04\x15\x15\x16&\x06\x06\xf8\x94h\x10\x86\x94R\x94h\x1b\x89h\x1c\x89u}\x94(h\x02\x8c\rCSA Fruit Box\x94h\x04\x89h\x05h\x08C\n\x07\xe8\t\x19\x0e\x1e\x00\x00\x00\x00\x94h\x10\x86\x94R\x94h\x13h\x08C\n\x07\xe8\t\x19\x0e\x1e\x00\x00\x00\x00\x94h\x10\x86\x94R\x94h\x17h\x08C\n\x07\xe8\x04\x15\x15\x16&\x06\x06\xf8\x94h\x10\x86\x94R\x94h\x1b\x89h\x1c\x89u}\x94(h\x02\x8c\rCSA Fruit Box\x94h\x04\x89h\x05h\x08C\n\x07\xe8\n\x02\x0e\x1e\x00\x00\x00\x00\x94h\x10\x86\x94R\x94h\x13h\x08C\n\x07\xe8\n\x02\x0e\x1e\x00\x00\x00\x00\x94h\x10\x86\x94R\x94h\x17h\x08C\n\x07\xe8\x04\x15\x15\x16&\x06\x06\xf8\x94h\x10\x86\x94R\x94h\x1b\x89h\x1c\x89ue.')
    # duplicate last event for testing
    events.append(events[-1])
    events.append(events[-1])
    events.append(events[-1])
    # TODO: an object here makes more sense than a dict?
    calDict = {'events': events, 'calStartDate': date(2024, 9, 1),
                'today': date(2024, 9, 2), 
                'lastRefresh': datetime(2024, 9, 1, 0, 1, 0, 0),
                'batteryLevel': 100, 'batteryDisplayMode': 0,
                'dayOfWeekText': ["M", "T", "W", "T", "F", "S", "S"],
                'weekStartDay': 6, 'maxEventsPerDay': 3, 'is24hour': False}

    renderService = RenderHelper(768, 960, 90)
    calBlackImage, calRedImage = renderService.process_inputs(calDict)
