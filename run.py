import click

from api import run_and_download_report


@click.command()
@click.option('--profile_id', prompt="Enter your DCM profile ID", help="Your DCM profile ID")
@click.option('--report_id', prompt="Enter report ID", help="Your DCM report ID")
@click.option('--path', default=None, help="Report save location")
def main(profile_id, report_id, path):
    if not path:
        path = None

    run_and_download_report(profile_id=profile_id, report_id=report_id, path=path)


if __name__ == '__main__':
    main()
