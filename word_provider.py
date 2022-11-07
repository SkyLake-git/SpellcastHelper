
import os
import sys
import urllib.error
from urllib import request

import git
import tqdm
import logger
import time
import math
import json

LOGGER = logger.Logger("Word Provider")

providers = {
	"jacksonrayhamilton": (
		"raw",
		(
			"https://raw.githubusercontent.com/jacksonrayhamilton/wordlist-english/master/sources/english-words.70",
			"https://raw.githubusercontent.com/jacksonrayhamilton/wordlist-english/master/sources/english-words.60",
			"https://raw.githubusercontent.com/jacksonrayhamilton/wordlist-english/master/sources/english-words.50",
			"https://raw.githubusercontent.com/jacksonrayhamilton/wordlist-english/master/sources/english-words.40",
			"https://raw.githubusercontent.com/jacksonrayhamilton/wordlist-english/master/sources/english-words.30",
			"https://raw.githubusercontent.com/jacksonrayhamilton/wordlist-english/master/sources/english-words.20",
			"https://raw.githubusercontent.com/jacksonrayhamilton/wordlist-english/master/sources/english-words.10",
			"https://raw.githubusercontent.com/jacksonrayhamilton/wordlist-english/master/sources/canadian-words.70",
			"https://raw.githubusercontent.com/jacksonrayhamilton/wordlist-english/master/sources/canadian-words.60",
			"https://raw.githubusercontent.com/jacksonrayhamilton/wordlist-english/master/sources/canadian-words.50",
			"https://raw.githubusercontent.com/jacksonrayhamilton/wordlist-english/master/sources/canadian-words.40",
			"https://raw.githubusercontent.com/jacksonrayhamilton/wordlist-english/master/sources/canadian-words.30",
			"https://raw.githubusercontent.com/jacksonrayhamilton/wordlist-english/master/sources/canadian-words.20",
			"https://raw.githubusercontent.com/jacksonrayhamilton/wordlist-english/master/sources/canadian-words.10",
			"https://raw.githubusercontent.com/jacksonrayhamilton/wordlist-english/master/sources/british-words.70",
			"https://raw.githubusercontent.com/jacksonrayhamilton/wordlist-english/master/sources/british-words.60",
			"https://raw.githubusercontent.com/jacksonrayhamilton/wordlist-english/master/sources/british-words.50",
			"https://raw.githubusercontent.com/jacksonrayhamilton/wordlist-english/master/sources/british-words.40",
			"https://raw.githubusercontent.com/jacksonrayhamilton/wordlist-english/master/sources/british-words.30",
			"https://raw.githubusercontent.com/jacksonrayhamilton/wordlist-english/master/sources/british-words.20",
			"https://raw.githubusercontent.com/jacksonrayhamilton/wordlist-english/master/sources/british-words.10",
			"https://raw.githubusercontent.com/jacksonrayhamilton/wordlist-english/master/sources/australian-words.70",
			"https://raw.githubusercontent.com/jacksonrayhamilton/wordlist-english/master/sources/australian-words.60",
			"https://raw.githubusercontent.com/jacksonrayhamilton/wordlist-english/master/sources/australian-words.50",
			"https://raw.githubusercontent.com/jacksonrayhamilton/wordlist-english/master/sources/australian-words.40",
			"https://raw.githubusercontent.com/jacksonrayhamilton/wordlist-english/master/sources/australian-words.30",
			"https://raw.githubusercontent.com/jacksonrayhamilton/wordlist-english/master/sources/australian-words.20",
			"https://raw.githubusercontent.com/jacksonrayhamilton/wordlist-english/master/sources/australian-words.10",
			"https://raw.githubusercontent.com/jacksonrayhamilton/wordlist-english/master/sources/american-words.70",
			"https://raw.githubusercontent.com/jacksonrayhamilton/wordlist-english/master/sources/american-words.60",
			"https://raw.githubusercontent.com/jacksonrayhamilton/wordlist-english/master/sources/american-words.55",
			"https://raw.githubusercontent.com/jacksonrayhamilton/wordlist-english/master/sources/american-words.50",
			"https://raw.githubusercontent.com/jacksonrayhamilton/wordlist-english/master/sources/american-words.40",
			"https://raw.githubusercontent.com/jacksonrayhamilton/wordlist-english/master/sources/american-words.35",
			"https://raw.githubusercontent.com/jacksonrayhamilton/wordlist-english/master/sources/american-words.20",
			"https://raw.githubusercontent.com/jacksonrayhamilton/wordlist-english/master/sources/american-words.10"

		)
	),
	"dwyl": (
		"raw",
		(
			"https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt",
		)
	),
	"sindresorhus": (
		"raw",
		(
			"https://raw.githubusercontent.com/sindresorhus/word-list/main/words.txt",
		)
	)
}

def download_all(stream_chunk_size: int = 12 * 1024):
	for provider_name in providers.keys():
		LOGGER.info(f"Downloading dictionary: \"{provider_name}\"")
		download(provider_name, stream_chunk_size=stream_chunk_size)

def download(provider_name: str, stream_chunk_size: int = 12 * 1024):
	if not provider_name in providers:
		raise Exception(f"provider name \"{provider_name}\" not found")

	provider = providers[provider_name]

	download_type = provider[0]
	urls = provider[1]

	output = ""

	if download_type.startswith("raw"):
		output = get_file(provider_name)
		download_type_split = download_type.split()
		is_json = False
		if len(download_type_split) > 1:
			is_json = download_type_split[1] == "json"

		files = []
		last_second = math.floor(time.time())
		last_display = 0
		total_bytes = 0
		bytes = 0
		kbps = 0
		current_uv = 0

		times = 0
		ascii_art_uv = [
			'\\',
			'/',
			"-"
		]

		for url in urls:

			st_url = time.time()

			base_url = os.path.basename(url)
			seq_output = get_file("_" + base_url)
			try:
				url_data = request.urlopen(url)
			except urllib.error.HTTPError:
				continue

			end_url = time.time()

			diff = end_url - st_url
			last_display -= diff
			last_second -= int(diff)


			with open(seq_output, mode = "wb") as f:
				while True:
					chunk_data = url_data.read(stream_chunk_size)
					if not chunk_data:
						break
					f.write(chunk_data)

					cur_time = time.time()
					second = math.floor(time.time())
					bytes += len(chunk_data)
					total_bytes += len(chunk_data)
					times += 1

					if second != last_second:
						kbps = bytes / 1024
						bytes = 0

					if cur_time - last_display >= 0.1:
						current_uv += 1
						if len(ascii_art_uv) <= current_uv:
							current_uv = 0
						uv = ascii_art_uv[current_uv]
						sys.stdout.write(f"\r>> {uv} | {round(total_bytes / 1024, 2)}kb ({round(kbps, 1)} kb/s)        ")

						last_display = cur_time
				files.append(seq_output)
		sys.stdout.write(f"\r>> @ | {round(total_bytes / 1024, 2)}kb | Success!\n         ")

		with open(output, "w", encoding="utf-8") as host_f:
			for file in files:
				with open(file, "rb") as read_f:
					host_f.write(read_f.read().decode("utf-8", errors="ignore"))
				os.unlink(file)

		if is_json:
			with open(output, "r", encoding="utf-8") as f:
				js = json.load(f)
			text = ""
			for word_json in js:
				for word in word_json.values():
					text += f"{word}\n"

			with open(output, "w", encoding="utf-8") as f:
				f.write(text)






	elif download_type == "unavailable":
		print()

def get_file(provider_name: str):
	return "./words/" + provider_name + ".txt"

def is_downloaded(provider_name: str) -> bool:
	file = get_file(provider_name)
	return os.path.exists(file) and os.path.isfile(file)

def get_providing(provider_name: str, auto_download: bool = True):
	file = get_file(provider_name)
	if not (os.path.exists(file) and os.path.isfile(file)):
		if auto_download:
			download(provider_name)
		else:
			raise Exception(f"word list \"{provider_name}\" not found")

	with open(get_file(provider_name), "r", encoding="utf-8") as f:
		result = f.read()

	return result


def get_default_provider():
	with open("./word_provider.txt", "r", encoding="utf-8") as f:
		word_provider = f.read()

	if len(word_provider) <= 0 or len(word_provider.split("\n")) > 1:
		raise Exception("invalid content for default provider config: \"word_provider.txt\"")

	return word_provider