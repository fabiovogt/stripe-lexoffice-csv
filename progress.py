"""Terminal progress that stays active during blocking API requests."""
import itertools
import sys
import threading


class Progress:
    def __init__(self, label, total=None, stream=None, interval=0.1):
        self.label = label
        self.total = total
        self.stream = stream if stream is not None else sys.stderr
        self.interval = interval
        self.completed = 0
        self._stop = threading.Event()
        self._thread = None
        self._interactive = self.stream.isatty()

    def _render(self, frame):
        count = f'{self.completed} Transaktionen'
        if self.total is not None:
            ratio = min(self.completed / self.total, 1) if self.total else 1
            filled = int(20 * ratio)
            count = f'[{"#" * filled}{"-" * (20 - filled)}] {self.completed}/{self.total} ({ratio:.0%})'
        self.stream.write(f'\r\033[K{frame} {self.label}: {count}')
        self.stream.flush()

    def _animate(self):
        for frame in itertools.cycle('|/-\\'):
            if self._stop.wait(self.interval):
                break
            self._render(frame)

    def __enter__(self):
        if self._interactive:
            self._render('|')
            self._thread = threading.Thread(target=self._animate, daemon=True)
            self._thread.start()
        else:
            print(f'{self.label} …', file=self.stream, flush=True)
        return self

    def advance(self):
        self.completed += 1

    def __exit__(self, exc_type, exc_value, traceback):
        self._stop.set()
        if self._thread:
            self._thread.join()
        status = 'Fertig' if exc_type is None else 'Abgebrochen'
        if self._interactive:
            self._render(status)
            self.stream.write('\n')
            self.stream.flush()
        else:
            print(f'{self.label}: {status} ({self.completed} Transaktionen)', file=self.stream, flush=True)
        return False
