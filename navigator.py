import pyautogui
import window
import main
import time

class Navigator:

	size: window.WindowSizeWizard

	def __init__(self, size: window.WindowSizeWizard):
		self.left_top = size.positions[0]
		self.size = size
		self.gap = 12 # hard coded

		self.button_size = 48 # hard coded

	def get_pos(self, x_num: int, y_num: int):
		x_diff = x_num * (self.button_size + self.gap) + (self.button_size / 2)
		y_diff = y_num * (self.button_size + self.gap) + (self.button_size / 2)
		return main.Vector(self.left_top.x + x_diff, self.left_top.y + y_diff)

	def get_region(self, x_num: int, y_num: int):
		x_diff = x_num * (self.button_size + self.gap)
		y_diff = y_num * (self.button_size + self.gap)
		return [
			self.left_top.x + x_diff,
			self.left_top.y + y_diff,
			self.button_size,
			self.button_size
		]

	def navigate(self, selection: main.Selection, nv_sleep: float = 0.0):
		down = False
		for length, c in selection.get_raw().items():
			window_v = self.get_pos(c.v.x, c.v.y)

			pyautogui.moveTo(window_v.x, window_v.y)
			if not down:
				pyautogui.mouseDown()

			time.sleep(nv_sleep)

		pyautogui.mouseUp()
