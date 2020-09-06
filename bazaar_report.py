import math
import pandas as pd
from matplotlib import pyplot as plt
import matplotlib.colors as colors

# Plot settings
voc_colors = dict(EK='#0173b2', RP='#de8f05', ED='#029e73', MS='#d55e00', N='#cc78bc', K='#0173b2', P='#de8f05',
                  D='#029e73', S='#d55e00')
pvp_colors = {'Open PvP': '#0173b2', 'Retro Hardcore PvP': '#de8f05', 'Retro Open PvP': '#029e73',
              'Optional PvP': '#d55e00', 'Hardcore PvP': '#cc78bc'}
color_dict = {'red':   ((0.0, 0.0, 0.0),   # no red at 0
                        (0.5, 1.0, 1.0),   # all channels set to 1.0 at 0.5 to create white
                        (1.0, 0.8, 0.8)),  # set to 0.8 so its not too bright at 1

              'green': ((0.0, 0.8, 0.8),   # set to 0.8 so its not too bright at 0
                        (0.5, 1.0, 1.0),   # all channels set to 1.0 at 0.5 to create white
                        (1.0, 0.0, 0.0)),  # no green at 1

              'blue':  ((0.0, 0.0, 0.0),   # no blue at 0
                        (0.5, 1.0, 1.0),   # all channels set to 1.0 at 0.5 to create white
                        (1.0, 0.0, 0.0))   # no blue at 1
              }

# Import scraped auction data and Tibia World data
complete_auction_dataframe = pd.read_pickle('last_scrape.pkl')
auction_dataframe = complete_auction_dataframe[~complete_auction_dataframe.duplicated(subset='Id', keep=False)]
worlds_dataframe = pd.read_pickle('tibia_game_worlds.pkl')

# Divide dataframe: successful and failed auctions
won_auctions = auction_dataframe[auction_dataframe.Type.eq("W")]
successful_auctions = won_auctions[won_auctions.Status.ne("cancelled")]
failed_auctions = auction_dataframe[auction_dataframe.Type.eq("M")]

# Calculate totals
total_transactions = len(auction_dataframe)
successful_transactions = len(successful_auctions)
failed_transactions = len(failed_auctions)
success_ratio = successful_transactions / total_transactions
fail_ratio = failed_transactions / total_transactions
total_value = successful_auctions['Bid'].sum()
average_sale = total_value / successful_transactions

# Calculate taxes
auction_tax = total_transactions * 50
sale_tax = [math.floor(tax) for tax in list(successful_auctions['Bid'] * 0.12)]
sale_tax_total = sum(sale_tax)
total_taxes = auction_tax + sale_tax_total

# Data by vocation
vocations = [('EK', 'K'), ('RP', 'P'), ('ED', 'D'), ('MS', 'S'), ('N',)]
voc_keys = list((map(lambda k: k[0], vocations)))
voc_columns = ['AvgLevel', 'AvgBid', 'Count']
vocation_totals = pd.DataFrame(columns=voc_columns, index=voc_keys)
for vocation in vocations:
    vocation_dataframe = successful_auctions[successful_auctions.Vocation.isin(vocation)]
    voc_avg_level = vocation_dataframe['Level'].mean()
    voc_avg_bid = vocation_dataframe['Bid'].mean()
    voc_count = len(vocation_dataframe)
    vocation_totals.loc[vocation[0]] = (voc_avg_level, voc_avg_bid, voc_count)

# Print summary to file
with open('totals_output.txt', 'w') as out_file:
    out_file.write("[code][quote]")
    out_file.write(f"\nConcluded auctions: {total_transactions:,}")
    out_file.write(f"\nSuccessful auctions: {successful_transactions:,} ({success_ratio * 100:.2f}%)")
    out_file.write(f"\nFailed auctions: {failed_transactions:,} ({fail_ratio * 100:.2f}%)")
    for voc_tuple in vocation_totals.iterrows():
        voc_count = voc_tuple[1]['Count']
        out_file.write(f"\n{voc_tuple[0]}s traded: {voc_count:,} ({100 * voc_count / successful_transactions:.2f}%)")
    out_file.write(f"\nSuccessful auctions total {total_value:,} Tibia Coins.")
    out_file.write(f"\nAuction taxes total {auction_tax:,} Tibia Coins.")
    out_file.write(f"\nSale taxes total {sale_tax_total:,} Tibia Coins.")
    out_file.write(f"\nTotal taxes: {total_taxes:,} Tibia Coins")
    out_file.write("[code][quote]")

# Pie plot: auctions by vocation
_, txts, autotxts = plt.pie(vocation_totals['Count'], labels=vocation_totals.index, wedgeprops={'edgecolor': 'black'},
                            autopct=lambda pct: "{:.2f}%\n({:d})".format(pct, int(pct * successful_transactions / 100)))
plt.style.use("seaborn-colorblind")
plt.title("Successful auctions by vocation", fontname="Cambria", size=20)
plt.setp(autotxts, fontname="Cambria", size=15)
plt.setp(txts, fontname="Cambria", size=20)
plt.show()

# Scatter plot: bid values by level for each vocation
fig, axs = plt.subplots(2, 2, sharey=True, sharex=True)
for index, vocation in enumerate(vocations[:-1]):
    vocation_dataframe = successful_auctions[successful_auctions.Vocation.isin(vocation)]
    failed_dataframe = failed_auctions[failed_auctions.Vocation.isin(vocation)]
    voc_color = voc_colors[vocation[0]]
    b = "0" + bin(index)[2:]
    bin_loc = b[-2:]
    i_idx = int(bin_loc[0])
    j_idx = int(bin_loc[1])
    axs[i_idx, j_idx].scatter(x=vocation_dataframe['Level'], y=vocation_dataframe['Bid'], edgecolor='black',
                              color=voc_color, label=vocation[0])
    axs[i_idx, j_idx].scatter(x=failed_dataframe['Level'], y=failed_dataframe['Bid'], edgecolor=voc_color,
                              color='none', label='(FAILED)', alpha=0.2)
    axs[i_idx, j_idx].legend(loc='upper left')
    axs[i_idx, j_idx].grid(which='both')
    axs[i_idx, j_idx].set_xlim(left=0)
plt.ylim(0, 1.1*successful_auctions['Bid'].max())
plt.xlim(0, 1.1*successful_auctions['Level'].max())
#plt.xlabel('Level', size=20)
#plt.ylabel('Bid', size=20)
plt.suptitle('Level (X) versus Winning Bids (Y) for each Vocation', size=20)
plt.show()

# Histogram: name lengths
name_lengths = list((map(lambda name: len(name), auction_dataframe['Name'])))
nl_bins = range(0, max(name_lengths)+2)
nl_hist = plt.hist(name_lengths, bins=nl_bins, color='#0173b2', edgecolor='black', alpha=0.5)
offset = max(nl_hist[0])/50
for idx in range(0, len(nl_bins)-1):
    string = str(int(nl_hist[0][idx])) + " (" + str(int(nl_hist[1][idx])) + ")"
    plt.text(nl_hist[1][idx], nl_hist[0][idx]+offset, string, size=8)
plt.xlim(0, max(name_lengths)+1)
plt.xlabel("Character Name Length", size=25)
plt.ylabel("Number of Auctions", size=25)
plt.show()

# Bubble plot: world, avg level, avg bid, transaction count, pvp type
worlds = list(worlds_dataframe.index)
for world in worlds:
    world_dataframe = auction_dataframe[auction_dataframe['World'].eq(world)]
    s_auctions = world_dataframe[world_dataframe['Type'].eq('W')]
    s_count = len(s_auctions)
    s_avg_level = s_auctions['Level'].mean()
    s_avg_bid = s_auctions['Bid'].mean()
    world_type = worlds_dataframe.loc[world]['Type']
    color = pvp_colors[world_type]
    plt.scatter(s_avg_level, s_avg_bid, s=s_count, alpha=0.5, color=color, edgecolor='black')
    plt.annotate(world, (s_avg_level, s_avg_bid), size=6)
world_types = pd.unique(worlds_dataframe['Type'])
for world_type in world_types:
    color = pvp_colors[world_type]
    plt.scatter(-100, -100, s=100, label=world_type, color=color, alpha=0.50, edgecolor='black')
plt.legend(frameon=True, title='World Types', loc='upper left', fontsize=20)
plt.xlabel('Average level', size=30)
plt.ylabel('Average Bid', size=30)
plt.xlim(80)
plt.ylim(600)
plt.grid(which='both')
plt.xticks(range(80, 320, 20))
plt.yticks(range(600, 5000, 200))
plt.show()


duplicated_chars_dataframe = successful_auctions[successful_auctions.duplicated(subset='Name', keep=False)]
duplicated_char_names = set(duplicated_chars_dataframe['Name'])
duplicated_count = len(duplicated_char_names)
first_check = duplicated_chars_dataframe.duplicated(subset='Name', keep='first')
first_entry = duplicated_chars_dataframe[~first_check]
second_onwards_first = duplicated_chars_dataframe[first_check]
second_entry = second_onwards_first[~second_onwards_first.duplicated(subset='Name', keep='first')]

first_bid_avg = first_entry['Bid'].mean()
second_bid_avg = second_entry['Bid'].mean()

green_to_red = colors.LinearSegmentedColormap('G2R', color_dict)
profit = []
level = []
for char_name in duplicated_char_names:
    char_dataframe = duplicated_chars_dataframe[duplicated_chars_dataframe['Name'].eq(char_name)]
    char_level = char_dataframe['Level'].iloc[0]
    first_bid = char_dataframe['Bid'].iloc[0]
    second_bid = char_dataframe['Bid'].iloc[1]
    char_profit = second_bid - first_bid
    if char_profit > 0:
        point_color = 'green'
    else:
        point_color = 'red'
    profit.append(char_profit)
    level.append(char_level)
    plt.scatter(char_level, char_profit, color=point_color, edgecolor='black')
max_profit = max(profit)
max_loss = min(profit)
min_level = min(level)
max_level = max(level)
x_step = 20
x_range = range(0, max_level+x_step, x_step)
y_step = 200
y_range = range(200*round((max_loss-y_step)/200), max_profit+y_step, y_step)
plt.yticks(y_range)
plt.xticks(x_range)
plt.xlim(0, max_level+x_step)
plt.grid(which='both')
plt.xlabel('Character level', size=20)
plt.ylabel('Resale profit (taxes disregarded)', size=20)
plt.title('Characters Auctioned Twice', size=20)
#plt.scatter(level, profit, c=profit, cmap=green_to_red, edgecolor='black')
plt.show()


#name_lengths = list((map(lambda name: len(name), auction_dataframe['Name'])))
#nl_bins = range(0, max(name_lengths)+2)
#nl_hist = plt.hist(name_lengths, bins=nl_bins, color='#0173b2', edgecolor='black', alpha=0.5)
#offset = max(nl_hist[0])/50
#for idx in range(0, len(nl_bins)-1):
#    string = str(int(nl_hist[0][idx])) + " (" + str(int(nl_hist[1][idx])) + ")"
#    plt.text(nl_hist[1][idx], nl_hist[0][idx]+offset, string, size=8)
#plt.xlim(0, max(name_lengths)+1)
#plt.xlabel("Character Name Length", size=25)
#plt.ylabel("Number of Auctions", size=25)
#plt.show()