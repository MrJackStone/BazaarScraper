import os
import pandas as pd

home_dir = 'D:\\Programming\\Python\\TibiaAuctions'

os.chdir(home_dir)

adf = pd.read_pickle('last_full_scrape.pkl')
nb = adf.drop('Bestiary', axis=1)

won_auctions = nb[adf.Type.eq("W")]
sa = won_auctions[won_auctions.Status.ne("cancelled")]

fa = pd.DataFrame()
failed_auctions = nb[nb.Type.eq("M")]
also_failed = won_auctions[won_auctions.Status.eq("cancelled")]
fa = fa.append(failed_auctions)
fa = fa.append(also_failed)


fu = pd.read_pickle('character_followup.pkl')

cl = pd.read_pickle('creature_library.pkl')

worlds = pd.read_pickle('tibia_game_worlds.pkl')

ast = pd.read_pickle('auction_status_record.pkl')