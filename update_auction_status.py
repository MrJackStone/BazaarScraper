import requests
import datetime
from requests_html import HTML
import pandas as pd
import os
import concurrent.futures
import logging
import pickle
from bazaar_scraper import str_to_datetime, get_page_count
import pytz

# Global variables:
request_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'}
#   Auction history url (main page)
root_url = 'https://www.tibia.com/charactertrade/?subtopic=pastcharactertrades'
# Server save hour (CET)
SS_HOUR = 10

dataframe_columns = ['Id', 'Name', 'End', 'Day0', 'Day1', 'Day2', 'Day3', 'Day4', 'Day5', 'Day6', 'Day7', 'Final']
# File to which the full dataframe will be written at the end of the run
status_record_filename = 'auction_status_record.pkl'


def update_auction_status(status_df):
    """Update auction status"""

    max_page = get_page_count()
    print(f"\nTotal number of pages: {max_page:,}", end='\n')

    # Integer immediately before first page to be scraped (usually =0)
    page_number = 0

    # Loop through each 'auction history' page
    while page_number <= max_page:
        page_number += 1

        page_url = root_url + '&currentpage=' + str(page_number)
        page_req = requests.get(page_url, headers=request_headers)

        if page_req.status_code == 200:
            page_html = HTML(html=page_req.text)
            status_df, auction_count, min_age, max_age = update_auctions_in_page(status_df, page_html)
            print(f'\nPage {page_number:,}: {auction_count} auctions updated ({min_age}-{max_age} days old).', end='', flush=True)

        else:
            min_age = -1
            error_code = page_req.status_code
            error_description = requests.status_codes._codes[error_code][0]
            print(f"\nFailed to access page {page_number} (error code {error_code}: {error_description}).")

        page_req.close()

        if min_age > 8:
            print(f'\nProcess interrupted on page {page_number}/{max_page}: older auctions already finalized.')
            break

    return status_df


def update_auctions_in_page(status_dataframe, page_html):
    """Scrape basic info on every auction in a page"""

    auction_tables = page_html.find(".Auction")

    # Loop through each auction on the page
    max_age = 0
    min_age = 100
    valid_count = 0
    for auction_html in auction_tables:

        summary_dict, age, status, column = get_auction_status(auction_html)

        if isinstance(summary_dict, dict):
            valid_count += 1

            if len(status_dataframe) > 0:
                id_match = status_dataframe['Id'].eq(summary_dict['Id'])
                matching_row = id_match.index[id_match == True].tolist()
            else:
                matching_row = None

            if matching_row:
                status_dataframe.at[matching_row[0], column] = status
            else:
                new_row = pd.DataFrame(summary_dict, index=[0])
                new_row.at[0, column] = status
                status_dataframe = status_dataframe.append(new_row)

            max_age = max(max_age, age)
            min_age = min(min_age, age)

    return status_dataframe, valid_count, min_age, max_age


def get_auction_status(auction_html):
    """Scrape auction summary data from an 'auction history' page"""

    auction_data = auction_html.find(".ShortAuctionData")[0].text.split("\n")
    data = list(map(lambda date_str: date_str.replace(u"\xa0", " "), auction_data))
    end_type = data[4][0]  # W: winning bid; M: minimum bid (failed auction)

    if end_type == 'W':

        name = auction_html.find(".AuctionCharacterName")[0].text
        header_table = auction_html.find(".AuctionHeader")[0]
        char_link = list(header_table.find(".AuctionCharacterName")[0].links)[0]
        auction_id = char_link.split("auctionid=")[-1].split("&")[0]
        end = str_to_datetime(data[3])

        today = datetime.datetime.now(pytz.timezone('CET')).replace(tzinfo=None)
        current_hour = today.hour
        time_delta = (SS_HOUR - 1 + 24 - current_hour) % 24
        tomorrow = today + datetime.timedelta(hours=time_delta)
        tomorrow = tomorrow.replace(minute=59, second=59, microsecond=0)
        auction_age = (tomorrow - end).days

        if auction_age > 7:
            column = 'Final'
        else:
            column = 'Day' + str(auction_age)

        bid_status = auction_html.find(".CurrentBid")[0].text.replace("\n", " ")
        auction_dict = dict(Id=auction_id, Name=name, End=end, Day0=None,
                            Day1=None, Day2=None, Day3=None, Day4=None, Day5=None, Day6=None, Day7=None, Final=None)
        return auction_dict, auction_age, bid_status, column

    else:
        return None, None, None, None


if __name__ == "__main__":

    # Display status message on console
    print("\nRunning Tibia Auction Status Updater!")
    if os.path.isfile(status_record_filename):
        print("\nRestoring dataframe values from file... ", end='', flush=True)
        with open(status_record_filename, 'rb') as pkl_file:
            status_dataframe = pickle.load(pkl_file)
        print(f"{len(status_dataframe):,} characters loaded!", end='\n')
    else:
        print("\nNo stored results were found.", end='\n')
        status_dataframe = pd.DataFrame(columns=dataframe_columns)

    # Scrape bazaar data for every auction
    status_dataframe = update_auction_status(status_dataframe)
    status_dataframe = status_dataframe.sort_values(['End','Id']).reset_index(drop=True)

    # Write scraped data to external files
    status_dataframe.to_pickle(status_record_filename)

    now = datetime.datetime.now()
    date = '_'.join(map(str, [now.year, now.month, now.day]))

    file_name = 'ACTSTAT_' + date
    csv_name = file_name + '.csv'
    pkl_name = file_name + '.pkl'
    with open(csv_name, 'w') as csv_file:
        csv_file.write("sep=,\n")
    status_dataframe.to_pickle(pkl_name)
    status_dataframe.to_csv(csv_name, index=True, mode='a')

    print(f"\nDone! Results written to {csv_name} and {pkl_name} files.")
