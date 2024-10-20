import shinen_gax as gax
import math
import struct

from general import get_period, get_freq
from gax_constants import sine_table
from gax_constructors import wave_param


'''
To do:

> mixing volume (85% accurate)
> touch up tone portamento (95% accurate)
> sustain point (95% accurate)

> vibrato support (33.3% accurate)
	> depth (figure out proper scaling)
	> speed / wait (accurate)

> wavetable modulation synthesis (not done)
	> unless i figure out how this works, this is not implemented
	> (use cases: Shin'en Multimedia intro jingle ~ Iridion II)
'''

class channel:
	
	def __init__(self):

		self.timer = 0

		#note delay
		self.tick_delay = 0

		#note pitch (from step data)
		self.semitone = 0 # the semitone straight from the GAX song data
		#note pitch (from perf list data)
		self.perf_semitone = 0
		self.old_perf_semitone = 0 #to allow for phase reset
		self.perf_pitch = 0

		self.is_fixed = False

		self.note_slide_amount = 0
		self.perf_note_slide_amount = 0

		self.old_semitone = 0 #to allow for pitch slides
		self.target_semitone = 0 
		self.is_tone_porta = False
		self.tone_porta_lerp = 0
		self.tone_porta_strength = 0

		self.vol_slide_amount = 0
		self.perf_vol_slide_amount = 0

		#instrument indexing
		self.instrument_idx = 0 #index into the instrument bank

		#performance list controls
		self.perf_row_idx = 0
		self.perf_row_buffer = None
		self.perf_row_delay = 0
		self.perf_row_speed = 0
		self.perf_row_volume = 255
		self.perf_row_timer = 0

		#sample waveform controls
		self.wave_data = b''
		self.wave_params = None
		self.wave_step_rate = 0
		self.wave_idx = 0
		self.wave_pitch = 0
		self.wave_position = 0
		self.wave_direction = 1
		self.wave_output = 0


		## vibrato controls
		self.use_vibrato = False  #to use vibrato at all
		self.is_vibrato = False   #True if we are now processing the vibrato
		self.vibrato_timer = 0    #timer for the vibrato + wait
		self.vibrato_subtimer = 0 #timer for the vibrato itself

		self.vibrato_init = 0     #ticks to wait before applying
		self.vibrato_depth = 0
		self.vibrato_speed = 0

		self.vibrato_pitch = 0    #detune pitch to apply to the main pitch
		self.vibrato_step_rate = 0 


		#envelope controls
		self.instrument_data = None
		self.volenv_timer = 0 
		self.volenv_buffer = None
		self.volenv_idx = 0
		self.volenv_cur_vol = 0
		self.volenv_lerp = 0

		self.volenv_pause = False #so the sustain point works properly
		self.volenv_pause_point = None
		self.volenv_note_off = False

		self.volenv_loop = False
		self.volenv_has_looped = False

		self.volenv_end = False

		#volume controls
		self.step_volume = 255
		self.mix_volume = 1 #use for fades

		#is the channel active or not
		self.is_active = False #set to false if an envelope finishes

		self.output_buffer = list()


	def tick_volenv(self):

		if len(self.volenv_buffer) > 1: #only read in volenv if there is any data

			self.volenv_loop = (self.instrument_data.volume_envelope["loop_start"] != None
								and self.instrument_data.volume_envelope["loop_end"] != None)
								#detect when it's appropriate to loop our volume envelope

			if self.timer == self.volenv_buffer[self.volenv_idx][0]:
				self.volenv_has_looped = False
					  
				#if our timer matches the current envelope point's time (X),
				#we increment the volenv_idx variable by 1 and set the appropriate volume
				self.volenv_cur_vol = self.volenv_buffer[self.volenv_idx][1]

				if not self.volenv_pause:
					self.volenv_idx += 1
				
				if not self.volenv_loop: 
					if self.volenv_idx >= len(self.instrument_data.volume_envelope["points"]):
						self.volenv_idx = 0
						self.volenv_lerp = 0
						self.volenv_end = True
						self.is_active = False
						
				#envelope loop controls (unconfirmed behavior)
				if self.volenv_loop: 
					if self.volenv_idx > self.instrument_data.volume_envelope["loop_end"]:
						#to do: Iridion II - Instrument #40's volume envelope is slightly faster than actual hardware
						self.volenv_idx = self.instrument_data.volume_envelope["loop_start"]
						self.timer = self.volenv_buffer[self.volenv_idx][0] #extremely shit solution but it works
						self.volenv_has_looped = True

		else:
			#no volume envelope here
			self.volenv_cur_vol = self.volenv_buffer[self.volenv_idx][1]
			self.volenv_lerp = 0


		#envelope lerping

		if len(self.volenv_buffer) > 1:

			if not self.volenv_end:

				#prevent the sample from getting louder and scaring the elderly
				if not self.volenv_pause:
					if self.volenv_buffer[self.volenv_idx][0] != (self.volenv_pause_point):
						try:
							volenv_a = self.volenv_buffer[self.volenv_idx]
							volenv_b = self.volenv_buffer[self.volenv_idx-1]
							self.volenv_lerp = ((volenv_b[1]-volenv_a[1])/(volenv_b[0]-volenv_a[0]))
						except:
							self.volenv_lerp = 0


			#sustain point handler

			if self.volenv_buffer[self.volenv_idx][0] == (self.volenv_pause_point): #when we reach the sustain point
				self.volenv_pause = True
				self.volenv_lerp = 0

			#sustain / pause handling

			if not self.volenv_pause:
				self.volenv_timer += 1

			if self.volenv_pause_point != None: #if there even exists a sustain point:
				if self.volenv_note_off == True:
					#reset to where we were before the sustain pause
					self.volenv_pause = False
					self.volenv_idx = self.instrument_data.volume_envelope["sustain_point"]
					self.timer = self.volenv_pause_point
					self.volenv_pause_point = None
					self.volenv_note_off = False


	def tick_audio(self, mix_rate, wave_bank, stream, fps=60, gain=3, debug=False):

		#replace these functions with the ones in general

		'''
		current bugs:
		> envelope pause timing / note off timing is inconsistent during speed modulation (cases - Jazz Jackrabbit, SpongeBob: Lights Camera Pants)
		> envelope looping is slightly faster (case - Iridion II ~ intro BGM)
		> vibrato depth calculation is incorrect
		> we don't need to reset the perf volume, yet we do anyways (cases - Camp Lazlo)
		'''

		self.output_buffer = list()

		if self.use_vibrato:
			if self.is_vibrato:
				self.vibrato_step_rate = (self.vibrato_pitch/mix_rate*fps)
				if debug:
					print((self.vibrato_depth))

		if self.wave_params != None:

			#apply finetune to both step rates for obvious reasons

			if not self.is_fixed:
				self.wave_step_rate = (get_freq(get_period(
									   (self.perf_semitone + (self.wave_params["finetune"]/32)) 
									   + self.semitone)) / mix_rate) + self.vibrato_step_rate
			else:
				self.wave_step_rate = (get_freq(get_period(
									   self.perf_semitone + (self.wave_params["finetune"]/32)
									   )))/mix_rate + self.vibrato_step_rate


			play_once = (self.wave_params["loop_start"] == 0 and self.wave_params["loop_end"] == 0)

			for i in range(int(mix_rate/fps)):

				if self.wave_idx >= len(wave_bank): #accurate GAX behavior
					break

				self.wave_position += (self.wave_step_rate)*self.wave_direction
				# read through the waveform data
						
				if len(wave_bank[self.wave_idx]) > 0:

					if not play_once:
						#looping handlers
						if (self.wave_position >= len(wave_bank[self.wave_idx])
							or self.wave_position >= self.wave_params["loop_end"]):
							if self.wave_params["ping_pong"]:
								#bidi loop
								self.wave_direction = -1
							else:
								#forward loop
								self.wave_position = self.wave_params["loop_start"]

						if (self.wave_position <= 0 or self.wave_position <= self.wave_params["loop_start"]):
							if self.wave_params["ping_pong"]:
								#return from backwards reading
								self.wave_direction = 1
				else:
					#don't attempt to read from an empty sample
					self.wave_position = 0

				#clamping
				if self.wave_position >= len(wave_bank[self.wave_idx]):
					self.wave_position = len(wave_bank[self.wave_idx]) - 1
				elif self.wave_position < 0:
					self.wave_position = 0
				
				#failsafe checking if all else fails
				if (self.wave_position >= len(wave_bank[self.wave_idx]) 
					or self.wave_position < 0):
					self.wave_position = 0

				self.tick_volenv()

				self.semitone += self.note_slide_amount/(mix_rate*(fps/1.875)/fps)   #cross checked with custom porta down tracks / Sigma Star Saga
				self.semitone += self.tone_porta_lerp/(mix_rate/(fps*(fps/11.1)))    #cross checked with custom tone portamento tracks
				self.step_volume += self.vol_slide_amount/(mix_rate*(fps/1.875)/fps) #unconfirmed

				if self.is_tone_porta:
					if int(self.semitone) == self.target_semitone:
						#now works in both directions!
						self.tone_porta_lerp = 0
						self.is_tone_porta = False
						self.semitone = self.target_semitone


				#output the current instrument's work
				if self.wave_idx != 0: #do not attempt to read sample #0 -> reserved empty sample
					self.wave_output = wave_bank[self.wave_idx][int(self.wave_position)] - 128

				#apply volume transformations
				
				self.wave_output *= self.perf_row_volume/255
				self.wave_output *= self.step_volume/255
				self.wave_output *= self.volenv_cur_vol/255

				self.step_volume += self.vol_slide_amount/255

				#clamp step volume so we don't blow out everything
				if self.step_volume > 255:
					self.step_volume = 255
				elif self.step_volume < 0:
					self.step_volume = 0
					self.vol_slide_amount = 0
				'''
				Apply gain here. 
				This is slightly inaccurate for now
				'''
				self.wave_output *= (gain)*self.mix_volume

				#clamp wave output so we don't blow out everything.. again
				if self.wave_output > 127:
					self.wave_output = 127
				elif self.wave_output < -128:
					self.wave_output = -128

				#convert to a signed PCM stream
				self.output_buffer.append(self.wave_output)

		#vibrato handlers

		if self.vibrato_timer == self.vibrato_init:
			self.is_vibrato = True

		if self.use_vibrato:
			self.vibrato_timer += 1

			if self.is_vibrato:
				self.vibrato_subtimer += 1*self.vibrato_speed
				try:
					# the magic number only works for instrument #128 in the spongebob movie
					# pls figure this out
					self.vibrato_pitch = (sine_table[self.vibrato_subtimer%64]) * self.vibrato_depth/200
				except:
					self.vibrato_pitch = 0


	def tick_perf_list(self, wave_bank):

		def tick_self():

			#note
			cur_perf_row = self.perf_row_buffer[self.perf_row_idx]
			self.old_perf_semitone = self.perf_semitone # our previous semitone from the last tick/step
			if cur_perf_row["note"] not in [0, None]:
				self.perf_semitone = cur_perf_row["note"] - 4 #apply note correction
				self.perf_pitch = self.perf_semitone * 32 # set that as our perf pitch
				
			#fixed
			if cur_perf_row["fixed"]:
				self.perf_semitone = cur_perf_row["note"] - 2
				self.perf_pitch = self.perf_semitone * 32
				self.is_fixed = True

			#wave slot idx
			if cur_perf_row["wave_slot_id"] > 0:
				#if the wave slot isn't empty
				self.wave_idx = self.instrument_data.header["wave_slots"][
					cur_perf_row["wave_slot_id"] - 1]

				try:
					self.wave_params = self.instrument_data.wave_params[cur_perf_row["wave_slot_id"] - 1]	
				except:
					raise Exception('cannot index nonexistent wave param!')

				if len(self.perf_row_buffer) > 1: #prevent buzzing in melodic instruments
					if math.ceil(self.old_perf_semitone) != self.perf_semitone:
						#only reset the wave position if the semitone changes
						self.wave_position = self.wave_params["start_position"]
						#the old perf semitone has to be rounded down so
						#some instruments won't buzz uncontrollably


			#clamping and looping
			if self.perf_row_volume > 255:
				self.perf_row_volume = 255
			elif self.perf_row_volume > 0:
				self.perf_row_volume = 0
			
			self.perf_row_idx += 1
			if self.perf_row_idx >= len(self.perf_row_buffer):
				#the perf list actually doesn't loop on its own; you have to make it loop manually
				self.perf_row_idx -= 1

			#effect

			self.perf_row_volume = 255

			for column in cur_perf_row["effect"]:

				fx_column = list(reversed(column)) #we can't index a tuple so this is what we gotta do

				if fx_column[0] == gax.perf_row_effect.pitch_slide_up:
					self.perf_note_slide_amount = fx_column[1]

				if fx_column[0] == gax.perf_row_effect.pitch_slide_down:
					self.perf_note_slide_amount = -fx_column[1]

				if fx_column[0] == gax.perf_row_effect.jump_to_row:
					self.perf_row_idx = fx_column[1]

				#<untested>

				if fx_column[0] == gax.perf_row_effect.jump_delay:
					if self.perf_row_delay == 0:
						self.perf_row_idx = fx_column[1]
					else:
						self.perf_row_delay -= 1

				#</untested>

				if fx_column[0] == gax.perf_row_effect.volume_slide_up:
					self.perf_vol_slide_amount = fx_column[1]

				if fx_column[0] == gax.perf_row_effect.volume_slide_down:
					self.perf_vol_slide_amount = -fx_column[1]	

				if fx_column[0] == gax.perf_row_effect.set_volume:
					self.perf_row_volume = fx_column[1]

				if fx_column[0] == gax.perf_row_effect.set_speed:
					self.perf_row_speed = fx_column[1]


		#slide functions
		self.perf_pitch += self.perf_note_slide_amount # the pitch of the note (affected by perf list porta effects)
		self.perf_semitone = self.perf_pitch / 32 # the "normalized" semitone
		self.perf_row_volume += self.perf_vol_slide_amount

		if self.perf_row_speed == 0: # this way prevents a division by zero.
			self.perf_row_idx = 0    # fake a speed of 0 by setting the perf row ID to 0 constantly
			tick_self()

		if self.perf_row_speed != 0:
			if self.perf_row_timer % self.perf_row_speed == 0:
				tick_self()


		if len(self.perf_row_buffer) > 1:
			self.perf_row_timer += 1


	def tick(self, wave_bank, stream, mixing_rate = 15769, fps=60, gain=3):

		if self.instrument_data != None:

			if self.timer == 0 and self.volenv_has_looped == False:
				#start from defined wave position
				try:
					self.wave_position = self.instrument_data.wave_params[
						self.perf_row_buffer[self.perf_row_idx]["wave_slot_id"] - 1
					]["start_position"]
				except:
					print('> could not get start position from nonexistant wave param!')
					self.wave_position = 0 #correct if possible

			self.tick_perf_list(wave_bank)

			self.tick_audio(mixing_rate, wave_bank, stream, fps=fps, gain=gain)
		else:
			#render silence
			self.output_buffer = [0]*int(mixing_rate/math.ceil(fps))
		
		self.timer += 1 #increment the timer at the end so there exists a timer value of 0
		self.volenv_cur_vol += self.volenv_lerp

		#todo: clamp the envelope value into bounds
		

	def init_instr(self, instrument_set, instr_idx=1, semitone=0x31):

		if instr_idx < len(instrument_set):

			self.volenv_timer = 0
			self.is_tone_porta = False
			self.volenv_note_off = False
			
			if instr_idx not in [0, None]:
				self.volenv_pause = False
				self.timer = 0 #reset timer
				self.instrument_data = instrument_set[instr_idx] #get the required data
				self.is_active = True #activate the instrument

			self.old_semitone = self.semitone
			self.semitone = semitone

			if instr_idx not in [0, None]:

				self.use_vibrato = False 
				self.vibrato_step_rate = 0 #do not carry the vibrato from
										   #one instrument to one that doesn't have vibrato	
				self.note_slide_amount = 0

				self.instrument_idx = instr_idx
				self.wave_direction = 1 # samples start playing forwards

				self.perf_note_slide_amount = 0 #reset the slide amount
				
				self.perf_semitone = 0
				self.perf_row_idx = 0
				self.perf_row_speed = self.instrument_data.perf_list["perf_row_speed"]
				self.perf_row_buffer = self.instrument_data.perf_list["perf_list_data"]
				self.perf_row_volume = 255
				self.perf_row_timer = 0

				self.is_fixed = False

				self.volenv_buffer = list(list(i) for i in self.instrument_data.volume_envelope["points"])
				self.volenv_idx = 0
				self.volenv_lerp = 0
				self.volenv_loop = False
				self.volenv_end = False

				try:
					self.volenv_pause_point = self.volenv_buffer[self.instrument_data.volume_envelope["sustain_point"]][0]
				except:
					self.volenv_pause_point = None


				#further initialization steps

				if self.instrument_data.volume_envelope["sustain_point"] == 0: #this feels kind of hacky :/
					self.volenv_pause = True #if the sustain point is directly at the start (i.e Finding Nemo, SpongeBob)

				vibrato_params = self.instrument_data.header['vibrato_params']

				if (vibrato_params['vibrato_wait'] == 0 and vibrato_params['vibrato_depth'] == 0 and vibrato_params['vibrato_speed'] == 0):
					self.use_vibrato = False
					self.is_vibrato = False
					self.vibrato_init = 0
					self.vibrato_depth = 0
					self.vibrato_speed = 0
				else:
					self.use_vibrato = True
					self.vibrato_init = vibrato_params['vibrato_wait']
					self.vibrato_depth = vibrato_params['vibrato_depth']
					self.vibrato_speed = vibrato_params['vibrato_speed']

					if vibrato_params['vibrato_wait'] == 0:
						self.is_vibrato = True


				#load the necessary wave params
				self.wave_params = self.instrument_data.wave_params[
								   self.perf_row_buffer[self.perf_row_idx]["wave_slot_id"] - 1]


def get_patterns_at_idx(song_data, idx):
	return(list(i[idx] for i in song_data.get_order_list()))


class replayer():

	'''
	to do:
	> mixing volume is inaccurate in very rare cases (i.e sampled intros)
	'''

	def __init__(self, gax_obj, song_idx = 0, allocate_fxch = False, fx_obj = None):

		self.gax_data = gax_obj
		self.song_data = self.gax_data.get_song_data(song_idx)

		if allocate_fxch == True:
			if fx_obj == None:
				raise Exception("You had allocated the FX channels, but you forgot to reference the FX object")
			self.fx_data = fx_obj

		self.timer = 0

		self.speed = [6,6]
		self.speed_timer = self.speed[0]

		self.cur_step = 0
		self.cur_pat = 0
		self.loop_count = 0 #For audio export
		self.skip = False #True if a pattern break is read

		self.cur_pat_data = get_patterns_at_idx(self.song_data, self.cur_pat) #get the first patterns

		self.step_count = self.song_data.get_properties().step_count
		self.pattern_count = self.song_data.get_properties().song_length
		self.restart_pos = self.song_data.get_properties().restart_position

		self.num_channels = self.song_data.get_properties().channel_count

		if allocate_fxch:
			self.num_fx_channels = self.song_data.get_properties().fx_channel_count
		else:
			self.num_fx_channels = None

		self.mix_amp = self.song_data.get_properties().song_volume

		self.cur_step_data = [0] * self.num_channels

		if allocate_fxch == False:
			self.channels = [channel() for n in range(self.num_channels)]
		else:
			self.channels = [channel() for n in range(self.num_channels+self.num_fx_channels)]

		self.output_buffer = ''


	def read_step_at_ch(self, channel):

		step_data = self.cur_step_data[channel]

		self.channels[channel].note_slide_amount = 0 #don't apply pitch slides if there are none
		self.channels[channel].vol_slide_amount = 0 #same for volume slides

		#do this only if the step data is *not* an empty step

		if step_data != 0:

			if step_data.semitone not in [None, gax.step_type(0x1)]:
				self.channels[channel].target_semitone = step_data.semitone+self.cur_pat_data[channel][1]
				self.channels[channel].init_instr(self.gax_data.instrument_set, 
												 instr_idx=step_data.instrument, 
												 semitone=step_data.semitone+self.cur_pat_data[channel][1])

				#if a set volume command is not present:

				#only reset the volume if there isn't a tone portamento
				#fixes Iridion II ~ 16: tenshi plains

				if step_data.instrument != 0:
					self.channels[channel].step_volume = 255

					#also turn off the tone portamento
					#fixes the SpongeBob SquarePants theme

					self.channels[channel].is_tone_porta = False
					self.channels[channel].tone_porta_lerp = 0


			if step_data.semitone == gax.step_type(0x1):
				self.channels[channel].volenv_note_off = True


			if step_data.effect_param == None:
				step_effect_param = 0
			else:
				step_effect_param = step_data.effect_param

			if step_data.effect_type != None:

				if type(step_data.effect_type) != int:

					match step_data.effect_type.value: #preferrable to writing
						                               #step_data.effect_type.value over and over
						case 0x1: #pitch slide up
							self.channels[channel].note_slide_amount = step_effect_param

						case 0x2: #pitch slide down
							self.channels[channel].note_slide_amount = -step_effect_param


						case 0x3: #tone portamento

							self.channels[channel].tone_porta_strength = step_effect_param
							#right now this behaves similar to XM's tone portamento, which is not how GAX does it
							#the number of ticks should remain the same length, even during one-note sweeps
							try:
								lerp = self.channels[channel].semitone - self.channels[channel].old_semitone
								self.channels[channel].tone_porta_lerp = (lerp / (step_effect_param*self.speed[0]))
							except:
								self.channels[channel].tone_porta_lerp = 0

							self.channels[channel].is_tone_porta = True
							self.channels[channel].semitone = self.channels[channel].old_semitone


						case 0x7: #speed modulation
							self.speed = [step_effect_param & 0xf,
										  step_effect_param >> 4]

						case 0xA: #volume slide up
							self.channels[channel].vol_slide_amount = step_effect_param
						case 0xB: #volume slide down
							self.channels[channel].vol_slide_amount = -step_effect_param

						case 0xC: #set volume
							self.channels[channel].step_volume = step_effect_param

						case 0xD: #break pattern
							self.skip = True
							#the param is ignored here

						case 0xE:
							if step_effect_param >> 4 == 0xD:
								print('>> unimplemented command! |', step_data.effect_type)

						case 0xF: #set speed
							self.speed = [step_effect_param]*2


	def tick(self, buffer, debug=False, export=False):

		self.timer += 1

		if self.speed_timer <= 0 and self.speed[0] != 0: #read the pattern data

			for i in range(0, self.num_channels):
				note_real = self.song_data.get_patterns()[self.cur_pat_data[i][0]][self.cur_step]
				self.cur_step_data[i] = note_real
				self.read_step_at_ch(i)

			self.cur_step += 1
			self.speed = self.speed[::-1] #allow for speed modulation
			self.speed_timer = self.speed[0]

		self.speed_timer -= 1

		if self.cur_step >= self.step_count or self.skip:
			self.cur_step = 0
			self.cur_pat += 1
			self.skip = False

			if self.cur_pat >= self.pattern_count:
				self.cur_pat = self.restart_pos
				self.loop_count += 1

			#update the current patterns to match
			self.cur_pat_data = get_patterns_at_idx(self.song_data, self.cur_pat)
		
		if self.num_fx_channels != None:
			num_ch = self.num_channels+self.num_fx_channels
		else:
			num_ch = self.num_channels

		mix_buffer = list(i//num_ch for i in self.channels[0].output_buffer)

		for i in range(1, num_ch):

			#go through each channel that had been processed
			#and "mix" them together

			j = 0

			#to do: optimize this somehow
			for float_value in self.channels[i].output_buffer:
				try:
					mix_buffer[j] += float_value // self.num_channels

					if mix_buffer[j] > 127: #cap the mixing buffer to
						mix_buffer[j] = 127 #valid int8 range
					elif mix_buffer[j] < -128:
						mix_buffer[j] = -128

					j += 1
				except:
					pass


		mix_buffer = list(round(i) for i in mix_buffer)
		self.output_buffer = list(x for x in mix_buffer)
		mix_buffer = bytes((x & 0xff for x in mix_buffer))

		if not export:
			buffer.write(mix_buffer)
		if debug:
			return mix_buffer

	def tick_channels(self, buffer, mixing_rate):

		for i in range(self.num_channels):
			self.channels[i].tick(self.gax_data.wave_bank, buffer, mixing_rate, gain=(self.mix_amp/100))		
		
		mix_buffer = list(i//self.num_channels for i in self.channels[0].output_buffer)

		for i in range(1, self.num_channels):

			#go through each channel that had been processed
			#and "mix" them together

			j = 0

			#to do: optimize this somehow
			for float_value in self.channels[i].output_buffer:
				try:
					mix_buffer[j] += float_value // self.num_channels

					if mix_buffer[j] > 127: #cap the mixing buffer to
						mix_buffer[j] = 127 #valid int8 range
					elif mix_buffer[j] < -128:
						mix_buffer[j] = -128

					j += 1
				except:
					pass


		mix_buffer = list(round(i) for i in mix_buffer)
		mix_buffer = bytes((x & 0xff for x in mix_buffer))

		buffer.write(mix_buffer)


	def play_sound(self, fxch=0, fx_idx=1):

		if self.num_channels+self.num_fx_channels > len(self.channels):
			raise Exception("Can't play SFX when there are no FX channels")

		if self.num_channels+fxch >= len(self.channels):
			raise Exception("Can't play SFX in an unallocated FX channel")

		self.channels[self.num_channels+fxch].init_instr(self.fx_data.instrument_set, fx_idx)

	def stop_sound(self, fxch=0):

		if self.num_channels+self.num_fx_channels > len(self.channels):
			raise Exception("Can't stop SFX when there are no FX channels")

		if self.num_channels+fxch >= len(self.channels):
			raise Exception("Can't stop SFX in a nonexistent FX channel")

		self.channels[self.num_channels+fxch] = channel()