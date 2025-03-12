from .shinen_gax   import *
from .gax_replayer import channel, replayer
from .calc_mem     import get_ram_usage
import pyaudio

#mimicks the GAX Sound Engine's playback functions as close as possible


class gax_replayer:

	def __init__(self, gax_mus_object, gax_fx_object = None, 
		song_index = 0, mixrate_override = 0, fps = 60):

		self.p = pyaudio.PyAudio()

		self.module_data = gax_mus_object

		if gax_fx_object is not None:
			self.vars = replayer(self.module_data, song_idx=song_index, 
			allocate_fxch=True, fx_obj=gax_fx_object) #default: grab song #0
		else:
			self.vars = replayer(self.module_data, song_idx=song_index) #default: grab song #0
		
		if mixrate_override > 0:
			self.mixing_rate = mixrate_override
		else:
			self.mixing_rate = self.vars.song_data.get_properties().mixing_rate

		self.fxch_count = self.vars.song_data.get_properties().fx_channel_count

		self.fps  = fps
		self.gain = 1

		self.maj_version = 3
		self.min_version = 5

		self.stream = self.p.open(format=pyaudio.paInt8,
				channels=1,
				rate=self.mixing_rate,
		output=True)	


	## useful functions

	def get_current_pattern(self):
		return self.vars.cur_pat

	def get_current_step(self):
		return self.vars.cur_step


	# API reimplementations

	## GAX2_new

	def GAX2_calc_mem(self):
		return get_ram_usage(mixing_rate  = self.mixing_rate, 
			mus_channels = self.vars.num_channels, 
			fx_channels  = self.fxch_count)

	## GAX2_init
	## GAX2_jingle
	## GAX_irq

	def GAX_play(self, debug = False):

		for ch in range(self.vars.num_channels):
			self.vars.channels[ch].tick(0,self.vars,
				self.module_data.instrument_set, 
				self.module_data.wave_set.wave_bank, 
				self.stream, self.mixing_rate, self.fps,
				gain=self.gain,
				major_version=self.maj_version,
				minor_version=self.min_version)
		try:
			if not debug:
				self.vars.tick(self.stream)
			else:
				return self.vars.tick(self.stream, debug=debug)
		except OSError as e:
			raise Exception('Audio output error')

	## GAX_stop
	## GAX2_new_fx
	## GAX2_fx

	def GAX_fx_note(self, fxch, note=0):
		self.vars.channels[self.vars.num_channels+fxch].semitone = note/32

	def GAX_fx_ex(self, fxid, fxch, prio=0, note=0):
		self.vars.play_sound(fxch=fxch, fx_idx=fxid)
		self.GAX_fx_note(fxch, note)	

	def GAX_fx_status(self, fxch):
		return self.vars.channels[self.vars.num_channels+fxch].instrument_idx

	def GAX_stop_fx(self, fxch):
		if fxch != -1:
			self.vars.stop_sound(fxch)
		else:
			for i in range(self.vars.num_fx_channels):
				self.vars.stop_sound(i)

	## GAX_backup_fx
	## GAX_restore_fx

	def GAX_set_music_volume(self, ch=-1, vol=256):

		corrected_vol = vol/256
		if corrected_vol > 1.0:
			corrected_vol = 1

		if ch != -1:
			self.vars.channels[ch].mix_volume = corrected_vol
		else:
			for i in range(self.vars.num_channels):
				self.vars.channels[i].mix_volume = corrected_vol

	def GAX_set_fx_volume(self, fxch, vol):

		corrected_vol = vol/256
		if corrected_vol > 1.0:
			corrected_vol = 1

		if fxch != -1:
			self.vars.channels[self.vars.num_channels+fxch].mix_volume = corrected_vol
		else:
			for i in range(self.vars.num_fx_channels):
				self.vars.channels[self.vars.num_channels+i].mix_volume = corrected_vol

	## GAX_pause
	## GAX_pause_music
	## GAX_resume
	## GAX_resume_music

