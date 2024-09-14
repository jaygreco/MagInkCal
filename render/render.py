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
                datetime_str = '12{}am'.format(datetime_str)
            elif datetimeObj.hour == 12:
                datetime_str = '12{}pm'.format(datetime_str)
            elif datetimeObj.hour > 12:
                datetime_str = '{}{}pm'.format(str(datetimeObj.hour % 12), datetime_str)
            else:
                datetime_str = '{}{}am'.format(str(datetimeObj.hour), datetime_str)
        return datetime_str

    def process_inputs(self, calDict):
        # calDict = {'events': eventList, 'calStartDate': calStartDate, 'today': currDate, 'lastRefresh': currDatetime, 'batteryLevel': batteryLevel}
        # first setup list to represent the 5 weeks in our calendar
        calList = []
        for i in range(35):
            calList.append([])

        # retrieve calendar configuration
        maxEventsPerDay = calDict['maxEventsPerDay']
        batteryDisplayMode = calDict['batteryDisplayMode']
        dayOfWeekText = calDict['dayOfWeekText']
        weekStartDay = calDict['weekStartDay']
        is24hour = calDict['is24hour']

        # for each item in the eventList, add them to the relevant day in our calendar list
        for event in calDict['events']:
            idx = self.get_day_in_cal(calDict['calStartDate'], event['startDatetime'].date())
            if idx >= 0:
                calList[idx].append(event)
            if event['isMultiday']:
                idx = self.get_day_in_cal(calDict['calStartDate'], event['endDatetime'].date())
                if idx < len(calList):
                    calList[idx].append(event)

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
        cal_days_of_week = ''
        for i in range(0, 7):
            cal_days_of_week += '<li class="font-weight-bold text-uppercase">' + dayOfWeekText[
                (i + weekStartDay) % 7] + "</li>\n"

        # Populate the date and events
        cal_events_text = ''
        for i in range(len(calList)):
            currDate = calDict['calStartDate'] + timedelta(days=i)
            dayOfMonth = currDate.day
            if currDate == calDict['today']:
                cal_events_text += '<li><div class="datecircle">' + str(dayOfMonth) + '</div>\n'
            elif currDate.month != calDict['today'].month:
                cal_events_text += '<li><div class="date text-muted">' + str(dayOfMonth) + '</div>\n'
            else:
                cal_events_text += '<li><div class="date">' + str(dayOfMonth) + '</div>\n'

            for j in range(min(len(calList[i]), maxEventsPerDay)):
                event = calList[i][j]
                cal_events_text += '<div class="event'
                if event['isUpdated']:
                    cal_events_text += ' text-danger'
                elif currDate.month != calDict['today'].month:
                    cal_events_text += ' text-muted'
                if event['isMultiday']:
                    if event['startDatetime'].date() == currDate:
                        cal_events_text += '">►' + event['summary']
                    else:
                        # calHtmlList.append(' text-multiday">')
                        cal_events_text += '">◄' + event['summary']
                elif event['allday']:
                    cal_events_text += '">' + event['summary']
                else:
                    cal_events_text += '">' + self.get_short_time(event['startDatetime'], is24hour) + ' ' + event[
                        'summary']
                cal_events_text += '</div>\n'
            if len(calList[i]) > maxEventsPerDay:
                cal_events_text += '<div class="event text-muted">' + str(len(calList[i]) - maxEventsPerDay) + ' more'

            cal_events_text += '</li>\n'

        # Append the bottom and write the file
        htmlFile = open(self.currPath + '/calendar.html', "w")
        htmlFile.write(calendar_template.format(month=month_name, battText=battText, dayOfWeek=cal_days_of_week,
                                                events=cal_events_text))
        htmlFile.close()

        self.get_screenshot(f"file://{self.currPath}/calendar.html", f"{self.currPath}/calendar.png")

        # TODO: hacky test
        resize_image(f"{self.currPath}/calendar.png", 768, 960)

        # TODO:
        # return calBlackImage, calRedImage
        return ([], [])

if __name__ == "__main__":
    import pickle

    events = pickle.loads(b'\x80\x04\x95\x0b\x03\x00\x00\x00\x00\x00\x00]\x94(}\x94(\x8c\x07summary\x94\x8c"Stay at Belmont Shore Beach Studio\x94\x8c\x06allday\x94\x88\x8c\rstartDatetime\x94\x8c\x08datetime\x94\x8c\x08datetime\x94\x93\x94C\n\x07\xe8\x08\x1e\x00\x00\x00\x00\x00\x00\x94\x8c\x04pytz\x94\x8c\x02_p\x94\x93\x94(\x8c\x13America/Los_Angeles\x94J\x90\x9d\xff\xffM\x10\x0e\x8c\x03PDT\x94t\x94R\x94\x86\x94R\x94\x8c\x0bendDatetime\x94h\x08C\n\x07\xe8\t\x02\x17;;\x0fB?\x94h\x10\x86\x94R\x94\x8c\x0fupdatedDatetime\x94h\x08C\n\x07\xe8\t\x02\x0b\x024\x08\xb6x\x94h\x10\x86\x94R\x94\x8c\tisUpdated\x94\x89\x8c\nisMultiday\x94\x88u}\x94(h\x02\x8c\rCSA Fruit Box\x94h\x04\x89h\x05h\x08C\n\x07\xe8\t\x04\x0e\x1e\x00\x00\x00\x00\x94h\x10\x86\x94R\x94h\x13h\x08C\n\x07\xe8\t\x04\x0e\x1e\x00\x00\x00\x00\x94h\x10\x86\x94R\x94h\x17h\x08C\n\x07\xe8\x04\x15\x15\x16&\x06\x06\xf8\x94h\x10\x86\x94R\x94h\x1b\x89h\x1c\x89u}\x94(h\x02\x8c\rCSA Fruit Box\x94h\x04\x89h\x05h\x08C\n\x07\xe8\t\x0b\x0e\x1e\x00\x00\x00\x00\x94h\x10\x86\x94R\x94h\x13h\x08C\n\x07\xe8\t\x0b\x0e\x1e\x00\x00\x00\x00\x94h\x10\x86\x94R\x94h\x17h\x08C\n\x07\xe8\x04\x15\x15\x16&\x06\x06\xf8\x94h\x10\x86\x94R\x94h\x1b\x89h\x1c\x89u}\x94(h\x02\x8c\rCSA Fruit Box\x94h\x04\x89h\x05h\x08C\n\x07\xe8\t\x12\x0e\x1e\x00\x00\x00\x00\x94h\x10\x86\x94R\x94h\x13h\x08C\n\x07\xe8\t\x12\x0e\x1e\x00\x00\x00\x00\x94h\x10\x86\x94R\x94h\x17h\x08C\n\x07\xe8\x04\x15\x15\x16&\x06\x06\xf8\x94h\x10\x86\x94R\x94h\x1b\x89h\x1c\x89u}\x94(h\x02\x8c\rCSA Fruit Box\x94h\x04\x89h\x05h\x08C\n\x07\xe8\t\x19\x0e\x1e\x00\x00\x00\x00\x94h\x10\x86\x94R\x94h\x13h\x08C\n\x07\xe8\t\x19\x0e\x1e\x00\x00\x00\x00\x94h\x10\x86\x94R\x94h\x17h\x08C\n\x07\xe8\x04\x15\x15\x16&\x06\x06\xf8\x94h\x10\x86\x94R\x94h\x1b\x89h\x1c\x89u}\x94(h\x02\x8c\rCSA Fruit Box\x94h\x04\x89h\x05h\x08C\n\x07\xe8\n\x02\x0e\x1e\x00\x00\x00\x00\x94h\x10\x86\x94R\x94h\x13h\x08C\n\x07\xe8\n\x02\x0e\x1e\x00\x00\x00\x00\x94h\x10\x86\x94R\x94h\x17h\x08C\n\x07\xe8\x04\x15\x15\x16&\x06\x06\xf8\x94h\x10\x86\x94R\x94h\x1b\x89h\x1c\x89ue.')
    calDict = {'events': [], 'calStartDate': date(2024, 9, 1), 'today': date(2024, 9, 1), 
                    'lastRefresh': datetime(2024, 9, 1, 0, 1, 0, 0),
                    'batteryLevel': 100, 'batteryDisplayMode': 0, 'dayOfWeekText': ["M", "T", "W", "T", "F", "S", "S"],
                    'weekStartDay': 6, 'maxEventsPerDay': 0,'is24hour': False}

    renderService = RenderHelper(768, 960, 90)
    calBlackImage, calRedImage = renderService.process_inputs(calDict)
