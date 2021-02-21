import math
import pandas as pd
from matplotlib import pyplot as plt
import matplotlib.colors as colors
import matplotlib.dates as mdates
import numpy as np
from scipy import stats
import os
import datetime
import timeit

# Plot settings
voc_colors = dict(EK='#0173b2', RP='#de8f05', ED='#029e73', MS='#d55e00', N='#cc78bc', K='#0173b2', P='#de8f05',
                  D='#029e73', S='#d55e00')
pvp_colors = {'Open PvP': '#0173b2', 'Retro Hardcore PvP': '#de8f05', 'Retro Open PvP': '#029e73',
              'Optional PvP': '#d55e00', 'Hardcore PvP': '#cc78bc'}
melee_colors ={'Axe':'#0173b2', 'Club':'#029e73', 'Sword':'#d55e00', 'Fist':'#cc78bc'}
voc_markers = {'K':'o', 'EK':'o', 'P':'^', 'RP':'^', 'D':'P', 'ED':'P', 'S':'s', 'MS':'s', 'N':'*'}
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
os.chdir('D:\\Programming\\Python\\TibiaAuctions')
complete_auction_dataframe = pd.read_pickle('last_full_scrape.pkl')
complete_auction_dataframe = complete_auction_dataframe.drop('Bestiary', axis=1)
status_dataframe = complete_auction_dataframe[~complete_auction_dataframe.duplicated(subset='Id', keep=False)]
worlds_dataframe = pd.read_pickle('tibia_game_worlds.pkl')
followup_df = pd.read_pickle('character_followup.pkl')

# Divide dataframe: successful and failed auctions
won_auctions = status_dataframe[status_dataframe.Type.eq("W")]
successful_auctions = won_auctions[won_auctions.Status.ne("cancelled")]

no_bids = status_dataframe[status_dataframe.Type.eq("M")]
cancelled_auctions = won_auctions[won_auctions.Status.eq("cancelled")]
failed_auctions = pd.DataFrame()
failed_auctions = failed_auctions.append(no_bids)
failed_auctions = failed_auctions.append(cancelled_auctions)
# failed_auctions = auction_dataframe[auction_dataframe.Type.eq("M")]

# Calculate totals
total_transactions = len(status_dataframe)

successful_transactions = len(successful_auctions)
failed_transactions = len(failed_auctions)
cancelled_transactions = len(cancelled_auctions)
nobid_transactions = len(no_bids)

success_ratio = successful_transactions / total_transactions
fail_ratio = failed_transactions / total_transactions
cancellation_ratio = cancelled_transactions / total_transactions
nobid_ratio = nobid_transactions / total_transactions

total_value = successful_auctions['Bid'].sum()
average_sale = total_value / successful_transactions

# Calculate taxes
auction_tax = total_transactions * 50
sale_tax = [math.floor(tax) for tax in list(successful_auctions['Bid'] * 0.12)]
sale_tax_total = sum(sale_tax)
cancellation_tax = [math.floor(tax) for tax in list(cancelled_auctions['Bid'] * 0.10)]
cancellation_tax_total = sum(cancellation_tax)
total_taxes = auction_tax + sale_tax_total + cancellation_tax_total

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
now = datetime.datetime.now()
file_date = '_'.join(map(str, [now.year, now.month, now.day]))
with open(f'totals_output_{file_date}.txt', 'w') as out_file:
    out_file.write("[code][quote]")
    out_file.write(f"\nConcluded auctions:  {total_transactions:>10,}")
    out_file.write(f"\nSuccessful auctions: {successful_transactions:>10,} ({success_ratio * 100:>5.2f}%)")
    out_file.write(f"\nFailed auctions:     {failed_transactions:>10,} ({fail_ratio * 100:>5.2f}%)")
    out_file.write(f"\n   Cancelled:        {cancelled_transactions:>10,} ({cancellation_ratio * 100:>5.2f}%)")
    out_file.write(f"\n   No bids:          {nobid_transactions:>10,} ({nobid_ratio * 100:>5.2f}%)")
    out_file.write('\n')
    for voc_tuple in vocation_totals.iterrows():
        voc_count = voc_tuple[1]['Count']
        out_file.write(f"\n{voc_tuple[0]:>2}s traded:          {voc_count:>10,} ({100 * voc_count / successful_transactions:>5.2f}%)")
    out_file.write('\n')
    out_file.write(f"\nSuccessful auctions total {total_value:>14,} Tibia Coins.")
    out_file.write(f"\nAuction taxes total       {auction_tax:>14,} Tibia Coins.")
    out_file.write(f"\nSale taxes total          {sale_tax_total:>14,} Tibia Coins.")
    out_file.write(f"\nCancellation taxes total  {cancellation_tax_total:>14,} Tibia Coins.")
    out_file.write(f"\nTotal taxes:              {total_taxes:>14,} Tibia Coins.")
    out_file.write("[/code][/quote]")

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
name_lengths = list((map(lambda name: len(name), status_dataframe['Name'])))
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
avg_levels = []
avg_bids = []
counts = []
for _,world in worlds_dataframe.iterrows():
    world_name = world.Name
    world_type = world.Type

    s_auctions = successful_auctions[successful_auctions['World'].eq(world_name)]
    s_count = len(s_auctions)
    s_avg_level = s_auctions['Level'].mean()
    s_avg_bid = s_auctions['Bid'].mean()

    avg_levels.append(s_avg_level)
    avg_bids.append(s_avg_bid)
    counts.append(s_count)

    color = pvp_colors[world_type]
    plt.scatter(s_avg_level, s_avg_bid, s=s_count, alpha=0.5, color=color, edgecolor='black')
    plt.annotate(world_name, (s_avg_level, s_avg_bid), size=6)

world_types = pd.unique(worlds_dataframe['Type'])
for world_type in world_types:
    color = pvp_colors[world_type]
    plt.scatter(-100, -100, s=100, label=world_type, color=color, alpha=0.50, edgecolor='black')
plt.legend(frameon=True, title='World Types', loc='upper left', fontsize=20)
plt.xlabel('Average level', size=30)
plt.ylabel('Average Bid', size=30)

max_count = max(counts)
max_bubble_size = 0 #max_count/50

min_level = min(avg_levels)
max_level = max(avg_levels)
xmin = int(((min_level//10)-1) * 10)
xmax = int(((max_level//10)+1) * 10)
plt.xlim(xmin, xmax)

min_bid = min(avg_bids)-100
max_bid = max(avg_bids)+100
ymin = int(((min_bid//100)-1) * 100)
ymax = int(((max_bid//100)+1) * 100)
plt.ylim(ymin, ymax)

plt.grid(which='both')
plt.xticks(range(xmin, xmax+1, 20))
plt.yticks(range(ymin, ymax+1, 200))
plt.show()


# # Resale profits and losses (slow code)
# resold_chars = successful_auctions[successful_auctions.duplicated(subset='Name', keep=False)]
# resale_count = resold_chars.pivot_table(index='Name', aggfunc='size')
# resold_names = list(resale_count.index)
#
# green_to_red = colors.LinearSegmentedColormap('G2R', color_dict)
# ids = []
# profit = []
# level = []
#
# for name in resold_names:
#     resold_char = resold_chars[resold_chars['Name'].eq(name)].sort_values(by='End', ascending=True)
#     for nth_resale in range(0,len(resold_char)-1):
#         sale_id = resold_char.iloc[nth_resale+1].Id
#
#         bought_for = resold_char.iloc[nth_resale].Bid
#         sold_for = resold_char.iloc[nth_resale+1].Bid
#
#         level_sold = resold_char.iloc[nth_resale+1].Level
#         nth_profit = math.ceil(sold_for*0.88) - bought_for - 50
#         if nth_profit > 0:
#             point_color = 'green'
#         else:
#             point_color = 'red'
#         voc_marker = voc_markers[resold_char.iloc[nth_resale].Vocation]
#         profit.append(nth_profit)
#         level.append(level_sold)
#         ids.append(sale_id)
#         plt.scatter(level_sold, nth_profit, color=point_color, edgecolor='black', marker=voc_marker)
#
# max_profit = max(profit)
# max_loss = min(profit)
# total_profit = sum(profit)
# min_level = min(level)
# max_level = max(level)
# x_step = 50
# y_step = 1000
# x_range = range(0, max_level+x_step, x_step)
# y_range = range(y_step*math.floor((max_loss-y_step)/y_step), y_step*math.ceil((max_profit+y_step)/y_step), y_step)
# plt.yticks(y_range)
# plt.xticks(x_range)
# plt.xlim(0, max_level+x_step)
# plt.grid(which='both')
# plt.xlabel('Character level', size=20)
# plt.ylabel('Resale profit', size=20)
# plt.title('Characters Auctioned Multiple Times', size=20)
#
# resale_summary = f'Number of resales: {len(profit):,}\nTotal profit: {total_profit:,} TC\nMax profit: {max_profit:,} TC\nMax loss: {max_loss:,} TC'
# bbox_properties = dict(boxstyle='round4,pad=0.5', fc='white', ec='k', lw=1, alpha=0.5)
# plt.text(max_level-200, max_profit, resale_summary, ha='left', va='top', size=15, bbox = bbox_properties, alpha=0.8, fontname='Consolas')
#
# for voc in ['EK', 'RP', 'ED', 'MS', 'N']:
#     voc_marker = voc_markers[voc]
#     plt.scatter(-100, -100, s=100, label=voc, color='k', alpha=0.50, edgecolor=None, marker=voc_marker)
# plt.legend(frameon=True, title='Vocations', loc='lower right', fontsize=20)
#
# plt.show()



# Resale profits and losses:
start_time = timeit.default_timer()

resold = followup_df[followup_df.NewId.notnull()]
id_pairs_purchase = list(resold.Id)
id_pairs_sale = list(resold.NewId)
id_pairs_voc = list(resold.Vocation)
id_pairs = [(voc, purch, sale) for voc,purch,sale in zip(id_pairs_voc, id_pairs_purchase, id_pairs_sale)]
true_ids = id_pairs_sale + id_pairs_purchase

EK_pairs = [pair for pair in id_pairs if pair[0] in ['K', 'EK']]
RP_pairs = [pair for pair in id_pairs if pair[0] in ['P', 'RP']]
ED_pairs = [pair for pair in id_pairs if pair[0] in ['D', 'ED']]
MS_pairs = [pair for pair in id_pairs if pair[0] in ['S', 'MS']]
N_pairs = [pair for pair in id_pairs if pair[0] == 'N']

resale_auctions = successful_auctions[successful_auctions.Id.isin(true_ids)]

resale_EKs = resale_auctions[resale_auctions.Vocation.isin(['K','EK'])]
resale_RPs = resale_auctions[resale_auctions.Vocation.isin(['P','RP'])]
resale_EDs = resale_auctions[resale_auctions.Vocation.isin(['D','ED'])]
resale_MSs = resale_auctions[resale_auctions.Vocation.isin(['S','MS'])]
resale_Ns = resale_auctions[resale_auctions.Vocation.eq('N')]

data_by_voc = [('EK', EK_pairs, resale_EKs),
               ('RP', RP_pairs, resale_RPs),
               ('ED', ED_pairs, resale_EDs),
               ('MS', MS_pairs, resale_MSs),
               ('N', N_pairs, resale_Ns)]

levels = []
profits = []
skipped = 0

for voc_data in data_by_voc:
    vocation = voc_data[0]
    pairs = voc_data[1]
    df = voc_data[2]

    valid_ids = list(df.Id)
    voc_marker = voc_markers[vocation]

    voc_data_levels = []
    voc_data_profits = []

    for id_pair in pairs:

        purchase_id = id_pair[1]
        sale_id = id_pair[2]

        if purchase_id in valid_ids and sale_id in valid_ids:

            purchase_auction = df[df.Id.eq(purchase_id)]
            sale_auction = df[df.Id.eq(sale_id)]

            purchase_price = purchase_auction.Bid.item()
            sale_price = sale_auction.Bid.item()

            profit = math.ceil(sale_price * 0.88) - 50 - purchase_price

            level = purchase_auction.Level.item()

            voc_data_levels.append(level)
            voc_data_profits.append(profit)

        else:
            skipped += 1

    levels_array = np.array(voc_data_levels)
    profits_array = np.array(voc_data_profits)
    loss_masked = np.ma.masked_where(profits_array > 0, profits_array)
    profit_masked = np.ma.masked_where(profits_array <= 0, profits_array)
    plt.scatter(levels_array, loss_masked, color='red', edgecolor='k', marker=voc_marker, alpha=0.5)
    plt.scatter(levels_array, profit_masked, color='green', edgecolor='k', marker=voc_marker, alpha=0.5)

    levels = levels + voc_data_levels
    profits = profits + voc_data_profits

max_profit = max(profits)
max_loss = min(profits)
total_profit = sum(profits)
min_level = min(levels)
max_level = max(levels)
x_step = 50
y_step = 2000
x_range = range(0, max_level+x_step, x_step)
y_range = range(y_step*math.floor((max_loss-y_step)/y_step), y_step*math.ceil((max_profit+y_step)/y_step), y_step)
plt.yticks(y_range)
plt.xticks(x_range)
plt.xlim(0, max_level+x_step)
plt.grid(which='both')
plt.xlabel('Character level', size=20)
plt.ylabel('Resale profit', size=20)
plt.title('Characters Auctioned Multiple Times', size=20)

resale_summary = f'Number of resales: {len(profits):,}\nTotal profit: {total_profit:,} TC\nMax profit: {max_profit:,} TC\nMax loss: {max_loss:,} TC'
bbox_properties = dict(boxstyle='round4,pad=0.5', fc='white', ec='k', lw=1, alpha=0.5)
plt.text(max_level-200, max_profit, resale_summary, ha='left', va='top', size=15, bbox = bbox_properties, alpha=0.8, fontname='Consolas')

for voc in ['EK', 'RP', 'ED', 'MS', 'N']:
    voc_marker = voc_markers[voc]
    plt.scatter(-100, -100, s=100, label=voc, color='k', alpha=0.50, edgecolor=None, marker=voc_marker)
plt.legend(frameon=True, title='Vocations', loc='lower right', fontsize=20)

plt.show()

end_time = timeit.default_timer()
elapsed_time = end_time - start_time
print(f'{elapsed_time:.2f} seconds elapsed. {skipped} auctions skipped.')


# Knights: skill info
EKs = successful_auctions[successful_auctions.Vocation.isin(vocations[0])]
EK_count = len(EKs)

skill_value_dict = {'Axe':[0], 'Club':[0], 'Sword':[0], 'Fist':[0]}

skill_id_dict = {'Axe':['-'], 'Club':['-'], 'Sword':['-'], 'Fist':['-']}
for idx,EK in EKs.iterrows():
    id = EK.Id
    axe = EK['Axe Fighting']
    club = EK['Club Fighting']
    sword = EK['Sword Fighting']
    fist = EK['Fist Fighting']
    max_melee = max([axe, club, sword, fist])
    if axe == max_melee:
        skill_name = 'Axe'
    elif club == max_melee:
        skill_name = 'Club'
    elif sword == max_melee:
        skill_name = 'Sword'
    else:
        skill_name = 'Fist'
    skill_value_dict[skill_name].append(max_melee)
    skill_id_dict[skill_name].append(id)
max_melee = int(max([max(skill_values) for skill_values in list(skill_value_dict.values())]))

# Pie plot: chosen melee skill for knights
_, txts, autotxts = plt.pie([len(skill_value_dict['Axe']), len(skill_value_dict['Club']), len(skill_value_dict['Sword']), len(skill_value_dict['Fist'])], labels=['Axe', 'Club', 'Sword', 'Fist'], wedgeprops={'edgecolor': 'black'},
                            autopct=lambda pct: "{:.1f}%\n({:d})".format(pct, math.floor(pct * EK_count / 100)))
#plt.style.use("seaborn-colorblind")
plt.title("Chosen melee skill for knights", fontname="Cambria", size=20)
plt.setp(autotxts, fontname="Cambria", size=15)
plt.setp(txts, fontname="Cambria", size=20)
plt.show()


# Histograms: melee distribution for each skill for knights
bins = range(1, max_melee+2)
x_ticks = range(0, max_melee+2, 5)
#fig, axs = plt.subplots(2, 2, sharey=True, sharex=False)
melee_skills = ['Axe', 'Club', 'Sword', 'Fist']
for index, melee_type in enumerate(melee_skills):
    #skill_ids = skill_id_dict[melee_type]
    #chosen_melee_EKs = EKs[EKs['Id'].isin(skill_ids)]
    melee_values = skill_value_dict[melee_type]
    melee_color = melee_colors[melee_type]

    b = "0" + bin(index)[2:]
    bin_loc = b[-2:]
    i_idx = int(bin_loc[0])
    j_idx = int(bin_loc[1])

    # axs[i_idx, j_idx].grid(which='both')
    # axs[i_idx, j_idx].hist(melee_values, bins=bins, color=melee_color, edgecolor='black', histtype='stepfilled')
    # axs[i_idx, j_idx].set_title(f'{melee_type} Fighting Skill')
    # axs[i_idx, j_idx].set_xticks(x_ticks)

    plt.hist(melee_values, bins=bins, color=melee_color, edgecolor=melee_color, histtype='step', alpha=1, lw=3, label=melee_type)
    #axs[0, 0].set_title(f'{melee_type} Fighting Skill')

plt.grid(which='both')
plt.xticks(x_ticks)
plt.legend()
plt.xlim(0, max_melee)
plt.suptitle('Melee skill distribution for knights (main melee skill only)', size=20)
plt.show()


########################################################################################################################
# # RPs: distance fighting x level (deactivated)
# RPs = successful_auctions[successful_auctions.Vocation.isin(vocations[1])]
#
# RP_levels = RPs['Level']
# RP_distance = RPs['Distance Fighting']
# RP_bids = RPs['Bid']
#
# max_level = int(max(RP_levels))
# max_distance = int(max(RP_distance))
#
# plt.scatter(RP_distance, RP_levels, color=voc_colors['RP'], edgecolor='black')
# plt.grid(which='both')
# plt.xlabel('Distance Fighting Skill', size=30)
# plt.ylabel('Level', size=30)
# plt.xticks(range(0,max_distance+5,5))
# plt.yticks(range(0,max_level+20,20))
# plt.title('Paladins/Royal Paladins: skill vs. level', size=30)
# plt.show()
########################################################################################################################



# Histogram: distance fighting skill
RPs = successful_auctions[successful_auctions.Vocation.isin(vocations[1])]
RP_distance = RPs['Distance Fighting']
max_distance = int(max(RP_distance))

bins = range(1, max_distance+2)
xticks = range(0, max_distance+2, 5)
values, hist_bins, _ = plt.hist(RP_distance, bins=bins, color=voc_colors['RP'], edgecolor='black')
plt.title('Paladins: skill distribution', size=30)
plt.xlabel('Distance Fighting Skill', size=30)
plt.ylabel('Number of successful auctions', size=30)
plt.xticks(xticks)
plt.xlim(10, max_distance)
plt.grid(which='both')
plt.show()



# Bar plot: auction quantity and average bid per day
same_end_date = successful_auctions.groupby(successful_auctions['End'].apply(lambda date: date.date()))
x_values = [date_df[0].strftime("%d/%m") for date_df in same_end_date]
avgbids = [date_df[1]['Bid'].mean() for date_df in same_end_date]
quantities = [len(date_df[1]) for date_df in same_end_date]

fig, ax1 = plt.subplots()
formatter = mdates.DateFormatter('%m/%d')
locator = mdates.DayLocator(interval=1)

ax1.set_ylabel('Number of successful auctions', size=30, color='#0173b2')
ax1.bar(x_values, height=quantities, align='center', color='#0173b2', alpha=0.5, width=1, edgecolor='black')

for idx, quant in enumerate(quantities):
    ax1.text(x_values[idx], quant+20, str(quant), fontweight='bold', ha='center', size=8, rotation=90)

ax2 = ax1.twinx()

ax2.set_ylabel('Average Bid Value [TC]', size=30, color='red')
ax2.plot(x_values, avgbids, color='red', lw=5, alpha=0.7)
ax2.set_yticks(range(0,math.ceil(max(avgbids))+200,200))

ax1.set_xlabel('Auction End Date', size=30)
plt.setp(ax1.get_xticklabels(), rotation=90, size=8)

ax2.grid(which='both', color='red', alpha=0.5)
ax2.set_axisbelow(True)
ax1.set_xlim(-0.5, len(x_values)-0.5)

fig.tight_layout()
plt.show()



# Track world changes: followup_df
def world_shifts (fu, worlds, loc):
    EU_worlds = list(worlds[worlds.Location.eq('EU')].Name)
    NA_worlds = list(worlds[worlds.Location.eq('NA')].Name)
    SA_worlds = list(worlds[worlds.Location.eq('SA')].Name)

    if loc == 'EU':
        valid_worlds = EU_worlds
    elif loc == 'NA':
        valid_worlds = NA_worlds
    elif loc == 'SA':
        valid_worlds = SA_worlds
    else:
        return

    from_loc = fu[fu.World.isin(valid_worlds)]

    not_moved = from_loc[from_loc.NewWorld.isnull()]
    to_EU = from_loc[from_loc.NewWorld.isin(EU_worlds)]
    to_NA = from_loc[from_loc.NewWorld.isin(NA_worlds)]
    to_SA = from_loc[from_loc.NewWorld.isin(SA_worlds)]

    return [not_moved, to_EU, to_NA, to_SA]


all_locations = ['EU', 'NA', 'SA']

fig, axs = plt.subplots(1,4)
plt.style.use("seaborn-colorblind")

for i,location in enumerate(all_locations):

    world_shifting = world_shifts(followup_df, worlds_dataframe, location)

    shift_counts = list(map(lambda a: len(a), world_shifting))
    loc_total = sum(shift_counts)

    #labels = ['-', 'to EU', 'to NA', 'to SA']

    _, texts, auto_texts = axs[i].pie(x=shift_counts, wedgeprops={'edgecolor':'k'},
                                      autopct=lambda pct: '{:.1f}%'.format(pct))
    plt.setp(auto_texts, fontname='Cambria', c='w', weight='bold', fontsize=15)
    axs[i].set_title(f'From: {location}\n({loc_total:,} auctions)', size=30, fontname='Cambria')
    #axs[i].set_title(f'From: {location}({sum(world_shifting):,} transactions)', size=30, fontname='Cambria')
#plt.legend()
axs[3].axis('off')
global_labels = ['Not moved', 'to EU', 'to NA', 'to SA']
plt.figlegend(global_labels, loc=[0.75,0.4], fontsize=20, borderaxespad=1)
plt.tight_layout()
plt.show()



# Alternative method: realse profits and losses (turns out this is also too slow)
# start_time = timeit.default_timer()
#
# successful_ids = list(successful_auctions.Id)
# resold = followup_df[followup_df.NewId.notnull()]
# resold = resold.iloc[0:1000]
# id_pairs = [(row.Vocation, row.Id, row.NewId) for _,row in resold.iterrows()]
#
# levels = []
# profits = []
# ids = []
# skipped = 0
#
# for id_pair in id_pairs:
#     purchase_id = id_pair[0]
#     sale_id = id_pair[1]
#
#     if purchase_id in successful_ids and sale_id in successful_ids:
#
#         purchase_auction = successful_auctions[successful_auctions.Id.eq(purchase_id)]
#         sale_auction = successful_auctions[successful_auctions.Id.eq(sale_id)]
#
#         vocation = purchase_auction.Vocation.item()
#         level = purchase_auction.Level.item()
#
#         purchase_price = purchase_auction.Bid.item()
#         sale_price = sale_auction.Bid.item()
#
#         profit = math.ceil(sale_price*0.88) - 50 - purchase_price
#         point_color = 'green' if profit > 0 else 'red'
#         voc_marker = voc_markers[vocation]
#
#         profits.append(profit)
#         levels.append(level)
#         ids.append(sale_id)
#
#         plt.scatter(level, profit, color=point_color, edgecolor='k', marker=voc_marker)
#
#     else:
#
#         skipped += 1
#
#
# max_profit = max(profits)
# max_loss = min(profits)
# total_profit = sum(profits)
# min_level = min(levels)
# max_level = max(levels)
# x_step = 50
# y_step = 2000
# x_range = range(0, max_level+x_step, x_step)
# y_range = range(y_step*math.floor((max_loss-y_step)/y_step), y_step*math.ceil((max_profit+y_step)/y_step), y_step)
# plt.yticks(y_range)
# plt.xticks(x_range)
# plt.xlim(0, max_level+x_step)
# plt.grid(which='both')
# plt.xlabel('Character level', size=20)
# plt.ylabel('Resale profit', size=20)
# plt.title('Characters Auctioned Multiple Times', size=20)
#
# resale_summary = f'Number of resales: {len(profits):,}\nTotal profit: {total_profit:,} TC\nMax profit: {max_profit:,} TC\nMax loss: {max_loss:,} TC'
# bbox_properties = dict(boxstyle='round4,pad=0.5', fc='white', ec='k', lw=1, alpha=0.5)
# plt.text(max_level-200, max_profit, resale_summary, ha='left', va='top', size=15, bbox = bbox_properties, alpha=0.8, fontname='Consolas')
#
# for voc in ['EK', 'RP', 'ED', 'MS', 'N']:
#     voc_marker = voc_markers[voc]
#     plt.scatter(-100, -100, s=100, label=voc, color='k', alpha=0.50, edgecolor=None, marker=voc_marker)
# plt.legend(frameon=True, title='Vocations', loc='lower right', fontsize=20)
#
# plt.show()
#
# end_time = timeit.default_timer()
#
# elapsed_time = end_time - start_time
# print(f'{elapsed_time:.2f} seconds elapsed. {skipped} auctions skipped.')
#
#
#
#
#
