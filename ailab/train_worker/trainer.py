"""The seam between the loop and whatever trains the model: a job's images in, a Teachable Machine link out."""

from pathlib import Path
from typing import Protocol


MAX_PROJECT_BYTES = 100 * 1024 * 1024  # a saved project above this is refused (trainer_failed)
JOB_BUDGET_S = 300     # image and pose: five minutes for the whole job, retry included
AUDIO_BUDGET_S = 900   # audio plays its sounds into the page in real time: about 40 s a class, plus training
HARD_CAP_GRACE_S = 60  # the loop gives up on a trainer call this long after its budget, even if the call never returns


def hard_cap(kind: str) -> float:
    """Seconds the loop waits for a trainer call before it fails the job itself. The browser trainer keeps its own budget; this is
    the backstop for a call that never returns (a frozen page, a Playwright call nothing unblocks), which would otherwise hold
    the slot and keep the lease alive with heartbeats forever."""
    return (AUDIO_BUDGET_S if kind == "audio" else JOB_BUDGET_S) + HARD_CAP_GRACE_S


class TrainerError(Exception):
    """The trainer failed; code is one of the job failure codes the API accepts (trainer_failed, trainer_unavailable)."""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class Trainer(Protocol):
    def train(self, name: str, classes: dict[str, list[Path]], *, settings: dict | None = None,
              project_in: Path | None = None, project_out: Path | None = None, kind: str = "image") -> str:
        """Train a model named name on the images of each class; return its https://teachablemachine.withgoogle.com/models/<id>/ link.

        settings: epochs, batch_size, learning_rate (None means the default). project_in: a saved project to open first and add the
        images to (a retrain). kind: image or pose, the Teachable Machine project to train. project_out: where to save the project file once trained, before publishing."""
        ...
