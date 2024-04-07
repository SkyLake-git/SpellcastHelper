import typing
import crayons
import pymorton

LETTERS = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j', 'k', 'l', 'm', 'n', 'o', 'p', 'q', 'r', 's', 't', 'u', 'v',
		   'w', 'x', 'y', 'z']


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

	def equals(self, v):
		return v.x == self.x and v.y == self.y

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


T1 = typing.TypeVar("T1")


class VectorMap(typing.Generic[T1]):
	map: dict[int, dict[int, T1]]

	def __init__(self):
		self.map = {}

	def add(self, v: Vector, value: T1):
		if not v.x in self.map:
			self.map[v.x] = {}

		self.map[v.x][v.y] = value

	def get_at(self, vx: int, vy: int) -> T1:
		if vx in self.map:
			if vy in self.map[vx]:
				return self.map[vx][vy]

		return None

	def clear(self, vx: int, vy: int):
		if vx in self.map:
			if vy in self.map[vx]:
				self.map[vx].pop(vy)

	def get(self, v: Vector) -> T1:
		return self.get_at(v.x, v.y)


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
	swapped: bool

	def __init__(self, v: Vector, c: SingleChar, value: int, multiplier: float = 1.0, mark_double: bool = False):
		self.v = v
		self.c = c
		self.value = value
		self.multiplier = multiplier
		self.mark_double = mark_double
		self.swapped = False
		self.swapped_from = None
		if not (c.char in LETTERS):
			raise Exception(f"char \"{c.char}\" not used in spellcast")

	def get_value(self):
		return self.value * self.multiplier


class Selection:
	word: dict[int, SpellCastChar]
	elimination: dict[int, list[int]]

	length: int

	dirty: bool

	vectors: VectorMap[SpellCastChar]

	def __init__(self):
		self.word = {}
		self.elimination = {}
		self.length = 0
		self.dirty = False
		self.vectors = VectorMap()

	def reset(self):
		self.length = 0
		self.word = {}
		self.vectors = VectorMap()
		self.dirty = True

	def next(self, char: SpellCastChar):
		self.length += 1
		self.word[self.length] = char
		self.vectors.add(char.v, char)
		self.dirty = True

	def eliminate(self, l: int, v: Vector):
		self.elimination.setdefault(l, [])
		self.elimination.get(l).append(pymorton.interleave2(v.x, v.y))

	def is_eliminated(self, v: Vector, l: typing.Union[int, None] = None):
		if l is None:
			l = self.length

		self.elimination.setdefault(l, [])

		return pymorton.interleave2(v.x, v.y) in self.elimination.get(l)

	def has(self, c: SingleChar):
		for char in self.word.values():
			if char.c.char == c.char:
				return True
		return False

	def has_exact(self, tchar: SpellCastChar):
		return self.vectors.get(tchar.v) is not None

	def previous(self):
		if self.length < 1:
			raise Exception("length < 1")

		if self.length in self.elimination:
			del self.elimination[self.length]

		char = self.word.get(self.length)
		self.word.pop(self.length)
		self.vectors.clear(char.v.x, char.v.y)
		self.length -= 1
		self.dirty = True

	def get_current(self) -> SpellCastChar:
		return self.word[self.length]

	def get(self):
		if self.dirty:
			sorted_v = sorted(self.word.items())

			self.word = {}

			for offset, char in sorted_v:
				self.word[offset] = char

			self.dirty = False

			return self.word
		else:
			return self.word

	def get_dirty(self) -> dict[int, SpellCastChar]:
		return self.word

	def get_text(self):
		txt = ""
		for c in self.get().values():
			c_c = c.c.char
			if c.swapped:
				txt += crayons.red(c_c, bold=True)
			elif c.mark_double:
				txt += crayons.magenta(c_c)
			elif c.multiplier > 1.0:
				txt += crayons.yellow(c_c)
			else:
				txt += crayons.cyan(c_c)
		return txt

	def get_raw_text(self):
		return "".join(map(lambda c: c.c.char, self.get().values()))

	def get_total_value(self):
		value = sum(list(map(lambda c: c.get_value(), self.get().values())))

		if self.has_double_points():
			value *= 2

		if len(self.word) >= 6:
			value += 10

		return value

	def has_double_points(self):
		for c in self.get().values():
			if c.mark_double:
				return True
		return False

	def get_swapped(self) -> list[SpellCastChar]:
		results = []
		for c in self.get().values():
			if c.swapped:
				results.append(c)

		return results

	def get_text_vectors(self):
		return "".join(map(lambda c: f"({c.v.x}, {c.v.y})", self.get().values()))


class SpellCastMap:
	map: dict[int, dict[int, SpellCastChar]]
	size: int
	neighbours_cache: VectorMap[SpellCastChar]
	map_by_char: dict[str, list[int]]

	def __init__(self, size: int):
		self.map = {}
		self.size = size
		self.neighbours_cache = VectorMap()
		self.map_by_char = {}

	def generate_map_by_char(self):
		for v, c in self.vector_map().items():
			self.map_by_char.setdefault(c.c.char, [])
			self.map_by_char.get(c.c.char).append(pymorton.interleave2(v.x, v.y))

	def find(self, char: str):
		pos_list = self.map_by_char.get(char)

		if pos_list is not None:
			results = []
			for pos in pos_list:
				v = pymorton.deinterleave2(pos)
				results.append(self.map[v[0]][v[1]])
			return results
		else:
			return None

	def get_neighbours(self, v: Vector):
		if self.neighbours_cache.get(v) is not None:
			return self.neighbours_cache.get(v)

		neighbours = get_chars(v.neighbour(), self)
		self.neighbours_cache.add(v, neighbours)

		return neighbours

	def vector_map(self) -> dict[Vector, SpellCastChar]:
		result = {}
		for x, content in self.map.items():
			for y, char in content.items():
				result[Vector(x, y)] = char

		return result

	def set(self, char: SpellCastChar) -> None:
		if not char.v.x in self.map:
			self.map[char.v.x] = {}
		self.map[char.v.x][char.v.y] = char
		self.neighbours_cache = VectorMap()

	def get(self, v: Vector) -> typing.Union[SpellCastChar, None]:
		if v.x in self.map:
			if v.y in self.map[v.x]:
				return self.map[v.x][v.y]

		return None

	def visualize_selection(self, sel: Selection):
		tree = Selection()

		from_to_set = []
		for offset, char in sel.get().items():
			if tree.length > 1:
				from_char = tree.previous()
			else:
				from_char = None

			tree.next(char)

			if from_char is not None:
				from_to_set.append((from_char, char))

	def get_at(self, x: int, y: int) -> typing.Union[SpellCastChar, None]:
		return self.get(Vector(x, y))

	def row(self, row_x: int) -> list[Vector]:
		result = []

		for v in self.vector_map():
			if v.x == row_x:
				result.append(v)

		if len(result) > self.size:
			raise Exception("result length must be same or lower as size")

		return result

	def column(self, column_y: int) -> list[Vector]:
		result = []

		for v in self.vector_map():
			if v.y == column_y:
				result.append(v)

		if len(result) > self.size:
			raise Exception("result length must be same or lower as size")

		return result


def get_chars(vectors: list, spellcast_map_v: SpellCastMap) -> dict[Vector, SpellCastChar]:
	chars = {}
	for v in vectors:
		char = spellcast_map_v.get(v)
		if char is not None:
			chars[v] = char

	return chars
