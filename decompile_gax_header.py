import argparse
import os
import libs.shinen_gax as gax
import libs.gba as gba
import struct

from libs.gax_constants import (
	mixing_rates, max_channels, min_channels, max_fx_channels
)


def parse_song_setting(offset, rom):

	#adapted from loveemu's GAX scanner
	#from Gaxripper v1

	if offset + 0x20 >= len(rom):
		return None

	settings = struct.unpack_from('<5Hxx3LHHB3xL', rom, offset)
	settings = {
		"num_channels": settings[0],
		"step_count": settings[1],
		"num_patterns": settings[2],
		"restart_position": settings[3],
		"master_volume": settings[4],
		"seq_data_pointer": settings[5],
		"inst_data_pointer": settings[6],
		"wave_data_pointer": settings[7],
		"mixing_rate": settings[8],
		"fx_mixing_rate": settings[9],
		"num_fx_slots": settings[10]
	}

	channel_count = settings["num_channels"]

	if channel_count == min_channels or channel_count > max_channels:
		#songs have a minimum of 1 channel, and a max of 32 channels. 
		#FX files have a minimum and maximum of 0 channels.
		#if it does happen to find a FX song settings struct, it's just going to return None anyways.
		return None

	if rom[offset+0x1e] != 0x00:
		#this area of the settings struct is reserved (set to 0)
		return None

	#checks if the sequence, instrument and sample data pointers are valid ROM locations, or are pointers to 32-bit aligned positions
	if not gba.is_rom_address(settings["seq_data_pointer"]) or gba.from_rom_address(settings["seq_data_pointer"]) > len(rom) or settings["seq_data_pointer"] % 4 != 0:
		return None
	if not gba.is_rom_address(settings["inst_data_pointer"]) or gba.from_rom_address(settings["inst_data_pointer"]) > len(rom) or settings["inst_data_pointer"] % 4 != 0:
		return None
	if not gba.is_rom_address(settings["wave_data_pointer"]) or gba.from_rom_address(settings["wave_data_pointer"]) > len(rom) or settings["wave_data_pointer"] % 4 != 0:
		return None

	if settings["mixing_rate"] not in mixing_rates:
		return None


	#if the end offset of the channel pointers is less or equal to the ROM size, return None.
	if offset + 0x20 + (channel_count * 4) >= len(rom):
		return None

	#check here if the addresses in this struct are ROM pointers.
	for address in struct.unpack_from("<" + "L" * channel_count, rom, offset + 0x20):
		if not gba.is_rom_address(address) or address % 4 != 0:
			return None

	return settings


def scan_ROM(rom):
	song_setting_list = list()
	for dword in range(0, len(rom), 4):
		song_setting = parse_song_setting(dword, rom)
		if song_setting != None:
			print(">> Song setting data found at", hex(gba.to_rom_address(dword)))
			song_setting_list.append(dword)
	return song_setting_list




parser = argparse.ArgumentParser()
parser.add_argument('file_path', help="Game Boy Advance .gba ROM file")
parser.add_argument('--song_prefix', default=True, action=argparse.BooleanOptionalAction, help="GAX header files from 2005 and onwards don't have this")

args = parser.parse_args()
gba_path = os.path.realpath(args.file_path)
prefix = args.song_prefix


with open(gba_path, "rb") as f:

	#the same as Gaxripper v2, but we only save the header file

	gba_rom = f.read()

	#parse the .gba ROM header
	try:
		gba_header = gba.parse_rom_header(gba_rom)
	except:
		print('The file specified is either not a Game Boy Advance ROM, or is corrupted.')

	gameTitle = gba_header["game_title"].rstrip('\x00')
	gameCode = gba_header["game_code"].rstrip('\x00')

	#print GBA ROM info, parameters and settings
	if gameTitle == '':
		print("> Internal game title | <n/a>")
	else:
		print("> Internal game title |", gameTitle)

	if gameCode == '':
		print("> Internal game code  | <n/a>")
	else:
		print("> Internal game code  |", gameCode)

	try:
		product_code = gba.get_product_code(gba_header["game_code"])
		print('> Product code        |', product_code)
	except:
		product_code = None
		print('> Product code        | <n/a>')

	print(">=====================|--------------")

	print("> Maker code          |", gba_header["maker_code"])
	print('> Fixed value         |', hex(gba_header["fixed_value"]))
	print('> Main unit code      |', hex(gba_header["main_unit_code"]))
	print('> Software version    |', gba_header["software_version"])
	print('> Compliment check    |', hex(gba_header["compliment_check"]) + '\n\n')



#detect the GAX version used in the ROM
gax_library = gax.get_GAX_library(gba_rom)
song_settings = scan_ROM(gba_rom)

print("> Unpacking from ROM")
gax_object = gax.unpack_gax_from_rom(song_settings, gba_rom)
print("> GAX data unpacked.\n")

#recreate the input music.h file from the song bank
print("> Reconstructing music.h")
try:
	g = open("music.h", "w")
	g.write(gax.get_cpp_define_file(gax_object, has_prefix = prefix))
	print("> music.h reconstructed")
	g.close()
except Exception as e:
	print('> Could not successfully write music header file')
	raise e
