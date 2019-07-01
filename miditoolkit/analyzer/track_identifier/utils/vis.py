import numpy as np
import pandas as pd
import seaborn as sn

from scipy import stats
from matplotlib import pyplot as plt

from sklearn import metrics
from sklearn.metrics import confusion_matrix

from track_identifier.utils.misc import unit_normalize


def estimate_pdf(data, x_range=(0, 1), nbins=10000, is_norm=True):
    hist_raw = np.histogram(data)
    hist, val = hist_raw
    hist_act = np.where(hist > 0)[0]
    x_kde = np.linspace(x_range[0], x_range[1], nbins)

    if len(hist_act) == 1:
        y_kde = np.zeros_like(x_kde)
        y_val = val[hist_act]
        y_idx = np.where(y_val<x_kde)[0][0]
        y_kde[y_idx] = 1 
    else:
        kde = stats.gaussian_kde(data)
        y_kde = kde(x_kde)
    if is_norm:
        y_kde = unit_normalize(y_kde)
    return x_kde, y_kde


def plot_distribution(x, y, color='blue', alpha='0.5', label=None):
    plt.plot(x, y, color=color, label=label)
    plt.fill_between(x, y, color=color, alpha='0.5')


def plot_confusion_table(y, y_, classes):
    acc =  metrics.accuracy_score(y, y_)
    mat = confusion_matrix(y, y_)
    df_cm = pd.DataFrame(mat, index = [i for i in classes],
                      columns = [i for i in classes])
    sn.heatmap(df_cm, annot=True)
    plt.title('accuracy: {:.6f}'.format(acc))
    