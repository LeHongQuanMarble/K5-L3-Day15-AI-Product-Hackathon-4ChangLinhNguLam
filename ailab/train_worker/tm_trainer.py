"""Trainer on a headless Chromium: a fresh browser per attempt, one retry, and one shared budget for the whole job."""

import logging
import os
import shutil
import signal
import tempfile
import threading
import time
import uuid
from pathlib import Path

# The full Chromium build (not the headless shell: its WebGL is refused by TF.js) with software WebGL; it also needs a writable HOME (the Dockerfile sets one).
CHROMIUM_ARGS = ["--disable-dev-shm-usage", "--ignore-gpu-blocklist", "--enable-unsafe-swiftshader", "--disable-quic"]  # QUIC off: the audio page failed to load over it

from playwright.sync_api import sync_playwright

from . import sounds
from .tm_page import MIC_INIT_JS, NOISE_CLASS, train_and_publish, train_audio_and_publish
from .trainer import AUDIO_BUDGET_S, JOB_BUDGET_S, MAX_PROJECT_BYTES, TrainerError

log = logging.getLogger("train.browser")

TRAIN_URL = "https://teachablemachine.withgoogle.com/train/image"
# One train page per project kind; the page for a kind answers to the same steps.
TRAIN_URLS = {"image": TRAIN_URL, "pose": "https://teachablemachine.withgoogle.com/train/pose",
              "audio": "https://teachablemachine.withgoogle.com/train/audio"}
ATTEMPTS = 2


def chrome_path():
    """Trình duyệt đầy đủ trên máy (đặt AILAB_CHROME để chỉ rõ); không tải Chromium riêng cho Playwright."""
    for cand in (os.environ.get("AILAB_CHROME"), shutil.which("google-chrome"), shutil.which("chromium"), shutil.which("chromium-browser")):
        if cand:
            return cand
    raise TrainerError("trainer_unavailable")


def _kill_marked(marker: str) -> None:
    """SIGKILL every process whose command line carries this attempt's marker (its own Chromium; another job's browser is untouched)."""
    for pid in filter(str.isdigit, os.listdir("/proc")):
        try:
            with open(f"/proc/{pid}/cmdline", "rb") as f:
                if marker.encode() in f.read():
                    os.kill(int(pid), signal.SIGKILL)
        except OSError:
            pass


class TmBrowserTrainer:
    def __init__(self, url: str | None = None, budget_s: float = JOB_BUDGET_S, attempts: int = ATTEMPTS):
        self.url, self.budget_s, self.attempts = url, budget_s, attempts  # url set: every kind goes there (tests)

    def train(self, name, classes, *, settings=None, project_in=None, project_out=None, kind="image"):
        deadline = time.monotonic() + (max(self.budget_s, AUDIO_BUDGET_S) if kind == "audio" else self.budget_s)
        for attempt in range(1, self.attempts + 1):
            if time.monotonic() >= deadline:
                break
            try:
                url = self._attempt(name, classes, deadline, settings, project_in, project_out, kind)
                if project_out is not None and project_out.stat().st_size > MAX_PROJECT_BYTES:
                    raise TrainerError("trainer_failed")  # too big to keep: the job fails, the model is not published either
                return url
            except Exception as e:  # a page change, a timeout, a crash: try once more, then the job fails
                # the type or the code only: Playwright messages quote page text (a teacher's class names)
                log.warning("attempt %d failed: %s", attempt, getattr(e, "code", type(e).__name__))
        raise TrainerError("trainer_failed")

    def _attempt(self, name, classes, deadline, settings, project_in, project_out, kind):
        # A page whose main thread freezes blocks any call that has no timeout (evaluate, count): at the deadline a watchdog
        # kills this attempt's browser from outside, which makes every blocked Playwright call raise.
        marker = f"--july-train-job={uuid.uuid4().hex}"
        watchdog = threading.Timer(max(0.0, deadline - time.monotonic()), _kill_marked, args=(marker,))
        watchdog.daemon = True
        watchdog.start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True, executable_path=chrome_path(), args=[*CHROMIUM_ARGS, marker])
                try:
                    context = browser.new_context(viewport={"width": 1500, "height": 1400})
                    if kind == "audio":
                        context.add_init_script(MIC_INIT_JS)
                    page = context.new_page()
                    page.set_default_timeout(max(1, int((deadline - time.monotonic()) * 1000)))
                    page.goto(self.url or TRAIN_URLS[kind], wait_until="domcontentloaded", timeout=max(1, int((deadline - time.monotonic()) * 1000)))
                    if kind == "audio":  # one WAV per class to play; Background Noise is the page's first class
                        scratch = Path(tempfile.mkdtemp(prefix="sounds-"))
                        try:
                            ordered = {NOISE_CLASS: sounds.join(classes[NOISE_CLASS], scratch / "noise.wav")}
                            for i, (label, files) in enumerate(c for c in classes.items() if c[0] != NOISE_CLASS):
                                ordered[label] = sounds.join(files, scratch / f"{i}.wav")
                            return train_audio_and_publish(page, name, ordered, deadline)
                        finally:
                            shutil.rmtree(scratch, ignore_errors=True)
                    return train_and_publish(page, name, classes, deadline, settings=settings, project_in=project_in,
                                             project_out=project_out, kind=kind)
                finally:
                    try:
                        browser.close()
                    except Exception:  # noqa: BLE001 - the watchdog may have killed it already
                        pass
        finally:
            watchdog.cancel()
            _kill_marked(marker)  # nothing of this attempt outlives it
