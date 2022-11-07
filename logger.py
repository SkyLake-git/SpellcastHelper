import crayons
import datetime

def datetime_format(format: str):
	now = datetime.datetime.now()
	return now.strftime(format)

class Logger:

	name: str

	def __init__(self, name: str):
		self.name = name

	def info(self, message: str):
		self.log(f"/ {self.name}: INFO >> " + crayons.black(message, bold=True))

	def warning(self, message: str):
		self.log(crayons.yellow(f"/ {self.name}: WARNING >> ") + crayons.black(message, bold=True))

	def log(self, message: str):
		print(crayons.cyan(datetime_format('[%Y/%m/%d %H:%M:%S]'), bold=True) + " " + message, flush=True)