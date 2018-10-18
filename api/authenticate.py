import argparse
import os
from oauth2client import tools
from oauth2client.client import flow_from_clientsecrets
from oauth2client.file import Storage


def run(scope, secret_path):
    parser = argparse.ArgumentParser(parents=[tools.argparser])
    flags = parser.parse_args()

    storage = Storage(os.path.join(os.path.split(__file__)[0], 'credentials.json'))
    flow = flow_from_clientsecrets(secret_path,
                                   scope=scope)

    tools.run_flow(flow, storage, flags)


if __name__ == '__main__':
    path, _ = os.path.split(__file__)
    secret_path = os.path.join(path, 'client_secret.json')
    scope = 'https://www.googleapis.com/auth/dfareporting'

    run(scope, secret_path)
