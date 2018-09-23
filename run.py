from dcm_api import run_and_download_report

if __name__ == '__main__':
    profile_id = input("Enter your DCM profile ID: ")
    report_id = input("Enter report ID: ")
    path = input("Enter destination or press Enter for default location: ")

    if not path:
        path = None

    run_and_download_report(profile_id=profile_id, report_id=report_id, path=path)
    print()
    input("Press Enter to exit")
