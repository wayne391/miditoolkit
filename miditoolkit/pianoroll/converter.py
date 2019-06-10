import numpy as np
from copy import deepcopy
from scipy.sparse import csc_matrix

'''
Note Stream: dict
    start: int, tich
    end: int, tick
    pitch: int, 0 127
    velocity: 0 127
'''
PITCH_RANGE = 128


def convert_note_stream_to_pianoroll(
        note_stream_ori, 
        ticks_per_beat, 
        downbeat=None, 
        resample_resolution=None, 
        resample_method=round,
        binary_thres=None,
        max_tick=None,
        to_sparse=False, 
        keep_note=True):
    
    # pass by value
    note_stream = deepcopy(note_stream_ori)

    # sort by end time
    note_stream = sorted(note_stream, key=lambda x: x.end)
    
    # set max tick
    if max_tick is None:
        max_tick = 0 if len(note_stream) == 0 else note_stream[-1].end
        
    # set resampling factor
    resample_factor = 1.0
    if resample_resolution is not None:
        resample_factor = resample_resolution / ticks_per_beat
    
    # resampling
    if resample_factor != 1.0:
        max_tick = int(resample_method(max_tick * resample_factor))
        for note in note_stream:
            note.start = int(resample_method(note.start * resample_factor))
            note.end = int(resample_method(note.end * resample_factor))
    
    # create pianoroll
    time_coo = []
    pitch_coo = []
    velocity = []
    
    for note in note_stream:
        # discard notes having no velocity
        if note.velocity == 0:
            continue

        # duration
        duration = note.end - note.start

        # keep notes with zero length (set to 1)
        if keep_note and (duration == 0):
            duration = 1
            note.end += 1

        # set time
        time_coo.extend(np.arange(note.start, note.end))
        
        # set pitch
        pitch_coo.extend([note.pitch] * duration)
        
        # set velocity
        v_tmp = note.velocity
        if binary_thres is not None:
            v_tmp = v_tmp > binary_thres
        velocity.extend([v_tmp] * duration)
    
    # output
    pianoroll = csc_matrix((velocity, (time_coo, pitch_coo)), shape=(max_tick, PITCH_RANGE))
    pianoroll = pianoroll if to_sparse else pianoroll.toarray()
    
    return pianoroll      


def convert_pianoroll_to_note_stream():
    pass