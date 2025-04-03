from .gax_enums import (
	perf_row_effect, step_effect
)
from . import shinen_gax as gax

#gax dictionary object return functions
def perf_row():
	return {
		"note": 0,
		"fixed": False,
		"wave_slot_id": 0,

		"effect": [(0, perf_row_effect(0)), (0, perf_row_effect(0))]
	}

def wave_param():
	return {
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


#generator return functions
def generate_song_metadata(song_name = "", auth_name = "Manfred Linzner"):
	return ('"' + song_name + '" © ' + auth_name).encode('iso-8859-1')

def generate_order_list(channel_count):
	return [[0,0]]*channel_count

def generate_instrument(return_empty = False):
	if return_empty:
		return gax.instrument(None, 0, unpack=False)
	instr_obj = gax.instrument(None, 0, unpack=False)
	instr_obj.header["is_null"] = False
	return instr_obj

def generate_wavetable_set():
	return gax.wave_set(None, 0, unpack=False)


#gax object generators
def gax_song_template(song_name = "", auth_name = "Manfred Linzner"):
	song_obj = gax.song_data(None, 0, unpack=False)
	song_obj.song_metadata_field = generate_song_metadata(song_name=song_name, auth_name=auth_name)
	return song_obj

def gax_module_template(auth_name = "Manfred Linzner", add_instr = True):
	gax_obj = gax.gax_module(auth=auth_name)
	#start setting up the empty object for use

	#set up instrument #0 - can't be accessed directly in GAX editor
	if add_instr:
		for __ in range(2):
			gax_obj.instrument_set.append(gax.instrument(None, 0, unpack=False))
		gax_obj.instrument_set[-1].header["is_null"] = False
	else:
		gax_obj.instrument_set.append(gax.instrument(None, 0, unpack=False))

	gax_obj.wave_set = (gax.wave_set(None, 0, unpack=False))

	gax_obj.song_bank["auth"] = auth_name
	gax_obj.song_bank["songs"].append(
		{
			"songname": "",
			"songdata": gax_song_template(auth_name=auth_name)
		}
	)

	return gax_obj

