import csv
from collections import defaultdict
import os
import re

from .config import plan_path


from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common import exceptions

import time


class MediaPlan(object):

    def __init__(self, path):

        with open(path, "r") as f:
            reader = csv.reader(f)
            self.columns = next(reader)

            self.media_plan = list(reader)

        for i, col in enumerate(self.columns):
            col = re.sub(r"[^a-zA-Z\s]", "", col)
            col = re.sub(r"\s", "_", col.strip()).lower()
            self.__setattr__(col, i)

        self.path = path

        # self.campaign_name = self.media_plan[1][0].strip()

        self.packages = defaultdict(list)

    def is_placement_row(self, row):
        return row[self.rate] and row[self.cost] and row[self.units] and row[self.supplier]

    def is_package_placement_row(self, row):
        return row[self.units] and row[self.supplier] and row[self.cost] and not row[self.unit_dimensions]

    def get_parent_row(self, index):
        """Go up the list until you find a non-placement"""

        if not self.is_placement_row(self.media_plan[index]):
            return self.get_parent_row(index - 1)
        else:
            return index

    def to_float(self, string_value):
        return float(string_value.replace(",", "").replace("$", ""))

    def parse(self):

        self.output = []

        for index, row in enumerate(self.media_plan):

            if not self.is_package_placement_row(row) and not self.is_placement_row(row):
                parent_row = self.media_plan[self.get_parent_row(index)]
                self.packages[parent_row[self.name]].append(row)

            if self.is_placement_row(row) and not self.is_package_placement_row(row):
                self.output.append((row[self.campaign_name],
                                    row[self.name],
                                    self.to_float(row[self.units]),
                                    self.to_float(row[self.cost]),
                                    self.to_float(row[self.rate]),
                                    row[self.start_date],
                                    row[self.end_date]))

        for parent in self.packages:
            for row in self.media_plan:
                if parent in row:
                    package_campaign_name = row[self.campaign_name]
                    package_units = self.to_float(row[self.units])
                    package_cost = self.to_float(row[self.cost])
                    package_rate = self.to_float(row[self.rate])
                    package_start = row[self.start_date]
                    package_end = row[self.end_date]
                    break

            for child in self.packages[parent]:
                child_campaign_name = package_campaign_name
                child_units = package_units / len(self.packages[parent])
                child_cost = package_cost / len(self.packages[parent])
                child_rate = package_rate
                child_start = package_start
                child_end = package_end

                self.output.append((child_campaign_name,
                                    child[self.name],
                                    child_units,
                                    child_cost,
                                    child_rate,
                                    child_start,
                                    child_end))

            self.columns = ["Campaign", "Placement", "Planned Units", "Planned Cost", "Rate", "Placement Start Date", "Placement End Date"]

    def save(self, dest):

        with open(dest, "w", newline="\n") as f:
            writer = csv.writer(f)
            writer.writerow(["Campaign", "Placement", "Planned Units", "Planned Cost", "Rate", "Placement Start Date", "Placement End Date"])
            for row in self.output:
                writer.writerow(row)


def get_media_plan_files(path=None):

    if not path:
        path = plan_path

    if not os.path.isdir(path):
        raise ValueError(f"{path} is not a directory.")

    files = next(os.walk(path))[2]
    output = []
    for file in files:
        if "Media Plan" in file and ".csv" in file:
            output.append(os.path.join(path, file))

    return output


def delay(seconds=10):
    def outer_wrapper(func):
        def wrapper(*ars, **kws):
            # print(f"Waiting {seconds} seconds")
            time.sleep(seconds)
            return func(*ars, **kws)
        return wrapper
    return outer_wrapper


class PrismaWebPage(object):

    def __init__(self, campaign_id, folder_path="default"):
        self.campaign_id = campaign_id

        self.url = f"https://omgca-prisma.mediaocean.com/campaign-management/#osAppId=prsm-cm-spa&osPspId=prsm-cm-buy&campaign-id={self.campaign_id.upper()}&route=online"

        if folder_path == "default":
            destination = plan_path
        else:
            destination = folder_path

        chromeOptions = webdriver.ChromeOptions()
        prefs = {"download.default_directory": destination}
        chromeOptions.add_experimental_option("prefs", prefs)

        # chromedriver = "path/to/chromedriver.exe"
        chromedriver = os.path.join(os.path.split(__file__)[0], 'chromedriver.exe')

        self.driver = webdriver.Chrome(chrome_options=chromeOptions, executable_path=chromedriver)
        self.driver.implicitly_wait(10)
        # self.driver.set_window_size(1920, 1080)
        self.driver.maximize_window()
        self.driver.get(self.url)

    def element_exists(self, by, element):
        try:
            self.find_element(by, element)
            return True
        except exceptions.NoSuchElementException:
            return False

    @delay(5)
    def find_element(self, by, lookup):
        return self.driver.find_element(by, lookup)

    def old_buy_tab(self):
        if not self.element_exists(By.ID, "switch-to-plpb"):
            pass  # Already on old buy tab page
        else:
            elem = self.find_element(By.ID, "switch-to-plpb")
            elem.send_keys(Keys.RETURN)

    def new_buy_tab(self):

        if not self.element_exists(By.ID, "switch-to-new-buy-tab"):
            pass  # Already on new buy tab page
        else:
            elem = self.find_element(By.ID, "switch-to-new-buy-tab")
            elem.send_keys(Keys.RETURN)

    def export_media_plan(self):

        try:
            button = self.find_element(By.CLASS_NAME, "mi-export-import")
        except exceptions.NoSuchElementException:
            self.new_buy_tab()
            button = self.find_element(By.CLASS_NAME, "mi-export-import")

        button.send_keys(Keys.RETURN)

        download_link = self.find_element(By.LINK_TEXT, "Export media plan")
        download_link.send_keys(Keys.RETURN)

    def close(self):
        self.driver.close()


def plan_file_exists(campaign_id, folder_path):
    plan_files = get_media_plan_files(folder_path)
    if True in [campaign_id in plan for plan in plan_files]:
        return True
    else:
        return False


def download_plan(campaign_id, folder_path, wait_time=5):
    plan = PrismaWebPage(campaign_id, folder_path)
    plan.export_media_plan()

    while True:
        if plan_file_exists(campaign_id, folder_path):
            return True
        else:
            time.sleep(wait_time)


if __name__ == '__main__':
    pass
