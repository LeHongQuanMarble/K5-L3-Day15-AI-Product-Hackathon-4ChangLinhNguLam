"""The Teachable Machine train page, driven the way a person drives it. The only module that knows that page's structure."""

import logging
import time
from pathlib import Path

from playwright.sync_api import TimeoutError as PlaywrightTimeout

import base64
import re

from .trainer import TrainerError

log = logging.getLogger("train.tm")

# Everything the module reads from the page. Playwright locators pierce open shadow roots.
SELECTORS = {
    # Verified against the live page (spike 2026-11-17). Text selectors pierce open shadow roots.
    "add_class": 'text="Add a class" >> visible=true',
    "class_card": "tm-classifier-drawer",
    "class_label": "tm-editable-label",
    "upload_button": 'button[title="Add sample: upload"]',
    "file_input": "input[type=file][multiple]",
    "train_button": '[aria-label="Train Model"] button',
    "trained_text": "text=Model Trained",
    "export_button": 'text="Export Model" >> visible=true',
    "upload_model_button": 'text="Upload my model" >> visible=true',
    "hosted_url": "#hosted-url-text",
    # The menu (hamburger) and its project items; the project file goes in and out through the hidden zip input.
    "menu_button": '[aria-label="Open navigation"]',
    "download_project": 'text="Download project as file" >> visible=true',
    "open_project_input": "input#zip-file-input",
    # The Advanced row under Training: its toggle, then Epochs, Batch Size and Learning Rate (Reset Defaults is not used).
    "advanced_toggle": "#edit-model-btn",
    "epochs": 'input[type=number][max="9999"]',
    "batch_size": "select#select-input[name=batch-size]",
    "learning_rate": "#learning-rate-input",
}

# Teachable Machine's own defaults: a job that asks for these leaves the Advanced row untouched.
ADVANCED_DEFAULTS = {"epochs": 50, "batch_size": 16, "learning_rate": 0.001}
OPEN_SETTLE_MS = 6000
# A click on empty canvas (the page is always laid out at this viewport) closes the menu.
CANVAS_CLICK = (1000, 1250)

# The onboarding box must stay in the page: removing it makes training throw null.show. Hiding it is enough.
HIDE_ONBOARDING_JS = """() => {
  const hide = (root) => {
    root.querySelectorAll('tm-onboard-box, #onboard-container')
      .forEach((el) => el.style.setProperty('display', 'none', 'important'));
    root.querySelectorAll('*').forEach((el) => { if (el.shadowRoot) hide(el.shadowRoot); });
  };
  hide(document);
}"""


def _left(deadline: float) -> int:
    """Milliseconds left of the job's budget; out of time is a failed job."""
    left = deadline - time.monotonic()
    if left <= 0:
        raise TrainerError("trainer_failed")
    return max(1, int(left * 1000))


def _wait(page, check, deadline: float):
    while not check():
        _left(deadline)  # raises when the budget is spent
        page.wait_for_timeout(200)


def _hide_onboarding(page):
    page.evaluate(HIDE_ONBOARDING_JS)


def _ensure_classes(page, count: int, deadline: float):
    cards = page.locator(SELECTORS["class_card"])
    while cards.count() < count:
        before = cards.count()
        page.locator(SELECTORS["add_class"]).first.click(timeout=_left(deadline))
        _hide_onboarding(page)
        _wait(page, lambda: cards.count() > before, deadline)


def _name_class(page, card, name: str, deadline: float):
    label = card.locator(SELECTORS["class_label"])
    label.click(timeout=_left(deadline))
    page.keyboard.press("Control+A")
    page.keyboard.type(name)
    page.keyboard.press("Enter")
    _wait(page, lambda: card.get_by_text(name, exact=True).count() > 0, deadline)


def _read_hosted_url(page, deadline: float) -> str:
    loc = page.locator(SELECTORS["hosted_url"])
    while True:
        text = (loc.first.text_content(timeout=_left(deadline)) or "").strip() if loc.count() else ""
        if text.startswith("https://") and "[" not in text:
            return text
        _left(deadline)
        page.wait_for_timeout(300)


def _menu(page, deadline: float):
    """Open the menu and click one of its items, then close it: an open menu covers the class buttons."""
    page.locator(SELECTORS["menu_button"]).first.click(timeout=_left(deadline))


def _close_menu(page):
    page.mouse.click(*CANVAS_CLICK)
    page.wait_for_timeout(200)


def _sample_count(card, word: str = "Image") -> int:
    """The class's sample count as the page words it: "12 Image Samples" on an image project, "12 Pose Samples" on a pose one."""
    for text in card.get_by_text(f"{word} Samples").all_inner_texts():
        m = re.match(rf"\s*(\d+) {word} Samples", text)
        if m:
            return int(m.group(1))
    return 0


UPLOAD_ATTEMPTS = 3
UPLOAD_WAIT_S = 15


def _upload(page, card, files, deadline: float, word: str = "Image"):
    """Add the files to the class. A page still starting (a pose page loads its body model first) drops a file set too early and
    shows nothing, so a count that does not move within UPLOAD_WAIT_S is tried again, up to UPLOAD_ATTEMPTS times."""
    _hide_onboarding(page)
    target = _sample_count(card, word) + len(files)
    for attempt in range(UPLOAD_ATTEMPTS):
        if card.locator(SELECTORS["file_input"]).count() == 0:  # the panel stays open after a first try: its button is gone
            card.locator(SELECTORS["upload_button"]).click(timeout=_left(deadline))
        card.locator(SELECTORS["file_input"]).first.set_input_files([str(p) for p in files], timeout=_left(deadline))
        try_until = min(deadline, time.monotonic() + UPLOAD_WAIT_S)
        while _sample_count(card, word) < target:
            if time.monotonic() >= try_until:
                break
            page.wait_for_timeout(200)
        else:
            return
        if attempt < UPLOAD_ATTEMPTS - 1:
            page.wait_for_timeout(2000)
    _wait(page, lambda: _sample_count(card, word) >= target, deadline)


def open_project(page, path: Path, deadline: float, word: str = "Image"):
    """Open a saved project file; wait until its classes show their samples, then close the menu."""
    page.locator(SELECTORS["class_card"]).first.wait_for(state="attached", timeout=_left(deadline))  # the app renders after its HTML
    # The page takes a few seconds more to start: a file set before that is dropped and nothing is restored (spike 2026-11-18).
    page.wait_for_timeout(OPEN_SETTLE_MS)
    _hide_onboarding(page)
    _menu(page, deadline)
    page.locator(SELECTORS["open_project_input"]).set_input_files(str(path), timeout=_left(deadline))
    _close_menu(page)
    cards = page.locator(SELECTORS["class_card"])
    _wait(page, lambda: cards.count() > 0 and all(
        cards.nth(i).get_attribute("label") and _sample_count(cards.nth(i), word) > 0 for i in range(cards.count())), deadline)


def download_project(page, dest: Path, deadline: float):
    """Save the project as a file. The page makes the file itself, so this only saves what it offers."""
    _menu(page, deadline)
    with page.expect_download(timeout=_left(deadline)) as download:
        page.locator(SELECTORS["download_project"]).click(timeout=_left(deadline))
    download.value.save_as(str(dest))
    _close_menu(page)


def _format(value: float) -> str:
    return f"{value:.6f}".rstrip("0").rstrip(".")


def set_advanced(page, settings: dict, deadline: float):
    """Put the Advanced values on the page and read them back. Untouched when every value is the default."""
    wanted = {k: (settings.get(k) if settings.get(k) is not None else ADVANCED_DEFAULTS[k]) for k in ADVANCED_DEFAULTS}
    if wanted == ADVANCED_DEFAULTS:
        return
    _hide_onboarding(page)  # the Train step's bubble reappears once a project is open and covers the Advanced row
    epochs = page.locator(SELECTORS["epochs"]).first
    if not epochs.is_visible():
        page.locator(SELECTORS["advanced_toggle"]).first.click(timeout=_left(deadline))
    epochs.fill(str(wanted["epochs"]), timeout=_left(deadline))
    page.locator(SELECTORS["batch_size"]).first.select_option(str(wanted["batch_size"]), timeout=_left(deadline))
    rate = page.locator(SELECTORS["learning_rate"]).first
    rate.fill(_format(wanted["learning_rate"]), timeout=_left(deadline))
    rate.press("Tab")
    ok = (epochs.input_value() == str(wanted["epochs"])
          and page.locator(SELECTORS["batch_size"]).first.input_value() == str(wanted["batch_size"])
          and abs(float(rate.input_value()) - wanted["learning_rate"]) < 1e-9)
    if not ok:  # the page did not keep what was set: training would use other values
        raise TrainerError("trainer_failed")


# The word each project kind's page puts before "Samples" in a class card.
SAMPLE_WORD = {"image": "Image", "pose": "Pose"}
# A pose page loads its body model after its cards render, and drops any file set before that (spike 2026-11-18); an image page does not.
SETTLE_MS = {"Image": 0, "Pose": 6000}


def train_and_publish(page, name: str, classes: dict[str, list[Path]], deadline: float, *, settings: dict | None = None,
                      project_in: Path | None = None, project_out: Path | None = None, kind: str = "image") -> str:
    """Name each class, add its images, train, publish, and return the model's link. Raises TrainerError("trainer_failed").

    project_in: a saved project to open first (a retrain): the images go to the classes of the same name, and a new name makes a
    new class. project_out: where the project file is saved once trained (before publishing)."""
    try:
        return _train_and_publish(page, name, classes, deadline, settings or {}, project_in, project_out, SAMPLE_WORD[kind])
    except PlaywrightTimeout as e:  # a step the page never reached in time
        raise TrainerError("trainer_failed") from e


def _train_and_publish(page, name, classes, deadline, settings, project_in, project_out, word):
    # The page renders after its HTML loads: hide the onboarding bubble only once it exists, or it later covers the buttons.
    page.locator(SELECTORS["class_card"]).first.wait_for(state="attached", timeout=_left(deadline))
    page.wait_for_timeout(SETTLE_MS[word])
    _hide_onboarding(page)
    if project_in is None:
        _ensure_classes(page, len(classes), deadline)
        for i, (label, files) in enumerate(classes.items()):
            card = page.locator(SELECTORS["class_card"]).nth(i)
            _name_class(page, card, label, deadline)
            _upload(page, card, files, deadline, word)
    else:
        open_project(page, project_in, deadline, word)
        for label, files in classes.items():
            cards = page.locator(SELECTORS["class_card"])
            index = next((i for i in range(cards.count()) if cards.nth(i).get_attribute("label") == label), None)
            if index is None:  # a new class: add it at the end and name it
                before = cards.count()
                page.locator(SELECTORS["add_class"]).first.click(timeout=_left(deadline))
                _hide_onboarding(page)
                _wait(page, lambda: cards.count() > before, deadline)
                index = before
                _name_class(page, cards.nth(index), label, deadline)
            _upload(page, page.locator(SELECTORS["class_card"]).nth(index), files, deadline, word)
    set_advanced(page, settings, deadline)
    _hide_onboarding(page)
    # A real click: the page ignores a script's el.click().
    page.locator(SELECTORS["train_button"]).click(timeout=_left(deadline))
    page.locator(SELECTORS["trained_text"]).wait_for(state="visible", timeout=_left(deadline))
    if project_out is not None:
        download_project(page, project_out, deadline)
    page.locator(SELECTORS["export_button"]).click(timeout=_left(deadline))
    page.locator(SELECTORS["upload_model_button"]).click(timeout=_left(deadline))
    url = _read_hosted_url(page, deadline)
    log.info("published a model")
    return url


# ---- Audio projects -------------------------------------------------------------------------------------------------------------
# The audio page takes samples only from a microphone (its Upload accepts nothing but its own "Download samples" zip). The worker gives
# the page a microphone that plays the teacher's sounds: this script replaces getUserMedia with a stream from an AudioContext, a new one
# for each request (the page stops the tracks of the one it closes).
MIC_INIT_JS = """
(() => {
  const AC = window.AudioContext || window.webkitAudioContext;
  let ctx, dest, src;
  const ensure = () => { if (!ctx) ctx = new AC(); return ctx; };
  const fresh = () => { dest = ensure().createMediaStreamDestination(); if (src) src.connect(dest); return dest; };
  window.__julyPlay = async (b64) => {
    ensure(); await ctx.resume();
    const bin = atob(b64); const buf = new Uint8Array(bin.length); for (let i = 0; i < bin.length; i++) buf[i] = bin.charCodeAt(i);
    const audio = await ctx.decodeAudioData(buf.buffer);
    if (src) { try { src.stop(); } catch (e) {} }
    src = ctx.createBufferSource(); src.buffer = audio; src.loop = true; if (!dest) fresh(); else src.connect(dest); src.start();
    return audio.duration;
  };
  const md = navigator.mediaDevices;
  md.getUserMedia = async (c) => { ensure(); await ctx.resume(); if (c && c.video) throw new DOMException('no camera', 'NotFoundError'); return fresh().stream; };
  md.enumerateDevices = async () => [{ deviceId: 'july', kind: 'audioinput', label: 'July', groupId: 'g' }];
})();
"""

AUDIO_SELECTORS = {
    "mic_button": 'button[title="Add sample: mic"]',
    "record_noise": "Record 20 Seconds",
    "record_sound": "Record 2 Seconds",
    "extract": "Extract Sample",
}
NOISE_CLASS = "Background Noise"
MIC_SETTLE_MS = 2500        # the panel opens the microphone and shows its meter first
SAMPLE_CAP = 16             # samples read per sound class: each two-second recording yields two, and the page asks for 8
NOISE_SAMPLES = 20
RECORD_NOISE_MS = 21500
RECORD_SOUND_MS = 2600


def _audio_count(card) -> int:
    for text in card.get_by_text("Audio Samples").all_inner_texts():
        m = re.match(r"\s*(\d+) Audio Samples", text)
        if m:
            return int(m.group(1))
    return 0


def _play(page, wav: Path):
    page.evaluate("(b) => window.__julyPlay(b)", base64.b64encode(wav.read_bytes()).decode())


def _extract(page, card, deadline: float):
    # The mic panel's overlay covers the button for a real click: the page takes a forced one.
    buttons = card.get_by_role("button", name=AUDIO_SELECTORS["extract"])
    if buttons.count():
        buttons.first.click(force=True, timeout=_left(deadline))


def _record_audio_class(page, card, wav: Path, target: int, noise: bool, deadline: float):
    _play(page, wav)
    card.locator(AUDIO_SELECTORS["mic_button"]).click(timeout=_left(deadline))
    page.wait_for_timeout(MIC_SETTLE_MS)
    if noise:
        card.get_by_role("button", name=AUDIO_SELECTORS["record_noise"]).click(timeout=_left(deadline))
        page.wait_for_timeout(RECORD_NOISE_MS)
        _extract(page, card, deadline)
    else:
        while _audio_count(card) < target:
            _left(deadline)
            card.get_by_role("button", name=AUDIO_SELECTORS["record_sound"]).click(timeout=_left(deadline))
            page.wait_for_timeout(RECORD_SOUND_MS)
            _extract(page, card, deadline)
            page.wait_for_timeout(500)
    _wait(page, lambda: _audio_count(card) >= target, deadline)


def train_audio_and_publish(page, name: str, classes: dict[str, Path], deadline: float) -> str:
    """classes: class name -> one WAV of that class's sounds (Background Noise first). Records each class through the page's microphone,
    trains and publishes, and returns the model's link. Raises TrainerError("trainer_failed")."""
    try:
        page.locator(SELECTORS["class_card"]).first.wait_for(state="attached", timeout=_left(deadline))
        page.wait_for_timeout(OPEN_SETTLE_MS)
        _hide_onboarding(page)
        _ensure_classes(page, len(classes), deadline)
        for i, (label, wav) in enumerate(classes.items()):
            card = page.locator(SELECTORS["class_card"]).nth(i)
            noise = label == NOISE_CLASS
            if i == 0 and not noise:
                raise TrainerError("trainer_failed")  # the first card is the page's own Background Noise
            if not noise:
                _name_class(page, card, label, deadline)
            _record_audio_class(page, card, wav, NOISE_SAMPLES if noise else SAMPLE_CAP, noise, deadline)
        _hide_onboarding(page)
        page.locator(SELECTORS["train_button"]).click(timeout=_left(deadline))
        page.locator(SELECTORS["trained_text"]).wait_for(state="visible", timeout=_left(deadline))
        page.locator(SELECTORS["export_button"]).click(timeout=_left(deadline))
        page.locator(SELECTORS["upload_model_button"]).click(timeout=_left(deadline))
        url = _read_hosted_url(page, deadline)
    except PlaywrightTimeout as e:
        raise TrainerError("trainer_failed") from e
    log.info("published an audio model")
    return url
