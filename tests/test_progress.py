import io
import threading
import unittest
from progress import Progress


class Terminal(io.StringIO):
    def __init__(self):
        super().__init__()
        self.animated = threading.Event()
        self.writes = 0

    def isatty(self):
        return True

    def write(self, text):
        result = super().write(text)
        self.writes += 1
        if self.writes > 1:
            self.animated.set()
        return result


class ProgressTest(unittest.TestCase):
    def test_animates_while_work_is_blocked_and_finishes(self):
        stream = Terminal()
        with Progress('Export', total=2, stream=stream, interval=0.01) as progress:
            self.assertTrue(stream.animated.wait(1))
            progress.advance()
            progress.advance()
        self.assertFalse(progress._thread.is_alive())
        self.assertIn('2/2 (100%)', stream.getvalue())
        self.assertIn('Fertig', stream.getvalue())

    def test_interrupt_stops_thread_and_propagates(self):
        stream = Terminal()
        with self.assertRaises(KeyboardInterrupt):
            with Progress('Export', stream=stream) as progress:
                raise KeyboardInterrupt()
        self.assertFalse(progress._thread.is_alive())
        self.assertIn('Abgebrochen', stream.getvalue())

    def test_redirected_output_has_no_control_codes(self):
        stream = io.StringIO()
        with Progress('Export', total=0, stream=stream):
            pass
        self.assertNotIn('\033', stream.getvalue())
        self.assertIn('Fertig', stream.getvalue())
