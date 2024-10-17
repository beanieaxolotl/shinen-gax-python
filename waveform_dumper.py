import argparse
import os
import libs.shinen_gax as gax
import wave


parser = argparse.ArgumentParser()
parser.add_argument('file_path', help="GAX .gax/.o file")

args = parser.parse_args()
#Path and file name of the file
gax_path = os.path.realpath(args.file_path)
file_name = os.path.basename(gax_path)

with open(gax_path, "rb") as f:

	#create output folder
	output_path = str(os.getcwd())+"\\waveform_dumps\\" + file_name + " (waveforms)""\\"
	try:
		os.makedirs(output_path)
	except:
		pass #path already exists

	gax_file = f.read()
	gax_obj = gax.unpack_GAX_file(gax_file)

	idx = 0
	for waveform in gax_obj.wave_set.wave_bank:

		if len(waveform) > 0:

			wave_name = "wave_" + '{:0>3}'.format(f'{idx}') + '.wav'
			print(">  saving waveform to {} | {} KiB".format(wave_name, str(len(waveform) / 1024)[0:4]))

			with wave.open(output_path + wave_name, mode="wb") as wav_file:
				wav_file.setnchannels(1)
				wav_file.setsampwidth(1)
				wav_file.setframerate(7884)
				wav_file.writeframes(waveform)

		else:
			print(">> skipping empty waveform")
		
		idx += 1

	print("\nall waveforms saved!")
