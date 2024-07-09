import argparse
import os
import struct
import libs.shinen_gax as gax
import math

parser = argparse.ArgumentParser()
parser.add_argument('file_path', help="GAX .o file")

args = parser.parse_args()
#Path and file name of the file
gax_path = os.path.realpath(args.file_path)
file_name = os.path.basename(gax_path)

with open(gax_path, "rb") as f:

	#create output folder
	output_path = str(os.getcwd())+"\\" + file_name + " (Waveforms)""\\"
	try:
		os.makedirs(output_path)
	except:
		pass #path already exists

	gax_file = f.read()
	gax_obj = gax.unpack_GAX_file(gax_file)

	idx = 0
	for waveform in gax_obj.wave_set.wave_bank:

		if len(waveform) > 0:

			wave_name = "wave_" + '{:0>3}'.format(f'{idx}') + '.raw'
			print(">  Saving waveform to", wave_name, "|", str(len(waveform) / 1024)[0:4], "KiB")

			g = open((output_path + wave_name), "wb")
			g.write(waveform)
			g.close()

		else:
			print(">> Skipping empty waveform")
		
		idx += 1

	print("\nAll waveforms saved!")
