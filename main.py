import tqdm
from typing import Union, Dict, Any
import navigator
import window
import time
from PIL import Image
import logger
import sys
import crayons
import word_provider
from concurrent import futures

LETTERS = ['a','b','c','d','e','f','g','h','i','j','k','l','m','n','o','p','q','r','s','t','u','v','w','x','y', 'z']

class Vector:

	x: int
	y: int

	def __init__(self, x: int, y: int):
		self.x = x
		self.y = y

	def add(self, x: int, y: int):
		return Vector(self.x + x, self.y + y)

	def add_vector(self, v):
		return Vector(self.x + v.x, self.y + v.y)

	def sides(self) -> list:
		result = [
			self.add(1, 0),
			self.add(-1, 0),
			self.add(0, 1),
			self.add(0, -1)
		]

		return result

	def neighbour(self) -> list:
		result = self.sides()

		neighbours = [
			self.add(1, 1),
			self.add(-1, -1),
			self.add(1, -1),
			self.add(-1, 1),
		]

		for side in neighbours:
			result.append(side)

		return result

class SingleChar:

	char: str

	def __init__(self, char: str):
		if len(char) != 1:
			raise Exception("char must be length 1")

		self.char = char

	def __str__(self):
		return self.char

class SpellCastChar:

	v: Vector
	c: SingleChar
	value: int
	multiplier: float
	mark_double: bool

	def __init__(self, v: Vector, c: SingleChar, value: int, multiplier: float = 1.0, mark_double: bool = False):
		self.v = v
		self.c = c
		self.value = value
		self.multiplier = multiplier
		self.mark_double = mark_double
		if not (c.char in LETTERS):
			raise Exception(f"char \"{c.char}\" not used in spellcast")

	def get_value(self):
		return self.value * self.multiplier

class SpellCastMap:

	map: dict[int, dict[int, SpellCastChar]]
	size: int

	def __init__(self, size: int):
		self.map = {}
		self.size = size


	def vector_map(self) -> dict[Vector, SpellCastChar]:
		result = {}
		for x, content in self.map.items():
			for y, char in content.items():
				result[Vector(x, y)] = char

		return result

	def set(self, char: SpellCastChar) -> None:
		if not char.v.x in self.map.keys():
			self.map[char.v.x] = {}
		self.map[char.v.x][char.v.y] = char

	def get(self, v: Vector) -> Union[SpellCastChar, None]:
		if v.x in self.map.keys():
			if v.y in self.map[v.x].keys():
				return self.map[v.x][v.y]

		return None

	def get_at(self, x: int, y: int) -> Union[SpellCastChar, None]:
		return self.get(Vector(x, y))

	def row(self, row_x: int) -> list[Vector]:
		result = []

		for v in self.vector_map().keys():
			if v.x == row_x:
				result.append(v)

		if len(result) > self.size:
			raise Exception("result length must be same or lower as size")

		return result

	def column(self, column_y: int) -> list[Vector]:
		result = []

		for v in self.vector_map().keys():
			if v.y == column_y:
				result.append(v)

		if len(result) > self.size:
			raise Exception("result length must be same or lower as size")

		return result

class Selection:

	vectors: dict[int, SpellCastChar]

	length: int

	dirty: bool

	def __init__(self):
		self.vectors = {}
		self.length = 0
		self.dirty = False

	def reset(self):
		self.length = 0
		self.vectors = {}
		self.dirty = True

	def next(self, char: SpellCastChar):
		self.length += 1
		self.vectors[self.length] = char
		self.dirty = True

	def has(self, c: SingleChar):
		for char in self.vectors.values():
			if char.c.char == c.char:
				return True
		return False

	def has_exact(self, tchar: SpellCastChar):
		for char in self.vectors.values():
			if char.c.char == tchar.c.char and char.v.x == tchar.v.x and char.v.y == tchar.v.y:
				return True
		return False

	def previous(self):
		if self.length < 1:
			raise Exception("length < 1")

		self.vectors.pop(self.length)
		self.length -= 1
		self.dirty = True

	def get_current(self) -> SpellCastChar:
		return self.vectors[self.length]

	def get(self):
		if self.dirty:
			sorted_v = sorted(self.vectors.items())

			self.vectors = {}

			for offset, char in sorted_v:
				self.vectors[offset] = char

			self.dirty = False

			return self.vectors
		else:
			return self.vectors

	def get_dirty(self) -> dict[int, SpellCastChar]:
		return self.vectors

	def get_text(self):
		return "".join(map(lambda c: c.c.char, self.get().values()))

	def get_total_value(self):
		value = sum(list(map(lambda c: c.get_value(), self.get().values())))

		if self.has_double_points():
			value *= 2

		return value

	def has_double_points(self):
		for c in self.get().values():
			if c.mark_double:
				return True
		return False


	def get_text_vectors(self):
		return "".join(map(lambda c: f"({c.v.x}, {c.v.y})", self.get().values()))

class CharStream:
	
	text: str

	def __init__(self, text: str):
		self.text = text
		self.offset = 0

	def is_eof(self):
		return (self.offset + 1) == len(self.text)

	def is_start(self):
		return self.offset == 0

	def next(self) -> SingleChar:
		text = self.text[self.offset]
		self.offset += 1

		if len(self.text) <= self.offset:
			raise Exception("no char in buffer")

		return text

	def previous(self):
		self.offset -= 1

		if self.offset < 0:
			raise Exception("offset < 0")

	def current(self) -> SingleChar:
		return SingleChar(self.text[self.offset])

	def __str__(self):
		return self.current()



def get_chars(vectors: list, spellcast_map_v: SpellCastMap) -> dict[Vector, SpellCastChar]:
	chars = {}
	for v in vectors:
		char = spellcast_map_v.get(v)
		if char is not None:
			chars[v] = char

	return chars

class SpellCastCharFactory:

	values: dict[str, int]

	def __init__(self):
		self.values = {
			"a": 1,
			"b": 4,
			"c": 5,
			"d": 3,
			"e": 1,
			"f": 5,
			"g": 3,
			"h": 4,
			"i": 1,
			"j": 7,
			"k": 6,
			"l": 3,
			"m": 4,
			"n": 2,
			"o": 1,
			"p": 4,
			"q": 8,
			"r": 2,
			"s": 2,
			"t": 2,
			"u": 4,
			"v": 5,
			"w": 5,
			"x": 7,
			"y": 4,
			"z": 8
		}

	def get(self, v: Vector, c: SingleChar, multiplier: float = 1.0, mark_double: bool = False):
		if not c.char in LETTERS:
			raise Exception(f"char \"{c.char}\" not used in spellcast")

		return SpellCastChar(v, c, self.values[c.char], multiplier, mark_double)

class FindWordWizard:

	selection: Selection
	eliminated: list
	start: SpellCastChar
	word: CharStream
	spellcast: SpellCastMap
	success: bool


	def __init__(self, start: SpellCastChar, target_word: str, spellcast_m: SpellCastMap):
		self.selection = Selection()
		self.selection.next(start)
		self.start = start
		self.eliminated = []
		self.word = CharStream(target_word)
		self.word.next()
		self.spellcast = spellcast_m
		self.success = False

	def run(self):
		while True:
			neighbours = get_chars(self.selection.get_current().v.neighbour(), self.spellcast)
			current_char = self.word.current().char

			found = False
			for v, c in neighbours.items():
				if current_char == c.c.char and (not (c in self.eliminated)) and (not self.selection.has_exact(c)): # c.c.char www
					found = True

					self.selection.next(c)

					# print("Attempting: " + self.selection.get_text() + " / " + self.word.text + f" (current: {current_char}, word_offset: {self.word.offset})")
					if self.selection.get_text() == self.word.text:
						self.success = True
						break

					self.word.next()

					break

			if self.success:
				break

			if not found:
				if self.word.offset <= 1:
					break

				self.eliminated.append(self.selection.get_current())
				self.word.previous()
				if self.selection.length > 1:
					self.selection.previous()

def find_selection(spellcast_m: SpellCastMap, word_map: list) -> list[FindWordWizard]:
	results = []
	for word_m in word_map:
		for v, c in spellcast_m.vector_map().items():
			if c.c.char == word_m[0]:
				wizard = FindWordWizard(c, word_m, spellcast_m)
				wizard.run()

				results.append(wizard)

	return results

if __name__ == '__main__':
	main_logger = logger.Logger("Main")
	char_factory = SpellCastCharFactory()

	threaded = False
	future_executor = futures.ProcessPoolExecutor()

	auto_navigate = False

	if len(sys.argv) > 1:
		auto_navigate = sys.argv[1] == "true"

	words = []
	spellcast = SpellCastMap(5)

	default_provider = word_provider.get_default_provider()

	if not word_provider.is_downloaded(default_provider):
		main_logger.info(f"Word provider \"{default_provider}\" not downloaded. Downloading...")
		word_provider.download(default_provider)

	main_logger.info(f"Getting word list. provider: \"{default_provider}\"")
	words_raw = word_provider.get_providing(default_provider, False)

	size_wizard = window.WindowSizeWizard()

	if auto_navigate:
		with open("./default_spellcast_window.txt", "r", encoding="utf-8") as f:
			positions = f.read().split("\n")
			if len(positions) == 6:
				size_wizard.positions = {
					0: window.AbsolutePosition(float(positions[0]), float(positions[1])),
					1: window.AbsolutePosition(float(positions[2]), float(positions[3])),
					2: window.AbsolutePosition(float(positions[4]), float(positions[5]))
				}
				size_wizard.finalize()

				main_logger.info("Loaded window size from default.")

		if len(size_wizard.positions) != 3:
			main_logger.info("Run window size words for navigating.")
			size_wizard.run()

		nav = navigator.Navigator(size_wizard)



	main_logger.info("Please input spellcast map")
	main_logger.info("Format: ")
	print(
"""----->
----->
----->
----->
----->""")

	for y in range(5):
		for x in range(5):
			while True:
				data = input(f"({x}, {y}): ")
				sp_data = data.split()

				if len(sp_data) <= 0:
					sys.stdout.write("\rInvalid data. ")
					continue

				main_char = sp_data[0]

				if len(main_char) != 1:
					sys.stdout.write("\rInvalid char. ")
					continue

				multiplier = 1.0
				mark_double = False
				if len(sp_data) > 1:
					multiplier = float(sp_data[1])

				if len(sp_data) > 2:
					mark_double = bool(sp_data[2] == "true")

				break



			spellcast.set(char_factory.get(Vector(x, y), SingleChar(main_char), multiplier, mark_double))

	words = list(set(words))

	main_logger.info("Loading words...")
	for word in tqdm.tqdm(words_raw.split("\n"), colour="cyan"):
		if len(word) <= 1:
			continue
		words.append(word)

	print() # for fix tqdm bug

	main_logger.info("Searching start in 1 seconds...")
	time.sleep(1)

	futures = []
	result = []
	start = time.time()
	cur = 0
	cur_words = []

	if threaded:
		for word in tqdm.tqdm(words, position=0, ncols=70, mininterval=0.03):
			cur += 1
			cur_words.append(word)
			if cur > 10000:
				future = future_executor.submit(find_selection, spellcast, cur_words)
				futures.append(
					future
				)
				cur = 0
				cur_words = []
	else:
		for word in tqdm.tqdm(words, position=0, ncols=70, mininterval=0.03):
			wizards = find_selection(spellcast, [word])
			for wizard in wizards:
				if wizard.success:
					selection = wizard.selection
					result.append(selection)
					sys.stdout.write("\r")
					text = selection.get_text()
					main_logger.info(crayons.green(f"Word found! {text}                         "))

	if threaded:
		for future in tqdm.tqdm(futures, position=0, ncols=70, mininterval=0.03):
			wizards = future.result()
			for wizard in wizards:
				if wizard.success:
					selection = wizard.selection
					result.append(selection)
					sys.stdout.write("\r")
					text = selection.get_text()
					main_logger.info(crayons.green(f"Word found! {text}                         "))

	end = time.time()
	elapsed = end - start
	main_logger.info(f"Takes {round(elapsed, 3)}s")
	print("\n")

	main_logger.info(f"Found {len(result)} words.")

	for result_word in sorted(result, key=lambda x: x.get_total_value(), reverse=True):
		print(result_word.get_text() + " " + result_word.get_text_vectors())

		if auto_navigate:
			nav.navigate(result_word)
			time.sleep(3)