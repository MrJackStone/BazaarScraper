import requests
import datetime
import time
import sys
from requests_html import HTML
import pandas as pd
from matplotlib import pyplot as plt
import os
import math


def get_page_count():
    # Get the total number of pages from the main "Auction History" page:
    main_url = 'https://www.tibia.com/charactertrade/?subtopic=pastcharactertrades'
    time.sleep(1)
    request_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'}
    main_r = requests.get(main_url, headers=request_headers)
    if main_r.status_code == 200:
        main_html_text = main_r.text
        main_r_html = HTML(html=main_html_text)
        page_numbers = main_r_html.find(".PageLink")

        max_page = int(list(page_numbers[-1].links)[0].split("page=")[-1])
        return max_page

    else:
        return 0


def scrape_tibia_auctions(auction_dataframe):

    root_url = 'https://www.tibia.com/charactertrade/?subtopic=pastcharactertrades&currentpage='
    max_page = get_page_count()
    print(f"\nScraping a total of {max_page} pages:")

    request_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'}

    for page_number in range(1, max_page+1):

        page_url = root_url + str(page_number)

        time.sleep(1)
        page_req = requests.get(page_url, headers=request_headers)

        if page_req.status_code == 200:
            page_html_text = page_req.text
            page_html = HTML(html=page_html_text)

            page_dataframe = get_page_data(auction_dataframe, page_html, page_number)
            auction_dataframe = auction_dataframe.append(page_dataframe)
            auction_dataframe.to_pickle('last_full_scrape.pkl')

        else:
            error_code = page_req.status_code
            error_description = requests.status_codes._codes[error_code][0]
            print(f"\nFailed to access page {page_number} (error code {error_code}: {error_description}).")

    return auction_dataframe


def get_page_data(auction_dataframe, page_html, page_number):

    page_df = pd.DataFrame(None)
    auction_tables = page_html.find(".Auction")

    for auction in auction_tables:
        nth_auction_data = get_auction_data(auction_dataframe, auction, page_number)
        page_df = page_df.append(nth_auction_data)

    return page_df


def get_auction_data(auction_dataframe, auction, page_number):
    name = auction.find(".AuctionCharacterName")[0].text
    print(150 * " ", end="\r")
    print(f"Analyzing page {page_number}... parsing character '{name}'", end="\r")

    header_table = auction.find(".AuctionHeader")[0]
    char_link = list(header_table.find(".AuctionCharacterName")[0].links)[0]
    auction_id = char_link.split("auctionid=")[-1].split("&")[0]

    if auction_dataframe['Id'].eq(auction_id).sum():

        # skipped_characters.append(auction_id)
        print(f"Character '{name}' skipped (already registered).")
        return None

    else:

        header_text = header_table.text
        header_parts = header_text[header_text.find("\n")+1:].split("|")
        level = int(header_parts[0].split(":")[-1])
        voc = ''.join([capital_letter for capital_letter in header_parts[1].split(":")[-1] if capital_letter.isupper()])
        sex = header_parts[2].strip()[0]
        world = header_parts[3].split(":")[-1].strip()

        auction_data = auction.find(".ShortAuctionData")[0].text.split("\n")
        data = list(map(lambda date_str: date_str.replace(u"\xa0", " "), auction_data))
        start = date_str_to_list(data[1])
        end = date_str_to_list(data[3])
        end_type = data[4][0]  # W: winning bid; M: minimum bid (failed auction)
        bid = int(data[5].replace(",", ""))

        bid_status = auction.find(".CurrentBid")[0].text.replace("\n", " ")

        auction_dict = dict(Name=[name], Level=[level], Vocation=[voc], World=[world], Sex=[sex], Bid=[bid],
                            Type=[end_type], Start=[start], End=[end], Status=bid_status, Id=auction_id, Link=char_link,
                            Page=[page_number])
        auction_df = pd.DataFrame(auction_dict)

        skills, bank, bestiary = get_character_data(char_link)

        for skill_data in skills:
            auction_df.loc[0, skill_data] = skills[skill_data]

        for bank_data in bank:
            if isinstance(bank[bank_data], list):
                auction_df.loc[0, bank_data] = None
                auction_df[bank_data] = auction_df[bank_data].astype(object)
                auction_df.at[0, bank_data] = bank[bank_data]
            else:
                auction_df.loc[0, bank_data] = bank[bank_data]

        auction_df.loc[0, 'Bestiary'] = bestiary

        return auction_df


def get_character_data(char_url):
    time.sleep(1)
    request_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'}
    char_req = requests.get(char_url, headers=request_headers)

    if char_req.status_code == 200:
        req_text = char_req.text
        char_html = HTML(html=req_text)
        char_html.render(timeout=0)

        # # Unused so far:
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
        # Unused so far: hitpoints, mana, capacity, speed, blessings, mounts, outfits, titles
        # general_stats = general_tables[0].text.split("\n")
        # stat_names = list((map (lambda stat: stat.replace(":", ""), general_stats[0::2])))
        # stat_values = list((map (lambda value: int(value.split("/")[0].replace(",", "")), general_stats[1::2])))
        general_skills = general_tables[1].text.split("\n")
        skill_names = general_skills[0::3]
        skill_values = list((map(lambda skill: int(skill), general_skills[1::3])))
        skill_dict = {}
        for skill_name, skill_value in zip(skill_names, skill_values):
            skill_dict[skill_name] = skill_value

        # Collect bank data
        general_second_row = general_data.find(".InnerTableContainer > table > tbody > tr")[1].text.split("\n")
        bank_dict = {'Creation Date': date_str_to_list(general_second_row[1].replace("\xa0", " ")),
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
                creature_count = int(creature_entry[1][:-1].replace(",",""))
                bestiary_dict[creature_name] = creature_count

        return skill_dict, bank_dict, [bestiary_dict]

    else:

        return None


def date_str_to_list(date_str):
    date_list = date_str.replace(',', '').split(' ')
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    month = months.index(date_list[0]) + 1
    day = int(date_list[1])
    year = int(date_list[2])
    # time = date_list[3]
    return [year, month, day]


if __name__ == "__main__":

    print("\nRunning Tibia Auction Scraper!")

    last_scrape_filename = "last_full_scrape.pkl"
    if os.path.isfile(last_scrape_filename):
        print("\nRestoring dataframe values from file...")
        auction_dataframe = pd.read_pickle(last_scrape_filename)
    else:
        print("\nNo stored results were found.")
        dataframe_columns = ['Name', 'Level', 'Vocation', 'World', 'Sex', 'Bid', 'Type', 'Start', 'End', 'Status', 'Id',
                             'Link', 'Page', 'Axe Fighting', 'Club Fighting', 'Distance Fighting', 'Fishing',
                             'Fist Fighting', 'Magic Level', 'Shielding', 'Sword Fighting', 'Creation Date',
                             'Experience', 'Gold', 'Achievement Points', 'Bestiary']
        auction_dataframe = pd.DataFrame(columns=dataframe_columns)

    current_date = datetime.datetime.now()
    date = '_'.join(map(str, [current_date.year, current_date.month, current_date.day]))
    csv_name = 'BAZAAR_' + date + '.csv'
    pkl_name = 'BAZAAR_' + date + '.pkl'

    auction_dataframe = scrape_tibia_auctions(auction_dataframe)
    auction_dataframe = auction_dataframe[~auction_dataframe.duplicated(subset='Id', keep=False)]
    auction_dataframe = auction_dataframe.reset_index(drop=True)

    with open(csv_name, 'w') as csv_file:
        csv_file.write("sep=,\n")

    auction_dataframe.to_csv(csv_name, index=True, mode='a')
    auction_dataframe.to_pickle(pkl_name)
    auction_dataframe.to_pickle('last_scrape.pkl')
    auction_dataframe.to_pickle(last_scrape_filename)

    print(f"\nDone! Results written to {csv_name}.CSV file.")
