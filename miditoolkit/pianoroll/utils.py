import numpy as np
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics import pairwise_distances
from scipy import signal


def downsample(pianoroll, ori_resol, factor):
    pass


def tochroma(pianoroll):
    chroma = np.zeros((pianoroll.shape[0], 12))
    for note in range(12):
        chroma[:, note] = np.sum(pianoroll[:, note::12], axis=1)
    return chroma


def pitch_padding(pianroll, pitch_range, padding_range=(0, 127), value=0):
    st, ed = pitch_range
    st_pad, ed_pad = padding_range
    res = np.pad(
        pianroll,
        [(0, 0), (st - st_pad, ed_pad - ed + 1)],
        mode='constant',
        constant_values=value)
    return res


def unit_normalize(tensor):
    res = (tensor - np.min(tensor)) / (np.max(tensor) - np.min(tensor))
    return res


def sampler(to_compute, win, hop=None, start=0):
    blocks = []
    t, p = to_compute.shape

    if hop is None:
        hop = win * 1
    for s in range(0, t - win + 1, hop):
        blocks.append(to_compute[s + start:s + win, :])
    return np.array(blocks)


def ssm(X, metric='l1', is_norm=True, reverse=False, thres=0):
    '''
    'cityblock', 'cosine', 'euclidean', 'l1', 'l2', 'manhattan'
    '''
    X = X.reshape(X.shape[0], -1)
    S = pairwise_distances(X, metric=metric)
    S[S <= thres] = 0
    if is_norm:
        S = unit_normalize(S)
    if reverse:
        S = 1 - S
    return S


def recurrence_plot(X, k=10, p=1):
    X = X.reshape(X.shape[0], -1)
    knn = NearestNeighbors(n_neighbors=k, p=p)
    N = len(X)
    knn.fit(X)
    tR = np.zeros((N, N))
    R = np.zeros((N, N))
    for i in range(N):
        connect = knn.kneighbors([X[i]], return_distance=False)
        tR[i, connect] = 1

    for i in range(N):
        for j in range(N):
            if tR[i, j] == tR[j, i] == 1:
                R[i, j] = 1
    return R


def time_to_lag(time):
    N = time.shape[0]
    lagmap = np.zeros((N, N))
    for i in range(N):
        for j in range(N):
            k = (i + j - 1) % N
            lagmap[i, j] = time[i, k]
    return lagmap


def spatial_conv(to_compute, win_x, win_y, variance):
    stdev_t = (variance * (win_x) * 0.5)
    stdev_l = (variance * (win_y) * 0.5)

    gt = signal.gaussian(win_x, std=(win_x - 1) / 2 / stdev_t)
    gl = signal.gaussian(win_y, std=(win_y - 1) / 2 / stdev_l)

    G = np.outer(gt, gl)
    res = signal.convolve2d(to_compute, G, mode='same')
    return res
