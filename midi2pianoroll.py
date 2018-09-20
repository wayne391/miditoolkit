from scipy.sparse import csc_matrix
import numpy as np
import collections


class MultiTrackPianoroll(object):
    def __init__(self):
        pass

    # def get_beats_array(self, midi):
    #     time_signatures = midi.time_signature_changes
    #     ticks_per_beat = midi.ticks_per_beat

    #     if not time_signatures or time_signatures[0].time > 0:
    #         time_signatures.insert(0, TimeSignature(4, 4, start_tick))

    #     start_tick = time_signatures[0].time
    #     fianl_tick = midi.max_tick
    #     beats = []
    #     downbeats = []
    #     num_ts = len(time_signatures)
    #     for idx in range(num_ts):
    #         ts = time_signatures[idx]
    #         tmp_end_tick = time_signatures[idx+1].time if (idx+1) < num_ts else fianl_tick

    #         beat_len = ticks_per_beat/(ts.denominator/4)
    #         if beat_len % 1 != 0:
    #             raise ValueError('length of beat is fractional')
    #         beats_per_bar = ts.numerator

    #         tmp_beats = [t for t in range(start_tick, tmp_end_tick, int(beat_len))]
    #         tmp_downbeats = tmp_beats[0:-1:beats_per_bar]

    #         beats.extend(tmp_beats)
    #         downbeats.extend(tmp_downbeats)
    #         start_tick = tmp_end_tick
    #     return beats, downbeats


class TrackPianoroll(object):
    def __init__(self, midi_track, max_tick, beat_resolution, tick_to_time):
        self.is_drum = midi_track.is_drum
        self.name = midi_track.name
        self.program = midi_track.program
        self.max_step = max_tick
        self.beat_resolution = beat_resolution
        self.notes = midi_track.notes
        self.control_changes = self.load_control_change_array(midi_track.control_changes)
        self.tick_to_time = tick_to_time

    def load_control_change_array(self, control_changes):
        cc_map = collections.defaultdict(list)
        for cc in control_changes:
            cc_map[cc.number].append((cc.time, cc.value))
        return cc_map

    def get_note_on_map(self, velocity=True, is_sparse=False, note_off_policy=None, fs=None):

        '''
        note_off_policy = None, ('every', -1), ('consecutive', 0)
        '''

        t_coo = []
        p_coo = []
        values = []
        if note_off_policy is None:
            policy = None
            indicator = None
        else:
            policy = note_off_policy[0]
            indicator = note_off_policy[1]

        for note in self.notes:
            if note.velocity == 0:
                continue
            if fs is not None:
                note.start = self.to_abs(note.start, fs)
                note.end = self.to_abs(note.end, fs)
            duration = (note.end-note.start)
            if policy is None:
                t_coo.extend(np.arange(note.start, note.end))
                p_coo.extend([note.pitch]*duration)
                v = note.velocity if velocity else note.velocity > 0
                values.extend([v]*duration)
            if policy is 'every':
                t_coo.extend(np.arange(note.start, note.end))
                p_coo.extend([note.pitch]*duration)
                v = note.velocity if velocity else note.velocity > 0
                values.extend([v]*(duration-1) + [indicator])
            elif policy is 'consecutive':
                # find previous note-on
                last_note_ons = self._search_index(t_coo, note.start-1)
                last_note_ons_pitches = [p_coo[i] for i in last_note_ons]
                pindex = self._search_index(last_note_ons_pitches, note.pitch)

                # apply indicator if the previous note-on exists
                if pindex:
                    indicator_index = last_note_ons[pindex]
                    t_coo[indicator_index] = indicator
                    p_coo[indicator_index] = indicator

                # write note
                t_coo.extend(np.arange(note.start, note.end))
                p_coo.extend([note.pitch]*duration)
                v = note.velocity if velocity else note.velocity > 0
                values.extend([v]*duration)
            else:
                pass

        # convrting type
        if not velocity and not indicator:
            values = list(map(bool, values))
        else:
            values = list(map(np.uint8, values))

        shape = (self.max_step+1, 128) if fs is None else (int(self.tick_to_time[-1]/(1./fs))+1, 128)
        print(shape)
        result = csc_matrix((values, (t_coo, p_coo)), shape=shape)
        output = result if is_sparse else result.toarray()
        return output

    def get_transient_map(self, is_sparse=False, event='note_on', fs=None):
        t_coo = []
        p_coo = []
        values = []
        for note in self.notes:
            if note.velocity == 0:
                continue
            if event == 'note_on':
                t = note.start if fs is None else self.to_abs(note.start, fs)
            elif event == 'note_off':
                t = note.end if fs is None else self.to_abs(note.end, fs)
            else:
                pass
            t_coo.append(t)
            p_coo.append(note.pitch)
            v = bool(note.velocity)
            values.append(v)
        shape = (self.max_step+1, 128) if fs is None else (int(self.tick_to_time[-1]/(1./fs))+1, 128)
        result = csc_matrix((values, (t_coo, p_coo)), shape=shape)
        output = result if is_sparse else result.toarray()
        return output

    def _search_index(self, list_, item):
        return [i for i, x in enumerate(list_) if x == item]

    def to_abs(self, index, fs):
        return int(round(self.tick_to_time[index] / (1./fs)))
