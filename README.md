# MagInkCal
This is a fork of [Maginkcal](https://github.com/speedyg0nz/MagInkCal) that has been modified to use the [epd-hidapi](https://github.com/jaygreco/epd-hidapi) library and underlying EPD panel driver so that it works with a repurposed e-ink display that was reverse-engineered. As opposed to the upstream repo, this fork sends the display data over raw HID to an Adafruit ThinkInk feather, which drives the actual panel.

![20210924_175459](https://user-images.githubusercontent.com/5581989/134661608-bac1f0bf-e7e3-41fe-b92e-37c26dad8fbe.jpg)


## Changes vs upstream Maginkcal
Most of the code was refactored and cleaned up to suit my personal preferences, although the main project structure remains the same. The CSS and dashboard HTML were modified to fit better to the lower resolution of the display used. There is also a systemd unit file and timer instead of relying on cron to periodically schedule jobs. The main Python script is also structured to be run more frequently and compare the calendar events with the previous run so that new or modified events can be picked up within a short period of time. Lastly, the image capture was changed from chromium, which is relatively heavyweight, to use [cutycapt](https://cutycapt.sourceforge.net/) and [xvfb](https://www.x.org/releases/X11R7.6/doc/man/man1/Xvfb.1.xhtml). As of right now, this version of the project isn't using a battery, but rather an always-powered pi, so it's not pulling in any of the PiSugar tools.

## Setting Up Raspberry Pi Zero

1. Start by flashing [Raspberrypi OS Lite](https://www.raspberrypi.org/software/operating-systems/) to a MicroSD Card. Make sure to set up wifi SSH access.

1. Run the following commands in the RPi Terminal to setup the environment to run the Python scripts.

```bash
sudo apt update
sudo apt install python3-pip
sudo apt install cutycapt
sudo apt install xvfb
sudo apt install libopenjp2-7-dev
```

1. Clone this repository on the pi, or download a zip archive and copy the files over and unzip.
```
$ git clone https://github.com/jaygreco/MagInkCal && cd MagInkCal
```

1. Create a virtual environment inside the `Maginkcal` repository from the step above.
```
python3 -m venv env && source env/bin/activate
pip install -r requirements.txt
```

1. If only using iCloud calendars, skip the next two steps. If using Google Calendars (or both), it's necessary to first grant API access. Follow the [instructions here](https://developers.google.com/calendar/api/quickstart/python) on your PC to get the credentials.json file from your Google API. Don't worry, take your time. I'll be waiting here.

1. Once done, copy the credentials.json file to the "gcal" folder in this project. Run the following command on the pi. A link to a web browser should appear, asking you to grant access to your calendar. Once done, you should see a "token.pickle" file in your "gcal" folder.

```bash
python3 quickstart.py
```

1. Follow the steps in `systemd/usage.md` to install and activate the systemd service and timer, which will automatically run the calendar at a specified interval.

1. That's all! Your Magic Calendar should now be refreshed at the time interval that is specified in the systemd timer unit.

## Acknowledgements
- Upstream [Maginkcal](https://github.com/speedyg0nz/MagInkCal)
- [Quattrocento Font](https://fonts.google.com/specimen/Quattrocento): Font used for the calendar display
- [Bootstrap Calendar CSS](https://bootstrapious.com/p/bootstrap-calendar): Stylesheet that was adapted heavily for the calendar display
- [/u/aceisace](https://www.reddit.com/user/aceisace/): For the tips on E-Ink development and the [InkyCal](https://github.com/aceisace/Inkycal) repo (worth checking out even though I didn't use it for this project).
