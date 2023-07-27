import contextlib
import time


class TimeCostHolder:
	cost: float = float()

	def __repr__(self):
		return repr(self.cost)

	def str(self):
		return str(self.cost)

	def __round__(self, *args, **kwargs):
		return self.cost.__round__(*args, **kwargs)


@contextlib.contextmanager
def time_cost():
	holder = TimeCostHolder()
	start = time.time()
	yield holder
	holder.cost = time.time() - start
