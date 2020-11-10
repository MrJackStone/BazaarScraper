import os
import pandas as pd
import datetime
import requests
from requests_html import HTML
from bazaar_scraper import str_to_datetime
import time

home_dir = 'D:\\Programming\\Python\\TibiaAuctions'
followup_filename = 'character_followup.pkl'
temp_storage = 'cf_temp.pkl'
scraped_filename = 'last_full_scrape.pkl'
followup_columns = (
'Id', 'Name', 'World', 'Sex', 'Vocation', 'Level', 'AccessDate', 'NewName', 'NewWorld', 'NewSex', 'NewVocation',
'NewLevel', 'LastLogin', 'AccountStatus', 'NewId')
request_headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'}
today = datetime.datetime.now()
failed_updates = []
save_step = 1000
auction_range = False  # range(0,90000)


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


def new_row(df, new, old, access):
    data = list(map(lambda o, n: None if o == n else n, old[1:], new))
    char_dict = dict(Id=old[0], Name=old[1], World=old[2], Sex=old[3], Vocation=old[4],
                     Level=old[5], AccessDate=access, NewName=data[0], NewWorld=data[1], NewSex=data[2],
                     NewVocation=data[3], NewLevel=data[4], LastLogin=new[5], AccountStatus=new[6],
                     NewId=None,
                     Scheduled=new[7], Deleted=new[8])
    char_df = pd.DataFrame(char_dict, index=[0])
    df = df.append(char_df).reset_index(drop=True)
    return df


def recently_accessed(row, followup_df, day_threshold=10):
    # Calculate days since last access for given auction
    today = datetime.datetime.today()
    last_access = followup_df.iloc[row]['AccessDate']
    delta_time = today - last_access
    days_since = delta_time.days
    if days_since > day_threshold:
        return None
    else:
        return days_since


def resold_check(row, followup_df):
    new_id = followup_df.iloc[row]['NewId']
    deleted = followup_df.iloc[row]['Deleted']
    scheduled = followup_df.iloc[row]['Scheduled']
    return (isinstance(new_id, str) and len(new_id) > 0) or deleted or scheduled


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
    time.sleep(1)
    req = requests.get(char_url, headers=tibiaring_headers)

    # Failed request: return None
    if req.status_code != 200:
        print(f'FAILED --- ERROR {req.status_code}: {req.reason}. ', end='', flush=True)
        return None

    # Empty page: return None
    text = req.text
    if len(text) == 0:
        print(f'FAILED -- empty HTML!', end='', flush=True)
        return None

    # Successful access: return new character name
    html = HTML(html=text)
    character_box = html.find(".CSC")[0]
    new_name = character_box.text
    print(f'success! New name: {new_name}. Collecting info... ', end='', flush=True)
    return new_name


def get_character_info(char_name, headers=None):
    url_root = 'https://www.tibia.com/community/?subtopic=characters&name='
    default_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.77 Safari/537.36'}

    url_name = char_name.replace(' ', '+').replace('ö', '%F6')
    char_url = url_root + url_name
    if not headers:
        headers = default_headers

    req = requests.get(char_url, headers=headers)
    if req.status_code != 200:
        print(f'Tibia.com ERROR {req.status_code}: {req.reason}. ')
        return None

    tx = req.text
    html = HTML(html=tx)

    # Check if character name is valid
    character_information_table = html.find('table')[0].text
    if character_information_table.find('Character Information') < 0:
        print('checking TibiaRing for alias... ', end='', flush=True)
        new_name = get_tibiaring_alias(url_name)
        if not new_name:
            return None
        new_char_url = url_root + new_name.replace(' ', '+').replace('ö', '%F6')
        req = requests.get(new_char_url, headers=headers)
        if req.status_code != 200:
            print(f'Tibia.com ERROR {req.status_code}: {req.reason}. ')
            return None
        tx = req.text
        html = HTML(html=tx)
        character_information_table = html.find('table')[0].text
        if character_information_table.find('Character Information') < 0:
            return None
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

    return [name, world, sex, vocation, level, login, status, del_date]


def incorporate_auction(auction, followup_df):
    failed_pair = None

    # Get auction data
    old_id = auction.Id
    old_name = auction.Name
    old_world = auction.World
    old_sex = auction.Sex
    old_vocation = auction.Vocation
    old_level = auction.Level
    old_data = [old_id, old_name, old_world, old_sex, old_vocation, old_level]

    print(f'Parsing character {old_name} (#{old_id}): ', end='', flush=True)

    # Check if auction has already been registered
    id_match = findex(list(followup_df.Id), old_id)
    if isinstance(id_match, int):
        print('\n\t\t\t\tFound matching ID! ', end='', flush=True)
        if isinstance(days_since := recently_accessed(id_match, followup_df), int):
            print(f'\n\t\t\t\tAuction skipped: checked {days_since} days ago.', end='\n', flush=True)
            return followup_df, failed_pair
        else:
            if resold_check(id_match, followup_df):
                print(f'\n\t\t\t\tAuction skipped: permanently closed (resold).', end='\n', flush=True)
                return followup_df, failed_pair

    # Get current data from Tibia.com website
    print(f'\n\t\t\t\tAccessing character page... ', end='', flush=True)
    time.sleep(0.5)
    access_time = datetime.datetime.now()
    new_data = get_character_info(old_name)
    print('done!', end='', flush=True)

    # Check if data collection from Tibia.com was successful
    deleted = None
    if not new_data:
        print(f'\n\t\t\t\tCharacter {old_name} not found: registered as DELETED. ', end='', flush=True)
        new_data = [None] * 8
        deleted = True
        failed_pair = (old_id, old_name)
    name, world, sex, vocation, level, login, status, del_date = new_data

    # Incorporate auction into DataFrame
    if isinstance(id_match, int):
        print(f'\n\t\t\t\tAuction ID #{old_id}: updating... ', end='', flush=True)
        output_followup = update_row(followup_df, id_match, NewName=name, NewWorld=world, NewSex=sex,
                                     NewVocation=vocation, NewLevel=level, LastLogin=login, AccountStatus=status,
                                     AccessDate=access_time, Scheduled=del_date, Deleted=deleted)
        print('done!', end='\n', flush=True)

    else:
        # Look for name match: first in column 'Name' (last match) then in column 'NewName' (first match)
        name_match = rindex(list(followup_df.Name), old_name)
        if not isinstance(name_match, int):
            name_match = findex(list(followup_df.NewName), old_name)

        if isinstance(name_match, int):
            print('\n\t\t\t\tFound matching name! ', end='', flush=True)
            # Case: auctioned character's name matches registered name
            if resold_check(name_match, followup_df):
                print(f'\n\t\t\t\tAuction skipped: permanently closed (resold).   *** UNEXPECTED ***', end='\n',
                      flush=True)
                return followup_df, failed_pair
            else:
                print(f'\n\t\t\t\tClosing permanently: resold as {old_name} (auction ID #{old_id}).', end='',
                      flush=True)
                followup_df = update_row(followup_df, name_match, NewId=old_id, NewName=old_name, NewWorld=old_world,
                                         NewSex=old_sex, NewVocation=old_vocation, NewLevel=old_level,
                                         AccessDate=access_time, Deleted=deleted)

        print('\n\t\t\t\tAppending new row... ', end='', flush=True)
        new_data.append(deleted)
        output_followup = new_row(followup_df, new_data, old_data, access_time)
        print('done!', end='\n', flush=True)

    return output_followup, failed_pair


# Import scraped auctions and sort them by end date
print('\nLoading scraped auctions...', end='', flush=True)
os.chdir(home_dir)
adf = pd.read_pickle(scraped_filename)
nb = adf.drop('Bestiary', axis=1)
won_auctions = nb[adf.Type.eq("W")]
sa = won_auctions[won_auctions.Status.ne("cancelled")]
sbe = sa.sort_values(by='End').reset_index()
if auction_range:
    sbe = sbe.iloc[auction_range]
auction_count = len(sbe)
print(f' done: {auction_count:,} auctions loaded!', end='\n', flush=True)

# Load tracked characters
print('\nLoading recorded follow-up...', end='', flush=True)
if os.path.isfile(followup_filename):
    character_followup = pd.read_pickle(followup_filename)
    print(f' done: {len(character_followup):,} entries loaded!', end='\n', flush=True)
else:
    character_followup = pd.DataFrame(columns=followup_columns)
    print(' no records: new follow-up DataFrame created.', end='\n', flush=True)
print('\n\n')

# Transfer scraped auctions to character follow-up dataframe
save_counter = 0
for i, auction in sbe.iterrows():
    # Perform auto-save operation
    save_counter += 1
    if save_counter % save_step == 0:
        character_followup.to_pickle(temp_storage)
        print(
            f"\n\nAUTOSAVE {save_counter:,}: 'character_followup' DataFrame saved to '{temp_storage}' temporary file.\n\n")

    clock = datetime.datetime.now().strftime("%H:%M:%S")
    print(f'{clock} [{auction_count - i:,}] ', end='', flush=True)

    character_followup, failed = incorporate_auction(auction, character_followup)

    if failed:
        failed_updates.append(failed)

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

# Write follow-up report
failed_count = len(failed_updates)
with open(failed_today, 'w') as fail_reg:
    fail_reg.write(f'Auctioned Characters follow-up report\n')
    fail_reg.write(f'Update finished on {print_date}\n')
    fail_reg.write(f'\nParsed auctions:      {auction_count:>8,}')
    fail_reg.write(f'\nSuccessfully updated: {auction_count - failed_count:>8,}')
    fail_reg.write(f'\nFailed to update:     {failed_count:>8,}')
    fail_reg.write('\n\n\nList of characters & auction IDs that could not be updated:')
    fail_reg.write('\n\nAuction ID   Character Name')
    for id_name_tuple in failed_updates:
        fail_reg.write(f'\n{id_name_tuple[0]:>10}   {id_name_tuple[1]}')
print(f'\n\nFailure report written to file {failed_today}.')
