import pypianoroll
import numpy as np
import re
import collections
import os
from pypianoroll import Multitrack, Track

TS_PER_BAR = 96
MAX_BAR = 5000
MIDDLE_C = 60
BEAT_PER_BAR = 4
ONE_SACLE_LENGTH = 12
PIANO_ROLL_Y_DIM = 128
TS_PER_HALF_BEAT = TS_PER_BAR // (BEAT_PER_BAR*2)

g_chord_map = collections.OrderedDict()
g_chord_map["d7"]           = [0, 4, 7, 10]     # Dominant seventh chord (Cdom7)
g_chord_map["maj7"]         = [0, 4, 7, 11]     # Major seventh chord (Cmaj7)
g_chord_map["min7"]         = [0, 3, 7, 10]     # Minor seventh chord (Cmin7)
g_chord_map["dim7"]         = [0, 3, 6, 9]      # Diminished seventh chord (Cdim7)
g_chord_map["hdim7"]        = [0, 3, 6, 10]     # Half-diminished seventh chord
g_chord_map["majmin7"]      = [0, 3, 7, 11]     # Major minor seventh chord

# Shell chords
g_chord_map["d7(omit5)"]    = [0, 4, 10]
g_chord_map["maj7(omit5)"]  = [0, 4, 11]
g_chord_map["min7(omit5)"]  = [0, 3, 10]

# Suspend chords
# g_chord_map["perf5"]         = [0, 7]
# g_chord_map["min(omit3)"]    = [0, 7, 10]
# g_chord_map["maj(omit3)"]    = [0, 7, 11]

g_chord_map["maj"]          = [0, 4, 7]         # Major triad (CMaj)
g_chord_map["min"]          = [0, 3, 7]         # Minor triad (Cmin)
g_chord_map["dim"]          = [0, 3, 6]         # Diminished triad (Cdim)
g_chord_map["a"]            = [0, 4, 8]         # Augmented triad (Caug, C+)

g_add_map = {1: "+b9", 2: "+9", 3: "+#9", 4: "+b11", 5: "+11", 6: "+#11", 8: "+b13", 9: "+13", 10: "+#13", 11: "+7" }
g_add_idx = {"b9": 1, "9": 2, "#9": 3, "b11": 4, "11": 5, "#11": 6, "b13": 8, "13": 9, "#13": 10, "7": 11 }

g_note_map = {"C": 0, "#C": 1, "bD": 1, "D": 2, "#D": 3, "bE": 3, "E": 4, "F": 5,
              "#F": 6, "bG": 6, "G": 7, "#G": 8, "bA": 8, "A": 9, "#A": 10, "bB": 10, "B": 11}
g_note_idx = ["C", "bD", "D", "bE", "E", "F", "bG", "G", "bA", "A", "bB", "B"]


def quantize_chord(result, total_ts_len):
    if len(result) < 1:
       return None
    result.reverse()
    quantize = []
    cur_chord = result.pop()[1]
    for t in range(0, total_ts_len, TS_PER_HALF_BEAT):
        while result and result[-1][0] < t:
            cur_chord = result.pop()[1]
        quantize.append(cur_chord)
    return quantize


def notes2midi(path, chord_seq, melody, harmony):
    max_t = chord_seq[-1][0] + TS_PER_BAR
    chord_seq.append((max_t, set()))
    piano = np.zeros((max_t, 128))
    for i in range(len(chord_seq)-1):
        onset, notes = chord_seq[i]
        offset, _ = chord_seq[i+1]
        piano[onset:offset-1, list(notes)] = 65
    track = Track(pianoroll=piano, name="Detected Chords")
    multitrack = Multitrack(tracks=[melody, harmony, track])
    pypianoroll.write(multitrack, path)


def align_note_on(notes):
    notes = sorted(notes, key=lambda note: note[1])
    _, t, _ = notes[0]
    aligned = [notes[0]]
    for c, s, e in notes[1:]:
        if s - t <= 1:
            aligned.append((c, t, e))
        else:
            t = s
            aligned.append((c, s, e))
    return aligned


def find_notes(data):
    ''' find_notes: output all notes in form (pitch, start_t, end_t)

    Args:
        data (piano-roll): input note

    Returns:
        array of all note in the form (pitch, start_t, end_t)
    '''

    notes = []
    # for each note pitch
    for c in range(data.shape[1]):
        note_start = -1
        note_end = -1
        # for each time step
        for t in range(data.shape[0]):
            if data[t][c]:
                if note_start == -1:
                    note_start = t
                note_end = t
            else:
                if note_start != -1:
                    notes.append((c, note_start, note_end))
                    note_start = -1
                    note_end = -1
        if note_start != -1:
            notes.append((c, note_start, note_end))
            note_start = -1
            note_end = -1

    return notes


def check_chord(notes, normalized_type):
    global g_note_idx
    global g_add_map
    global g_chord_map
    note_map = g_note_idx
    add_map = g_add_map

    chord_map = g_chord_map

    min_pitch = min(notes) % 12
    pitch_num = len(notes)
    if pitch_num < 3:
        return "NA", 100000

    pitch_array = []
    for n in notes:
        n %= 12
        pitch_array.append(n)
        pitch_array.append(n + 12)
    pitch_array.sort()

    base_idx = 0
    min_cost = 10000
    min_chord = "NA"

    for base_idx in range(pitch_num):
        base_pitch = pitch_array[base_idx]
        pitch_map = set([pitch_array[base_idx + j] - base_pitch for j in range(pitch_num)])

        cur_chord = ""
        add_note = set()
        add_note = []
        for ch in chord_map:
            cur_cost = 0
            if set(chord_map[ch]).issubset(pitch_map):
                cur_chord = ch
                add_note = pitch_map - set(chord_map[ch])
                add_note = sorted(list(add_note))
            else:
                continue

            add_chord = ""
            if add_note:
                add_chord = " "
                for an in add_note:
                    if an in add_map:
                        add_chord += add_map[an]
                    else:
                        cur_cost += 100

            chord_pitch = note_map[base_pitch]
            if base_pitch != min_pitch and normalized_type != 'base':
                chord_pitch += "/" + note_map[min_pitch]
                cur_cost += 2

            cur_cost += len(add_note)
            if cur_cost < min_cost:
                min_cost = cur_cost

                if normalized_type == 'all':
                    ''' Use all chord'''
                    min_chord = ("%s %s" % (chord_pitch, cur_chord)) + add_chord

                elif normalized_type == 'add-reduce':
                    ''' Use base chord + 3 types of addition '''
                    replace_map = {
                        "+b9": "+9",
                        "+#9": "+9",
                        "+b11": "+11",
                        "+#11": "+11",
                        "+b13": "+13",
                        "+#13": "+13"
                    }
                    for c in replace_map:
                        add_chord = add_chord.replace(c, replace_map[c])
                    min_chord = ("%s %s" % (chord_pitch, cur_chord)) + add_chord

                elif normalized_type == 'base-shell':
                    exit('base-shell not supported yet')

                elif normalized_type == 'base':
                    ''' Ignore add and shell completely '''
                    min_chord = ("%s %s" % (chord_pitch, cur_chord))
                    min_chord = min_chord.replace("(omit5)", "")

    return min_chord, min_cost


def shortestpath(edge_cost, src, dst):
    # print(edge_cost, src, dst)
    cost = [-1 for _ in range(dst)] + [0]
    next_nei = {}
    # for n in range(dst-1, -1, -1)
    for n in range(dst, -1, -1):
        min_cost = float('inf')
        for nei in edge_cost[n]:
            if cost[nei] != -1:
                if edge_cost[n][nei] + cost[nei] < min_cost:
                    min_cost = edge_cost[n][nei] + cost[nei]
                    cost[n] = min_cost
                    next_nei[n] = nei
    path = [0]
    while path[-1] in next_nei:
        path.append(next_nei[path[-1]])
    # print(path)
    return path


def gen_chord_seq(
        pianoroll,
        normalized_type='base',
        key='C',
        minor_or_major='major'):
    ''' chord_detect estimate chord sequence from input data and save as midi

    Args:
        pianoroll: numpy array
        normalized_type (string): type of chord normalization

    Returns:
        write result as midi
    '''

    # note map
    global g_note_map
    note_map = g_note_map

    # key
    key_shift = 0
    if minor_or_major == 'minor':
        key_shift = note_map[key] - note_map["A"]
    else:
        key_shift = note_map[key] - note_map["C"]

    # body
    notes = find_notes(pianoroll)
    notes = align_note_on(notes) if notes else None
    note_seq = collections.defaultdict(set)
    for _, t, _ in notes:
        for p, s, e in notes:
            if s <= t <= e:
                note_seq[t].add(p - key_shift)

    note_seq = sorted([(t, note_seq[t]) for t in note_seq])

    cur_notes = set()
    edge_cost = collections.defaultdict(dict)
    edge_name = collections.defaultdict(dict)
    edge_notes = collections.defaultdict(dict)
    for start in range(len(note_seq)):
        start_t = note_seq[start][0]
        cur_notes = set()
        for j in range(start, len(note_seq)):
            end_t = note_seq[j][0]
            if end_t - start_t > TS_PER_BAR:
                break
            note = note_seq[j][1]
            cur_notes |= note
            chord, chord_cost = check_chord(cur_notes, normalized_type)
            if chord:
                time_cost = min(j - start, (end_t - start_t) / 24) if j - start >= 1 else 0
                edge_cost[start][j+1] = chord_cost + time_cost
                edge_name[start][j+1] = chord
                edge_notes[start][j+1] = cur_notes.copy()

    # shortest path
    path = shortestpath(edge_cost, 0, len(note_seq))

    # result
    result = []
    chord_seq = []
    for s_idx in range(len(path) - 1):
        s = path[s_idx]
        n = path[s_idx + 1]

        if ((not result) or result[-1][1] != edge_name[s][n]) and edge_name[s][n] != "NA":
            chord_seq.append((note_seq[s][0], edge_notes[s][n]))
            result.append((note_seq[s][0], edge_name[s][n]))

    return result


def chord_detect(pianoroll):
    est_chord = gen_chord_seq(pianoroll)
    ts_length = pianoroll.shape[0]
    est_chord_padded = quantize_chord(est_chord, ts_length)

    return est_chord_padded
