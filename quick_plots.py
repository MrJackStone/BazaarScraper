from matplotlib import pyplot as plt
import pandas as pd
import datetime
import math


def f_knights(df):
    return auction_filter(df, column='Vocation', values=['EK', 'K'])


def f_paladins(df):
    return auction_filter(df, column='Vocation', values=['RP', 'P'])


def f_druids(df):
    return auction_filter(df, column='Vocation', values=['ED', 'D'])


def f_sorcerers(df):
    return auction_filter(df, column='Vocation', values=['MS', 'S'])


def auction_filter(df, column, values):
    if isinstance(values, list) or isinstance(values, tuple):
        df = df[df[column].isin(values)]
    else:
        df = df[df[column].eq(values)]
    return df


def next_plot_color():
    # voc_colors = ['#0173b2', '#de8f05', '#029e73', '#d55e00', '#cc78bc']
    voc_colors = ['#3BA6FF', '#FF0000', '#34B049', '#FF00FF', '#FF8F11', '#3BFFFF']
    index = 0
    while True:
        yield voc_colors[index]
        index = index + 1 if index < len(voc_colors) - 1 else 0


def plot_vocation_split(adf, plot_title=None, ax=None):
    vocations = [('EK', 'K'), ('RP', 'P'), ('ED', 'D'), ('MS', 'S'), ('N',)]
    voc_names = []
    voc_count = []
    for voc in vocations:
        voc_names.append(voc[0])
        voc_count.append(len(adf[adf.Vocation.isin(voc)]))

    subtitle = f'\n({len(adf):,} auctions)'
    plt_title = (plot_title if plot_title else '') + subtitle

    plt.style.use('seaborn-colorblind')

    if ax:
        _, texts, auto_texts = ax.pie(voc_count, labels=voc_names, wedgeprops={'edgecolor': 'k'},
                                       autopct=lambda pct: '{:.1f}%'.format(pct))
        ax.set_title(plt_title, fontname='Monospac821 BT', size=20)
    else:
        _, texts, auto_texts = plt.pie(voc_count, labels=voc_names, wedgeprops={'edgecolor': 'k'},
                                       autopct=lambda pct: '{:.1f}%'.format(pct))
        plt.title(plt_title, fontname='Monospac821 BT', size=20)

    plt.setp(auto_texts, fontname='Monospac821 BT', size=15, fontweight='bold', c='w', alpha=0.5)
    plt.setp(texts, fontname='Monospac821 BT', size=25, fontweight='bold')
    plt.tight_layout()
    plt.show()


def plot_by_date(adf, line_keys=None, plot_title=None, save_only=False, ax0=None, bar_label=None):
    plot_color = next_plot_color()
    color = next(plot_color)
    tick_steps = 10

    same_end_date = adf.groupby(adf['End'].apply(lambda date: date.date()))
    days = [date_pair[0].strftime('%d/%m') for date_pair in same_end_date]

    daily_quantities = [len(date_pair[1]) for date_pair in same_end_date]

    if not ax0:
        fig, ax0 = plt.subplots(figsize=(16,9))
    else:
        color = next(plot_color)

    ax0.set_xlabel('Auction end date', color='k', size=25)
    ax0.set_ylabel('Number of auctions', color=color, size=25)
    ax0.bar(days, height=daily_quantities, align='center', color=color, alpha=0.5, width=1, edgecolor='k', label=bar_label)
    ax0.get_yaxis().set_ticks([])

    plt.setp(ax0.get_xticklabels(), rotation=90, size=8)

    text_offset = math.ceil(max(daily_quantities) * 0.01)
    for day, quant in enumerate(daily_quantities):
        ax0.text(days[day], quant + text_offset, str(quant), ha='center', size=8, alpha=0.5)

    axes = []
    if line_keys:

        if not isinstance(line_keys, list):
            line_keys = [line_keys]

        axis_offset = 1
        for i, key in enumerate(line_keys):

            if key in adf.keys():
                daily_avgs = [(date_pair[1][key].mean()) for date_pair in same_end_date]

                tick_min = int(min(daily_avgs))
                tick_max = int(max(daily_avgs))
                tick_spacing = (tick_max - tick_min) / tick_steps
                tick_spacing = int(round(tick_spacing, -int(math.log10(tick_spacing))))
                tick_marks = list(range(0, tick_max + tick_spacing, tick_spacing))

                ax = ax0.twinx()
                axes.append(ax)

                color = next(plot_color)

                ax.set_ylabel(key, size=20, c=color)
                ax.plot(days, daily_avgs, lw=5, alpha=0.8, c=color)
                ax.grid(which='both', color=color, alpha=0.6, ls='--')
                ax.set_axisbelow(True)

                ax.spines['right'].set_position(('axes', axis_offset))
                # ax.set_frame_on(True)
                # ax.patch.set_visible(False)
                # for sp in ax.spines.values():
                #     sp.set_visible(False)
                # ax.spines['right'].set_visible(True)
                # ax.yaxis.label.set_color(color)
                ax.tick_params(axis='y', colors=color)
                ax.get_yaxis().set_ticks(tick_marks)
                axis_offset += 0.1

    # ax0.grid(which='both')
    ax0.set_xlim(-0.5, len(days) - 0.5)

    if plot_title:
        plt.title(plot_title, size=30)

    #fig.tight_layout()

    if save_only:
        plt.savefig(plot_title + '.png')
        #plt.close(fig)
    else:
        plt.show()

    return ax0, axes


def plot_vocation_progress(auctions):
    vocations = [('EK', 'K'), ('RP', 'P'), ('ED', 'D'), ('MS', 'S')]
    plot_color = next_plot_color()

    fig, ax0 = plt.subplots()
    ax0.set_xlabel('Auction end date', color='k', size=25)
    ax0.set_ylabel('Average character level', size=25)
    plt.setp(ax0.get_xticklabels(), rotation=90, size=8)
    ax0.grid(which='both')
    ax0.set_axisbelow(True)

    # ax1 = ax0.twinx()
    # ax1.set_ylabel('Average bid', size=25)

    sorted_df = auctions.sort_values('End')
    gbe = sorted_df.groupby(sorted_df['End'].apply(lambda date: date.date()), sort=False)
    days = [day[0].strftime('%d/%m') for day in gbe]

    for voc in vocations:
        color = next(plot_color)

        voc_dfs = [day_df[day_df.Vocation.isin(voc)] for day_df in [g[1] for g in gbe]]
        daily_means = [df[['Bid', 'Level']].mean() for df in voc_dfs]
        bids = [pair[0] for pair in daily_means]
        levels = [pair[1] for pair in daily_means]

        # mean_values = voc_df.groupby(voc_df['End'].apply(lambda date: date.date()), sort=False)[['Bid', 'Level']].mean()

        ax0.plot(days, levels, lw=2, alpha=1, c=color, label=voc[0])
        # ax1.plot(days, bids, lw=2, alpha=0.4, c=color, ls='--')

    ax0.legend(fontsize=20)
    ax0.set_xlim(0, len(days) - 1)


def plot_vocation_prices(auctions, selected_vocations=None):
    vocations = [('EK', 'K'), ('RP', 'P'), ('ED', 'D'), ('MS', 'S')]
    if selected_vocations:
        any_match = lambda valid_entries, checked_list: list(map(lambda nth_entry: nth_entry in checked_list,
                                                                 valid_entries if isinstance(valid_entries, list) else [
                                                                     valid_entries])).count(True) > 0
        vocations = [pair for pair in vocations if any_match(selected_vocations, pair)]

    plot_color = next_plot_color()

    fig, ax0 = plt.subplots()
    ax0.set_xlabel('Auction end date', color='k', size=25)
    ax0.set_ylabel('Average bid', size=25)
    plt.setp(ax0.get_xticklabels(), rotation=90, size=8)
    ax0.grid(which='both')
    ax0.set_axisbelow(True)

    # ax1 = ax0.twinx()
    # ax1.set_ylabel('Average bid', size=25)

    sorted_df = auctions.sort_values('End')
    gbe = sorted_df.groupby(sorted_df['End'].apply(lambda date: date.date()), sort=False)
    days = [day[0].strftime('%d/%m') for day in gbe]

    for voc in vocations:
        color = next(plot_color)

        voc_dfs = [day_df[day_df.Vocation.isin(voc)] for day_df in [g[1] for g in gbe]]
        daily_means = [df[['Bid', 'Level']].mean() for df in voc_dfs]
        bids = [pair[0] for pair in daily_means]
        # levels = [pair[1] for pair in daily_means]

        # mean_values = voc_df.groupby(voc_df['End'].apply(lambda date: date.date()), sort=False)[['Bid', 'Level']].mean()

        ax0.plot(days, bids, lw=2, alpha=1, c=color, label=voc[0])

    ax0.legend(fontsize=20)
    ax0.set_xlim(0, len(days) - 1)


def plot_level_range(auctions, min_level=0, max_level=1300, level_step=100, ymin=None, ymax=None, ystep=None,
                     plot_title=None):
    level_lb = list(range(min_level, max_level, level_step))
    level_ub = [lb + level_step + 1 for lb in level_lb]

    fbl = auctions[auctions.Level.isin(range(min_level, max_level + 1))]
    sbe = fbl.sort_values('End')

    gbl = []
    for lb, ub in zip(level_lb, level_ub):
        group = sbe[sbe.Level.isin(range(lb, ub))]
        gbl.append([(lb, ub), group])

    fig, ax = plt.subplots()

    all_bids = []
    for level_range in gbl:
        lr = level_range[0]
        df = level_range[1]

        gbe = df.groupby(df.End.apply(lambda date: date.date()), sort=False)
        days = [pair[0].strftime('%d/%m') for pair in gbe]
        bids = [pair[1].Bid.mean() for pair in gbe]

        all_bids += bids

        lab = f'{lr[0]:,}-{lr[1] - 1:,}'

        ax.plot(days, bids, label=lab, lw=1, marker='o', ls='--', markersize=4)

    ax.legend(fontsize=20)
    ax.set_ylabel('Average bid [TC]', fontsize=20)
    ax.set_xlabel('Auction end date', fontsize=20)

    max_bid = int(max(all_bids))
    if isinstance(ymin, int) and isinstance(ymax, int) and isinstance(ystep, int):
        plt.yticks(range(ymin, ymax, ystep), fontsize=10)
        ax.set_ylim(0, ymax)
    else:
        bid_step = round(int(max_bid / 10), -2)
        yticks = range(0, max_bid, bid_step)
        plt.yticks(yticks, fontsize=10)
        ax.set_ylim(0, round(max_bid, 1 - len(str(max_bid))))

    plt.xticks(fontsize=7, rotation=90)
    ax.set_xlim(-0.5, len(ax.get_xticks()) - 0.5)
    ax.grid(which='both')

    if isinstance(plot_title, str):
        plt.title(plot_title, fontsize=30)
    else:
        plt.title('Average bid value per level range', fontsize=30)
    plt.tight_layout()
    plt.show()


def auction_pie_plot(slices, labels, absolute=False, plot_title=None):
    if absolute:
        formatted_string = '{:.1f}%\n({:d})'
        total = sum(slices)
        txt_function = lambda percentage: formatted_string.format(percentage, int(percentage*total/100))
    else:
        formatted_string = '{:.1f}%'
        txt_function = lambda percentage: formatted_string.format(percentage)

    _, txts, autotxts = plt.pie(slices, labels=labels, wedgeprops={'edgecolor': 'w'}, autopct=txt_function)

    if not isinstance(plot_title, str):
        plot_title = 'Bestiary Kill Split'
    plt.style.use("seaborn-colorblind")
    plt.title(plot_title, fontname="Cambria", size=25)
    plt.setp(autotxts, fontname="Cambria", size=10, weight='bold', color='k', alpha=0.6)
    plt.setp(txts, fontname="Cambria", size=15)
    plt.show()


def plot_top_bestiary(auctions, top=3, plot_title=False):

    bestiary = {}
    best_entries = list(auctions.Bestiary)

    for nth_bestiary in best_entries:
        for creature in nth_bestiary.keys():
            if creature in bestiary.keys():
                bestiary[creature] = bestiary[creature] + nth_bestiary[creature]
            else:
                bestiary[creature] = nth_bestiary[creature]

    total_kills = sum(list(bestiary.values()))
    sorted_bestiary = {creature: bestiary[creature] for creature in sorted(bestiary, key=lambda creature_name: bestiary[creature_name], reverse=True)}

    top_kills = {creature: sorted_bestiary[creature] for creature in list(sorted_bestiary.keys())[0:top]}
    total_top_kills = sum(list(top_kills.values()))

    other_kills = total_kills - total_top_kills
    top_kills['Other'] = other_kills

    wedge_texts = [txt + f'({top_kills[txt]:,})' for txt in top_kills.keys()]
    auction_pie_plot(top_kills.values(), wedge_texts, plot_title=plot_title)


def compile_bestiary():
    pass


def quick_pie(slices, plot_title=None, ax=None):

    plt_title = (plot_title if plot_title else '')

    plt.style.use('seaborn-colorblind')

    if ax:
        _, texts, auto_texts = ax.pie(slices, wedgeprops={'edgecolor': 'k'},
                                       autopct=lambda pct: '{:.1f}%'.format(pct))
        ax.set_title(plt_title, fontname='Monospac821 BT', size=20)
    else:
        _, texts, auto_texts = plt.pie(slices, wedgeprops={'edgecolor': 'k'},
                                       autopct=lambda pct: '{:.1f}%'.format(pct))
        plt.title(plt_title, fontname='Monospac821 BT', size=20)

    plt.setp(auto_texts, fontname='Monospac821 BT', size=15, fontweight='bold', c='w', alpha=0.5)
    plt.setp(texts, fontname='Monospac821 BT', size=25, fontweight='bold')
    plt.tight_layout()
    plt.show()


def chain_resales (fu):

    ids_dict = {k:v for k,v in zip(fu.Id, fu.NewId)}

    resold = fu[fu.NewId.notnull()]
    resale_ids = resold.NewId
    first_sale = resold[~resold.Id.isin(resale_ids)]
    first_ids = first_sale.Id
    total = len(first_ids)
    resale_chains = []
    for i,id in enumerate(first_ids):

        print(f'\rID {id} ({i+1}/{total})         ', end='', flush=True)

        resale_chain = [id]
        while isinstance(id, str):
            new = ids_dict[id]
            # new = fu[fu.Id.eq(id)].NewId.values.item()
            if isinstance(new, str):
                resale_chain.append(new)
            id = new
        resale_chains.append(resale_chain)
    return resale_chains