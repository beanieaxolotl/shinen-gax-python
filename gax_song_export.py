from libs.shinen_gax import *
from libs.gax_replayer import channel, replayer
from libs.general import sign_flip
import pyaudio
import os
import wave
import argparse


p = pyaudio.PyAudio()

fps = 59.7275
max_loops = 2
output_buffer = b''

hqx_render = True


## functions ##

def init_GAX_song(idx=0):

	global gax_replayer
	global mixing_rate
	global stream

	gax_replayer = replayer(gax_obj, song_idx = idx, allocate_fxch=False)

	if hqx_render:
		mixing_rate = 48000
	else:
		mixing_rate = gax_replayer.song_data.get_properties().mixing_rate

	stream = p.open(format=pyaudio.paInt8,
					channels=1,
					rate=mixing_rate,
					output=True)	

def tick_GAX():

	global output_buffer

	for i in range(gax_replayer.num_channels):
		gax_replayer.channels[i].tick(gax_obj.wave_set.wave_bank, stream, mixing_rate, fps,
									  gain=gax_replayer.mix_amp/100)
	output_buffer += gax_replayer.tick(stream, debug=True)


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


#create output folder
output_path = str(os.getcwd())+"\\song_export\\"
try:
	os.makedirs(output_path)
except:
	pass #path already exists


setup_GAX(music_path)
init_GAX_song(music_idx)
wave_name = "{:0>2X} ~ {} ({} khz).wav".format(music_idx, gaxTitleToWindowsNT(gax_obj.get_song_name(music_idx)), int(mixing_rate/1000))
print('Filename of output: {}\nOutput path: {}'.format(wave_name, output_path))

while gax_replayer.speed[0] != 0: 
	#luckily there is a way to know when the GAX song stops
	#otherwise this would be computationally impossible to pull off (ever heard of the halting problem?)
	tick_GAX()
	if gax_replayer.loop_count >= max_loops:
		break

with wave.open(output_path + wave_name, mode="wb") as wav_file:
	wav_file.setnchannels(1)
	wav_file.setsampwidth(1)
	wav_file.setframerate(mixing_rate)
	wav_file.writeframes(sign_flip(output_buffer))