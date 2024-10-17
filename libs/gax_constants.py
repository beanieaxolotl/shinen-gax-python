mixing_rates = [5735, 9079, 10513, 11469, 13380, 15769, 18158, 21025, 26760, 31537, 36316, 40138, 42049]
note_names = ['C-', 'C#', 'D-', 'D#', 'E-', 'F-', 'F#', 'G-', 'G#', 'A-', 'A#', 'B-']

max_channels = 32
min_channels = 0
max_fx_channels = 8 #confirmed by GAX replayer ROMs in the WayForward lot

sine_table = [ #Ripped from GAX Sound Engine 3.05 (Aug 13 2003)
	   0,   12,   24,   37, 
	  48,   60,   70,   80, 
	  90,   98,  106,  112,
	 117,  122,  125,  126,
	 127,  126,  125,  122,
	 117,  112,  106,   98,
	  90,   80,   70,   60,
	  48,   37,   24,   12,
	   0,  -12,  -24,  -37, 
	 -48,  -60,  -70,  -80, 
	 -90,  -98, -106, -112,
	-117, -122, -125, -126,
	-127, -126, -125, -122,
	-117, -112, -106,  -98,
	 -90,  -80,  -70,  -60,
	 -48,  -37,  -24,  -12
	] 

libgax_consts = {
	"gax.o":         b'\xf0\xb5\x07\x1c\xcd\x1b\x1f\x4e\x34\x68\x23\x1c\x80\x33\x1a\x68',
	"output.o":      b'\xf0\xb5\x88\xb0\x06\x1c\x00\x27\x79\x48\x01\x68\x08\x1c\x5e\x30',
	"output_asm.o":  b'\xf0\x1f\x2d\xe9\x0f\x00\xb0\xe8\x03\x32\xa0\xe1\x01\x20\x82\xe0',
	"speech.o":      b'\xf0\xb5\x57\x46\x4e\x46\x45\x46\xe0\xb4\x04\x1c\xf3\x20\xc0\x00',
	"sync.o":        b'\x00\x22\x82\x60\x42\x60\x82\x74\xc2\x74\x02\x76\x42\x76\x07\x49',
	"tracker.o":     b'\x10\xb5\x00\x22\x82\x63\x02\x71\xc2\x62\x00\x23\x11\x49\xc1\x81',
	"tracker_asm.o": b'\x18\x00\x2d\xe9\x90\x31\x84\xe0\x04\x00\xa0\xe1\x18\x00\xbd\xe8'
}