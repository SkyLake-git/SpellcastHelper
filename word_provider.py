
import os
from urllib import request

import git
import tqdm

providers = {
	"jacksonrayhamilton": (
		"unavailable",
		"https://github.com/jacksonrayhamilton/wordlist-english.git"
	),
	"dwyl": (
		"raw",
		"https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt"
	)
}

def download(provider_name: str, stream_chunk_size: int = 8 * 1024):
	if not provider_name in providers:
		raise Exception(f"provider name \"{provider_name}\" not found")

	provider = providers[provider_name]

	download_type = provider[0]
	url = provider[1]

	output = ""

	if download_type == "raw":
		output = get_file(provider_name)
		url_data = request.urlopen(url)

		with tqdm.tqdm() as tq:
			with open(output, mode = "wb") as f:
				while True:
					chunk_data = url_data.read(stream_chunk_size)

					if not chunk_data:
						break

					f.write(chunk_data)

					tq.update(len(chunk_data))
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