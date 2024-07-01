# Shin'en GAX Sound Engine tools for Python

This repo houses conversion and (un)packing tools for music and FX files made with Shin'en Multimedia's [GAX Sound Engine] library. 
Since this is a complete rewrite, some things in the original repo (i.e XM to GAX) are nonexistent, but this doesn't mean I won't implement them in the future.


## Tools:
- Gaxripper v2 - A command line tool to rip and reconstruct GAX Sound Engine music data from Game Boy Advance ROMs. 
- GAX Waveform Dumper - Allows one to dump sample data (internally referred to as waveforms) from .nax/.o files. For right now these are saved as .raw 8-bit unsigned files, not .wav or any typical audio format.
- GAX to Furnace Clipboard - This converts the GAX pattern data in a .nax/.o file into the clipboard format used by tildearrow's [Furnace].

## To do:
- Implement the export of GAX sound effects
- Implement GAX 1 and 2 support. There are some major differences, like the lack of an FX mixing rate and slightly different instrument formatting.
- Proper support for earlier revisions of GAX v3. v3.02 technically works but it is not explicitly supported.


Credits:
==============
Bernhard Wodok, Shin'en Multimedia - original sound engine

loveemu - [Documentation] of GAX's format and gax_scanner.py

nikku4211 - [Additional documentation] of GAX's sequence data format (used as a jump-off point for my own research)


[gax sound engine]: <https://www.shinen.com/music/music.php3?gax>
[documentation]: <https://gist.github.com/loveemu/9b3063ffd9a76cb18e379324e43f3251>
[additional documentation]: <https://gist.github.com/loveemu/9b3063ffd9a76cb18e379324e43f3251?permalink_comment_id=3504799#gistcomment-3504799>
[furnace]: <https://github.com/tildearrow/furnace>