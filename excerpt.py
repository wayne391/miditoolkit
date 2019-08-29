from  miditoolkit.midi.parser import MidiFile

mido_obj = MidiFile('test_midis/5006635.mid')
mido_obj.dump('seg.mid', segment=(480*4*5, 480*4*12))