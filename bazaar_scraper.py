import requests
import datetime
import time
from requests_html import HTML
from requests_html import HTMLSession
import pandas as pd
import os
import logging

# Global variables:
request_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'}
#   Auction history url (main page)
root_url = 'https://www.tibia.com/charactertrade/?subtopic=pastcharactertrades'
#   Output dataframe columns: Name               [str]
#                             Level              [int]
#                             Vocation           [str]   'E', 'EK', 'P', 'RP', 'D', 'ED', 'S', 'MS', 'N'
#                             World              [str]
#                             Sex                [str]   'M': male | 'F': female
#                             Bid                [int]
#                             Type               [str]   'W': auction was won | 'M': auction without bids
#                             Start              [list]  [<year:int>, <month:int>, <day:int>]
#                             End                [list]  [<year:int>, <month:int>, <day:int>]
#                             Status             [str]   website text: 'finished', 'currently processed', 'cancelled', 'will be transferred...'
#                             Id                 [str]   auction identification (unique)
#                             Link               [str]   url to specific auction
#                             Page               [int]   'auction history' page number at which the auction was found
#                             Axe Fighting       [int]
#                             Club Fighting      [int]
#                             Distance Fighting  [int]
#                             Fishing            [int]
#                             Fist Fighting      [int]
#                             Magic Level        [int]
#                             Shielding          [int]
#                             Sword Fighting     [int]
#                             Creation Date      [list]  [<year:int>, <month:int>, <day:int>]
#                             Experience         [int]
#                             Gold               [int]
#                             Achievement Points [int]
#                             Bestiary           [dict] {'<creature_name_1:str>':<number_of_kills:int>, '<creature_name_2:str>':<number_of_kills:int> ...}
dataframe_columns = ['Name', 'Level', 'Vocation', 'World', 'Sex', 'Bid', 'Type', 'Start', 'End', 'Status', 'Id',
                     'Link', 'Page', 'Axe Fighting', 'Club Fighting', 'Distance Fighting', 'Fishing',
                     'Fist Fighting', 'Magic Level', 'Shielding', 'Sword Fighting', 'Creation Date',
                     'Experience', 'Gold', 'Achievement Points', 'Bestiary']
# File to which the full dataframe will be written at the end of the run
last_scrape_filename = 'last_full_scrape.pkl'
# File to which partial dataframes will be written as each page is scraped
temp_scrape_filename = 'tmp_partial_scrape.pkl'
# Initialize counters: skipped & scraped chars
skipped_chars = 0
scraped_chars = 0


def get_page_count():
    """ Get the total number of pages (as integer) from the main "Auction History" page: """
    time.sleep(1)
    main_r = requests.get(root_url, headers=request_headers)
    if main_r.status_code == 200:
        main_r_html = HTML(html=main_r.text)
        page_numbers = main_r_html.find(".PageLink")
        main_r.close()
        max_page = int(list(page_numbers[-1].links)[0].split("page=")[-1])
        return max_page
    else:
        return 0


def scrape_tibia_auctions():
    """Scrape all bazaar data"""
    global auction_dataframe

    max_page = get_page_count()
    print(f"\nScraping a total of {max_page} pages:", end='\n')

    # Loop through each 'auction history' page
    for page_number in range(1, max_page + 1):

        page_url = root_url + '&currentpage=' + str(page_number)
        time.sleep(1)
        page_req = requests.get(page_url, headers=request_headers)

        if page_req.status_code == 200:
            page_html = HTML(html=page_req.text)
            page_dataframe = get_page_data(page_html, page_number)
            auction_dataframe = auction_dataframe.append(page_dataframe)
            auction_dataframe.to_pickle(temp_scrape_filename)

        else:
            error_code = page_req.status_code
            error_description = requests.status_codes._codes[error_code][0]
            print(f"\nFailed to access page {page_number} (error code {error_code}: {error_description}).")

        page_req.close()

    return auction_dataframe


def get_page_data(page_html, page_number):
    """Scrape every auction in a page"""
    global auction_dataframe

    page_df = pd.DataFrame(None)
    auction_tables = page_html.find(".Auction")

    # Loop through each auction on the page
    for auction in auction_tables:
        nth_auction_data = get_auction_data(auction, page_number)
        page_df = page_df.append(nth_auction_data)

    return page_df


def get_auction_data(auction, page_number):
    """Scrape all data from a single auction"""
    global auction_dataframe, skipped_chars, scraped_chars

    # Scrape auction summary data
    summary_dict = get_summary_data(auction, page_number)

    # Decide whether or not to perform full scrape on the auction
    if auction_dataframe['Id'].eq(summary_dict['Id']).sum():
        # Skip auction if it's already been registered
        skipped_chars += 1
        print("skipped.", end='\r')
        return None

    else:
        # Scrape full auction data
        print("scraping...", end='')
        auction_df = get_character_data(summary_dict)
        print(" done!", end='\r')
        scraped_chars += 1
        return auction_df


def get_summary_data (auction, page_num):
    """Scrape auction summary data from an 'auction history' page"""
    global skipped_chars, scraped_chars

    name = auction.find(".AuctionCharacterName")[0].text

    # Print status message to console
    print(120 * " ", end='\r')
    print(f"[Skipped: {skipped_chars:>7,} | Scraped: {scraped_chars:>7,}] Analyzing page {page_num}: parsing character '{name}'... ", end='')

    # Scrape auction header
    header_table = auction.find(".AuctionHeader")[0]
    char_link = list(header_table.find(".AuctionCharacterName")[0].links)[0]
    auction_id = char_link.split("auctionid=")[-1].split("&")[0]
    header_text = header_table.text
    header_parts = header_text[header_text.find("\n") + 1:].split("|")
    level = int(header_parts[0].split(":")[-1])
    voc = ''.join([capital_letter for capital_letter in header_parts[1].split(":")[-1] if capital_letter.isupper()])
    sex = header_parts[2].strip()[0]
    world = header_parts[3].split(":")[-1].strip()

    # Scrape auction table
    auction_data = auction.find(".ShortAuctionData")[0].text.split("\n")
    data = list(map(lambda date_str: date_str.replace(u"\xa0", " "), auction_data))
    start = date_str_to_list(data[1])
    end = date_str_to_list(data[3])
    end_type = data[4][0]  # W: winning bid; M: minimum bid (failed auction)
    bid = int(data[5].replace(",", ""))

    # Scrape status box
    bid_status = auction.find(".CurrentBid")[0].text.replace("\n", " ")

    # Store auction summary data in a dictionary
    auction_dict = dict(Name=name, Level=level, Vocation=voc, World=world, Sex=sex, Bid=bid, Type=end_type,
                        Start=[start], End=[end], Status=bid_status, Id=auction_id, Link=char_link, Page=page_num)

    return auction_dict


def get_character_data(summary_dict):
    """Scrape full auction data from the character's individual page"""

    char_url = summary_dict['Link']
    time.sleep(1)
    char_req = HTMLSession().get(char_url, headers=request_headers)

    if char_req.status_code == 200:

        char_req.html.render(timeout=0)
        char_html = char_req.html

        # # Available information, unused thus far:
        # item_data = html.find("#ItemSummary")[0]
        # store_data = html.find("#StoreItemSummary")[0]
        # mount_data = html.find("#Mounts")[0]
        # outfit_data = html.find("#Outfits")[0]
        # store_outfits_data = html.find("#StoreOutfits")[0]
        # blessing_data = html.find("#Blessings")[0]
        # imbuement_data = html.find("#Imbuements")[0]
        # charm_data = html.find("#Charms")[0]
        # area_data = html.find("#CompletedCyclopediaMapAreas")[0]
        # quest_data = html.find("#CompletedQuestLines")[0]
        # title_data = html.find("#Titles")[0]
        # achievement_data = html.find("#Achievements")[0]

        # Collect skills
        general_data = char_html.find("#General")[0]
        general_first_row = general_data.find(".InnerTableContainer > table > tbody > tr > td > table > tbody > tr")[0]
        general_tables = general_first_row.find("table")
        general_skills = general_tables[1].text.split("\n")
        skill_names = general_skills[0::3]
        skill_values = list((map(lambda skill: int(skill), general_skills[1::3])))
        skill_dict = {}
        for skill_name, skill_value in zip(skill_names, skill_values):
            skill_dict[skill_name] = skill_value
        # Available information, unused thus far: hitpoints, mana, capacity, speed, blessings, mounts, outfits, titles
        # general_stats = general_tables[0].text.split("\n")
        # stat_names = list((map (lambda stat: stat.replace(":", ""), general_stats[0::2])))
        # stat_values = list((map (lambda value: int(value.split("/")[0].replace(",", "")), general_stats[1::2])))

        # Collect bank data
        general_second_row = general_data.find(".InnerTableContainer > table > tbody > tr")[1].text.split("\n")
        bank_dict = {'Creation Date': (date_str_to_list(general_second_row[1].replace("\xa0", " ")),),
                     'Experience': int(general_second_row[3].replace(",", "")),
                     'Gold': int(general_second_row[5].replace(",", "")),
                     'Achievement Points': int(general_second_row[7].replace(",", ""))}

        # Collect bestiary
        bestiary_data = char_html.find("#BestiaryProgress")[0]
        bestiary_table = bestiary_data.find(".TableContent")[0]
        bestiary_rows = bestiary_table.find("tr")[1:-1]
        bestiary_dict = {}
        if len(bestiary_rows) > 0:
            for bestiary_creature in bestiary_rows:
                creature_entry = bestiary_creature.text.split("\n")
                creature_name = creature_entry[-1]
                creature_count = int(creature_entry[1][:-1].replace(",", ""))
                bestiary_dict[creature_name] = creature_count

        char_req.session.close()

        # Incorporate character data to dictionary and convert to dataframe
        summary_dict.update(skill_dict)
        summary_dict.update(bank_dict)
        char_dataframe = pd.DataFrame(summary_dict)
        char_dataframe.loc[0, 'Bestiary'] = [bestiary_dict]

        return char_dataframe

    else:

        return None


def date_str_to_list(date_str):
    """Converts string formatted as 'Aug 14, 2020 <dismissed_info>' to integer list [2020, 8, 14]"""
    date_list = date_str.replace(',', '').split(' ')
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    month = months.index(date_list[0]) + 1
    day = int(date_list[1])
    year = int(date_list[2])
    # time = date_list[3]
    return [year, month, day]


if __name__ == "__main__":

    # Display status message on console
    print("\nRunning Tibia Auction Scraper!")
    if os.path.isfile(last_scrape_filename):
        print("\nRestoring dataframe values from file... ", end='')
        auction_dataframe = pd.read_pickle(last_scrape_filename)
        print(f"{len(auction_dataframe):,} characters loaded!", end ='\n')
    else:
        print("\nNo stored results were found.", end='\n')
        auction_dataframe = pd.DataFrame(columns=dataframe_columns)

    # Scrape bazaar data for every auction
    auction_dataframe = scrape_tibia_auctions()
    auction_dataframe = auction_dataframe[~auction_dataframe.duplicated(subset='Id', keep=False)]
    auction_dataframe = auction_dataframe.reset_index(drop=True)

    # Write scraped data to external files
    now = datetime.datetime.now()
    date = '_'.join(map(str, [now.year, now.month, now.day]))
    file_name = 'BAZAAR_' + date
    csv_name = file_name + '.csv'
    pkl_name = file_name + '.pkl'
    with open(csv_name, 'w') as csv_file:
        csv_file.write("sep=,\n")
    auction_dataframe.to_csv(csv_name, index=True, mode='a')
    auction_dataframe.to_pickle(pkl_name)
    auction_dataframe.to_pickle(last_scrape_filename)

    print(f"\nDone! Results written to {csv_name} and {pkl_name} files.")
