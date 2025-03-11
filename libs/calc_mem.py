'''
Calculations for Shin'en GAX Sound Engine playback on the GBA
'''

#GBA related constants
refresh_rate = 59.7275

#GAX related constants
replayer_header_size   = 0x98
header_fxch_size       = 0x48
replayer_buffer_footer = 0x24c

replayer_mus_ch_header = 0x78
channel_struct_size    = 0x48

## functions

def get_ram_buffer_size(mixing_rate=15769):
	return(mixing_rate//(refresh_rate/2)) #this is an estimate

def get_ram_usage(mixing_rate=15769, mus_channels=6, fx_channels=2):
	ram_size = replayer_header_size + (header_fxch_size*fx_channels) + 8
	ram_size += get_ram_buffer_size(mixing_rate) + replayer_buffer_footer
	ram_size += replayer_mus_ch_header + (channel_struct_size*mus_channels)
	return int(ram_size)

