# Shin'en GAX Sound Engine tools for Python

This repo houses conversion and (un)packing tools for music and FX files made with Shin'en Multimedia's [GAX Sound Engine] library.  
This also works with .gax/.o files made with NAX Sound Engine, which shares the same data structure with GAX.  
Since this is a complete rewrite, some things in the original repo (i.e XM to GAX) are nonexistent, but this doesn't mean I won't implement them in the future.


## Tools:
- Gaxripper (v2) - A command line tool to rip and reconstruct GAX Sound Engine music data from Game Boy Advance ROMs.  
  This tool, like the GAX library script itself, is meant for GAX Sound Engine v3.05+, but support for anything below is flaky at best.

- Waveform dumper - Allows one to dump sample data (internally referred to as waveforms) from .nax/.o files.  
  For right now these are saved as .raw 8-bit unsigned files, not .wav or any typical audio format.

- Furnace clipboard converter - This converts the GAX pattern data in a .nax/.o file into the clipboard format used by tildearrow's [Furnace]. It was developed for an old version of this library, so things may work improperly.

- Header reconstructor - This decompiles/reconstructs a C/C++ header file (music.h) from the GAX music data in a Game Boy Advance ROM. This isn't really useful right now since there's no ELF object recompiler for either the music or FX data (yet).

- GAX library detection - Detects the GAX Sound Engine library (+ functions from libgax.a) in a Game Boy Advance ROM.

## To do:
- Proper support for earlier revisions of GAX v3, GAX v2 and v1 (if possible)
- Implement .ELF file reconstruction for GBA decompilation projects.

## In progress:
- A tracker / sound editor for the GAX format implemented with Pygame and MyreMylar's [pygame_gui]
- An accurate replayer engine for the GAX format, allowing for high-quality listening to tracks. GAX playback on the GBA is used as reference to gauge accuracy.


Credits:
==============
Bernhard Wodok, Shin'en Multimedia - original sound engine

loveemu - [Documentation] of GAX's format and gax_scanner.py

nikku4211 - [Additional documentation] of GAX's sequence data format (used as a jump-off point for my own research)


[gax sound engine]: <https://www.shinen.com/music/music.php3?gax>
[documentation]: <https://gist.github.com/loveemu/9b3063ffd9a76cb18e379324e43f3251>
[additional documentation]: <https://gist.github.com/loveemu/9b3063ffd9a76cb18e379324e43f3251?permalink_comment_id=3504799#gistcomment-3504799>
[furnace]: <https://github.com/tildearrow/furnace>
[pygame_gui]:<https://github.com/MyreMylar/pygame_gui>
