import argparse
import os
import struct
import libs.shinen_gax as gax
import libs.general as general

parser = argparse.ArgumentParser()
parser.add_argument('file_path', help="GAX .o file")
parser.add_argument('--song_idx', default=0, type=int, help="Song ID to print")


args = parser.parse_args()
#Path and file name of the file
gax_path = os.path.realpath(args.file_path)
file_name = os.path.basename(gax_path)

song_id = args.song_idx


def dump_step_data(step_cmd):

	def dumpEffect(step_cmd):

		effect_str = ''
		unknown_effect = False

		if type(step_cmd.effect_type) == gax.step_effect:

			if step_cmd.effect_type == gax.step_effect.set_volume:
				effect_str = '{:0>2}'.format(f'{step_cmd.effect_param:X}')
				return effect_str
			else:
				effect_str = '{:0>2}'.format(f'{step_cmd.effect_type.value:X}')

		if type(step_cmd.effect_type) == int:
			effect_str = '{:0>2}'.format(f'{step_cmd.effect_type:X}')
			unknown_effect = True

		elif step_cmd.effect_type == None:
			effect_str = '.'

		if step_cmd.effect_param != None:
			effect_str += '{:0>2}'.format(f'{step_cmd.effect_param:X}')
		else:
			effect_str += '..'

		return effect_str

	#we just uncompressed the rle data

	if step_cmd == None: # empty step
		return "...........|"

	elif step_cmd == gax.step_type.note_off: # note off
		return '===........|'

	else:

		if step_cmd.semitone == None: # effect only

			effect_str = dumpEffect(step_cmd)

			if step_cmd.effect_type == gax.step_effect.set_volume:
				return '.....' + effect_str + '....|'
			else:
				return "......." + effect_str + "|"

		if step_cmd.effect_type == None and step_cmd.effect_param == None: #note only

			return gax.semitone_to_note(step_cmd.semitone) + '{:0>2}'.format(f'{step_cmd.instrument:X}') + "......|"

		effect_str = dumpEffect(step_cmd)
		if step_cmd.instrument == 0:
			return gax.semitone_to_note(step_cmd.semitone) + '..' + effect_str + '|'
		else:
			# note + effect

			if step_cmd.effect_type == gax.step_effect.set_volume:
				return gax.semitone_to_note(step_cmd.semitone) + '{:0>2}'.format(f'{step_cmd.instrument:X}') + effect_str + '....|'
			else:
				return gax.semitone_to_note(step_cmd.semitone) + '{:0>2}'.format(f'{step_cmd.instrument:X}') + '..' + effect_str + '|'



with open(gax_path, "rb") as f:

	gax_file = f.read()
	gax_obj = gax.unpack_GAX_file(gax_file)

	print("\n> Composed by", gax_obj.get_auth())
	
	song_count = gax_obj.get_song_count()

	print("> Song", '{:0>2}'.format(f'{song_id}') + ":", gax_obj.get_song_name(song_id) + '\n')

	song_obj = gax_obj.get_song_data(song_id)
	#print(song_obj.dump_order_list())


	for c in range(song_obj.get_properties().song_length):

		step_id = 0
		print("> =========== Position #" + str(c), "=========== <\n")

		song_data_dump = "org.tildearrow.furnace - Pattern Data (214)\n0\n"

		
		for b in range(song_obj.get_properties().step_count):

			for a in range(song_obj.get_properties().channel_count):
				
				pattern_id = song_obj.get_order_list()[a][c][0]

				if song_obj.patterns[pattern_id] != None:
					song_data_dump += dump_step_data(song_obj.patterns[pattern_id][step_id])
				else:
					song_data_dump += "...........|"

			step_id += 1
			song_data_dump += "\n"

		print(song_data_dump)

		print()