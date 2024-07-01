import struct
import logging
import enum
import dataclasses

'''

# ////////////////////////////////////////////////// #
#            Nintendo Game Boy Advance               #
# ////////////////////////////////////////////////// #

A Python library to handle Nintendo Game Boy Advance ROM files. 
This library facilities the decoding (and hopefully encoding) the many
internal values and structs inside this type of ROM file; for hacking
and research purposes.

Documentation used:
	>NO$GBA - GBA Documentation by problemkaputt
	>mGBA

Nintendo, Game Boy, and Game Boy Advance are trademarks of Nintendo Co., Ltd.

''' 


#GBA related things:

nintendo_logo = b'\x24\xff\xae\x51\x69\x9a\xa2\x21\x3d\x84\x82\x0a\x84\xe4\x09\xad\x11\x24\x8b\x98\xc0\x81\x7f\x21\xa3\x52\xbe\x19\x93\x09\xce\x20\x10\x46\x4a\x4a\xf8\x27\x31\xec\x58\xc7\xe8\x33\x82\xe3\xce\xbf\x85\xf4\xdf\x94\xce\x4b\x09\xc1\x94\x56\x8a\xc0\x13\x72\xa7\xfc\x9f\x84\x4d\x73\xa3\xca\x9a\x61\x58\x97\xa3\x27\xfc\x03\x98\x76\x23\x1d\xc7\x61\x03\x04\xae\x56\xbf\x38\x84\x00\x40\xa7\x0e\xfd\xff\x52\xfe\x03\x6f\x95\x30\xf1\x97\xfb\xc0\x85\x60\xd6\x80\x25\xa9\x63\xbe\x03\x01\x4e\x38\xe2\xf9\xa2\x34\xff\xbb\x3e\x03\x44\x78\x00\x90\xcb\x88\x11\x3a\x94\x65\xc0\x7c\x63\x87\xf0\x3c\xaf\xd6\x25\xe4\x8b\x38\x0a\xac\x72\x21\xd4\xf8\x07'

class region_id(enum.Enum):
	japan = 'J'
	europe = 'P'
	france = 'F'
	spanish = 'S'
	english = 'E'
	germany = 'D'
	italy = 'I'

class region_name(enum.Enum):
	#https://www.reddit.com/r/Gameboy/comments/bux2j3/nintendo_cartridge_codes_decoded_what_that_number/
	japan = 'JPN'
	europe = 'EUR'
	france = 'FRA'
	spanish = 'SPA'
	english = 'USA'
	germany = 'DEU'
	italy = 'ITA'

#Memory addressing

def memory_map():
	#cross-referenced from mGBA
	memoryMap = {
		'bios': 0x0000000,
		'wram': 0x2000000,
		'iwram': 0x3000000,
		'mmio': 0x4000000,
		'palette_ram': 0x5000000,
		'vram': 0x6000000,
		'oam': 0x7000000,
		'game_pak': 0x8000000,
		'game_pak_waitstate1': 0xa000000,
		'game_pak_waitstate2': 0xc000000,
		'cart_ram': 0xe000000
	}
	return memoryMap

def to_rom_address(address):
	return 0x8000000 + address

def from_rom_address(rom_address):
	return rom_address ^ 0x8000000

def is_rom_address(address):
	#from loveemu's GAX scanner
	return 0x8000000 <= address <= 0x9ffffff


# ROM management

def validate_logo(logo):

	#Checks Nintendo logo data and validates it.

	# True - Logo data matches one in library
	# False - Logo data is corrupt/incorrect

	if len(logo) != 156:
		raise Exception('Logo data must be 156 bytes.')

	if logo == nintendo_logo:
		return True
	else:
		return False

def parse_rom_header(rom):

	#Parse (and check) the ROM's header.

	#Integrity checks
	if rom[0xb2] != 0x96: #Fixed value
		raise ValueError('Fixed value must be 0x96')
	elif rom[0xb5:0xbc] != b'\x00'*7: #Reserved area
		raise ValueError('Invalid reserved area (A)')
	elif rom[0xbe:0xc0] != b'\x00'*2: #Reserved area 2
		raise ValueError('Invalid reserved area (B)')
	elif validate_logo(rom[0x4:0xa0]) == False:
		raise Exception('Nintendo logo is invalid or corrupted')	

	header = {
	#NO$GBA documentation by problemkaputt used as reference
		"entry_point": rom[0x0:0x4],
		"nintendo_logo": rom[0x4:0xa0],
		"game_title": rom[0xa0:0xac].decode("ascii"),
		"game_code": rom[0xac:0xb0].decode("ascii"),
		"maker_code": rom[0xb0:0xb2].decode("ascii"),
		"fixed_value": rom[0xb2],
		"main_unit_code": rom[0xb3],
		"device_type": rom[0xb4],
		"reserved_area1": rom[0xb5:0xbc],
		"software_version": rom[0xbc],
		"compliment_check": rom[0xbd],
		"reserved_area2": rom[0xbe:0xc0]
	}
	return header

def get_product_code(game_code):

	#Generates a product code from the internal game code
	#A product code is the code that appears on the game's box and respective cartridge label.
	#For example:
	#Super Mario Advance 2 - Super Mario World's game code is AA2E.
	#The product code is AGB-AA2E-USA.

	if len(game_code) > 4:
		raise Exception('Game code must be 4 letters.')

	try:	
		region = region_id(game_code[3]).name
	except:
		return None
	return "AGB-" + game_code + '-' + region_name[region].value
