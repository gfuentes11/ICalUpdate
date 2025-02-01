# iCalUpdate

A Python script that synchronizes recurring calendar events from an Outlook (ICS) feed to iCloud using CalDAV. The script manually filters and expands events to avoid certain attribute errors when using the `ics` library and provides an option to delete all events from the target calendar.

---

## Table of Contents
- [Overview](#overview)
- [File Structure](#file-structure)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Usage](#usage)
  - [Sync Events](#sync-events)
  - [Delete All Events](#delete-all-events)
- [Known Limitations](#known-limitations)
- [License](#license)

---

## Overview

This project:
1. Fetches an Outlook ICS feed.
2. Parses the feed with the [`ics`](https://pypi.org/project/ics/) library.
3. Manually filters and expands recurring events within a specified date range.
4. Connects to your iCloud Calendar using [`caldav`](https://pypi.org/project/caldav/) and uploads these events.
5. Prevents duplicates by maintaining a record of existing events.
6. Allows for all events in the target calendar to be deleted using a `delete` command.

---

## File Structure
```
ICALUPDATE
├── .venv/ # (Optional) Python virtual environment
├── script/
│ ├── config.ini # Your personal configuration file
│ ├── ical.py # Main script to sync or delete events
│ └── sampleConfig.ini # Sample config demonstrating required fields
├── .gitignore
└── README.md
```

---

## Prerequisites

- Python 3.x
- A functional iCloud account with CalDAV access
- An Outlook ICS feed URL

In addition, the script depends on the following Python packages:
- `requests`
- `ics`
- `arrow`
- `pytz`
- `caldav`
- `icalendar`

---

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/ICALUPDATE.git
cd ICALUPDATE
```

### 2. Create (Optional) and Activate Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

(Alternatively, install dependencies individually if a `requirements.txt` is not provided.)

---

## Configuration

### 1. Duplicate Sample Configuration File

```bash
cp script/sampleConfig.ini script/config.ini
```

### 2. Edit `config.ini`

Provide the following details:

```ini
[calendar]
ICS_URL = https://outlook.office365.com/.../calendar.ics
CALDAV_URL = https://caldav.icloud.com
USERNAME = your_icloud_username
PASSWORD = your_icloud_app_specific_password
TARGET_CALENDAR_NAME = NameOfYouriCloudCalendar
```

- **ICS_URL**: URL to your Outlook ICS feed.
- **CALDAV_URL**: iCloud CalDAV endpoint (usually `https://caldav.icloud.com`).
- **USERNAME**: Your iCloud login (often the full email).
- **PASSWORD**: An App-Specific Password for iCloud.
- **TARGET_CALENDAR_NAME**: The specific iCloud calendar name you want to sync to.

---

## Usage

All commands should be run from the project directory (e.g., `ICALUPDATE/`).

### Sync Events

To synchronize events from Outlook ICS to iCloud:

```bash
python script/ical.py
```

- Fetches the ICS file.
- Parses it and expands recurring events.
- Manually filters them by date (default filter is from 1 year ago to 2 years in the future).
- Adds them to iCloud Calendar, skipping duplicates.

### Delete All Events

To remove all events from your target iCloud calendar:

```bash
python script/ical.py delete
```

- You will be prompted to type `YES` to confirm.
- Deletes every event from the configured `TARGET_CALENDAR_NAME`.

> ⚠ **Warning:** This action cannot be undone.

---

## Known Limitations

- **Date Range Filtering**: Currently, the script filters events from 1 year in the past to 2 years in the future. Adjust the logic in `sync_calendar()` as needed.
- **Recurring Events**: While recurring events are expanded, some complex recurrence patterns might need additional testing or adjustments.
- **Duplicates**: The script’s duplicate check is basic (summary, start, end). Two different events with the same summary and timing may be considered duplicates.

---

## License

This project is open source and available under the MIT License. Feel free to modify and adapt to your needs.

