import tqdm
from typing import Union, Dict, Any
import navigator
import window
import time
from PIL import Image

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

	def __init__(self, v: Vector, c: SingleChar, value: int, multiplier: float = 1.0):
		self.v = v
		self.c = c
		self.value = value
		self.multiplier = multiplier
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

	def __init__(self):
		self.vectors = {}
		self.length = 0

	def reset(self):
		self.length = 0
		self.vectors = {}

	def next(self, char: SpellCastChar):
		self.length += 1
		self.vectors[self.length] = char

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

	def get_current(self) -> SpellCastChar:
		return self.vectors[self.length]

	def get(self):
		sorted_v = sorted(self.vectors.items())

		result = {}

		for offset, char in sorted_v:
			result[offset] = char

		return result

	def get_raw(self) -> dict[int, SpellCastChar]:
		return self.vectors

	def get_text(self):
		return "".join(map(lambda c: c.c.char, self.get().values()))

	def get_total_value(self):
		return sum(list(map(lambda c: c.get_value(), self.get().values())))

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

	def get(self, v: Vector, c: SingleChar):
		if not c.char in LETTERS:
			raise Exception(f"char \"{c.char}\" not used in spellcast")

		return SpellCastChar(v, c, self.values[c.char])

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

def readable_image(img: Image):
	return img.convert('1', dither=Image.NONE)

if __name__ == '__main__':
	char_factory = SpellCastCharFactory()

	auto_navigate = False

	words = []
	spellcast = SpellCastMap(5)

	size_wizard = window.WindowSizeWizard()

	if auto_navigate:
		size_wizard.run()

	nav = navigator.Navigator(size_wizard)

	for y in range(5):
		for x in range(5):
			data = input(" ")
			spellcast.set(char_factory.get(Vector(x, y), SingleChar(data)))
		print("\n")

	words = list(set(words))

	with open("./words.txt", "r", encoding="utf-8") as f:
		lines = f.read()
		for word in lines.split("\n"):
			if len(word) <= 1:
				continue
			words.append(word)

	result = []
	for word in tqdm.tqdm(words, position=1):

		for v, c in spellcast.vector_map().items():
			if c.c.char == word[0]:
				wizard = FindWordWizard(c, word, spellcast)
				wizard.run()
				if wizard.success:
					result.append(wizard.selection)

	for result_word in sorted(result, key=lambda x: x.get_total_value(), reverse=True):
		print(result_word.get_text() + " " + result_word.get_text_vectors())

		if auto_navigate:
			nav.navigate(result_word)
			time.sleep(5)