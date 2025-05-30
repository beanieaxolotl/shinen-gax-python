import struct
import re
from . import general
import math
from . import gba

from .gax_enums import (
	perf_row_effect, step_effect
)
from .gax_constants import (
	mixing_rates, note_names, max_channels, min_channels, max_fx_channels, libgax_consts
)


class step_command:
	def __init__(self):
		self.semitone     = 0
		self.instrument   = 0
		self.effect_type  = step_effect(0x0)
		self.effect_param = 0

	def pack_command(self):
		packed_cmd = b''

		if self.semitone > 0 and self.instrument >= 0 and self.effect_type.value == 0 and self.effect_param == 0:
			# note / note off (no effect)
			packed_cmd += struct.pack('<2B', self.semitone ^ 0x80, self.instrument) #upper bit gets set here

		elif self.semitone == 0 and self.instrument == 0 and self.effect_type.value >= 0 and self.effect_param >= 0:
			# effect only
			packed_cmd += b'\xfa'
			packed_cmd += struct.pack('<2B', self.effect_type.value, self.effect_param)

		else:
			# note / note off (with effect)
			packed_cmd += struct.pack('<4B', self.semitone, self.instrument, self.effect_type.value, self.effect_param)


		return packed_cmd


## main functions ##

def unpack_steps(data, offset, step_count):	

	'''
	Unpack step data from an offset. The step count should be set to the song's step count.
	'''

	def setEffectData(step, data, offset):
		step.effect_type  = step_effect(data[offset])
		step.effect_param = data[offset+1]

	if general.get_bool_from_num(data[offset]) == True:
		return [step_command() for n in range(step_count)] #create a new empty pattern instead of outputting a None object

	offset += 1
	cmd_size = 0
	step_list = list()
	step_counter = 0 #keep track of how many steps we actually parse

	while step_counter < step_count:
		unpacked_step = step_command()

		if data[offset] == 0x80:
			##empty step
			cmd_size = 1
			step_counter += 1
			step_list.append(step_command()) #blank step command object

		elif data[offset] == 0xff:
			##multiple empty steps
			for i in range(0, data[offset+1]):
				step_list.append(step_command()) # decompress our RLE command

			cmd_size = 2
			step_counter += data[offset+1]


		elif data[offset] == 0xfa:
			#effect only
			setEffectData(unpacked_step, data, offset+1)

			cmd_size = 3
			step_counter += 1
			step_list.append(unpacked_step)
		

		elif general.get_normalized_bit(data[offset], 7) == 1:
			if (data[offset] & 0x7f) > 1: #strip away the first bit
				unpacked_step.semitone = data[offset] & 0x7f #note + instrument
			else:
				unpacked_step.semitone = 1 #note off + instrument

			unpacked_step.instrument = data[offset + 1]

			cmd_size = 2
			step_counter += 1
			step_list.append(unpacked_step)

		else:
			if data[offset] > 1:
				unpacked_step.semitone = data[offset] #note + effect data
			else:
				unpacked_step.semitone = 1 #note off + effect data

			unpacked_step.instrument = data[offset + 1]
			setEffectData(unpacked_step, data, offset+2)

			step_counter += 1
			cmd_size = 4
			step_list.append(unpacked_step)

		offset += cmd_size

	return (step_list)


def pack_steps(step_data):
	'''
	Pack step data into a binary blob
	'''

	def is_empty(command):
		return(command.semitone == 0 and 
			   command.instrument == 0 and 
			   command.effect_type.value == 0 and 
			   command.effect_param == 0)

	#check for completely empty patterns
	rest_counter = 0
	for step in step_data:
		if is_empty(step):
			rest_counter += 1
	if rest_counter == len(step_data):
		packed_steps = b'\x01'
		return packed_steps
		
	packed_steps = b'\x00'

	rest_counter = -1
	step_idx = 0


	def rest_compress():
		nonlocal packed_steps
		if rest_counter == 0:
			packed_steps += b'\x80'
		elif rest_counter > 0: #compress rests using RLE
			packed_steps += b'\xff'
			packed_steps += (rest_counter+1).to_bytes(1, byteorder='little', signed=False)


	for command in step_data:

		if not is_empty(command):
			rest_compress()

		if not is_empty(command):
			rest_counter = -1
		else:
			rest_counter += 1

		if rest_counter == -1:
			packed_steps += command.pack_command()

		step_idx += 1

	if rest_counter >= 0 and step_idx == len(step_data):
		if is_empty(command):
			rest_compress()


	return packed_steps


def semitone_to_note(semitone):
	'''
	Converts a given semitone into a formatted tracker note
	'''
	return note_names[(semitone-2) % 12] + str(math.floor((semitone-2)/12))
	#cross checked with GAX tracker screenshot: B-5 = 0x49


class song_properties:

	''' 
	Unpacker class for GAX song properties.

	Options:
		is_gax_gba: If set, this takes into account the GBA's ROM address offset (0x8000000).

	'''

	def __init__(self, data, offset, is_gax_gba = False, unpack = True, 
				 step_count=64, channel_count=6):

		if unpack:
			props_struct = struct.unpack_from('<Bx4Hxx3L2HB', data, offset)

			if props_struct[0] > max_channels:
				raise ValueError("Maximum channel count exceeded")

			#unpack song properties and params
			self.channel_count = props_struct[0]
			self.step_count = props_struct[1]
			self.song_length = props_struct[2]
			self.restart_position = props_struct[3]
			self.song_volume = props_struct[4]

			if is_gax_gba:
				self.step_data_pointer = gba.from_rom_address(props_struct[5])
				self.instrument_set_pointer = gba.from_rom_address(props_struct[6])
				self.wave_set_pointer = gba.from_rom_address(props_struct[7])
			else:
				self.step_data_pointer = props_struct[5]
				self.instrument_set_pointer = props_struct[6]
				self.wave_set_pointer = props_struct[7]

			self.mixing_rate = props_struct[8]
			self.fx_mixing_rate = props_struct[9]

			self.fx_channel_count = props_struct[10]

			self.channel_addr_table = list(struct.unpack_from("<" + "L" * self.channel_count, data, offset + 0x20))

			if is_gax_gba:

				#convert ROM addresses to pointers into ROM file

				for i in range(len(self.channel_addr_table)):
					self.channel_addr_table[i] = gba.from_rom_address(self.channel_addr_table[i])	
		
		else:

			self.channel_count = channel_count
			self.step_count = step_count #64 steps is confirmed by Harry Potter: Quidditch World Cup -> "" © Manfred Linzner
			self.song_length = 1
			self.restart_position = 0
			self.song_volume = 256

			self.mixing_rate = 15769
			self.fx_mixing_rate = 0 # share the song's mixing rate

			self.fx_channel_count = 2


	def pack_properties(self) -> dict:

		#integrity checks for properties
		##
		#music channels
		if self.channel_count > max_channels:
			raise ValueError("Maximum channel count exceeded")
		#music mix rate
		if self.mixing_rate < min(mixing_rates) or self.mixing_rate > max(mixing_rates):
			raise ValueError("Invalid music mixing rate supplied")
		#fx mix rate
		if (self.fx_mixing_rate < min(mixing_rates) or 
			self.fx_mixing_rate > max(mixing_rates)) and self.fx_mixing_rate != 0:
			#0 is actually a valid value here; this means that it shares the music mixing rate
			raise ValueError("Invalid FX mixing rate supplied")	
		#fx channels
		if (self.fx_channel_count > max_fx_channels):
			raise ValueError("Maximum FX channel count exceeded")
		

		a = struct.pack('<Bx4Hxx', 
			self.channel_count,
			self.step_count,
			self.song_length,
			self.restart_position,
			self.song_volume)

		b = struct.pack('2HB3x',
			self.mixing_rate,
			self.fx_mixing_rate,
			self.fx_channel_count)

		return {
			"song_properties": a,
			"mixing_rates_&_fx": b
		}


class song_data:

	''' 
	Unpacker class for GAX song data.

	Options:
		is_gax_gba: If set, this takes into account the GBA's ROM address offset (0x8000000).

	'''


	def __init__(self, data, offset, is_gax_gba = False, unpack = True, step_count=64, channel_count=6):

		self.properties = song_properties(data, offset, is_gax_gba, unpack, step_count, channel_count)

		if unpack:

			if self.properties.channel_count != 0: # the object has song data

				#get song metadata field
				field_end_offset = min(self.properties.channel_addr_table)

				for i in range(4): #skip through the 32-bit alignment padding
					if data[field_end_offset - 1] != 0x00:
						break
					field_end_offset -= 1

				#extract song metadata

				field_start_offset = field_end_offset
				quote_counter = 0

				while 0x20 <= data[field_start_offset - 1] <= 0x92 or data[field_start_offset - 1] == 0xa9:
					field_start_offset -= 1

					if data[field_start_offset] == ord('"'):
						quote_counter += 1
						if quote_counter >= 2: #fixes Happy Feet - Land Exploration
							break

				while data[field_start_offset] != ord('"'):
					field_start_offset += 1

				#removed third while loop: it was breaking songs without a name

				self.song_metadata_field = data[field_start_offset:field_end_offset].decode('iso-8859-1')

				#reconstruct order list
				channel_num = 0
				self.order_list = list()
				step_data_pointers = list()

				for channel_address in self.properties.channel_addr_table:

					channel_num += 1
					offset = 0
					order_line = list()

					for __ in range(self.properties.song_length):

						#get relative pattern pointer from the order list
						order_block = list(struct.unpack("<Hbx", data[channel_address+(offset*4):channel_address+((offset+1)*4)]))

						#make it absolute
						order_block[0] += self.properties.step_data_pointer
						step_data_pointers.append(order_block[0])

						order_line.append(order_block)
						offset += 1

					self.order_list.append(order_line)

				#create map of the patterns in the song
				step_data_pointers = sorted(set(list(step_data_pointers)))
				#retrieve original order list
				for channel in self.order_list:
					for position in channel:
						position[0] = step_data_pointers.index(position[0])

				#unpack the patterns / step data
				self.patterns = list()

				for step_data_addr in step_data_pointers:

					step_list = unpack_steps(data, step_data_addr, self.properties.step_count)
					self.patterns.append(step_list)

			#else we have an FX object

		else:

			self.order_list = list()
			self.patterns = list()

			for i in range(self.properties.channel_count):
				self.order_list.append([[i,0]])

			for __ in range(self.properties.channel_count):
				self.patterns.append([step_command() for n in range(self.properties.step_count)])



	def get_properties(self):
		return self.properties		

	def get_patterns(self):
		return self.patterns

	def get_order_list(self):
		return self.order_list
		

	def get_song_metadata(self) -> dict:
		metadata = re.match(r"\"(.+)?\" © (.+)", self.song_metadata_field).groups()

		# handler for nonexistent song names
		if metadata[0] == None:
			song_name = ''
		else:
			song_name = metadata[0]

		metadata = {
			# internal names gleaned from GAX v3.chm and ghx2 files
			"songname": song_name,
			"auth": metadata[1]
		}
		return metadata


	def get_cpp_define(self, song_prefix = False) -> str:
		'''
		Converts internal song metadata back into a GAX header define
		'''
		header = re.match(r"\"(.+)?\" © (.+)", self.song_metadata_field).groups()[0]
		header = re.sub(r"([_\'.\x92!\/])", "", header, 0, re.MULTILINE)

		if song_prefix:
			header = "SONG_Song_" + re.sub(r"([- ])", "_", header, 0, re.MULTILINE)
		else:
			header = "SONG__" + re.sub(r"([- ])", "_", header, 0, re.MULTILINE)

		return(header)


	def pack_song_data(self) -> dict:
		packed_patterns = b''
		pattern_pointers = list() # these are relative pointers

		for pattern in self.get_patterns():
			pattern_pointers.append(len(packed_patterns))
			packed_patterns += pack_steps(pattern)

		return {
			"pattern_pointers": pattern_pointers,
			"pattern_data": packed_patterns
		}


class wave_set:
	def __init__(self, data, offset, is_gax_gba = False, unpack = True):

		if unpack:

			if is_gax_gba:
				end_offset = gba.from_rom_address(int.from_bytes(data[4:8], byteorder='little'))
			else:
				end_offset = int.from_bytes(data[4:8], byteorder='little')

			self.wave_bank = list()

			while True:

				if offset >= len(data) or offset >= end_offset:
					break

				wave_metadata = list(struct.unpack_from("<2L", data, offset))
				if wave_metadata[1] > offset:
					break
				
				if is_gax_gba:
					if wave_metadata[0] != 0: # don't attempt to turn a null address into a file offset
						wave_metadata[0] = gba.from_rom_address(wave_metadata[0])

				if wave_metadata[0] >= len(data):
					break
				else:
					offset += 8
					self.wave_bank.append(data[wave_metadata[0]:wave_metadata[0]+wave_metadata[1]])

		else:
			self.wave_bank = [b''] # sample #0 is always empty in GAX v3+



class instrument:
	def __init__(self, data, offset, is_gax_gba = False, unpack = True):

		self.name = ""

		if unpack:

			# subfunctions
			def append_wave_params(params_list):
				wave_params_struct = struct.unpack_from("<hBB3Ll2H", data, offset)
				if (wave_params_struct[2] > 1) or (wave_params_struct[1] > 1):
					params_list.append(None)
				else:
					params_list.append({
						"finetune": wave_params_struct[0],
						"modulate": wave_params_struct[1] == True,
						"ping_pong": wave_params_struct[2] == True,
						"start_position": wave_params_struct[3],
						"loop_start": wave_params_struct[4],
						"loop_end": wave_params_struct[5],
						"modulate_size": wave_params_struct[6],
						"modulate_step": wave_params_struct[7],
						"modulate_speed": wave_params_struct[8]
					})		

			instrument_header_pointer = offset

			header_struct = struct.unpack_from("<?4Bxxx3BxL2bHL", data, offset)
			self.header = {
				"is_null": header_struct[0],
				"wave_slots": list(header_struct[1:5]),

				"vibrato_params": {
					"vibrato_wait": header_struct[5], # GAX screenshot used as a source for these names
					"vibrato_depth": header_struct[6],
					"vibrato_speed": header_struct[7]
				}
			}


			# unpack perf list data
			perf_list_pointer = header_struct[12]
			if is_gax_gba:
				perf_list_pointer = gba.from_rom_address(perf_list_pointer)

			offset = perf_list_pointer
			self.perf_list = {
				"perf_row_speed": header_struct[9],
				"perf_list_data": list()
			}

			perflist_struct = struct.unpack_from('<B?Bx4B', data, offset)

			for __ in range(header_struct[10]):
				perflist_struct = struct.unpack_from('<B?Bx4B', data, offset)
				perf_row = {
					"note": perflist_struct[0], # HQ GAX editor screenshot used as a source for these names
					"fixed": perflist_struct[1],
					"wave_slot_id": perflist_struct[2],

					"effect": [(perflist_struct[3], perf_row_effect(perflist_struct[4])), (perflist_struct[5], perf_row_effect(perflist_struct[6]))]
				}
				self.perf_list["perf_list_data"].append(perf_row)
				offset += 8


			# unpack volume envelope data
			volenv_pointer = header_struct[8]
			if is_gax_gba:
				volenv_pointer = gba.from_rom_address(volenv_pointer)

			self.unknown_u16 = header_struct[11]

			offset = volenv_pointer
			del header_struct

			volenv_struct = struct.unpack_from('<4B', data, offset)
			self.volume_envelope = {
				"sustain_point": volenv_struct[1],
				"loop_start": volenv_struct[2],
				"loop_end": volenv_struct[3],
				"points": []
			}

			# conversion of empty envelope looping and sustain values
			if self.volume_envelope["sustain_point"] == 0xff:
				self.volume_envelope["sustain_point"] = None
			if self.volume_envelope["loop_start"] == 0xff:
				self.volume_envelope["loop_start"] = None
			if self.volume_envelope["loop_end"] == 0xff:
				self.volume_envelope["loop_end"] = None

			offset += 4 # go to start of volenv data
			for __ in range(volenv_struct[0]):
				point = struct.unpack_from('<HxxB3x', data, offset) # ignore slope rise/fall value
				self.volume_envelope["points"].append(point)
				offset += 8

			del volenv_struct


			# finally, unpack wave parameters

			instrument_wave_pointer = instrument_header_pointer + 24
			offset = instrument_wave_pointer
			self.wave_params = list()

			# count the number of used waveform slots
			wave_slot_count = len([x for x in self.header["wave_slots"] if x != 0])
			if wave_slot_count > 0:
				for i in range(4):
					if self.header["wave_slots"][i] > 0:
						append_wave_params(self.wave_params)
						offset += 24
					else: 
						self.wave_params.append(None)

			else: # handler for empty instruments:
				append_wave_params(self.wave_params)


		else:

			# prepare dicts for the class variables 
			perf_row = {
				"note": 0,
				"fixed": False,
				"wave_slot_id": 1,

				"effect": [(0, perf_row_effect(0)), (0, perf_row_effect(0))]
			}
			wave_params_default = {
				"finetune": 0,
				"modulate": False,
				"ping_pong": False,
				"start_position": 0,
				"loop_start": 0,
				"loop_end": 0,
				"modulate_size": 0,
				"modulate_step": 0,
				"modulate_speed": 0
			}

			self.header = {
				"is_null": True,
				"wave_slots": [0]*4,

				"vibrato_params": {
					"vibrato_wait": 0,
					"vibrato_depth": 0,
					"vibrato_speed": 0
				}
			}

			self.perf_list = {
				"perf_row_speed": 1,
				"perf_list_data": [perf_row]
			}

			self.unknown_u16 = 0

			self.volume_envelope = {
				"sustain_point": None,
				"loop_start": None,
				"loop_end": None,
				"points": [(0,255)]
			}

			self.wave_params = [wave_params_default, None, None, None]

			del perf_row
			del wave_params_default

			

	def pack_instrument(self):

		def pack_GAX_byte(val):
			if val == None:
				return b'\xff'
			else:
				return val.to_bytes(1, signed=False)


		# pack the "volenv" data
		volenv_packed = struct.pack('<B', len(self.volume_envelope["points"]))
		volenv_packed += pack_GAX_byte(self.volume_envelope["sustain_point"])
		volenv_packed += pack_GAX_byte(self.volume_envelope["loop_start"])
		volenv_packed += pack_GAX_byte(self.volume_envelope["loop_end"])

		# start packing the volume envelope data itself
		# inbetween the x and y values there is a lerp value
		# i literally wouldn't have figured this out without desmos and a buddy at school

		i = 0
		j = i - 1

		for point in self.volume_envelope["points"]:

			if j < 0:
				j = 0 # prevent negative indexing

			try:
				lerp = math.trunc(
					(self.volume_envelope["points"][j][1] - self.volume_envelope["points"][i][1])/
					(self.volume_envelope["points"][j][0] - self.volume_envelope["points"][i][0])*256)

			except:
				lerp = 0

			if lerp < -32768: # signed short handler
				lerp &= 0x7fff
			elif lerp > 32767:
				lerp -= 65536

			volenv_packed += struct.pack('<HhB3x', point[0], lerp, point[1])

			i += 1
			j = i - 1


		# pack the performance list
		perflist_packed = b''
		for row in self.perf_list["perf_list_data"]:
			perflist_packed += struct.pack('<B?Bx4B',
				row['note'], row['fixed'], row['wave_slot_id'],
				row['effect'][0][0],
				row['effect'][0][1].value,
				row['effect'][1][0],
				row['effect'][1][1].value)


		# finally pack the instrument's header (internally referred to as a instrument by itself)
		# this is in a bunch of parts since we can't feasibly calculate pointers here

		instrument_header_packed = list()

		a = struct.pack("<?4B",
			self.header["is_null"],
			self.header["wave_slots"][0],
			self.header["wave_slots"][1],
			self.header["wave_slots"][2],
			self.header["wave_slots"][3]
			)
		a += struct.pack("<xxx3Bx",
			self.header["vibrato_params"]["vibrato_wait"],
			self.header["vibrato_params"]["vibrato_depth"],
			self.header["vibrato_params"]["vibrato_speed"]
			)

		instrument_header_packed.append(a) # part 1 > wave slots and vibrato parameters

		a = struct.pack("<2bH",
			self.perf_list["perf_row_speed"],
			len(self.perf_list["perf_list_data"]),
			self.unknown_u16
			)

		instrument_header_packed.append(a) # part 2 > performance row properties

		b = b''
		for wave_property in self.wave_params:
			if wave_property != None:
				b += struct.pack("<h??3Ll2H",
					wave_property["finetune"],
					wave_property["modulate"],
					wave_property["ping_pong"],
					wave_property["start_position"],
					wave_property["loop_start"],
					wave_property["loop_end"],
					wave_property["modulate_size"],
					wave_property["modulate_step"],
					wave_property["modulate_speed"]
					)

		instrument_header_packed.append(b) # part 3 > waveform properties

		instrument_packed = {
			"volenv": volenv_packed,
			"perflist": perflist_packed,
			"instrument": instrument_header_packed
		}

		return instrument_packed



class gax_module:
	'''
	Python class that represents a GAX binary blob
	'''
	def __init__(self, auth="Manfred Linzner"):
		self.version        = "3.05A" # do we really need this? maybe
		self.instrument_set = list()
		self.wave_set       = list()
		self.song_bank = {
			"auth": auth,
			"songs": list()
		}

	def get_song_count(self) -> int:
		return len(self.song_bank["songs"])

	def get_wave_count(self) -> int:
		return len(self.wave_set.wave_bank)

	def get_instrument_count(self) -> int:
		return len(self.instrument_set)	


	def get_auth(self) -> str:
		return self.song_bank["auth"]

	def get_song(self, idx):
		if idx >= self.get_song_count():
			raise ValueError("Invalid song ID")
		return self.song_bank["songs"][idx]

	def get_song_name(self, idx) -> str:
		return self.get_song(idx)["songname"]

	def get_song_data(self, idx):
		return self.get_song(idx)["songdata"]


def get_GAX_filetype(file):
	'''
	Retrieves the file type of a GAX-related file stream.
	'''
	if (file[0:4] == b'GHXC' 
		and file[0xc:0x10] == b'LZOD' 
		and file[0x16:0x21] == b'GHX20153SONG'): # sigma_04.ghx2
		return "ghx2"

	elif file[0:4] == b'GAX!': # music.gax ~ m05.o
		return "gax_ngage"
	else:
		return None


def unpack_GAX_file(gax_file):
	'''
	Unpacks a GAX/NAX binary file into an editable Python object
	'''

	# check file type of the chosen file
	file_type = get_GAX_filetype(gax_file)
	unpacked_GAX_file = gax_module()

	if file_type in ["ghx2", None]:
		raise ValueError("Unsupported format")

	if file_type == "gax_ngage": # Crash Nitro Kart / Payload (Nokia N.Gage)
		# get song pointers
		song_pointers = list()
		index = 4

		while True:
			song_pointer = int.from_bytes(gax_file[index:index+4], byteorder='little')
			if song_pointer > len(gax_file):
				del song_pointer
				break
			else:
				song_pointers.append(song_pointer)
			index += 4

		song_pointer_id = 0

		for song_pointer in song_pointers:

			unpacked_song_data = song_data(gax_file, song_pointer)

			# just make it a lil' neater mkay?
			song_props = unpacked_song_data.properties
			instrument_set_pointer = song_props.instrument_set_pointer
			wave_set_pointer = song_props.wave_set_pointer

			# get the first instance of an AUTH tag
			if song_pointer_id == 0 and song_props.channel_count != 0:
				auth_tag = unpacked_song_data.get_song_metadata()["auth"]

			# integrity checks
			if general.is_dword_aligned(instrument_set_pointer) == False:
				raise Exception("Instrument set pointer is not aligned to a dword")
			elif instrument_set_pointer >= len(gax_file):
				raise ValueError("Instrument set pointer is out-of-bounds")

			if general.is_dword_aligned(wave_set_pointer) == False:
				raise Exception("Wave set pointer is not aligned to a dword")
			elif wave_set_pointer >= len(gax_file):
				raise ValueError("Wave set pointer is out-of-bounds")		

			if song_props.channel_count != 0: # if we're in a music object

				author = unpacked_song_data.get_song_metadata()["auth"]
				# delete pointers since we don't need them anymore
				del song_props.step_data_pointer
				del song_props.instrument_set_pointer
				del song_props.wave_set_pointer

				unpacked_song_data = {
					"songname": unpacked_song_data.get_song_metadata()["songname"],
					"songdata": unpacked_song_data
				}

				# check the saved auth tag against the rest of the auth tags
				if auth_tag != author:
					raise Exception("All instances of the AUTH field must be identical")

				# set the auth tag when we find it
				unpacked_GAX_file.song_bank["auth"] = auth_tag
				unpacked_GAX_file.song_bank["songs"].append(unpacked_song_data)

			song_pointer_id += 1

		# unpack waveforms (that's their actual internal name btw)
		unpacked_GAX_file.wave_set = wave_set(gax_file, wave_set_pointer)

		# unpack instrument pointer set
		instrument_pointers = list()
		index = instrument_set_pointer
		while True:
			instrument_header_pointer = int.from_bytes(gax_file[index:index+4], byteorder='little')
			if instrument_header_pointer > len(gax_file):
				break
			instrument_pointers.append(instrument_header_pointer)
			index += 4

		for pointer in instrument_pointers:
			instrument_object = instrument(gax_file, pointer)
			unpacked_GAX_file.instrument_set.append(instrument_object)

		return unpacked_GAX_file


def unpack_gax_from_rom(pointers, rom):
	'''
	Unpacks GAX Sound Engine data from an extracted song pointers list.
	Requires a supplied ROM file object to work
	'''

	unpacked_GAX_file = gax_module()

	idx = 0 # internally count the id of the song pointer we're on

	for song_pointer in pointers:
		unpacked_song_data = song_data(rom, song_pointer, is_gax_gba = True)

		song_props = unpacked_song_data.properties	

		# all songs share the same instruments + waveforms. make sure the pointers for these things are the same across all songs
		if idx > 0 and (instrument_set_pointer != song_props.instrument_set_pointer or wave_set_pointer != song_props.wave_set_pointer):
			raise Exception("All songs must share the same instrument and waveform set")

		instrument_set_pointer = song_props.instrument_set_pointer
		wave_set_pointer = song_props.wave_set_pointer

		if idx == 0 and song_props.channel_count != 0:
			auth_tag = unpacked_song_data.get_song_metadata()["auth"]

		if general.is_dword_aligned(instrument_set_pointer) == False:
			raise Exception("Instrument set pointer is not aligned to a dword")
		elif instrument_set_pointer >= len(rom):
			raise ValueError("Instrument set pointer is outside of ROM!")

		if general.is_dword_aligned(wave_set_pointer) == False:
			raise Exception("Wave set pointer is not aligned to a dword")
		elif wave_set_pointer >= len(rom):
			raise ValueError("Wave set pointer is outside of ROM!")		


		if song_props.channel_count != 0: # non-FX objects

			author = unpacked_song_data.get_song_metadata()["auth"]
			# delete pointers since we don't need them anymore
			del song_props.step_data_pointer
			del song_props.instrument_set_pointer
			del song_props.wave_set_pointer

			unpacked_song_data = {
				"songname": unpacked_song_data.get_song_metadata()["songname"],
				"songdata": unpacked_song_data
			}

			if auth_tag != author:
				raise Exception("All instances of the AUTH field must be identical")

			unpacked_GAX_file.song_bank["auth"] = auth_tag
			unpacked_GAX_file.song_bank["songs"].append(unpacked_song_data)

		idx += 1

	unpacked_GAX_file.wave_set = wave_set(rom, wave_set_pointer, is_gax_gba = True)

	instrument_pointers = list()
	index = instrument_set_pointer
	while True:
		instrument_header_pointer = gba.from_rom_address(int.from_bytes(rom[index:index+4], byteorder='little'))
		if instrument_header_pointer > len(rom):
			break
		instrument_pointers.append(instrument_header_pointer)
		index += 4

	for pointer in instrument_pointers:
		instrument_object = instrument(rom, pointer, is_gax_gba = True)
		unpacked_GAX_file.instrument_set.append(instrument_object)

	return unpacked_GAX_file


def get_cpp_define_file(gax_module, has_prefix = False):

	'''
	Returns a guesstimate of the original input music.h file (included with the GAX library + object files).

	Options:
		has_prefix: Set this to recreate music.h files for GAX Sound Engine games developed in the timespan of 2005-07
		(i.e American Dragon Jake Long, Unfabulous)
	'''

	song_bank = gax_module.song_bank["songs"]
	cpp_header = "#ifndef __INCLUDED_1120209085__\n#define __INCLUDED_1120209085__\n\n#include \"gax.h\"\n\n#ifdef __cplusplus\nextern \"C\"{\n#endif\n\n"

	for i in range(len(song_bank)):

		if has_prefix:
			cpp_header += "extern const GAXVoid gaxSong"
		else:
			cpp_header += "extern const GAXVoid gax"
		cpp_header += str(i) + "_package;\n"

		x = song_bank[i-1]['songdata'].get_cpp_define(song_prefix = has_prefix)
		header_define = song_bank[i]['songdata'].get_cpp_define(song_prefix = has_prefix)

		if has_prefix:
			gax_defineName = " gaxSong"
		else:
			gax_defineName = " gax"

		# detect duplicate song names and append song ID
		cpp_header += "#define " + header_define	
		if x != header_define:
			cpp_header += gax_defineName + str(i) + "_package\n\n"
		else:
			cpp_header += str(i) + gax_defineName + str(i) + "_package\n\n"

	cpp_header += "#ifdef __cplusplus\n}\n#endif\n\n#endif"

	return cpp_header


def pack_GAX_file(gax_module, compile_object=False, blob_offset=0):
	'''
	Packs a shinen_gax GAX object into a .gax format binary file

	Options:
		compile_object: If set, this converts the GAX object into a binary blob w/o song pointers at the start.
	'''

	output_stream = bytearray()

	if compile_object:
		pass

	else:
		# otherwise just create the file header.
		# the zero padding is a placeholder for the song property pointers
		song_count = gax_module.get_song_count()
		if song_count == 0:
			song_count = 1

		output_stream += b'GAX!' + (b'\x00\x00\x00\x00') * song_count


	# some common-sense error handling
	if len(gax_module.instrument_set) > 255:
		raise Exception("Too many instruments!")
	elif len(gax_module.wave_set.wave_bank) > 255:
		raise Exception("Too many waveforms!")


	instrument_pointers = list()
	idx = 0
	blank_instr_pointer = 0

	for instrument in gax_module.instrument_set: # pack instrument data

		# subfunctions

		def append_instrument(packed_instr):
			nonlocal instrument_pointers
			nonlocal output_stream
			nonlocal blank_instr_pointer

			volenv_pointer = len(output_stream)+blob_offset
			output_stream += packed_instr['volenv']

			perflist_pointer = len(output_stream)+blob_offset
			output_stream += packed_instr['perflist']

			if idx > 0:
				instrument_pointers.append(len(output_stream)+blob_offset)
			else:
				blank_instr_pointer = len(output_stream)+blob_offset
				instrument_pointers.append(blank_instr_pointer)

			output_stream += packed_instr['instrument'][0]
			output_stream += volenv_pointer.to_bytes(4, byteorder='little', signed=False)
			output_stream += packed_instr['instrument'][1]
			output_stream += perflist_pointer.to_bytes(4, byteorder='little', signed=False)
			output_stream += packed_instr['instrument'][2]


		packed_instrument = instrument.pack_instrument()

		if instrument.header["is_null"] and idx == 0:
			blank_instr_pointer = len(output_stream)+blob_offset # get pointer to blank instrument so we can reuse it later

		if instrument.header["is_null"] and idx > 0:
			instrument_pointers.append(blank_instr_pointer) # reuse blank instr. pointer if possible
		else:
			append_instrument(packed_instrument)

		idx += 1


	# create instrument pointer array
	instrument_bank_pointer = len(output_stream)+blob_offset
	for pointer in instrument_pointers:
		output_stream += pointer.to_bytes(4, byteorder='little', signed=False)


	# create waveform data
	wave_bank_start_pointer = len(output_stream)+blob_offset
	wave_pointers = list()

	idx = 0
	for waveform in gax_module.wave_set.wave_bank:
		wave_pointers.append([len(output_stream)+blob_offset, len(waveform)])
		if idx == 0:
			output_stream += b'\x80'*2048 # generate null waveform
		else:		
			output_stream += waveform
		idx += 1

	# pad to nearest dword alignment
	while general.is_dword_aligned(len(output_stream)+blob_offset) != True:
		output_stream += b'\x00'

	wave_bank_end_pointer = len(output_stream)+blob_offset # internally called null waves
	output_stream += struct.pack('<2L', wave_pointers[0][0], wave_pointers[0][1])
	wave_bank_pointer = len(output_stream)+blob_offset

	output_stream += struct.pack('<2L', wave_bank_end_pointer, 0)

	for pointer in wave_pointers[1:len(wave_pointers)]:
		if pointer[1] == 0: # handler for deleted samples
			output_stream += struct.pack('<2L', 0, 0)
		else:
			output_stream += struct.pack('<2L', pointer[0], pointer[1])


	song_pointers = list()


	if len(gax_module.song_bank["songs"]) > 0:

		# music data #

		for song in gax_module.song_bank["songs"]:

			sequence_pointer = len(output_stream)+blob_offset
			track_data = song["songdata"].pack_song_data() # these are called tracks
			exp_auth = (
				'"' + song["songname"] + '" © ' + gax_module.get_auth()
				).encode('iso-8859-1') # exported metadata string


			output_stream += track_data["pattern_data"]
			output_stream += exp_auth
			while general.is_dword_aligned(len(output_stream)+blob_offset) != True:
				output_stream += b'\x00' # align the end of this data to the nearest dword

			# create channel playlists (or positions)

			pos_idx = 0 # keep track of the current "position"
			channel_address_table = list()
			for position in song["songdata"].order_list:
				channel_address_table.append(len(output_stream)+blob_offset)

				for pattern_idx in position:
					output_stream += struct.pack("<Hbx", 
						track_data["pattern_pointers"][pattern_idx[0]],
						pattern_idx[1]
						)

				pos_idx += 1

			# now get the address of the current song's properties
			song_pointers.append(len(output_stream))
			packed_properties = song["songdata"].properties.pack_properties()


			output_stream += packed_properties["song_properties"]
			output_stream += struct.pack('<3L',
				sequence_pointer,
				instrument_bank_pointer,
				wave_bank_pointer
				)
			output_stream += packed_properties["mixing_rates_&_fx"]


			channel_address_table_bytes = b''

			if len(channel_address_table) > 42:
				# this should not happen
				raise Exception("Can't fit the following channel addresses into a 42 dword array")

			for address in channel_address_table:
				channel_address_table_bytes += address.to_bytes(4, byteorder='little', signed=False)

			while len(channel_address_table_bytes) != 0xa8:
				channel_address_table_bytes += b'\x00'*4

			output_stream += channel_address_table_bytes

			if not compile_object:
				offset = 4
				for pointer in song_pointers:
					output_stream[offset:offset+4] = pointer.to_bytes(4, byteorder='little')
					offset += 4

	else:

		song_pointers.append(len(output_stream))
		output_stream += b'\x00'*(4*4)
		output_stream += struct.pack('<2L', instrument_bank_pointer, wave_bank_pointer)
		output_stream += b'\x00'*(58*4)

		offset = 4
		for pointer in song_pointers:
			output_stream[offset:offset+4] = pointer.to_bytes(4, byteorder='little')
			offset += 4		

	return output_stream


def get_GAX_version(rom):
	'''
	Gets the GAX Sound Engine library version string from a binary
	'''
	string_regex = rb'GAX Sound Engine v?(\d)\.(\d{1,2})([a-zA-Z-]{,4}) \(([a-zA-Z]{3} *\d{1,2} \d{4})\)'	

	result = re.search(string_regex, rom)
	if result != None:
		result = re.search(string_regex, rom)[0]

	return result


def get_GAX_sublibs(rom):
	'''
	Gets the location of several sub-libraries that are included with libgax.a
	'''
	func_names = list()
	func_pos = list()

	for func in libgax_consts:

		func_pos += [rom.find(libgax_consts.get(func))]
		func_names += [func]

	return dict(zip(func_names, func_pos))


def includes_GAX(rom):
	''' 
	Returns a bool. This is set to true if the ROM has a GAX version string.
	'''
	return get_GAX_version(rom) == True


def get_GAX_library(rom):

	version_str = get_GAX_version(rom)
	if version_str == None:
		raise Exception("Specified ROM has no GAX version string")

	gax_library = {
		"version_str": version_str.decode('iso-8859-1'),
		"libgax_subfuncs": get_GAX_sublibs(rom)
	}

	return(gax_library)

