import os
from . import authenticate


credentials = os.path.join(os.path.split(authenticate.__file__)[0], 'credentials.json')

if not os.path.isfile(credentials):
    path, _ = os.path.split(__file__)
    secret_path = os.path.join(path, 'client_secret.json')
    scope = 'https://www.googleapis.com/auth/dfareporting'

    authenticate.run(scope, secret_path)

from .api import Profile, Report, run_and_download_report, get_profiles, create_service, is_valid_user
