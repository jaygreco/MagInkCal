#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This project is designed for the WaveShare 12.48" eInk display. Modifications will be needed for other displays,
especially the display drivers and how the image is being rendered on the display. Also, this is the first project that
I posted on GitHub so please go easy on me. There are still many parts of the code (especially with timezone
conversions) that are not tested comprehensively, since my calendar/events are largely based on the timezone I'm in.
There will also be work needed to adjust the calendar rendering for different screen sizes, such as modifying of the
CSS stylesheets in the "render" folder.
"""
import datetime as dt
import sys

from config import Config
from pytz import timezone
from ical.ical import IcalHelper
from render.render import RenderHelper
from epd_hidapi.host.panel import Panel
from epd_hidapi.host.image import Image
import json
import logging
import pickle

def should_refresh(event_list, today):
    refresh = False
    last = {}

    try:
        with open("last.pickle", "rb") as fo:
            last = pickle.load(fo)

    except FileNotFoundError:
        # First run: always refresh
        refresh = True

    if event_list != last.get("event_list") or today != last.get("today"):
        refresh = True

    # Save for next time
    if refresh:
        last["today"] = today
        last["event_list"] = event_list
        with open("last.pickle", "wb") as fo:
            pickle.dump(last, fo)

    return refresh


def main():
    # Basic configuration settings (user replaceable)
    config = Config()

    # Create and configure logger
    logging.basicConfig()
    logger = logging.getLogger('maginkcal')
    logger.setLevel(logging.INFO)
    logger.info("Starting calendar update")

    try:
        # Establish current date and time information
        # Note: For Python datetime.weekday() - Monday = 0, Sunday = 6
        # For this implementation, each week starts on a Sunday and the calendar begins on the nearest elapsed Sunday
        # The calendar will also display 5 weeks of events to cover the upcoming month, ending on a Saturday
        config.displayTZ = timezone(config.displayTZ)
        currDatetime = dt.datetime.now(config.displayTZ)
        logger.info("Time synchronised to {}".format(currDatetime))
        currDate = currDatetime.date()
        calStartDate = currDate - dt.timedelta(days=((currDate.weekday() + (7 - config.weekStartDay)) % 7))
        calEndDate = calStartDate + dt.timedelta(days=(5 * 7 - 1))
        calStartDatetime = config.displayTZ.localize(dt.datetime.combine(calStartDate, dt.datetime.min.time()))
        calEndDatetime = config.displayTZ.localize(dt.datetime.combine(calEndDate, dt.datetime.max.time()))

        # Retrieve all events within start and end date (inclusive)
        start = dt.datetime.now()
        eventList = []

        gcal_calendars = [cal for cal in config.calendars if cal.get("type")  == "gcal"]
        logger.info("gcal_calendars: " + str(gcal_calendars))
        if gcal_calendars:
            # Use lazy imports so that gcal credentials aren't always required
            from gcal.gcal import GcalHelper
            gcalService = GcalHelper()
            eventList.extend(gcalService.retrieve_events(gcal_calendars, calStartDatetime, calEndDatetime, config.displayTZ, config.thresholdHours))

        ical_calendars = [cal for cal in config.calendars if cal.get("type") == "ical"]
        logger.info("ical_calendars: " + str(ical_calendars))
        if ical_calendars:
            icalService = IcalHelper(ical_calendars)
            eventList.extend(icalService.retrieve_events(calStartDatetime, calEndDatetime, config.displayTZ, config.thresholdHours))

        logger.info("Calendar events retrieved in " + str(dt.datetime.now() - start))

        # Only proceed if the calendar events have changed, or it's a new day. 
        if not should_refresh(eventList, currDate):
            logger.info("No updates; not refreshing panel")
            return

        logger.info("Refreshing panel")
        renderService = RenderHelper(events=eventList, start_date=calStartDate, today=currDate)
        renderService.process_inputs()

        image = Image("render/calendar.png")
        image.resize(width=config.screenWidth, height=config.screenHeight)
        image.rotate(rotation=90)
        image.extract(threshold=200)
        # image.save(f"{infile}_resized.png")
        # image.save(f"{infile}_black.bmp", monochrome=True, color="black")
        # image.save(f"{infile}_red.bmp", monochrome=True, color="red")

        # TODO: break out pixel splitting here instead of including it in panel?
        if config.isDisplayToScreen:
            panel = Panel()
            panel.upload_image(image.bit_array_black, image.bit_array_red)

    except Exception as e:
        logger.error(f"error: {e}")

    logger.info("Completed calendar update")

# TODO: update on-demand (poll for calendar )
if __name__ == "__main__":
    main()
