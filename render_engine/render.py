#!/usr/bin/env python3

# TODO: sort, format
# Add root to path so modules in the parent directory are accessible
import sys
import os
here = os.path.dirname(__file__)
sys.path.append(os.path.join(here, '..'))

from time import sleep
from datetime import timedelta, datetime, date
from render_engine.template import template as t
from config import Config
import pathlib
import logging
import shutil
from subprocess import call

class RenderHelper:
    def __init__(self, events, start_date, today, battery_level=100):
        self.logger = logging.getLogger(__name__)
        self._path = str(pathlib.Path(__file__).parent.absolute())
        self.events = events
        self.start_date = start_date
        self.today = today
        self.battery_level = battery_level

    def get_screenshot(self, uri, outfile, width=768, height=960):
        self.logger.info('Capturing calendar screenshot')

        call(f"xvfb-run --server-args='-screen 0, {width}x{height}x24' \
        cutycapt --url={uri} --min-width={width} --min-height={height} \
        --out={outfile}", shell=True)

        self.logger.info(f"Screenshot captured and saved to {outfile}")

    def get_day_in_cal(self, start_date, event_date):
        delta = event_date - start_date
        return delta.days

    def get_short_time(self, datetime_obj, is_24hour=False):
        datetime_str = ''
        if is_24hour:
            datetime_str = '{}:{:02d}'.format(datetime_obj.hour, datetime_obj.minute)
        else:
            if datetime_obj.minute > 0:
                datetime_str = ':{:02d}'.format(datetime_obj.minute)

            if datetime_obj.hour == 0:
                datetime_str = '12{}A'.format(datetime_str)
            elif datetime_obj.hour == 12:
                datetime_str = '12{}P'.format(datetime_str)
            elif datetime_obj.hour > 12:
                datetime_str = '{}{}P'.format(str(datetime_obj.hour % 12), datetime_str)
            else:
                datetime_str = '{}{}A'.format(str(datetime_obj.hour), datetime_str)
        return datetime_str

    def build_calendar_list(self):
        calendar_list = []

        NUM_DAYS = 35
        for i in range(NUM_DAYS):
            calendar_list.append([])

        # for each item in the eventList, add them to the relevant day in our calendar list
        for event in self.events:
            day = self.get_day_in_cal(self.start_date, event['startDatetime'].date())
            if day >= 0 and day <= NUM_DAYS:
                calendar_list[day].append(event)
            if event['isMultiday']:
                day = self.get_day_in_cal(self.start_date, event['endDatetime'].date())
                if day <= NUM_DAYS:
                    calendar_list[day].append(event)

        return calendar_list

    def process_inputs(self):
        self.logger.info('Rendering calendar HTML')

        # retrieve calendar configuration
        config = Config()

        # build calendar list from events
        calendar_days = self.build_calendar_list()

        # Insert battery icon
        # batteryDisplayMode - 0: do not show / 1: always show / 2: show when battery is low
        if config.batteryDisplayMode == 0:
            battery_text = 'batteryHide'
        elif config.batteryDisplayMode == 1:
            if self.battery_level >= 80:
                battery_text = 'battery80'
            elif self.battery_level >= 60:
                battery_text = 'battery60'
            elif self.battery_level >= 40:
                battery_text = 'battery40'
            elif self.battery_level >= 20:
                battery_text = 'battery20'
            else:
                battery_text = 'battery0'
        elif config.batteryDisplayMode == 2 and self.battery_level < 20.0:
            battery_text = 'battery0'
        elif config.batteryDisplayMode == 2 and self.battery_level >= 20.0:
            battery_text = 'batteryHide'

        # Populate the day of week row
        l = []
        for d in range(0, 7):
            l.append(t('li', c='font-weight-bold text-uppercase',
                body=config.dayOfWeekText[(d + config.weekStartDay) % 7]))
        cal_days_of_week = '\n'.join(l)

        # Populate the date and events
        cal_events = []
        todays_events = []
        for i, entry in enumerate(calendar_days):
            # TODO: can we do this without i? maybe?
            current_date = self.start_date + timedelta(days=i)
            day_of_month = current_date.day

            # Set day style
            if current_date == self.today:
                c = "datecircle"
            elif current_date.month != self.today.month:
                c = "date text-muted"
            else:
                c = "date"

            events = []
            for event in entry:

                # Set event styles
                text_style = ""
                badge_style = ""

                if current_date.month != self.today.month:
                    text_style = "text-muted"
                    badge_style = "badge-light"
                elif event['isUpdated']:
                    text_style = "text-danger"
                    badge_style = "badge-danger"
                else:
                    text_style = ""
                    badge_style = "badge-dark"

                event_time = self.get_short_time(event['startDatetime'], config.is24hour)

                if event['isMultiday'] and event['startDatetime'].date() == current_date:
                    event_summary = t('b', body="&rarr;") + event['summary']
                elif event['isMultiday']and event['startDatetime'].date() != current_date:
                    event_summary = t('b', body="&larr;") + event['summary']
                else:
                    event_summary = event['summary']

                time_badge = "" if event['allday'] else t('span', c=f'badge {badge_style}', body=event_time)
                events.append(
                    t('div', c=f'event {text_style}', body=(
                        time_badge, " ", 
                        t('b', body=event_summary.encode('ascii', 'xmlcharrefreplace').decode("utf-8"))
                        )
                    )
                )

            # Remove events above the maximum and add "+x more"
            if len(events) > config.maxEventsPerDay:
                event_summary = f"+{len(events) - config.maxEventsPerDay} more..."
                events = events[:config.maxEventsPerDay]
                events.append(
                    t('div', c='event text-muted', body=(t('i', body=event_summary)))
                )

            # Add the day's events
            cal_events.append(
                t('li', body=(
                    t('div', c=c, body=day_of_month),
                    "".join(events)
                    )
                )
            )

            if current_date == self.today:
                # Also add to today's events
                todays_events = events

        # Join is faster/more memory efficient than += for strings
        cal_events_text = '\n'.join(cal_events)

        # Read html template
        with open(f"{self._path}/calendar_template.html", 'r') as fo:
            calendar_template = fo.read()

        # Append the bottom and write the file
        calendar_html = open(f"{self._path}/calendar.html", "w")
        calendar_html.write(calendar_template.format(
            date=str(f"{self.today.month}/{self.today.day}"),
            battery_text=battery_text, days_of_week=cal_days_of_week,
            events_month=cal_events_text, events_today="\n".join(todays_events)))
        calendar_html.close()

        self.get_screenshot(
            f"file://{self._path}/calendar.html",
            f"{self._path}/calendar.png",
            width=config.screenWidth,
            height=config.screenHeight
            )


if __name__ == "__main__":
    import pickle

    logging.basicConfig(level=logging.INFO)

    events = pickle.loads(b'\x80\x04\x95\x0b\x03\x00\x00\x00\x00\x00\x00]\x94(}\x94(\x8c\x07summary\x94\x8c"Stay at Belmont Shore Beach Studio\x94\x8c\x06allday\x94\x88\x8c\rstartDatetime\x94\x8c\x08datetime\x94\x8c\x08datetime\x94\x93\x94C\n\x07\xe8\x08\x1e\x00\x00\x00\x00\x00\x00\x94\x8c\x04pytz\x94\x8c\x02_p\x94\x93\x94(\x8c\x13America/Los_Angeles\x94J\x90\x9d\xff\xffM\x10\x0e\x8c\x03PDT\x94t\x94R\x94\x86\x94R\x94\x8c\x0bendDatetime\x94h\x08C\n\x07\xe8\t\x02\x17;;\x0fB?\x94h\x10\x86\x94R\x94\x8c\x0fupdatedDatetime\x94h\x08C\n\x07\xe8\t\x02\x0b\x024\x08\xb6x\x94h\x10\x86\x94R\x94\x8c\tisUpdated\x94\x89\x8c\nisMultiday\x94\x88u}\x94(h\x02\x8c\rCSA Fruit Box\x94h\x04\x89h\x05h\x08C\n\x07\xe8\t\x04\x0e\x1e\x00\x00\x00\x00\x94h\x10\x86\x94R\x94h\x13h\x08C\n\x07\xe8\t\x04\x0e\x1e\x00\x00\x00\x00\x94h\x10\x86\x94R\x94h\x17h\x08C\n\x07\xe8\x04\x15\x15\x16&\x06\x06\xf8\x94h\x10\x86\x94R\x94h\x1b\x89h\x1c\x89u}\x94(h\x02\x8c\rCSA Fruit Box\x94h\x04\x89h\x05h\x08C\n\x07\xe8\t\x0b\x0e\x1e\x00\x00\x00\x00\x94h\x10\x86\x94R\x94h\x13h\x08C\n\x07\xe8\t\x0b\x0e\x1e\x00\x00\x00\x00\x94h\x10\x86\x94R\x94h\x17h\x08C\n\x07\xe8\x04\x15\x15\x16&\x06\x06\xf8\x94h\x10\x86\x94R\x94h\x1b\x89h\x1c\x89u}\x94(h\x02\x8c\rCSA Fruit Box\x94h\x04\x89h\x05h\x08C\n\x07\xe8\t\x12\x0e\x1e\x00\x00\x00\x00\x94h\x10\x86\x94R\x94h\x13h\x08C\n\x07\xe8\t\x12\x0e\x1e\x00\x00\x00\x00\x94h\x10\x86\x94R\x94h\x17h\x08C\n\x07\xe8\x04\x15\x15\x16&\x06\x06\xf8\x94h\x10\x86\x94R\x94h\x1b\x89h\x1c\x89u}\x94(h\x02\x8c\rCSA Fruit Box\x94h\x04\x89h\x05h\x08C\n\x07\xe8\t\x19\x0e\x1e\x00\x00\x00\x00\x94h\x10\x86\x94R\x94h\x13h\x08C\n\x07\xe8\t\x19\x0e\x1e\x00\x00\x00\x00\x94h\x10\x86\x94R\x94h\x17h\x08C\n\x07\xe8\x04\x15\x15\x16&\x06\x06\xf8\x94h\x10\x86\x94R\x94h\x1b\x89h\x1c\x89u}\x94(h\x02\x8c\rCSA Fruit Box\x94h\x04\x89h\x05h\x08C\n\x07\xe8\n\x02\x0e\x1e\x00\x00\x00\x00\x94h\x10\x86\x94R\x94h\x13h\x08C\n\x07\xe8\n\x02\x0e\x1e\x00\x00\x00\x00\x94h\x10\x86\x94R\x94h\x17h\x08C\n\x07\xe8\x04\x15\x15\x16&\x06\x06\xf8\x94h\x10\x86\x94R\x94h\x1b\x89h\x1c\x89ue.')
    # duplicate last event for testing
    events.append(events[-1])
    events.append(events[-1])
    events.append(events[-1])

    renderService = RenderHelper(events=events,
        start_date=date(2024, 9, 1), today=date(2024, 9, 2))
    renderService.process_inputs()
