import numpy as np
from track_identifier.utils.misc import unit_normalize


def convert_to_notestream(pianoroll):
    pianoroll_binary = pianoroll.astype(bool).astype(int)
    ticks, pitches = pianoroll_binary.shape
    pianoroll_pad = np.zeros((ticks+2, pitches))
    pianoroll_pad[1:-1, :] = pianoroll_binary
    pianoroll_diff = np.diff(pianoroll_pad, axis=0)

    note_stream = []
    for pitch in range(pitches):
        pitch_array = pianoroll_diff[:, pitch]
        note_ons = np.where(pitch_array > 0)[0]
        note_offs = np.where(pitch_array < 0)[0]
        for nidx in range(len(note_ons)):
            st = note_ons[nidx]
            ed = note_offs[nidx]
            note_info = {
                'note_on': st,
                'duration': ed - st,
                'pitch': pitch,
                'velocity': pianoroll[st, pitch]
            }
            note_stream.append(note_info)

    note_stream = sorted(note_stream, key=lambda x: x['note_on'])
    return note_stream


def norm_cnt_array(cnt_array):
    digit_list = []
    for cnt in cnt_array:
        digit_list.append(len(str(cnt))) 
    max_digit = max(digit_list)
    factor = max_digit - 1
    factor = 0 if factor < 0 else factor
    denom = 10 ** factor
    return cnt_array / denom


def analyze_pitch(pianoroll):
    act_map = np.sum(pianoroll, axis=0)
    act_pitch = np.where(act_map>0)[0]
    act_cnt = act_map[act_pitch]
    act_cnt_normed = norm_cnt_array(act_cnt)
    mean = np.sum(act_pitch * act_cnt_normed) / np.sum(act_cnt_normed)
    lowest = act_pitch[0]
    highest = act_pitch[-1]
    # print(lowest, highest, ave)
    # print(act_pitch)
    return lowest, highest, mean, act_pitch, act_cnt


def analyze_polyphony(pianoroll):
    pianoroll_binary = pianoroll.astype(bool).astype(int)
    act_map = np.sum(pianoroll_binary, axis=1)
    noteon_idx = np.where(act_map > 0)[0]
    poly_idx = np.where(act_map > 1)[0]
    ratio = len(poly_idx) / len(noteon_idx)
    # print(ratio)
    return ratio 


def analyze_duration(pianoroll):
    note_stream = convert_to_notestream(pianoroll)
    durations = []
    for note in note_stream:
        durations.append(note['duration'])
    mean = np.mean(durations)
    std = np.std(durations)
    # print(mean, std)
    return mean, std


def extract_features(pianoroll):
    # pitch
    pitch_lowest, _, pitch_mean, pitch_act, _ = analyze_pitch(pianoroll)
    num_pitches = len(pitch_act)

    # polyphony
    poly_ratio = analyze_polyphony(pianoroll)

    # duration
    duratoin_mean, duratoin_std = analyze_duration(pianoroll)

    feature = np.array([
        pitch_mean,
        pitch_lowest,
        num_pitches,
        poly_ratio,
        duratoin_mean,
        duratoin_std
    ])
    return feature
