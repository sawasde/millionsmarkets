from utils import utils
import matplotlib.pyplot as plt
from matplotlib.ticker import FormatStrFormatter
import gc

@utils.logger.catch
def plot_sublots(df, plot_features_dicts=[], xaxis='', save_picture=None, style='-o', show=False):
    ''' plot'''
    #df = pd.read_csv('BTC_ETH.csv')
    total_plots = len(plot_features_dicts)

    fig, axes = plt.subplots(total_plots, 1, sharex=True)
    axes[0].yaxis.set_major_formatter(FormatStrFormatter('%.2f'))
    fig.set_size_inches(13, 8)

    for i, ax in enumerate(axes):

        for feature, color in plot_features_dicts[i].items():
            ax.plot(df[xaxis], df[feature], style, color=color)

    # Show figure
    if show:
        plt.show()

    # Save figure
    if save_picture:
        fig.savefig(save_picture)

    # close
    plt.cla() 
    plt.clf() 
    plt.close('all')
    plt.close(fig)
    gc.collect()

