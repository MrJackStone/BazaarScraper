from bazaar_scraper import *

def update_auction_status (auction_id, wait=0):

    char_url = root_url + '&page=details&auctionid=' + auction_id
    print(f'Parsing auction #{auction_id} ', end='', flush=True)

    req = requests.get(char_url, headers=request_headers)
    if req.status_code == 200:

        print(f'successful request: collecting data... ', end='', flush=True)
        char_html = HTML(html=req.text)
        cb_table = char_html.find('.CurrentBid')
        if len(cb_table) > 0:
            auction_status = cb_table[0].text
            print(f'done! New status: {auction_status}.', end='\n', flush=True)
        else:
            print(f'FAILED! Auction missing!', end='\n', flush=True)
            return None

        time.sleep(wait)
        return auction_status

    else:

        return None