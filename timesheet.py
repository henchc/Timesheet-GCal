from __future__ import print_function
import httplib2
import os

from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

import datetime
import re
from dateutil.parser import parse
import csv
import subprocess


# Skeleton code from
# https://developers.google.com/google-apps/calendar/quickstart/python

try:
    import argparse
    parser = argparse.ArgumentParser(parents=[tools.argparser])
    # add arguments for start and end of timesheet
    # default to beginning of year for start
    parser.add_argument(
        '--start',
        type=str,
        help='start date for calendar parse',
        default='2018-01-01')
    # defaut to today for end
    parser.add_argument(
        '--end',
        type=str,
        help='end date for calendar parse',
        default=datetime.datetime.now().strftime('%Y-%m-%d'))
    flags = parser.parse_args()
except ImportError:
    flags = None

# If modifying these scopes, delete your previously saved credentials
# at ~/.credentials/calendar-python-quickstart.json
SCOPES = 'https://www.googleapis.com/auth/calendar.readonly'
CLIENT_SECRET_FILE = 'client_secret.json'
APPLICATION_NAME = 'Google Calendar API Python Quickstart'


def get_credentials():
    """Gets valid user credentials from storage.

    If nothing has been stored, or if the stored credentials are invalid,
    the OAuth2 flow is completed to obtain the new credentials.

    Returns:
        Credentials, the obtained credential.
    """
    print("Authenticating Google Calendar API credentials...")
    home_dir = os.path.expanduser('~')
    credential_dir = os.path.join(home_dir, '.credentials')
    if not os.path.exists(credential_dir):
        os.makedirs(credential_dir)
    credential_path = os.path.join(credential_dir,
                                   'calendar-python-quickstart.json')

    store = Storage(credential_path)
    credentials = store.get()
    if not credentials or credentials.invalid:
        flow = client.flow_from_clientsecrets(CLIENT_SECRET_FILE, SCOPES)
        flow.user_agent = APPLICATION_NAME
        if flags:
            credentials = tools.run_flow(flow, store, flags)
        else:  # Needed only for compatibility with Python 2.6
            credentials = tools.run(flow, store)
        print('Storing credentials to ' + credential_path)
    return credentials


def main():
    """Fetches list of events and parses out metadata for timesheet
    """
    credentials = get_credentials()
    http = credentials.authorize(httplib2.Http())
    service = discovery.build('calendar', 'v3', http=http)

    # start time for API call
    start_time_flag = datetime.datetime.strptime(
        flags.start, '%Y-%m-%d').isoformat() + 'Z'  # 'Z' indicates UTC time

    print('Parsing calendar events to timesheet...')
    eventsResult = service.events().list(
        calendarId='primary',
        timeMin=start_time_flag,
        maxResults=10000,
        singleEvents=True,
        orderBy='startTime').execute()
    events = eventsResult.get('items', [])

    if not events:
        print('No events found.')

    rows = []
    header = [
        'Category',
        'Date',
        'Start Time',
        'End Time',
        'Title',
        'Hours',
        'Description']

    rows.append(header)

    for event in events:
        try:
            # check if event is before end date
            if parse(
                    event['start']['dateTime']).replace(
                    tzinfo=None) < datetime.datetime.strptime(
                        flags.end, '%Y-%m-%d'):
                row = []
                title = event['summary']
                description = event['description']
                start_date = parse(
                    event['start']['dateTime']).strftime('%Y-%m-%d')
                end_date = parse(event['end']['dateTime']).strftime('%Y-%m-%d')
                start_time = parse(
                    event['start']['dateTime']).strftime('%H:%M')
                end_time = parse(event['end']['dateTime']).strftime('%H:%M')

                delta = parse(event['end']['dateTime']) - \
                    parse(event['start']['dateTime'])
                seconds = delta.seconds
                minutes = seconds / 60
                hours = minutes / 60
                categories = re.findall(r'\{.*\}', description)

                if len(categories) > 0:
                    for c in categories:
                        c = c.replace('{', '').replace('}', '')
                        rows.append([c, start_date, start_time, end_time,
                                     title, hours, description])

        except:
            pass

    username = subprocess.check_output(
        "whoami", shell=True).decode("utf-8").strip()
    fname = username + "-timesheet-" + flags.start + '--' + flags.end + ".csv"
    with open(fname, "w") as f:
        writer = csv.writer(f)
        writer.writerows(rows)

    print("Timesheet written to " + fname)


if __name__ == '__main__':
    main()
