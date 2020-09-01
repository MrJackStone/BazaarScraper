import requests
import datetime
import sys
from requests_html import HTML
import pandas as pd
from matplotlib import pyplot as plt
import os
import math


def get_page_count():
    # Get the total number of pages from the main "Auction History" page:
    main_url = 'https://www.tibia.com/charactertrade/?subtopic=pastcharactertrades'
    main_r = requests.get(main_url)
    if main_r.status_code == 200:
        main_html_text = main_r.text
        main_r_html = HTML(html=main_html_text)
        page_numbers = main_r_html.find(".PageLink")

        #max_page = max(list(map(lambda page_html_element: int(page_html_element.text), page_numbers)))
        max_page = int(list(page_numbers[-1].links)[0].split("page=")[-1])
        return max_page

    else:
        return 0


def scrape_tibia_auctions():

    root_url = 'https://www.tibia.com/charactertrade/?subtopic=pastcharactertrades&currentpage='
    max_page = get_page_count()
    print(f"\nScraping a total of {max_page} pages:")

    dataframe_columns = ['Name', 'Level', 'Vocation', 'World', 'Sex', 'Bid', 'Type', 'Start', 'End', 'Page']
    auction_dataframe = pd.DataFrame(columns=dataframe_columns)

    for page_number in range(1, max_page+1):

        page_url = root_url + str(page_number)

        page_req = requests.get(page_url)

        if page_req.status_code == 200:
            page_html_text = page_req.text
            page_html = HTML(html=page_html_text)

            page_dataframe = get_page_data(page_html, page_number, dataframe_columns)
            auction_dataframe = auction_dataframe.append(page_dataframe)


    return auction_dataframe


def get_page_data(page_html, page_number, dataframe_columns):

    page_df = pd.DataFrame(columns=dataframe_columns)
    auction_tables = page_html.find(".Auction")

    for auction in auction_tables:
        nth_auction_data = get_auction_data(auction, page_number)
        page_df = page_df.append(pd.DataFrame(nth_auction_data))

    return page_df


def get_auction_data(auction, page_number):
    name = auction.find(".AuctionCharacterName")[0].text
    print(150 * " ", end="\r")
    print(f"Analyzing page {page_number}... parsing character '{name}'", end="\r")

    header_text = auction.find(".AuctionHeader")[0].text
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

    auction_data = dict(Name=[name], Level=[level], Vocation=[voc], World=[world], Sex=[sex], Bid=[bid],
                        Type=[end_type], Start=[start], End=[end], Page=[page_number])

    return auction_data


def date_str_to_list(date_str):
    date_list = date_str.replace(',', '').split(' ')
    months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    month = months.index(date_list[0]) + 1
    day = int(date_list[1])
    year = int(date_list[2])
    time = date_list[3]
    return [year, month, day, time]


if __name__ == "__main__":

    print("\nRunning Tibia Auction Scraper!")

    current_date = datetime.datetime.now()
    date = '_'.join(map(str, [current_date.year, current_date.month, current_date.day]))
    csv_name = 'BAZAAR_' + date + '.csv'
    pkl_name = 'BAZAAR_' + date + '.pkl'

    auction_dataframe = scrape_tibia_auctions()

    with open(csv_name, 'w') as csv_file:
        csv_file.write("sep=,\n")

    auction_dataframe.to_csv(csv_name, index=True, mode='a')
    auction_dataframe.to_pickle(pkl_name)
    auction_dataframe.to_pickle('last_scrape.pkl')

    successful_auctions = auction_dataframe[auction_dataframe.Type.eq("W")]
    failed_auctions = auction_dataframe[auction_dataframe.Type.eq("M")]

    #
    #
    #
    #
    #
    #
    #
    #

    total_transactions = len(auction_dataframe)
    successful_transactions = len(successful_auctions)
    failed_transactions = len(failed_auctions)

    success_ratio = successful_transactions / total_transactions
    fail_ratio = failed_transactions / total_transactions

    total_value = successful_auctions['Bid'].sum()
    average_sale = total_value / successful_transactions

    auction_tax = total_transactions * 50
    sale_tax = [math.floor(tax) for tax in list(successful_auctions['Bid'] * 0.12)]
    sale_tax_total = sum(sale_tax)
    total_taxes = auction_tax + sale_tax_total

    s_EK = successful_auctions[successful_auctions.Vocation.isin(['EK', 'K'])]
    s_RP = successful_auctions[successful_auctions.Vocation.isin(['RP', 'P'])]
    s_ED = successful_auctions[successful_auctions.Vocation.isin(['ED', 'D'])]
    s_MS = successful_auctions[successful_auctions.Vocation.isin(['MS', 'S'])]
    s_N = successful_auctions[successful_auctions.Vocation.eq('N')]

    traded_EKs = len(s_EK)
    traded_RPs = len(s_RP)
    traded_EDs = len(s_ED)
    traded_MSs = len(s_MS)
    traded_Ns = len(s_N)

    f_EK = failed_auctions[failed_auctions.Vocation.isin(['EK', 'K'])]
    f_RP = failed_auctions[failed_auctions.Vocation.isin(['RP', 'P'])]
    f_ED = failed_auctions[failed_auctions.Vocation.isin(['ED', 'D'])]
    f_MS = failed_auctions[failed_auctions.Vocation.isin(['MS', 'S'])]
    f_N = failed_auctions[failed_auctions.Vocation.eq('N')]

    count_EK = len(s_EK)
    count_RP = len(s_RP)
    count_ED = len(s_ED)
    count_MS = len(s_MS)
    count_N = len(s_N)
    count_total = count_EK + count_RP + count_ED + count_MS + count_N

    print(f"\nDone! Results written to {csv_name}.CSV file.")

    with open('totals_output.txt', 'w') as out_file:
        out_file.write(f"\nConcluded auctions: {total_transactions}")
        out_file.write(f"\nSuccessful auctions: {successful_transactions} ({success_ratio * 100}%)")
        out_file.write(f"\nFailed auctions: {failed_transactions} ({fail_ratio * 100}%)")
        out_file.write(f"\nEKs traded: {traded_EKs} ({100 * traded_EKs / successful_transactions}%)")
        out_file.write(f"\nRPs traded: {traded_RPs} ({100 * traded_RPs / successful_transactions}%)")
        out_file.write(f"\nEDs traded: {traded_EDs} ({100 * traded_EDs / successful_transactions}%)")
        out_file.write(f"\nMSs traded: {traded_MSs} ({100 * traded_MSs / successful_transactions}%)")
        out_file.write(f"\nNONEs traded: {traded_Ns} ({100 * traded_Ns / successful_transactions}%)")
        out_file.write(f"\nSuccessful auctions total {total_value} Tibia Coins.")
        out_file.write(f"\nAuction taxes total {auction_tax} Tibia Coins.")
        out_file.write(f"\nSale taxes total {sale_tax_total} Tibia Coins.")
        out_file.write(f"\nTotal taxes: {total_taxes} Tibia Coins")

    print(f"\nConcluded auctions: {total_transactions}")
    print(f"\nSuccessful auctions: {successful_transactions} ({success_ratio*100}%)")
    print(f"\nFailed auctions: {failed_transactions} ({fail_ratio*100}%)")

    print(f"\nEKs traded: {traded_EKs} ({100*traded_EKs/successful_transactions}%)")
    print(f"\nRPs traded: {traded_RPs} ({100*traded_RPs/successful_transactions}%)")
    print(f"\nEDs traded: {traded_EDs} ({100*traded_EDs/successful_transactions}%)")
    print(f"\nMSs traded: {traded_MSs} ({100*traded_MSs/successful_transactions}%)")
    print(f"\nNONEs traded: {traded_Ns} ({100*traded_Ns/successful_transactions}%)")

    print(f"\nSuccessful auctions total {total_value} Tibia Coins.")
    print(f"\nAuction taxes total {auction_tax} Tibia Coins.")
    print(f"\nSale taxes total {sale_tax_total} Tibia Coins.")
    print(f"\nTotal taxes: {total_taxes} Tibia Coins")
