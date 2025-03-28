import enum


class perf_row_effect(enum.Enum):

	no_effect         = 0x0
	pitch_slide_up    = 0x1
	pitch_slide_down  = 0x2
	invalid_0x3       = 0x3
	invalid_0x4       = 0x4	
	jump_to_row       = 0x5
	jump_delay        = 0x6
	invalid_0x7       = 0x7
	invalid_0x8       = 0x8
	invalid_0x9       = 0x9	
	volume_slide_up   = 0xa
	volume_slide_down = 0xb
	set_volume        = 0xc
	invalid_0xd       = 0xd
	invalid_0xe       = 0xe	
	set_speed         = 0xf

class step_effect(enum.Enum):

	no_effect         = 0x0
	pitch_slide_up    = 0x1
	pitch_slide_down  = 0x2
	tone_portamento   = 0x3
	invalid_0x4       = 0x4
	invalid_0x5       = 0x5
	invalid_0x6       = 0x6
	modulate_speed    = 0x7
	invalid_0x8       = 0x8
	invalid_0x9       = 0x9
	volume_slide_up   = 0xa
	volume_slide_down = 0xb
	set_volume        = 0xc
	pattern_break     = 0xd
	step_delay        = 0xe
	set_speed         = 0xf