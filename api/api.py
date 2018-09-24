# myproject.py

"""
Module for downloading reports via the DCM API.
It aims to eliminate what is otherwise a repetitive and time-consuming task:
manually going into the platform, selecting, downloading, then copy/pasting the data
into Excel.
"""


import os
import datetime as dt
import time

from apiclient.discovery import build
import httplib2
from oauth2client.file import Storage
from googleapiclient import errors
from contextlib import contextmanager


class Profile(object):

    def __init__(self, profile_id):

        if not is_valid_user(profile_id):
            raise ValueError(f'Invalid user profile id: {profile_id}')

        self.profile_id = str(profile_id)
        self._service = _create_service()

        self.metadata = [pr for pr in get_profiles() if pr['profileId'] == self.profile_id][0]

        self.username = self.metadata.get('userName')
        self.accountname = self.metadata.get('accountName')

    def make_request(self):
        pass

    def get_reports(self):
        request = self._service.reports().list(profileId=self.profile_id)
        response = request.execute()
        reports = [Report(self.profile_id, report['id'], self._service)
                   for report in response['items']]
        return reports


class Report(object):

    def __init__(self, profile_id, report_id, service=None,):
        self.id = str(report_id)
        self.profile_id = str(profile_id)

        if service is None:
            self._service = _create_service()
        else:
            self._service = service

        self.body = self.get_report_body()

        self.format = self.body.get('format')
        self.name = self.body.get('name')
        self.filename = self.body.get('fileName')
        # Pull in report attributes

    def get_report_body(self):
        request = self._service.reports().get(profileId=self.profile_id, reportId=self.id)

        return request.execute()

    def refresh_body(self):
        self.body = self.get_report_body()

    def get_available_files(self, get_all=True):
        '''Get a list of all files associated with a report id'''
        request = self._service.files().list(profileId=self.profile_id)
        response = request.execute()['items']

        files = response

        return sorted(files, key=lambda f: int(f['lastModifiedTime']))

    def download_file(self, file_id, filename):
        '''
        Download report file and return as a raw CSV format.
        Accepts reportid and file_id as arguments.
        '''

        request = self._service.files().get_media(reportId=self.id, fileId=file_id)
        response = request.execute()

        _, ext = os.path.splitext(filename)
        if ext.lower() != '.csv':
            raise TypeError("Wrong format; must be CSV")

        with open(filename, 'w') as f:
            f.write(response.decode())
        return True

    def download_latest_file(self, filename):
        files = self.get_available_files()

        if len(files) == 0:
            raise ValueError("No files available for download with this report")

        latest = sorted(files, key=lambda f: f.date_ran, reverse=True)[0]
        return self.download_file(latest.file_id, filename)

    def run(self):
        '''Run a report. Returns the file_id if successful'''

        request = self._service.reports().run(profileId=self.profile_id,
                                              reportId=self.id)
        file = request.execute()
        return file['id']

    @contextmanager
    def update_request_body(self):
        try:
            body = self.body.copy()
            yield body

        finally:

            req = self._service.reports().update(reportId=self.id, profileId=self.profile_id, body=body)
            new_body = req.execute()

            self.body = new_body

    def set_date_range(self, *, start=None, end=None, period=None):

        # LAST_14_DAYS
        # LAST_24_MONTHS
        # LAST_30_DAYS
        # LAST_365_DAYS
        # LAST_60_DAYS
        # LAST_7_DAYS
        # LAST_90_DAYS
        # MONTH_TO_DATE
        # PREVIOUS_MONTH
        # PREVIOUS_QUARTER
        # PREVIOUS_WEEK
        # PREVIOUS_YEAR
        # QUARTER_TO_DATE
        # TODAY
        # WEEK_TO_DATE
        # YEAR_TO_DATE
        # YESTERDAY

        if (start or end) and period:
            raise ValueError("You select either a start and end date, or a period, but not both")

        if not period and not start and not end:
            raise TypeError("You must include either a start and end date, or a period")

        with self.update_request_body() as body:

            body['criteria']["dateRange"] = {}

            if period is not None:
                period = period.upper()
                body["criteria"]["dateRange"]["relativeDateRange"] = period

            else:
                body["criteria"]["dateRange"] = {}
                body["criteria"]["dateRange"]["startDate"] = start
                body["criteria"]["dateRange"]["endDate"] = end

    def set_filename(self, filename):

        with self.update_request_body() as body:
            body["fileName"] = filename

    def __repr__(self):
        return f"Report(name='{self.name}', id='{self.id}', profile_id='{self.profile_id}')"


# class File(object):

#     def __init__(self, file_id, report_id, timestamp, status, info):
#         self.file_id = file_id
#         self.report_id = report_id
#         self.status = status
#         self.info = info

#         timestamp = int(str(timestamp)[:10])
#         self.date_ran = dt.datetime.fromtimestamp(timestamp)

#     def __repr__(self):
#         return f"File(file_id='{self.file_id}', status='{self.status}', date_ran='{self.date_ran}')"


def _create_service(api_name='dfareporting', version='v2.8',
                    credentials='credentials.json'):
    '''
    Returns a service object from which API calls are made. The Report and
    Profile classes use this function to create a 'service' attribute; it is
    through this that various calls are made to the API.
    Requires a credentials file saved in the same location as the module. This
    can be obtained by running authenticate.py
    Args:
    api_name (default 'dfareporting')
    version (default 'v2.8')
    credentials (default 'credentials.dat')
    The list of APIs can be found: https://developers.google.com/api-client-library/python/apis/
    '''
    path, _ = os.path.split(__file__)
    storage = Storage(os.path.join(path, credentials))
    credentials = storage.get()

    if credentials is None or credentials.invalid:
        errormessage = f'Missing or invalid credentials at {path}. Run authenticate.py to regenerate'
        raise ValueError(errormessage)

    http = httplib2.Http()
    http = credentials.authorize(http)
    service = build(api_name, version, http=http)

    return service


def is_valid_user(profile_id):
    profile_id = str(profile_id)
    profiles = get_profiles()

    if profile_id in [x['profileId'] for x in profiles]:
        return True

    return False


def get_profiles():
    service = _create_service()
    request = service.userProfiles().list()
    return request.execute()['items']


def run_and_download_report(report_id, profile_id, path=None, check_interval=10):
    report = Report(report_id=report_id, profile_id=profile_id)
    print(f"Running report '{report.name}'...")

    report = Report(profile_id, report_id)
    today = dt.datetime.today().strftime('%Y-%m-%d')

    if path is None:
        path = os.path.join(os.getcwd(), f'{report.name}_{today}.csv')

    file_id = report.run()

    print(f"Downloading report '{report.name}'...")
    time.sleep(check_interval)
    flag = True
    while flag:
        try:
            report.download_file(file_id, path)
        except errors.HttpError:
            print(f"Report '{report.name}' hasn't finished running. Trying again...")
            time.sleep(check_interval)
        else:
            print(f"Downloaded {path}")
            flag = False


if __name__ == '__main__':
    profile = Profile(4251083)
    report = profile.get_reports()[0]
    print(get_profiles())
