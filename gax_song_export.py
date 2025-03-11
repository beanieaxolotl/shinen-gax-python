from libs.shinen_gax import *
from libs.gax_wrapper import gax_replayer
from libs.general import sign_flip
import pyaudio
import os
import wave
import argparse

## variables ##

fps = 59.7275
max_loops = 2
output_buffer = b''

hqx_render = True


## functions ##

def setup_GAX(mus_path):

	global gax_obj

	with open(mus_path, "rb") as f:

		gax_file = f.read()

		try:
			gax_obj = unpack_GAX_file(gax_file)
		except:
			#addresses the error message in #16 ~ "Song Export Not currently functioning..."
			raise Exception("Could not unpack {} as the program couldn't detect it as a .gax file".format(os.path.basename(music_path))) from None
		
		del gax_file


def gaxTitleToWindowsNT(song_title):
	return re.sub(r"[\\\/:*?\"<>|]", "~", song_title, 0, re.MULTILINE)


## main ##

parser = argparse.ArgumentParser()
parser.add_argument('file_path', help=".gax/.o file to load")
parser.add_argument('--idx', default=0, type=int, help="Song in file to load")
parser.add_argument('--loops', default=2, type=int, help="Number of times to repeat the song. Does nothing on one-shot jingles")
parser.add_argument('--hqx', default=False, type=bool, help="Whenever or not to render the specified track at 48khz")

args = parser.parse_args()
music_path = os.path.realpath(args.file_path)
music_idx = args.idx
hqx_render = args.hqx
max_loops = args.loops

if hqx_render:
	mixing_rate = 48000
else:
	mixing_rate = 0

#create output folder
output_path = str(os.getcwd())+"\\song_export\\"
try:
	os.makedirs(output_path)
except:
	pass #path already exists


setup_GAX(music_path)
replayer = gax_replayer(gax_obj, None, music_idx, mixing_rate, fps)
wave_name = "{:0>2X} ~ {} ({} khz).wav".format(music_idx, gaxTitleToWindowsNT(gax_obj.get_song_name(music_idx)), int(replayer.mixing_rate/1000))

print('Filename of output: {}\nOutput path: {}'.format(wave_name, output_path))

while replayer.vars.speed[0] != 0: 
	#luckily there is a way to know when the GAX song stops
	#otherwise this would be computationally impossible to pull off (ever heard of the halting problem?)

	output_buffer += replayer.GAX_play(debug=True)
	if replayer.vars.loop_count >= max_loops:
		break

with wave.open(output_path + wave_name, mode="wb") as wav_file:
	wav_file.setnchannels(1)
	wav_file.setsampwidth(1)
	wav_file.setframerate(replayer.mixing_rate)
	wav_file.writeframes(sign_flip(output_buffer))