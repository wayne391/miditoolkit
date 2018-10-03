from core_midi import midi_parser
from midi2pianoroll import TrackPianoroll
import matplotlib.pyplot as plt
import pprint
plt.switch_backend('agg')

# load file
midi_file = 'test_midi/test4.mid'

# parse file
midi = midi_parser.MidiFile(midi_file)

# to pianoroll
track = TrackPianoroll(midi.instruments[0], midi.max_tick, midi.ticks_per_beat, midi.tick_to_time)

# ---------------------------- #

# symbolic
track.time_range = (0, 4000)
track.plot_pianoroll_midi('symbolic.png')
print(track, '\n\n')

# absolute
track.timing_type = 'absolute'
track.time_range = (0, 4000)  # when change timing, the window should be rest
track.plot_pianoroll_midi('absolute.png')
print(track, '\n\n')

# symbolic
track.timing_type = 'symbolic'  # switch back to symbolic
track.time_range = (6000, 6240)
track.pitch_range = (40, 80)
print(track, '\n\n')
track.plot_pianoroll_mat('symbolic_off_none.png')  # use plot 'matatrix'
track.note_off_policy = ('every', -1)  # set note off policy
print(track, '\n\n')
track.plot_pianoroll_mat('symbolic_off_-1.png')

track.time_range = (0, 8000)
track.pitch_range = (24, 108)
track.plot_pianoroll_mat('symbolic_larger.png')

# control change
track.time_range = (2000, 8000)
track.plot_control_change(64, 'cc_64')

print(track.pianoroll.shape)

