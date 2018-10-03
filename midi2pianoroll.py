
import collections
import copy
import pylab
import matplotlib
import numpy as np
from core_midi.constants import CONTROL_CHANGE_MAP
from scipy.sparse import csc_matrix
from matplotlib import pyplot as plt
HAS_MATPLOTLIB = True

check = lambda x, up, low: isinstance(x, int) and low<=x<=up

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
    def __init__(self,
                 midi_track,
                 max_tick,
                 beat_resolution,
                 tick_to_time,
                 debug=True,
                 timing_type='symbolic',
                 pianoroll_type='classical',
                 fs=1000,
                 with_velocity=True,
                 to_sparse=False,
                 note_off_policy=None,):

        # Fixed Attributes
        #     From MIDI parser
        self.is_drum = midi_track.is_drum
        self.name = midi_track.name
        self.program = midi_track.program
        self.midi_cc_map = self._load_control_changes_map(midi_track.control_changes)
        self.midi_notes = midi_track.notes
        self.midi_max_step = max_tick

        #     From Multi-track Class
        self.tick_to_time = tick_to_time
        self.beat_resolution = beat_resolution

        # Controllable Parameters
        #     Outer
        self._debug = True
        self._timing_type = 'symbolic'
        self._pianoroll_type = 'classical'
        self._fs = 1000
        self._with_velocity = True
        self._to_sparse = False
        self._note_off_policy = None
        self._pitch_range = (0, 128)
        self._time_range = (0, self.midi_max_step)

        # Baisc Variable Parameters
        self.max_step = self._set_max_step()
        self.cc_map = copy.deepcopy(self._set_cc_map())
        self.notes = copy.deepcopy(self._set_notes())
        self._method = self.get_pianoroll

        # Generated Arrays
        self.control_changes_arrays = self.get_control_changes_arrays()
        self.pianoroll = self.get_pianoroll()

    # setter
    def _set_pianoroll(self):
        return self._method()[self.time_range[0]:self.time_range[1],
                              self.pitch_range[0]:self.pitch_range[1]]

    def _set_max_step(self):
        if self._timing_type == 'symbolic':
            return copy.deepcopy(self.midi_max_step) + 1
        elif self._timing_type == 'absolute':
            return int(round(self.tick_to_time[-1]/(1./self.fs))) + 1
        else:
            raise ValueError('Unknown Timimg Type')

    def _set_notes(self):
        notes_list = []
        for note in self.midi_notes:
            note_ = copy.deepcopy(note)
            note_.start = self._to_abs(note_.start)
            note_.end = self._to_abs(note_.end)
            notes_list.append(note_)
        return notes_list

    def _set_cc_map(self):
        cc_map = collections.defaultdict(list)
        for cc, l in self.midi_cc_map.items():
            tmp = []
            for e in l:
                e_ = copy.deepcopy(e)
                e_.time = self._to_abs(e_.time)
                tmp.append(e_)
            cc_map[cc] = tmp
        return cc_map

    def _set_time_attributes(self):
        self.max_step = self._set_max_step()
        self.cc_map = self._set_cc_map()
        self.notes = self._set_notes()
        self.control_changes_arrays = self.get_control_changes_arrays()
        self.pianoroll = self._set_pianoroll()

    def _set_arrays(self):
        self.control_changes_arrays = self.get_control_changes_arrays()
        self.pianoroll = self._set_pianoroll()

    # decoraters
    @property
    def timing_type(self):
        return self._timing_type

    @property
    def pianoroll_type(self):
        return self._pianoroll_type

    @property
    def fs(self):
        return self._fs

    @property
    def with_velocity(self):
        return self._with_velocity

    @property
    def is_sparse(self):
        return self._is_sparse

    @property
    def note_off_policy(self):
        return self._note_off_policy

    @property
    def debug(self):
        return self._debug

    @property
    def pitch_range(self):
        return self._pitch_range

    @property
    def time_range(self):
        return self._time_range

    # set and check
    @pitch_range.setter
    def pitch_range(self, value):
        if self._pitch_range != value:
            if isinstance(value, tuple) or isinstance(value, list):
                if value[0] > value[1]:
                    raise ValueError('Invalid format. Start > End')
                if check(value[0], 127, 0) and check(value[1], 127, 0):
                    self._pitch_range = value
                    self.pianoroll = self._set_pianoroll()
                else:
                    raise ValueError('Invalid value range. (0~127) required')

    @time_range.setter
    def time_range(self, value):
        if self._time_range != value:
            if isinstance(value, tuple) or isinstance(value, list):
                if value[0] > value[1]:
                    raise ValueError('Invalid format. Start > End')
                if check(value[0], self.max_step, 0) and check(value[1], self.max_step, 0):
                    self._time_range = value
                    self.pianoroll = self._set_pianoroll()
                else:
                    raise ValueError('Invalid value range.')

    @timing_type.setter
    def timing_type(self, value):
        if self._timing_type != value:
            if value.lower() in ['absolute', 'symbolic']:
                self._timing_type = value.lower()
                self._set_time_attributes()
                self._time_range = (0, self.max_step)
            else:
                raise ValueError('Invalid timing type.')

    @fs.setter
    def fs(self, value):
        if self._fs != value:
            self._fs = value
            self._set_time_attributes()
            self._time_range = (0, self.max_step)

    @is_sparse.setter
    def is_sparse(self, value):
        if self._is_sparse != value:
            self._is_sparse = value
            self._set_arrays()

    @pianoroll_type.setter
    def pianoroll_type(self, value):
        if self._pianoroll_type != value:
            if value == 'classical':
                self._method = self.get_pianoroll
            elif value == 'note_on':
                self._method = self.get_note_on_pianoroll
            elif value == 'note_off':
                self._method = self.get_note_off_pianoroll
            else:
                raise ValueError('Unknown Pianoroll Type')
            self._pianoroll_type = value
            self.pianoroll = self._set_pianoroll()

    @with_velocity.setter
    def with_velocity(self, value):
        if self._with_velocity != value:
            if not isinstance(value, bool):
                raise ValueError('Wrong data tpye. bool reqired.')
            self._with_velocity = value
            self.pianoroll = self._set_pianoroll()

    @note_off_policy.setter
    def note_off_policy(self, value):
        if self._note_off_policy != value:
            if value is None:
                pass
            elif isinstance(value, tuple):
                if value[0] in ['every', 'consecutive']:
                    if isinstance(value[1], int):

                        self._note_off_policy = value
                        self.pianoroll = self._set_pianoroll()
                    else:
                        raise ValueError('Indicator should be integer.')
                else:
                    raise ValueError('Unknown Policy.')
            else:
                raise ValueError('Wrong data tpye. Tuple required.')

    @debug.setter
    def debug(self, value):
        if self._debug != value:
            self._debug = value

    def get_control_changes_arrays(self):
        cc_arr_map = dict()
        for cc, l in self.cc_map.items():
            tmp = copy.deepcopy(l)
            cc_arr_map[cc] = self._load_control_change_array(tmp)
        return cc_arr_map

    def get_pianoroll(self):
        # parse note_off_ policy
        if self.note_off_policy is None:
            policy = None
            indicator = None
        else:
            policy = self.note_off_policy[0]
            indicator = self.note_off_policy[1]

        # for sparse matrix
        max_step = self.max_step
        t_coo = []
        p_coo = []
        values = []

        # main processing part
        for note in self.notes:
            # discard notes without velocity
            if note.velocity == 0:
                continue

            # duration
            duration = note.end - note.start

            # no note off
            if policy is None:
                t_coo.extend(np.arange(note.start, note.end))
                p_coo.extend([note.pitch]*duration)
                v = note.velocity if self.with_velocity else note.velocity > 0
                values.extend([v]*duration)

            # every
            if policy is 'every':
                t_coo.extend(np.arange(note.start, note.end))
                p_coo.extend([note.pitch]*duration)
                v = note.velocity if self.with_velocity else note.velocity > 0
                values.extend([v]*(duration-1) + [indicator])

            # consecutive
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
                v = note.velocity if self.with_velocity else note.velocity > 0
                values.extend([v]*duration)
            else:
                pass

        # converting type
        if (not self.with_velocity) and (not indicator):
            values = list(map(bool, values))
        else:
            values = list(map(int, values))

        # output
        result = csc_matrix((values, (t_coo, p_coo)), shape=(max_step, 128))
        output = result if self._to_sparse else result.toarray()
        return output

    def get_note_on_pianoroll(self):
        return self._load_transient_pianoroll('note_on')

    def get_note_off_pianoroll(self):
        return self._load_transient_pianoroll('note_off')

    # inner function for loading cc
    def _load_control_change_array(self, cc):
        max_step = self.max_step
        fianl_tick = max_step
        if cc[0].time != 0:
            fake = copy.deepcopy(cc[0])
            fake.value = 0
            fake.time = 0
            cc.insert(0, fake)
        cc_line = np.zeros((max_step,))

        num_cc = len(cc)
        start_tick = 0
        for idx in range(num_cc):
            end_tick = cc[idx+1].time if (idx+1) < num_cc else fianl_tick
            if end_tick > max_step:
                end_tick = max_step
            value = np.uint8(cc[idx].value)
            cc_line[start_tick:end_tick] = value
            start_tick = end_tick
        output = csc_matrix(cc_line) if self._to_sparse else cc_line
        return output

    def _load_transient_pianoroll(self, event):
        # for sparse matrix
        max_step = self.max_step
        t_coo = []
        p_coo = []
        values = []

        # main processing part
        for note in self.notes:
            if note.velocity == 0:
                continue
            if event == 'note_on':
                t = note.start
            elif event == 'note_off':
                t = note.end
            else:
                pass
            t_coo.append(t)
            p_coo.append(note.pitch)
            v = note.velocity if self.with_velocity else note.velocity > 0
            values.append(v)

        # converting type
        if not self.with_velocity:
            values = list(map(bool, values))
        else:
            values = list(map(np.uint8, values))

        # output
        result = csc_matrix((values, (t_coo, p_coo)), shape=(max_step, 128))
        output = result if self._to_sparse else result.toarray()
        return output

    def _load_control_changes_map(self, midi_cc):
        cc_map = collections.defaultdict(list)
        for cc in midi_cc:
            cc_map[cc.number].append(cc)
        return cc_map

    def _search_index(self, list_, item):
        return [i for i, x in enumerate(list_) if x == item]

    def _to_abs(self, index):
        if self._timing_type == 'symbolic':
            return index
        elif self._timing_type == 'absolute':
            return int(round(self.tick_to_time[index] / (1./self.fs)))
        else:
            raise ValueError('Unknown Timimg Type')

    def __str__(self):
        print_timing = "\'%s\'"%self._timing_type if self._timing_type=='symbolic' else "\'%s\'"%self._timing_type+" fs=%d"%self.fs
        return "<TrackPianoroll Name=\'{}\'(program={} is_drum={}) pianoroll_type=\'{}\' size={} (time={}, pitch={}) note_off_policy={} timing_type={} with_velocity={} to_sparse={} at {}>".format(
                    self.name,
                    self.program,
                    self.is_drum,
                    self._pianoroll_type,
                    str(self.pianoroll.shape[0])+'x'+str(self.pianoroll.shape[1]),
                    str(self._time_range[0])+'~'+str(self._time_range[1]),
                    str(self._pitch_range[0])+'~'+str(self._pitch_range[1]),
                    self._note_off_policy,
                    print_timing,
                    self._with_velocity,
                    self._to_sparse,
                    hex(id(self)))

    def __repr__(self):
        return self.__str__()

    def plot_pianoroll_midi(self, filename='test.png', dpi=200,
                            note_cmap=matplotlib.cm.get_cmap(name='Greens', lut=None)):
        fig, ax = plt.subplots(dpi=dpi)
        to_plot = self._method().T

        # plot basic
        plot_basic(ax, to_plot, self.beat_resolution)

        # plot notes
        plot_note_event(ax,
            self.notes,
            self._time_range,
            shift=0.5,
            note_width=1,
            lw=0.5,
            cmap=note_cmap)

        # range
        pylab.xlim([self._time_range[0], self._time_range[1]])
        pylab.ylim([self._pitch_range[0]-0.6, self._pitch_range[1]+0.6])

        # save
        plt.show()
        plt.savefig(filename)
        plt.close()

    def plot_pianoroll_mat(self, filename='test.png', dpi=200,
                           note_cmap=matplotlib.cm.get_cmap(name='Greens', lut=None),
                           indicator_color='Reds'):

        fig, ax = plt.subplots(dpi=dpi)
        to_plot = self._method().T

        # plot basic
        plot_basic(ax, to_plot, self.beat_resolution)

        # plot notes
        plot_note_entries(ax, to_plot, cmap=note_cmap)
        if self.note_off_policy is not None and self.note_off_policy[1] < 0:
            plot_note_off_indicator(ax, to_plot, self.note_off_policy[1], cmap=indicator_color)

        # range
        pylab.xlim([self._time_range[0], self._time_range[1]])
        pylab.ylim([self._pitch_range[0]-0.6, self._pitch_range[1]+0.6])

        # save
        plt.show()
        plt.savefig(filename)
        plt.close()

    def plot_control_change(self, cc_number, filename, dpi=200):
        fig, ax = plt.subplots(dpi=dpi)
        plot_contorl_change(ax, self.cc_map[cc_number], max_step=self.max_step)

        # range
        pylab.xlim([self._time_range[0], self._time_range[1]])

        # save
        plt.title(' [CC%d]'%cc_number+CONTROL_CHANGE_MAP[cc_number])
        plt.show()
        plt.savefig(filename)
        plt.close()

#-----------------------------------------------------------------------------#

def plot_basic(ax,
               to_plot,
               beat_resolution,
               color_white_key=0.96,
               color_black_key=0.78,
               axis='x',
               color='k',
               linestyle=':',
               linewidth=.5):

    # plot background
    plot_background_pianoroll(
        ax, to_plot,
        color_white_key=color_white_key,
        color_black_key=color_black_key)

    # set tick
    plot_set_ytick(ax)
    num_beat = to_plot.shape[1]//beat_resolution
    plot_set_xtick(ax, beat_resolution, num_beat)
    ax.grid(axis=axis, color=color, linestyle=linestyle,linewidth=linewidth)

def plot_background_pianoroll(
        ax,
        refer_map,
        color_white_key=0.96,
        color_black_key=0.78):
    pianoroll_bg = np.ones_like(refer_map) * color_white_key
    all_black_index = []
    for n in range(11):
        all_black_index.extend(list(map(lambda x:x+12*n, [1, 3, 6, 8, 10])))
    pianoroll_bg[all_black_index[:-2]] = color_black_key
    ax.imshow(pianoroll_bg, aspect='auto', cmap='gray',vmin=0, vmax=1,
          origin='lower', interpolation='none')

def plot_note_event(
        ax,
        notes,
        time_range,
        shift = 0.5,
        note_width = 1,
        lw = 0.3,
        cmap=matplotlib.cm.get_cmap(name='Greens', lut=None)):

    pitch_map = collections.defaultdict(list)
    velocity_map = collections.defaultdict(list)
    for n in notes:
        if n.start > time_range[1]:
            break
        st = n.start
        ed = n.end
        p = n.pitch
        if n.start < time_range[0]:
            st = time_range[0]
        if n.end > time_range[1]:
            ed = time_range[1]
        pitch_map[p].append((st, ed-st))
        velocity_map[p].append(cmap(n.velocity/127))

    for p, note_list in pitch_map.items():
        ax.broken_barh(note_list, (p-shift, note_width),
                        facecolors=(velocity_map[p]), edgecolor='black', lw=lw)

def plot_note_entries(ax, to_plot, cmap='Greens'):
    masked_data = np.ma.masked_where(to_plot<=0, to_plot+50)
    ax.imshow(masked_data, cmap=cmap, aspect='auto', vmin=0, vmax=127,
                      origin='lower', interpolation='none')

def plot_note_off_indicator(ax, to_plot, indicator, cmap='Reds'):
    masked_data = np.ma.masked_where(to_plot != indicator, abs(to_plot))
    ax.imshow(masked_data, cmap=cmap, aspect='auto', vmin=0, vmax=1,
                      origin='lower', interpolation='none')

def plot_set_ytick(ax, type_='note_number'):
    if type_ == 'note_number':
        ax.set_yticks(np.arange(0, 128, 12))
    elif type_ == 'symbol':
        ax.set_yticklabels(['C{}'.format(i - 2) for i in range(11)])
    else:
        raise ValueError('Unknown Type. \'note_number\' or \'symbol\'')

def plot_set_xtick(ax, beat_resolution, num_beat):
    xticks_major = beat_resolution * np.arange(0, num_beat)
    xticks_minor = beat_resolution * (0.5 + np.arange(0, num_beat))
    xtick_labels = np.arange(1, 1 + num_beat)
    ax.set_xticks(xticks_major)
    ax.set_xticklabels('')
    ax.set_xticks(xticks_minor, minor=True)
    ax.set_xticklabels(xtick_labels, minor=True)
    ax.tick_params(axis='x', which='minor', width=0)

def plot_contorl_change(ax, control_change, max_step):
    '''
    plot one control change of one track
    '''
    fianl_tick = max_step
#     if control_change[0].time != 0:
#         control_change.insert(0, (0, 0))
    cc_line = np.zeros((max_step,))

    num_cc = len(control_change)
    start_tick = 0
    x_spots = []
    y_spots = []
    for idx in range(num_cc):
        end_tick = control_change[idx+1].time if (idx+1) < num_cc else fianl_tick
        value =  np.uint8(control_change[idx].value)
        cc_line[start_tick:end_tick] = value
        x_spots.append(start_tick)
        y_spots.append(value)
        start_tick = end_tick

    #
    y = cc_line
    x = np.arange(len(y))
    ax.set_facecolor('gainsboro')
    plt.plot(x, y, color='k', linewidth=0.75)
    ax.fill_between(x, y, alpha=.3, color='darkslategray')
    ax.grid(axis='both', color='k', linestyle=':', linewidth=.5)
    ax.set_ylim([0, 128])
    ax.set_xlim([0, len(y)])
    ax.set_yticks(list(np.arange(0, 128, 32))+[127])
#     plt.title(' [CC%d]'%cc_number+CONTROL_CHANGE_MAP[cc_number])
    plt.scatter(x_spots, y_spots, color='k', s=7.5)
