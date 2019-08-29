from miditoolkit.midi.parser import MidiFile


path_midi = 'test_midis/test_1.mid'
obj = MidiFile(path_midi)

obj.dump('test_midis/haha.mid', segment=(480*4*8, 480*4*16))
 
