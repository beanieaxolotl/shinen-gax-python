def get_bool_from_num(num_val):
	if num_val >= 2:
		raise Exception("Incorrect value!")
	return (num_val == 1)

def is_dword_aligned(num):
	return num % 4 == 0

def get_normalized_bit(value, bit_id):
	return (value >> bit_id) & 1
	#https://realpython.com/python-bitwise-operators/


def get_period(note):
	return 7680 - note * 64

def get_freq(period):
	return 8363 * pow(2, (4608 - period) / 768)
	
def sign_flip(sample):
	return bytes((i+128)%256 for i in sample)