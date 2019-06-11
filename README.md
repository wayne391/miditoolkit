
# miditoolkit
Warning: **beta version**

Python package for Midi to pianoroll conversion and visualization.

## Major Advantages
* Directly parsing from MIDI
* arbitrary resample
* Symbolic and absolute timing
* Arbitrary range of time and pitch
* Control Changes
* Two visualization method: MIDI (in rectanlge) and Matrix
* Arbitrary note off design (<0 for different color)

All modification can be made by simply setting the attributes of classes.

## TODO List
* Multitrack level
    * beat/downbeat extractor (Done)
    * Major Container
* Other visualization metod: magnitude and etc.
* ticks of X and Y axis
* Linting and better structure
* pianoroll to midi (through mido)
* Sanity Check

## Usage

You can directly run the main.py scrpit

## Sample Result

![Fig](figs/symbolic.png)
![Fig](figs/figs/absolute.png)
![Fig](figs/symbolic_larger.png)
![Fig](figs/symbolic_off_none.png)
![Fig](figs/symbolic_off_-1.png)
![Fig](figs/cc_64.png)


## Piano Roll ToolKit

Set of functions for piano roll editing and visualization.

![image](figs/test.png)
![image](figs/test_chroma.png)
![image](figs/test2.png)
