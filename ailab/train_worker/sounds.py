"""Âm thanh của một lớp: nối các mẩu WAV (16-bit PCM) thành một WAV để micro giả của trang Teachable Machine phát (từ learning/train-worker)."""

import wave
from pathlib import Path


class TooFewImages(Exception):
    """Không có âm thanh nào dùng được."""


def join(paths, dest):
    first = None
    frames = []
    for p in paths:
        with wave.open(str(p)) as w:
            fmt = (w.getnchannels(), w.getsampwidth(), w.getframerate())
            if first is None:
                first = fmt
            if fmt == first:
                frames.append(w.readframes(w.getnframes()))
    if first is None:
        raise TooFewImages("no sound to play")
    with wave.open(str(dest), "wb") as out:
        out.setnchannels(first[0])
        out.setsampwidth(first[1])
        out.setframerate(first[2])
        out.writeframes(b"".join(frames))
    return Path(dest)
