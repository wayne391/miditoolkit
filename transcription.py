import os
import librosa
import numpy as np

from madmom.features.downbeats import DBNDownBeatTrackingProcessor, RNNDownBeatProcessor
from madmom.features.beats import RNNBeatProcessor
from madmom.features.tempo import TempoEstimationProcessor

from miditoolkit.midi import parser
from miditoolkit.midi.containers import TimeSignature, TempoChange


def find_nearest_np(array, value):
    return (np.abs(array - value)).argmin()


def find_first_downbeat(proc_res):
    rythm = np.where(proc_res[:, 1] == 1)[0]
    pos = proc_res[rythm[0], 0]
    return pos


def interp_linear(src, target, num, tail=False):
    src = float(src)
    target = float(target)
    step = (target - src) / float(num)
    middles = [src + step * i for i in range(1, num)]
    res = [src] + middles
    if tail:
        res += [target]
    return res


def estimate_beat(path_audio):
    proc = DBNDownBeatTrackingProcessor(beats_per_bar=[3, 4], fps=100)
    act = RNNDownBeatProcessor()(path_audio)
    proc_res = proc(act) 
    return proc_res


def align_midi(proc_res, path_midi_input, path_midi_output, ticks_per_beat=480):
    midi_data = parser.MidiFile(path_midi_input)

    # compute tempo
    beats = np.array([0.0] + list(proc_res[:, 0]))
    intervals = np.diff(beats)
    bpms = 60 / intervals
    tempo_info = list(zip(beats[:-1], bpms))
    
    # get absolute timing of instruments
    abs_instr = midi_data.get_instruments_abs_timing()

    # get end time of file
    end_time = midi_data.get_tick_to_time_mapping()[-1]

    # compute time to tick mapping
    resample_timing = []
    for i in range(len(beats)-1):
        start_beat = beats[i]
        end_beat = beats[i + 1]
        resample_timing += interp_linear(start_beat, end_beat, ticks_per_beat)
        
    # fill the empty in the tail (using last tick interval)
    last_tick_interval = resample_timing[-1] - resample_timing[-2]
    cur_time = resample_timing[-1]
    while cur_time < end_time:
        cur_time += last_tick_interval
        resample_timing.append(cur_time)
    resample_timing = np.array(resample_timing)
        
    # new a midifile obj
    midi_res = parser.MidiFile()

    # convert abs to sym
    sym_instr = parser.convert_instruments_timing_from_abs_to_sym(abs_instr, resample_timing)

    # time signature
    first_db_sec = find_first_downbeat(proc_res)
    first_db_tick = find_nearest_np(resample_timing, first_db_sec)
    time_signature_changes = [TimeSignature(numerator=4, denominator=4, time=first_db_tick)]
    
    # tempo
    tempo_changes = [] 
    for pos, bpm in tempo_info:
        pos_tick = find_nearest_np(resample_timing, pos)
        tempo_changes.append(TempoChange(tempo=float(bpm), time=pos_tick))
    
    # set attributes
    midi_res.ticks_per_beat = ticks_per_beat
    midi_res.tempo_changes = tempo_changes 
    midi_res.time_signature_changes = time_signature_changes 
    midi_res.instruments = sym_instr
    
    # saving
    midi_res.dump(filename=path_midi_output)


if __name__ == '__main__':
    path_audio = 'testcases/chord_progression_BPM90.mp3'
    path_midi_input = 'testcases/piano.mid'
    path_midi_output = 'testcases/trytry.mid'

    proc_res = estimate_beat(path_audio)
    align_midi(proc_res, path_midi_input, path_midi_output)