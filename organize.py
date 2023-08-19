#!/usr/bin/env python3
#
# 20230820 Ewald
# script to organize a webdirectory where subdirectory names are based on a date in the format YYYYMMDD
# e.g. 12 january 2023 will be 20230112
# The script makes sure that there is a link latest present which points to the most subdirectory
# For subdirectories of the previous month, it creates an archive Directory in the format YYYYMM
# and moves the relevant entries to that archive directories.
#
import os
import shutil
from datetime import datetime

def get_latest_directory(dir_path):
    # Filter out items that don't match the YYYYMMDD format
    dirs = [d for d in os.listdir(dir_path) if d.isdigit() and len(d) == 8]

    # Return the most recent directory
    return max(dirs) if dirs else None

def archive_last_month(dir_path, current_year_month):
    last_month = int(current_year_month) - 1
    if current_year_month.endswith("01"):  # if January, set to December of last year
        last_month = int(current_year_month) - 89  # e.g., 202201 - 89 = 202112

    archive_dir = os.path.join(dir_path, str(last_month))
    
    if not os.path.exists(archive_dir):
        os.mkdir(archive_dir)

    for d in os.listdir(dir_path):
        if d.startswith(str(last_month)):
            shutil.move(os.path.join(dir_path, d), archive_dir)

def update_latest_link(dir_path):
    # Remove the 'latest' link if it exists
    latest_link = os.path.join(dir_path, 'latest')
    if os.path.exists(latest_link):
        os.remove(latest_link)

    # Get the latest directory and create a symbolic link to it
    latest_dir = get_latest_directory(dir_path)
    if latest_dir:
        os.symlink(os.path.join(dir_path, latest_dir), latest_link)

def main():
    dir_path = './'  # You can update this path to your directory

    # Get current year and month in YYYYMM format
    current_year_month = datetime.now().strftime("%Y%m")

    update_latest_link(dir_path)
    archive_last_month(dir_path, current_year_month)

if __name__ == '__main__':
    main()

