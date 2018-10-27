# api.py

"""
Module for downloading reports via the DCM API.
"""


import json
import os
import time

from apiclient.discovery import build
import httplib2
from oauth2client.file import Storage
from googleapiclient import errors
from contextlib import contextmanager


class APIResource(object):

    def __init__(self, resource_type, **params):
        self.resource_type = resource_type
        self._service = create_service()
        self.params = params
        self.body = self.get(**params)

    def get(self, **kws):
        obj = getattr(self._service, self.resource_type)()
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

        super().__init__("userProfiles", profileId=profileId)
        self.profileId = str(profileId)

        self.username = self.body.get('userName')
        self.accountname = self.body.get('accountName')

    def make_request(self):
        pass

    def get_reports(self):
        request = self._service.reports().list(profileId=self.profileId)
        response = request.execute()
        reports = [Report(self.profileId, report['id'], self._service)
                   for report in response['items']]
        return reports

    def __repr__(self):
        return f"Profile({self.profileId}, name='{self.accountname}')"


class Report(APIResource):

    def __init__(self, profileId, reportId):
        super().__init__('reports', reportId=reportId, profileId=profileId)

        self.reportId = str(reportId)
        self.profileId = str(profileId)

        # Pull in report attributes

    @property
    def format(self):
        return self.body.get('format')

    @property
    def name(self):
        return self.body.get('name')

    @property
    def filename(self):
        return self.body.get('fileName')

    def get_report_body(self):
        request = self._service.reports().get(profileId=self.profileId, reportId=self.reportId)

        return request.execute()

    def refresh_body(self):
        self.body = self.get_report_body()

    def get_available_files(self, get_all=True):
        '''Get a list of all files associated with a report id'''
        request = self._service.files().list(profileId=self.profileId)
        response = request.execute()['items']

        files = response

        return sorted(files, key=lambda f: int(f['lastModifiedTime']))

    def download_file(self, file_id, path):

        request = self._service.files().get_media(reportId=self.reportId, fileId=file_id)
        response = request.execute()

        if self.format == "CSV":

            with open(path, 'w') as f:
                f.write(response.decode())

        if self.format == "EXCEL":

            with open(path, 'wb') as f:
                f.write(response)

    def download_latest_file(self, filename):
        files = self.get_available_files()

        if len(files) == 0:
            raise ValueError("No files available for download with this report")

        latest = sorted(files, key=lambda f: f['lastModifiedTime'], reverse=True)[0]
        return self.download_file(latest['id'], filename)

    def run(self):
        '''Run a report. Returns the file_id if successful'''

        request = self._service.reports().run(profileId=self.profileId,
                                              reportId=self.reportId)
        file = request.execute()
        return file['id']

    @contextmanager
    def update_request_body(self):
        try:
            body = self.body.copy()
            yield body

        finally:

            req = self._service.reports().update(reportId=self.reportId,
                                                 profileId=self.profileId,
                                                 body=body)
            new_body = req.execute()

            self.body = new_body

    def set_date_range(self, start=None, end=None, *, period=None):

        if (start or end) and period:
            raise ValueError("You select either a start and end date, or a period, but not both")

        if not period and not start and not end:
            raise ValueError("You must include either a start and end date, or a period")

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

    def set_format(self, format):

        if format not in ["CSV", "EXCEL"]:
            raise ValueError("Wrong format, must be either 'CSV' or 'EXCEL'")

        with self.update_request_body() as body:
            body["format"] = format

    def set_dimensions(self, dimensions):

        path = os.path.join(os.path.split(__file__)[0], "standard_dimensions.json")

        with open(path, "r") as f:
            standard_dimensions = json.load(f)

        with self.update_request_body() as body:
            body['criteria']['dimensions'] = []
            for dimension in dimensions:
                entry = {'kind': 'dfareporting#sortedDimension',
                         'name': standard_dimensions[dimension.lower()]["API Name"]}

                body['criteria']['dimensions'].append(entry)

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

    if profileId in [x['profileId'] for x in get_profiles()]:
        return True

    return False


def get_profiles():
    service = create_service()
    request = service.userProfiles().list()
    return request.execute()['items']


def run_and_download_report(profileId, reportId, path=None, check_interval=10):
    report = Report(reportId=reportId, profileId=profileId)
    print(f"Running report '{report.name}'...")

    report = Report(profileId, reportId)
    # today = dt.datetime.today().strftime('%Y-%m-%d')

    if path is None:
        filename = report.filename
        if report.format == "EXCEL":
            filename = filename + ".xlsx"
        else:
            filename = filename + ".csv"

        path = os.path.join(os.getcwd(), f'{report.filename}')

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

            # check_interval += check_interval ** 2
        else:
            print(f"Downloaded {path}")
            flag = False


if __name__ == '__main__':
    pass
