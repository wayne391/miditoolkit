'''
Modified from pretty_midi: all tempi stored in tick (symolic timing)
'''

import mido
import six
import warnings
import collections
import numpy as np
from .containers import KeySignature, TimeSignature, Lyric, Note, PitchBend, ControlChange, Instrument, TempoChange


MAX_TICK = 1e7
DEFAUL_BPM = 120.0


class MidiFile(object):
    def __init__(self, midi_file=None, resample_ticks_per_beat=None, resample_method=round):

        if midi_file is not None:
            # Load in the MIDI data using the midi module
            if isinstance(midi_file, six.string_types):
                # If a string was given, pass it as the string filename
                midi_data = mido.MidiFile(filename=midi_file)
            else:
                # Otherwise, try passing it in as a file pointer
                midi_data = mido.MidiFile(file=midi_file)

            # resample_ticks_per_beat
            self.resample_ratio = 1.0
            if resample_ticks_per_beat:
                self.resample_ratio = resample_ticks_per_beat/midi_data.ticks_per_beat
                self.ticks_per_beat = resample_ticks_per_beat
            else:
                self.ticks_per_beat = midi_data.ticks_per_beat

            # Convert tick values in midi_data to absolute, a useful thing.
            midi_data = self._delta_to_abs(midi_data, method=resample_method)

            # tempo_changes (in BPM)
            self.tempo_changes = self._load_tempo_changes(midi_data)

            # Update the array which maps ticks to time
            self.max_tick = max([max([e.time for e in t]) for t in midi_data.tracks]) + 1

            # If max_tick is huge, the MIDI file is probably corrupt
            # and creating the __tick_to_time array will thrash memory
            if self.max_tick > MAX_TICK:
                raise ValueError(('MIDI file has a largest tick of {},'
                                  ' it is likely corrupt'.format(self.max_tick)))

            # get tick to time (for abs timing)
            self.tick_to_time = self._load_tick_to_time()

            # Populate the list of key and time signature changes
            self.key_signature_changes, self.time_signature_changes, self.lyrics = self._load_metadata(midi_data)

            # sort
            self.time_signature_changes.sort(key=lambda ts: ts.time)
            self.key_signature_changes.sort(key=lambda ks: ks.time)
            self.lyrics.sort(key=lambda lyc: lyc.time)

            # Check that there are tempo, key and time change events
            # only on track 0
            if any(e.type in ('set_tempo', 'key_signature', 'time_signature')
                   for track in midi_data.tracks[1:] for e in track):
                warnings.warn(
                    "Tempo, Key or Time signature change events found on "
                    "non-zero tracks.  This is not a valid type 0 or type 1 "
                    "MIDI file.  Tempo, Key or Time Signature may be wrong.",
                    RuntimeWarning)

            # Populate the list of instruments
            self.instruments = self._load_instruments(midi_data)

        else:
            self.ticks_per_beat = 96
            self.tempo_changes = [DEFAUL_BPM]
            self.max_tick = 0
            self.key_signature_changes = []
            self.time_signature_changes = []
            self.lyrics = []
            self.instruments = []

    def _delta_to_abs(self, midi_data, method=round):
        for track in midi_data.tracks:
            tick = int(0)
            for event in track:
                if self.resample_ratio != 1.0:
                    event.time = int(method(event.time*self.resample_ratio))
                    event.time += tick
                else:
                    event.time += tick
                tick = event.time
        return midi_data

    def _load_tempo_changes(self, midi_data, track_idx=0):
        tempo_changes = [TempoChange(DEFAUL_BPM, 0)]

        for event in midi_data.tracks[track_idx]:
            if event.type == 'set_tempo':
                bpm = mido.tempo2bpm(event.tempo)
                tick = event.time
                if tick == 0:
                    tempo_changes = [TempoChange(bpm, 0)]
                else:
                    last_bpm = tempo_changes[-1].tempo
                    if bpm != last_bpm:
                        tempo_changes.append(TempoChange(bpm, tick))
        return tempo_changes

    def _load_metadata(self, midi_data):
        """Populates ``self.time_signature_changes`` with ``TimeSignature``
        objects, ``self.key_signature_changes`` with ``KeySignature`` objects,
        and ``self.lyrics`` with ``Lyric`` objects.

        Parameters
        ----------
        midi_data : midi.FileReader
            MIDI object from which data will be read.
        """
        # Initialize empty lists for storing key signature changes, time
        # signature changes, and lyrics
        key_signature_changes = []
        time_signature_changes = []
        lyrics = []

        for event in midi_data.tracks[0]:
            if event.type == 'key_signature':
                key_obj = KeySignature(event.key, event.time)
                key_signature_changes.append(key_obj)

            elif event.type == 'time_signature':
                ts_obj = TimeSignature(event.numerator,
                                       event.denominator,
                                       event.time)
                time_signature_changes.append(ts_obj)

            elif event.type == 'lyrics':
                lyrics.append(Lyric(event.text, event.time))

        return key_signature_changes, time_signature_changes, lyrics

    def _load_tick_to_time(self):
        """Creates ``self.__tick_to_time``, a class member array which maps
        ticks to time starting from tick 0 and ending at ``max_tick``.

        Parameters
        ----------
        max_tick : int
            Last tick to compute time for.  If ``self._tick_scales`` contains a
            tick which is larger than this value, it will be used instead.

        """
        tick_to_time = np.zeros(self.max_tick + 1)
        num_tempi = len(self.tempo_changes)

        fianl_tick = self.max_tick
        acc_time = 0
        for idx in range(num_tempi):
            start_tick = self.tempo_changes[idx].time
            tmp_bpm = self.tempo_changes[idx].tempo
            # compute tick scale
            tick_scale = 60.0/(tmp_bpm * self.ticks_per_beat)
            # set end tic
            end_tick = self.tempo_changes[idx+1].time if (idx+1) < num_tempi else fianl_tick
            ticks = np.arange(end_tick - start_tick + 1)
            tick_to_time[start_tick:end_tick + 1] = (acc_time + tick_scale*ticks)
            acc_time = tick_to_time[end_tick]
        return tick_to_time

    def _load_instruments(self, midi_data):
        """Populates ``self.instruments`` using ``midi_data``.

        Parameters
        ----------
        midi_data : midi.FileReader
            MIDI object from which data will be read.
        """
        # MIDI files can contain a collection of tracks; each track can have
        # events occuring on one of sixteen channels, and events can correspond
        # to different instruments according to the most recently occurring
        # program number.  So, we need a way to keep track of which instrument
        # is playing on each track on each channel.  This dict will map from
        # program number, drum/not drum, channel, and track index to instrument
        # indices, which we will retrieve/populate using the __get_instrument
        # function below.
        instrument_map = collections.OrderedDict()
        # Store a similar mapping to instruments storing "straggler events",
        # e.g. events which appear before we want to initialize an Instrument
        stragglers = {}
        # This dict will map track indices to any track names encountered
        track_name_map = collections.defaultdict(str)

        def __get_instrument(program, channel, track, create_new):
            """Gets the Instrument corresponding to the given program number,
            drum/non-drum type, channel, and track index.  If no such
            instrument exists, one is created.

            """
            # If we have already created an instrument for this program
            # number/track/channel, return it
            if (program, channel, track) in instrument_map:
                return instrument_map[(program, channel, track)]
            # If there's a straggler instrument for this instrument and we
            # aren't being requested to create a new instrument
            if not create_new and (channel, track) in stragglers:
                return stragglers[(channel, track)]
            # If we are told to, create a new instrument and store it
            if create_new:
                is_drum = (channel == 9)
                instrument = Instrument(
                    program, is_drum, track_name_map[track_idx])
                # If any events appeared for this instrument before now,
                # include them in the new instrument
                if (channel, track) in stragglers:
                    straggler = stragglers[(channel, track)]
                    instrument.control_changes = straggler.control_changes
                    instrument.pitch_bends = straggler.pitch_bends
                # Add the instrument to the instrument map
                instrument_map[(program, channel, track)] = instrument
            # Otherwise, create a "straggler" instrument which holds events
            # which appear before we actually want to create a proper new
            # instrument
            else:
                # Create a "straggler" instrument
                instrument = Instrument(program, track_name_map[track_idx])
                # Note that stragglers ignores program number, because we want
                # to store all events on a track which appear before the first
                # note-on, regardless of program
                stragglers[(channel, track)] = instrument
            return instrument

        for track_idx, track in enumerate(midi_data.tracks):
            # Keep track of last note on location:
            # key = (instrument, note),
            # value = (note-on tick, velocity)
            last_note_on = collections.defaultdict(list)
            # Keep track of which instrument is playing in each channel
            # initialize to program 0 for all channels
            current_instrument = np.zeros(16, dtype=np.int)
            for event in track:
                # Look for track name events
                if event.type == 'track_name':
                    # Set the track name for the current track
                    track_name_map[track_idx] = event.name
                # Look for program change events
                if event.type == 'program_change':
                    # Update the instrument for this channel
                    current_instrument[event.channel] = event.program
                # Note ons are note on events with velocity > 0
                elif event.type == 'note_on' and event.velocity > 0:
                    # Store this as the last note-on location
                    note_on_index = (event.channel, event.note)
                    last_note_on[note_on_index].append((
                        event.time, event.velocity))
                # Note offs can also be note on events with 0 velocity
                elif event.type == 'note_off' or (event.type == 'note_on' and
                                                  event.velocity == 0):
                    # Check that a note-on exists (ignore spurious note-offs)
                    key = (event.channel, event.note)
                    if key in last_note_on:
                        # Get the start/stop times and velocity of every note
                        # which was turned on with this instrument/drum/pitch.
                        # One note-off may close multiple note-on events from
                        # previous ticks. In case there's a note-off and then
                        # note-on at the same tick we keep the open note from
                        # this tick.
                        end_tick = event.time
                        open_notes = last_note_on[key]

                        notes_to_close = [
                            (start_tick, velocity)
                            for start_tick, velocity in open_notes
                            if start_tick != end_tick]
                        notes_to_keep = [
                            (start_tick, velocity)
                            for start_tick, velocity in open_notes
                            if start_tick == end_tick]

                        for start_tick, velocity in notes_to_close:
                            start_time = start_tick
                            end_time = end_tick
                            # Create the note event
                            note = Note(velocity, event.note, start_time,
                                        end_time)
                            # Get the program and drum type for the current
                            # instrument
                            program = current_instrument[event.channel]
                            # Retrieve the Instrument instance for the current
                            # instrument
                            # Create a new instrument if none exists
                            instrument = __get_instrument(
                                program, event.channel, track_idx, 1)
                            # Add the note event
                            instrument.notes.append(note)

                        if len(notes_to_close) > 0 and len(notes_to_keep) > 0:
                            # Note-on on the same tick but we already closed
                            # some previous notes -> it will continue, keep it.
                            last_note_on[key] = notes_to_keep
                        else:
                            # Remove the last note on for this instrument
                            del last_note_on[key]
                # Store pitch bends
                elif event.type == 'pitchwheel':
                    # Create pitch bend class instance
                    bend = PitchBend(event.pitch, event.time)
                    # Get the program for the current inst
                    program = current_instrument[event.channel]
                    # Retrieve the Instrument instance for the current inst
                    # Don't create a new instrument if none exists
                    instrument = __get_instrument(
                        program, event.channel, track_idx, 0)
                    # Add the pitch bend event
                    instrument.pitch_bends.append(bend)
                # Store control changes
                elif event.type == 'control_change':
                    control_change = ControlChange(
                        event.control, event.value, event.time)
                    # Get the program for the current inst
                    program = current_instrument[event.channel]
                    # Retrieve the Instrument instance for the current inst
                    # Don't create a new instrument if none exists
                    instrument = __get_instrument(
                        program, event.channel, track_idx, 0)
                    # Add the control change event
                    instrument.control_changes.append(control_change)
        # Initialize list of instruments from instrument_map
        instruments = [i for i in instrument_map.values()]
        return instruments
