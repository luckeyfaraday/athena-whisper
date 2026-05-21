from __future__ import annotations

import subprocess
from dataclasses import dataclass

from .base import InjectionResult


@dataclass(frozen=True)
class YdotoolTypeInjector:
    backend_name: str = "ydotool-type"

    def inject(self, text: str) -> InjectionResult:
        subprocess.run(["ydotool", "type", text], check=True)
        return InjectionResult(
            inserted=True,
            backend=self.backend_name,
            detail="Typed text using ydotool. Requires ydotoold and /dev/uinput access.",
        )
