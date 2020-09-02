import pandas as pd
from matplotlib import pyplot as plt

# seaborn_colorblind = ['#0173b2', '#de8f05', '#029e73', '#d55e00', '#cc78bc', '#ca9161', '#fbafe4', '#949494', '#ece133', '#56b4e9']
# auction_dataframe
auction_dataframe = pd.read_pickle('last_scrape.pkl')
successful_auctions = auction_dataframe[auction_dataframe.Type.eq("W")]
failed_auctions = auction_dataframe[auction_dataframe.Type.eq("M")]

levels = list(auction_dataframe['Level'])
max_level = max(levels)

#vocs = [auction_dataframe.Vocation.unique()]
vocs = [('EK', 'K'), ('RP', 'P'), ('ED', 'D'), ('MS', 'S'), ('N',)]
voc_colors = dict(EK='#0173b2', RP='#de8f05', ED='#029e73', MS='#d55e00', N='#cc78bc', K='#0173b2', P='#de8f05',
                  D='#029e73', S='#d55e00')

fig, axs = plt.subplots(1, len(vocs), sharey=True, tight_layout=True)

for index, voc in enumerate(vocs):
    voc_dataframe = auction_dataframe[auction_dataframe.Vocation.isin(voc)]
    succeeded_df = successful_auctions[successful_auctions.Vocation.isin(voc)]
    failed_df = failed_auctions[failed_auctions.Vocation.isin(voc)]

    succeeded_levels = list(succeeded_df['Level'])
    failed_levels = list(failed_df['Level'])
    bins = list(range(0, max_level, 25))
    voc_color = voc_colors[voc[0]]

    axs[index].hist(succeeded_levels, bins, histtype='stepfilled', label=voc, color=voc_color, alpha=1, edgecolor=voc_color)
    axs[index].hist(failed_levels, bins, histtype='step', label=voc[0]+" (FAILED)", color='black', alpha=0.8)
    axs[index].legend()
    axs[index].set_xlim(left=0, right=max_level)

#plt.legend()
plt.show()

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



