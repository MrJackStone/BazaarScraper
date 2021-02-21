import os
import pandas as pd
import datetime
import requests
from requests_html import HTML
import math
import concurrent.futures
from bazaar_scraper import str_to_datetime
import time
import timeit
import logging

home_dir = 'D:\\Programming\\Python\\TibiaAuctions'

scraped_auctions_filename = 'last_full_scrape.pkl'
scraped_info_filename = 'scraped_followup.pkl'
followup_filename = 'character_followup.pkl'
logging_file = 'followup_log.txt'

name_range = 50000
recent_check_threshold = 10
batch_size = 100
batch_wait = 3

info_scraping_time_estimate = 0.2  # estimated time to scrape a single character when running threading, in seconds
incorp_time_estimate = 0.04  # estimated time to incorporate an auction to follow-up dataframe, in seconds

followup_columns = ('Id', 'Name', 'World', 'Sex', 'Vocation', 'Level', 'AccessDate', 'NewName', 'NewWorld', 'NewSex',
                    'NewVocation', 'NewLevel', 'LastLogin', 'AccountStatus', 'NewId', 'Scheduled', 'Deleted')
today = datetime.datetime.now()
failed_updates = []


def update_row(df, row, NewId=None, NewName=None, NewWorld=None, NewSex=None, NewVocation=None, NewLevel=None,
               LastLogin=None, AccountStatus=None, AccessDate=None, Scheduled=None, Deleted=None):
    update_pairs = [(None, 'NewId', NewId),
                    ('Name', 'NewName', NewName),
                    ('World', 'NewWorld', NewWorld),
                    ('Sex', 'NewSex', NewSex),
                    ('Vocation', 'NewVocation', NewVocation),
                    ('Level', 'NewLevel', NewLevel),
                    (None, 'LastLogin', LastLogin),
                    (None, 'AccountStatus', AccountStatus),
                    (None, 'AccessDate', AccessDate),
                    (None, 'Scheduled', Scheduled),
                    (None, 'Deleted', Deleted)]
    for pair in update_pairs:
        check_key = pair[0]
        set_key = pair[1]
        set_value = pair[2]
        if check_key:
            # Case 1: different column needs to be checked before setting value
            if set_value != None:
                original_value = df.iloc[row][check_key]
                if original_value != set_value:
                    # Case 1.1: new value is different -- set to value
                    df.at[row, set_key] = set_value
                else:
                    # Case 1.2: new value is the same -- set to None
                    df.at[row, set_key] = None
        else:
            # Case 2: set value without checking any columns
            if set_value != None:
                df.at[row, set_key] = set_value
    return df


def load_scraped_info ():
    scraped_data = pd.read_pickle('scraped_followup.pkl')
    data_dict = {entry.OriginalName: list(entry.values)[1:] for _,entry in scraped_data.iterrows()}
    return data_dict


def skip_check(row, followup_df):
    new_id = followup_df.iloc[row]['NewId']
    deleted = followup_df.iloc[row]['Deleted']
    scheduled = followup_df.iloc[row]['Scheduled']

    if isinstance(new_id, str) and len(new_id) > 0:
        return 'resold'
    elif deleted is True:
        return 'deleted'
    # elif scheduled:
    #     return 'scheduled to be deleted'
    else:
        return None


def rindex(list, value):
    return len(list) - 1 - list[::-1].index(value) if value in list else None


def findex(list, value):
    return list.index(value) if value in list else None


def get_tibiaring_alias(url_name):
    # Standard TibiaRing url and headers
    tibiaring_root = 'http://www.tibiaring.com/char.php?c='
    tibiaring_headers = {"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                         "Accept-Language": "pt-BR,pt;q=0.8,en-US;q=0.5,en;q=0.3",
                         "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:81.0) Gecko/20100101 Firefox/81.0"}

    # Generate TibiaRing url
    char_url = tibiaring_root + url_name

    # Access TibiaRing page for character
    req = requests.get(char_url, headers=tibiaring_headers)

    # Failed request
    if req.status_code != 200:
        return None

    # Empty page
    text = req.text
    if len(text) == 0:
        return -1

    # Successful access: return new character name
    html = HTML(html=text)
    character_box = html.find(".CSC")[0]
    new_name = character_box.text
    return new_name


def get_character_info(char_name, headers=None):
    url_root = 'https://www.tibia.com/community/?subtopic=characters&name='
    default_headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'}

    url_name = char_name.replace(' ', '+').replace('ö', '%F6')
    char_url = url_root + url_name
    if not headers:
        headers = default_headers

    # First access to character page on Tibia.com
    req = requests.get(char_url, headers=headers)
    if req.status_code != 200:
        print(f'Checking: {char_name:<25} --- Tibia.com ERROR {req.status_code}: {req.reason}.')
        return req.status_code
    tx = req.text
    html = HTML(html=tx)

    # Check if character name is valid
    character_information_table = html.find('table')[0].text
    if character_information_table.find('Character Information') < 0:
        new_name = get_tibiaring_alias(url_name)
        if not new_name:
            print(f'Checking: {char_name:<25} --- checking TibiaRing for alias... not found.')
            return None
        elif new_name == -1:
            print(f'Checking: {char_name:<25} --- checking TibiaRing for alias... DELETED.')
            return 'DELETED'
        new_char_url = url_root + new_name.replace(' ', '+').replace('ö', '%F6')
        req = requests.get(new_char_url, headers=headers)
        if req.status_code != 200:
            print(f'Checking: {char_name:<25} --- checking TibiaRing for alias... Tibia.com ERROR {req.status_code}: {req.reason}.')
            return req.status_code
        tx = req.text
        html = HTML(html=tx)
        character_information_table = html.find('table')[0].text
        if character_information_table.find('Character Information') < 0:
            print(f'Checking: {char_name:<25} --- DELETED. ')
            return 'DELETED'
    info = character_information_table.replace('\xa0', ' ').split('\n')

    # Collect character info
    name = info[info.index('Name:') + 1].split(' (traded)')[0]

    # Check if character is scheduled to be deleted
    if name.find(', will be deleted') >= 0:
        name_del = name
        name = name_del.split(',')[0]
        del_date = str_to_datetime(name_del.split('at ')[-1])
    else:
        del_date = None

    # Process collected information
    sex = info[info.index('Sex:') + 1][0].upper()
    world = info[info.index('World:') + 1]
    vocation = ''.join(list(map(lambda s: s[0], info[info.index('Vocation:') + 1].split())))
    level = int(info[info.index('Level:') + 1])
    last_login = info[info.index('Last Login:') + 1]
    if last_login.find('never') >= 0:
        login = None
    else:
        login = str_to_datetime(last_login)
    status = ''.join(list(map(lambda s: s[0], info[info.index('Account Status:') + 1].split())))

    access = datetime.datetime.now()
    print(f'Checking: {char_name:<25} --- succeeded!')
    return [name, world, sex, vocation, level, login, status, del_date, access]


def incorporate_auction(auction, followup_df):

    # Get auction data
    auction_id = auction.Id
    auction_name = auction.Name
    auction_world = auction.World
    auction_sex = auction.Sex
    auction_vocation = auction.Vocation
    auction_level = auction.Level

    print(f'Parsing character {auction_name} (#{auction_id}): ', end='', flush=True)

    # Check if auction has already been registered
    id_match = findex(list(followup_df.Id), auction_id)
    if isinstance(id_match, int):
        print('\n\t\t\t\tFound matching ID. Returning unmodified follow-up dataframe.')
        return followup_df

    else:
        # Look for name match: first in column 'Name' (last match) then in column 'NewName' (first match)
        name_match = rindex(list(followup_df.Name), auction_name)
        if not isinstance(name_match, int):
            name_match = findex(list(followup_df.NewName), auction_name)

        if isinstance(name_match, int):
            print('\n\t\t\t\tFound matching name! ', end='', flush=True)
            corresponding_id = followup_df.iloc[name_match].Id
            # Case: auctioned character's name matches registered name
            if skip_reason:=skip_check(name_match, followup_df):
                print(f'\n\t\t\t\tSpurious name coincidence (#{corresponding_id}): matches permanently closed entry ({skip_reason}).', end='\n', flush=True)
            else:
                print(f'\n\t\t\t\tUpdating entry #{corresponding_id}: closing permanently as "resold".', end='', flush=True)
                followup_df = update_row(followup_df, name_match, NewId=auction_id, NewName=auction_name, NewWorld=auction_world,
                                         NewSex=auction_sex, NewVocation=auction_vocation, NewLevel=auction_level)

        print('\n\t\t\t\tAppending new row... ', end='', flush=True)
        output_followup = followup_df.append({'Id': auction_id, 'Name': auction_name, 'World': auction_world, 'Sex': auction_sex,
                                              'Vocation': auction_vocation, 'Level': auction_level}, ignore_index=True)
        print('done!', end='\n', flush=True)

    return output_followup


def update_followup(followup_df, scraped_char_dict):

    registered_names = list(followup_df.Name)
    registered_new_names = list(followup_df.NewName)
    failed_requests = []

    for character_name in scraped_char_dict.keys():

        character_data = scraped_char_dict[character_name]
        print(f'Updating character {character_name}: ', end='', flush=True)

        # Check if character info was successfully collected
        if isinstance(character_data, list):
            print(f'\n\tInfo successfully collected!', end='', flush=True)
            scraped_data = character_data + [None]
        elif isinstance(character_data, int):
            print(f'\n\tRequest failed --- error code: {character_data}.')
            scraped_data = None
        elif character_data is None:
            print(f'\n\tCharacter not found --- presumed deleted.', end='', flush=True)
            scraped_data = 8*[None] + [datetime.datetime.now(), True]
        elif character_data == 'DELETED':
            print(f'\n\tCharacter deleted.', end='', flush=True)
            scraped_data = 8*[None] + [datetime.datetime.now(), True]
        else:
            print(f'\n\t*** UNEXPECTED DATA*** : {character_data}')
            scraped_data = None

        # Update follow-up dataframe with collected character info
        if not scraped_data:
            failed_requests.append(character_name)
        else:
            print('\n\tUpdating character info... ', end='', flush=True)
            char, world, sex, vocation, level, login, status, deletion, access, deleted = scraped_data

            # Look for name match: first in column 'Name' (last match) then in column 'NewName' (first match)
            name_match = rindex(registered_names, character_name)
            if isinstance(name_match, int):
                match_type = 'Name'
            else:
                name_match = findex(registered_new_names, character_name)
                match_type = 'NewName' if isinstance(name_match, int) else None

            if match_type:
                print(f'found matching "{match_type}": updating... ', end='', flush=True)
                followup_df = update_row(followup_df, name_match, NewName=char, NewWorld=world, NewSex=sex,
                                         NewVocation=vocation, NewLevel=level, LastLogin=login, AccountStatus=status,
                                         AccessDate=access, Scheduled=deletion, Deleted=deleted)
                print('done!')
            else:
                print(f'\n\t\t\t\tUnexpected error: character name not found in follow-up dataframe.')

    return followup_df, failed_requests


def names_to_check(followup_df, new_auctions_df):
    if followup_df.empty:
        registered_names = []
        changed_names = []
        excluded_names = set()
    else:
        registered_names = list(followup_df.Name)
        changed_names = [name for name in followup_df.NewName if isinstance(name, str)]
        deleted_check = followup_df.Deleted.notnull()
        renamed_check = followup_df.NewName.notnull()
        recent_check = followup_df.AccessDate.apply(lambda date: (today - date).days if isinstance(date, datetime.datetime) else recent_check_threshold) < recent_check_threshold
        excluded_names = {name for name, deleted, renamed, recent in zip(registered_names, deleted_check, renamed_check, recent_check) if deleted or renamed or recent}

    new_names = list(new_auctions_df.Name)

    all_names = set(registered_names + changed_names + new_names)

    return all_names - excluded_names | set(new_names)


def filter_new_auctions(followup_df, auctions_df):
    if followup_df.empty:
        return auctions_df
    else:
        registered_ids = list(followup_df.Id)
        return auctions_df[~auctions_df.Id.isin(registered_ids)]


if __name__ == "__main__":

    followup_start = timeit.default_timer()

    # initialize logging
    logging.basicConfig(filename=logging_file, level=logging.INFO, filemode='a')

    # Import scraped auctions and sort them by end date
    print('\nLoading scraped auctions...', end='', flush=True)
    os.chdir(home_dir)
    adf = pd.read_pickle(scraped_auctions_filename)
    nb = adf.drop('Bestiary', axis=1)
    won_auctions = nb[nb.Type.eq("W")]
    sa = won_auctions[won_auctions.Status.eq('finished')]
    sbe = sa.sort_values(by='End').reset_index(drop=True)
    print(f' done: {len(sbe):,} auctions loaded!', end='\n', flush=True)

    # Load tracked characters
    print('\nLoading recorded follow-up...', end='', flush=True)
    if os.path.isfile(followup_filename):
        character_followup = pd.read_pickle(followup_filename)
        print(f' done: {len(character_followup):,} entries loaded!', end='\n', flush=True)

    else:
        character_followup = pd.DataFrame(columns=followup_columns)
        print(' no records: new follow-up DataFrame created.', end='\n', flush=True)
    print('\n\n')

    # Get newly scraped auctions
    new_auctions = filter_new_auctions(character_followup, sbe)
    incorporated_auction_count = len(new_auctions)

    # Get character names to search
    searched_character_names = names_to_check(character_followup, new_auctions)
    searched_character_names = list(searched_character_names)[0:name_range if name_range else None]
    character_count = len(searched_character_names)

    # Set batch scraping parameters
    first_index = 0
    last_index = min(first_index + batch_size, character_count)
    run_count = math.ceil(character_count / batch_size)
    run_index = 0
    estimated_time = character_count*info_scraping_time_estimate + run_count*batch_wait + incorporated_auction_count*incorp_time_estimate

    # Display run summary
    print(f'\nRun summary:\n'
          f'\t\t{incorporated_auction_count:,} new auctions to incorporate.\n'
          f'\t\t{character_count:,} character names to search.\n'
          f'\t\tEstimated scraping run time: {estimated_time/60:,.2f} minutes.\n\n')
    time.sleep(5)

    # Incorporate new auctions into follow-up dataframe
    print(f'\nIncorporating {incorporated_auction_count:,} new auctions...')
    incorp_start = timeit.default_timer()
    for _,auction in new_auctions.iterrows():
        character_followup = incorporate_auction(auction, character_followup)
    incorp_end = timeit.default_timer()
    incorp_elapsed = (incorp_end - incorp_start)/60
    character_followup.to_pickle(followup_filename)
    print(f'\n\nFinished incorporating {incorporated_auction_count:,} auctions in {incorp_elapsed:,.2f} minutes.\n')

    # Run batch character info scraping
    print(f'\nScraping info for {character_count:,} characters...')
    scrape_start = timeit.default_timer()
    character_info_dict = {}
    total_403_count = 0
    total_None_count = 0
    total_deleted_count = 0
    total_collected_count = 0

    while first_index < character_count:

        batch_start = timeit.default_timer()
        run_index += 1
        print(f'\n\nExecuting batch run #{run_index} out of {run_count}:\n\n')

        selected_names = searched_character_names[first_index:last_index]

        # Collect current character info
        with concurrent.futures.ThreadPoolExecutor() as executor:
            nth_run_collection = list(executor.map(get_character_info, selected_names))

        # Aggregate scraped info
        batch_end = timeit.default_timer()
        batch_time = batch_end - batch_start
        total_time = batch_end - scrape_start
        character_info_dict.update({char_name: char_info for char_name,char_info in zip(selected_names, nth_run_collection)})

        # Collection totals for current iteration
        nth_403_count = nth_run_collection.count(403)
        nth_None_count = nth_run_collection.count(None)
        nth_deleted_count = nth_run_collection.count('DELETED')
        nth_collected_count = sum(isinstance(collection, list) for collection in nth_run_collection)

        # Collection totals for cumulative iterations
        total_403_count += nth_403_count
        total_None_count += nth_None_count
        total_deleted_count += nth_deleted_count
        total_collected_count += nth_collected_count

        # Display report and wait before next batch scraping iteration
        print(f'\n\nFinished run #{run_index} in {batch_time:.1f} seconds (sleeping for {batch_wait} seconds)')
        print(f'\tTotal elapsed time: {total_time/60:.1f} minutes.')
        print(f'\tError 403: {nth_403_count:>5,}\n'
              f'\tDeleted:   {nth_deleted_count:>5,}\n'
              f'\tNot found: {nth_None_count:>5,}\n'
              f'\tCollected: {nth_collected_count:>5,}')
        time.sleep(batch_wait)

        # Update indices for next batch scrape iteration
        first_index = last_index
        last_index = min(first_index + batch_size, character_count)

    # Done scraping: display report
    scrape_end = timeit.default_timer()
    scrape_elapsed = (scrape_end - scrape_start)/60
    print(f'\n\nDone scraping!')
    print(f'\tTime elapsed: {scrape_elapsed:,.2f} minutes.')
    print(f'\tError 403: {total_403_count:>8,}\n'
          f'\tDeleted:   {total_deleted_count:>8,}\n'
          f'\tNot found: {total_None_count:>8,}\n'
          f'\tCollected: {total_collected_count:>8,}\n\n')
    time.sleep(batch_wait/2)

    # Store scraped data in dataframe and export to .PKL file
    print(f"\nWriting collected info to file '{scraped_info_filename}'... ", end='', flush=True)
    scraped_df = pd.DataFrame()
    scraped_columns = ['OriginalName', 'Name', 'World', 'Sex', 'Vocation', 'Level', 'LastLogin', 'AccountStatus', 'Scheduled', 'AccessDate']
    for char in character_info_dict.keys():
        info = character_info_dict[char]
        if not isinstance(info, list):
            info = [None] * 9
        char_info_dict = {key: value for key, value in zip(scraped_columns, [char] + info)}
        scraped_df = scraped_df.append(pd.DataFrame(char_info_dict, index=[0]))
    scraped_df = scraped_df.reset_index(drop=True)
    scraped_df.to_pickle(scraped_info_filename)
    print('done!\n')

    # Update follow-up entries using scraped data
    print(f'\nUpdating info for {len(character_info_dict):,} characters...')
    update_start = timeit.default_timer()
    character_followup, failed_updates = update_followup(character_followup, character_info_dict)
    update_end = timeit.default_timer()
    update_elapsed = (update_end - update_start)/60
    print(f'\nFinished updating {len(character_info_dict):,} characters on follow-up dataframe in {update_elapsed:,.2f} minutes!')

    # Get time at the end of the run
    end_date = datetime.datetime.now()
    file_date = '_'.join(map(str, [end_date.year, end_date.month, end_date.day]))
    print_date = '/'.join(map(str, [end_date.year, end_date.month, end_date.day]))
    followup_today = 'cf_' + file_date + '.pkl'
    failed_today = 'followup_report_' + file_date + '.txt'

    # Write dataframe to files
    character_followup.to_pickle(followup_today)
    character_followup.to_pickle(followup_filename)
    print(f'\n\nFinished follow-up! DataFrame written to {followup_filename} & {followup_today}')

    followup_end = timeit.default_timer()

    # Write follow-up report
    followup_elapsed = (followup_end - followup_start)/60
    with open(failed_today, 'w') as fail_reg:
        fail_reg.write(f'Auctioned Characters follow-up report\n')
        fail_reg.write(f'Update finished on {print_date}\n')
        fail_reg.write(f'\nRunning time:          {followup_elapsed:,.2f} minutes')
        fail_reg.write(f'\n    Incorporating:     {incorp_elapsed:,.2f} minutes')
        fail_reg.write(f'\n    Scraping:          {scrape_elapsed:,.2f} minutes')
        fail_reg.write(f'\n    Updating:          {update_elapsed:,.2f} minutes\n')
        fail_reg.write(f'\nIncorporated auctions: {incorporated_auction_count:>8,}')
        fail_reg.write(f'\nSearched characters:   {character_count:>8,}')
        fail_reg.write(f'\n    Succeeded:         {total_collected_count:>8,}')
        fail_reg.write(f'\n    Deleted:           {total_deleted_count:>8,}')
        fail_reg.write(f'\n    Not found:         {total_None_count:>8,}')
        fail_reg.write(f'\n    403 error:         {total_403_count:>8,}')
        fail_reg.write('\n\n\nList of characters that could not be updated:')
        for char in failed_updates:
            fail_reg.write(f'\n{char}')
    print(f'\n\nReport written to file {failed_today}.')

