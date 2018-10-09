# myproject.py

"""
Module for downloading reports via the DCM API.
It aims to eliminate what is otherwise a repetitive and time-consuming task:
manually going into the platform, selecting, downloading, then copy/pasting the data
into Excel.
"""


import os
import time

from apiclient.discovery import build
import httplib2
from oauth2client.file import Storage
from googleapiclient import errors
from contextlib import contextmanager


class APIResource(object):

    def __init__(self, name, **params):
        self.name = name
        self.service = create_service()
        self.params = params
        self.body = self.get(**params)

    def get(self, **kws):
        obj = getattr(self.service, self.name)()
        req = obj.get(**kws)
        return req.execute()

    def list(self):
        raise NotImplementedError

    def update(self):
        raise NotImplementedError


class Profile(APIResource):

    def __init__(self, profileId):

        if not is_valid_user(profileId):
            raise ValueError(f'Invalid user profile id: {profileId}')

        super().__init__(name="userProfiles", profileId=profileId)
        self.profileId = str(profileId)

        self.username = self.body.get('userName')
        self.accountname = self.body.get('accountName')

    def make_request(self):
        pass

    def get_reports(self):
        request = self.service.reports().list(profileId=self.profileId)
        response = request.execute()
        reports = [Report(self.profileId, report['id'], self.service)
                   for report in response['items']]
        return reports

    def __repr__(self):
        return f"Profile({self.profileId}, name='{self.accountname}')"


class Report(APIResource):

    def __init__(self, profileId, reportId):
        super().__init__('reports', reportId=reportId, profileId=profileId)

        self.reportId = str(reportId)
        self.profileId = str(profileId)

        self.format = self.body.get('format')
        self.name = self.body.get('name')
        self.filename = self.body.get('fileName')
        # Pull in report attributes

    def get_report_body(self):
        request = self.service.reports().get(profileId=self.profileId, reportId=self.reportId)

        return request.execute()

    def refresh_body(self):
        self.body = self.get_report_body()

    def get_available_files(self, get_all=True):
        '''Get a list of all files associated with a report id'''
        request = self.service.files().list(profileId=self.profileId)
        response = request.execute()['items']

        files = response

        return sorted(files, key=lambda f: int(f['lastModifiedTime']))

    def download_file(self, file_id, path):
        '''
        Download report file and return as a raw CSV format.
        Accepts reportid and file_id as arguments.
        '''

        request = self.service.files().get_media(reportId=self.reportId, fileId=file_id)
        response = request.execute()

        if self.format.lower() != 'csv':
            raise TypeError("Wrong format; must be CSV")

        with open(path, 'w') as f:
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

        request = self.service.reports().run(profileId=self.profileId,
                                             reportId=self.reportId)
        file = request.execute()
        return file['id']

    @contextmanager
    def update_request_body(self):
        try:
            body = self.body.copy()
            yield body

        finally:

            req = self.service.reports().update(reportId=self.reportId, profileId=self.profileId, body=body)
            new_body = req.execute()

            self.body = new_body

    def set_date_range(self, start=None, end=None, period=None):

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
        return f"Report(name='{self.name}', id='{self.reportId}', profileId='{self.profileId}')"


def create_service(api_name='dfareporting', version='v2.8',
                   credentials='credentials.json'):
    '''
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


def is_valid_user(profileId):
    profileId = str(profileId)
    profiles = get_profiles()

    if profileId in [x['profileId'] for x in profiles]:
        return True

    return False


def get_profiles():
    service = create_service()
    request = service.userProfiles().list()
    return request.execute()['items']


def run_and_download_report(profileId, reportId, path=None, check_interval=2):
    report = Report(reportId=reportId, profileId=profileId)
    print(f"Running report '{report.name}'...")

    report = Report(profileId, reportId)
    # today = dt.datetime.today().strftime('%Y-%m-%d')

    if path is None:
        path = os.path.join(os.getcwd(), f'{report.filename}.csv')

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

            check_interval = check_interval ** 2
        else:
            print(f"Downloaded {path}")
            flag = False


if __name__ == '__main__':
    rep = Report(profileId=3085707, reportId=155277304)
