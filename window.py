import pyautogui
from pynput import mouse
import time
import sys

class AbsolutePosition():

	def __init__(self, x: float, y: float):
		self.x = x
		self.y = y

	def tuple(self):
		return self.x, self.y

	def __str__(self):
		return f"{self.x} {self.y}"




class WindowSizeWizard:

	def __init__(self):
		self.step = 0
		self.names = {
			0: "左上",
			1: "左下",
			2: "右上"
		}
		self.positions = {}
		self.size = (0, 0)
		self.center = None
		self.listener = None
		self.aw_pos = None

	def run(self):
		while self.do_step():
			time.sleep(1)

		self.finalize()

	def finalize(self):
		self.size = (
			self.positions[2].x - self.positions[0].x,
			self.positions[0].y - self.positions[1].y
		)

		self.center = AbsolutePosition(
			self.positions[0].x + self.size[0] / 2,
			self.positions[1].y + self.size[1] / 2
		)


	def do_step(self) -> bool:
		print(f"{self.names[self.step]} の場所をクリックしてください")
		def on_click(x, y, button, pressed):
			self.aw_pos = AbsolutePosition(x, y)
			self.listener.stop()


		with mouse.Listener(
			on_click = on_click
		) as listener:
			self.listener = listener
			self.listener.join()

		self.positions[self.step] = self.aw_pos

		self.step += 1

		print("Ok, クリックをやめてください")

		if self.step > max(self.names.keys()):
			return False

		return True
