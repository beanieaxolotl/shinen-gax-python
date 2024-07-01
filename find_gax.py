import argparse
import os
import libs.shinen_gax as gax
import libs.gba as gba

parser = argparse.ArgumentParser()
parser.add_argument('file_path', help="Game Boy Advance .gba ROM file")

args = parser.parse_args()
gba_path = os.path.realpath(args.file_path)


with open(gba_path, "rb") as f:
	gba_rom = f.read()
	gba_header = gba.parse_rom_header(gba_rom)

	gameTitle = gba_header["game_title"].rstrip('\x00')
	gameCode = gba_header["game_code"].rstrip('\x00')

	#print GBA ROM info, parameters and settings
	if gameTitle == '':
		print("> Game title | <n/a>")
	else:
		print("> Game title |", gameTitle)

	print(">============|")

	if gameCode == '':
		print("> Game code  | <n/a>")
	else:
		print("> Game code  |", gameCode)

	print("> Maker code |", gba_header["maker_code"])


	#detect the GAX version used in the ROM
	gax_library = gax.get_GAX_library(gba_rom)

	print("\n> Detected GAX library |", gax_library["version_str"] + '\n')
	for func in gax_library["libgax_subfuncs"]:

		func_address = gax_library["libgax_subfuncs"].get(func)
		if func_address != -1:
			print("> GAX submodule", func, "found at ROM address", hex(gba.to_rom_address(func_address)))
		else:
			print("> Could not find GAX submodule", func)