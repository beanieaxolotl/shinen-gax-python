import enum

class step_type(enum.Enum):
	note_off = 0x1

class perf_row_effect(enum.Enum):
	no_effect = 0x0
	pitch_slide_up = 0x1
	pitch_slide_down = 0x2
	jump_to_row = 0x5
	jump_delay = 0x6
	volume_slide_up = 0xa
	volume_slide_down = 0xb
	set_volume = 0xc
	set_speed = 0xf

class step_effect(enum.Enum):
	no_effect = 0x0
	pitch_slide_up = 0x1
	pitch_slide_down = 0x2
	tone_portamento = 0x3
	modulate_speed = 0x7
	volume_slide_up = 0xa
	volume_slide_down = 0xb
	set_volume = 0xc
	pattern_break = 0xd
	step_delay = 0xe
	set_speed = 0xf
