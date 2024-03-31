import os.path
import typing

import pymorton
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
from spellcast import *


class CharStream:
	text: str

	def __init__(self, text: str):
		self.text = text
		self.offset = 0

	def is_eof(self):
		return (self.offset + 1) == len(self.text)

	def is_reached_eof(self):
		return self.offset >= len(self.text)

	def is_start(self):
		return self.offset == 0

	def next(self) -> str:
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

	def __init__(self, start: SpellCastChar, target_word: str, spellcast_m: SpellCastMap, swap_available: int):
		self.selection = Selection()
		self.selection.next(start)
		self.start = start
		self.eliminated = []
		self.word = CharStream(target_word)
		self.word.next()
		self.spellcast = spellcast_m
		self.success = False
		self.swap_available = swap_available
		self.last_tried_swap = False

	def __old_is_eliminated(self, v: Vector):
		return pymorton.interleave2(v.x, v.y) in self.eliminated

	def __old_eliminate(self, v: Vector):
		self.eliminated.append(pymorton.interleave2(v.x, v.y))

	def is_eliminated(self, v: Vector):
		return self.selection.is_eliminated(v)

	def eliminate(self, v: Vector):
		self.selection.eliminate(self.selection.length, v)

	def find_neighbours(self, v: Vector, target_char: SingleChar) -> Union[SpellCastChar, None]:
		neighbours = self.spellcast.get_neighbours(v)

		found = False
		for v, c in neighbours.items():
			if target_char.char == c.c.char and (not self.is_eliminated(v)) and (
					not self.selection.has_exact(c)):  # c.c.char www
				found = True

				break
		if found:
			return c
		else:
			return None

	def check_selection(self):
		if self.selection.get_raw_text() == self.word.text:
			self.success = True
		return self.success

	def run(self):
		while True:
			current_char = self.word.current()

			#print(self.selection.get_text() + f", {current_char}" + " / " + self.word.text)

			result = self.find_neighbours(self.selection.get_current().v, current_char)

			found = result is not None

			# 次のchar があったなら
			if found:
				self.selection.next(result)

				# print("Attempting: " + self.selection.get_text() + " / " + self.word.text + f" (current: {
				# current_char}, word_offset: {self.word.offset})")
				if self.check_selection():
					break

				self.word.next()
			if not found:
				# print("not found")
				if self.check_selection():
					break

				if self.word.offset <= 1:
					break

				if len(self.selection.get_swapped()) < self.swap_available and not self.last_tried_swap:
					# まだスワップできて前回スワップ失敗していないなら

					swap_result = Union[SpellCastChar, None]
					scaffold = None
					swap_found = False
					# print("try swap")

					for target_v, c in self.spellcast.get_neighbours(self.selection.get_current().v).items():
						if (not self.is_eliminated(target_v)) and (not self.selection.has_exact(c)):
							swap_result = c
							scaffold = target_v
							break
					swap_found = swap_result is not None

					if swap_found and scaffold is not None:

						char_swap_from = self.spellcast.get(scaffold)

						char = SpellCastChar(scaffold, current_char, 0, char_swap_from.multiplier,
											 char_swap_from.mark_double)
						char.swapped = True
						char.swapped_from = char_swap_from

						# self.spellcast.set(char)

						self.selection.next(char)
						if not self.word.is_eof():
							self.word.next()

						if self.check_selection():
							break
					else:
						self.last_tried_swap = True
					continue

				# これ以上見つからなかったら現在のマスを排除されたとしてマークして、前のマスに戻る

				before = self.selection.get_current()
				self.word.previous()
				if self.selection.length > 1:
					self.selection.previous()

				self.eliminate(before.v)

			self.last_tried_swap = False
# print("break")


def find_selection(spellcast_m: SpellCastMap, word_map: list, swap_available_m: int) -> list[FindWordWizard]:
	results = []
	for word_m in word_map:
		starts = spellcast_m.find(word_m[0])
		if starts is None:
			continue
		for c in starts:
			wizard = FindWordWizard(c, word_m, spellcast_m, swap_available_m)
			wizard.run()
			results.append(wizard)

	return results


if __name__ == '__main__':
	main_logger = logger.Logger("Main")
	char_factory = SpellCastCharFactory()

	if not os.path.exists("./words"):
		os.makedirs("./words", exist_ok=True)
		main_logger.info(crayons.yellow("words folder not found. Downloading all word dictionaries...", bold=True))
		time.sleep(3)
		word_provider.download_all()

	threaded = False
	future_executor = futures.ProcessPoolExecutor()

	auto_navigate = False

	swap_available = 1

	if len(sys.argv) > 1:
		auto_navigate = sys.argv[1] == "true"

	if len(sys.argv) > 2:
		swap_available = int(sys.argv[2])

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
			main_logger.info("Run window size wizard for navigating.")
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

	spellcast.generate_map_by_char()
	words = list(set(words))

	main_logger.info("Loading words...")
	for word in tqdm.tqdm(words_raw.split("\n"), colour="cyan"):
		if len(word) <= 3:
			continue
		if len(word) > pow(spellcast.size, 2):
			continue
		if (not word.isascii()) or (not word.isalpha()):
			continue
		words.append(word)

	print()  # for fix tqdm bug

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
			if cur > 13000:
				future = future_executor.submit(find_selection, spellcast, cur_words, swap_available)
				futures.append(
					future
				)
				cur = 0
				cur_words = []
	else:
		for word in tqdm.tqdm(words, position=0, ncols=70, mininterval=0.03):
			wizards = find_selection(spellcast, [word], swap_available)
			for wizard in wizards:
				if wizard.success:
					selection = wizard.selection
					result.append(selection)
			# sys.stdout.write("\r")
			# text = selection.get_text()
			# main_logger.info(crayons.green(f"Word found! {text}                         "))

	if threaded:
		for future in tqdm.tqdm(futures, position=0, ncols=70, mininterval=0.03):
			wizards = future.result()
			for wizard in wizards:
				if wizard.success:
					selection = wizard.selection
					result.append(selection)
			# sys.stdout.write("\r")
			# text = selection.get_text()
			# main_logger.info(crayons.green(f"Word found! {text}                         "))

	end = time.time()
	elapsed = end - start
	main_logger.info(f"Takes {round(elapsed, 3)}s")
	print("\n")

	main_logger.info(f"Found {len(result)} words.")

	count = 0

	for result_word in sorted(result, key=lambda x: x.get_total_value(), reverse=True):
		count += 1
		print(
			result_word.get_text() + f": {crayons.magenta(result_word.get_total_value(), bold=True)} " + result_word.get_text_vectors())

		swapped = result_word.get_swapped()

		# print("Swapped Chars: " + ", ".join(map(lambda c: f"{c.swapped_from.c.char} -> {c.c.char}", swapped)))

		if auto_navigate:
			nav.navigate(result_word)
			time.sleep(3)

		if count > 100:
			break
