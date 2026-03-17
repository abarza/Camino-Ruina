from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass


@dataclass(frozen=True)
class TmuxTarget:
    session: str
    pane: str

    @staticmethod
    def from_env() -> "TmuxTarget":
        return TmuxTarget(
            session=os.getenv("TMUX_SESSION", "df"),
            pane=os.getenv("TMUX_PANE", "0"),
        )

    def pane_id(self) -> str:
        # session:pane
        return f"{self.session}:{self.pane}"


def _run_tmux(args: list[str]) -> str:
    p = subprocess.run(
        ["tmux", *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if p.returncode != 0:
        raise RuntimeError(f"tmux fallo ({p.returncode}): {' '.join(args)}\n{p.stderr.strip()}")
    return p.stdout


_ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")
_NOISE_PATTERNS = [
    re.compile(r"^Broken unicode:", re.IGNORECASE),
    re.compile(r"^Unknown SDLKey:", re.IGNORECASE),
    re.compile(r"^Unknown binding:", re.IGNORECASE),
    re.compile(r"^Loading bindings from", re.IGNORECASE),
    re.compile(r"^New window size:", re.IGNORECASE),
    re.compile(r"^Font size:", re.IGNORECASE),
    re.compile(r"^Resizing (grid|font) to", re.IGNORECASE),
    re.compile(r"^locale::facet::_S_create_c_locale", re.IGNORECASE),
    re.compile(r"^\]$"),
    re.compile(r"^(?:KP_[0-9]|\.)+$"),
]


def _is_noise_line(line: str) -> bool:
    return any(p.search(line) for p in _NOISE_PATTERNS)


def _sanitize_capture(text: str) -> str:
    text = _ANSI_RE.sub("", text)
    lines = text.splitlines()

    cleaned: list[str] = []
    blank_run = 0
    for raw in lines:
        line = raw.rstrip()
        if _is_noise_line(line):
            continue
        if not line:
            blank_run += 1
            if blank_run > 1:
                continue
        else:
            blank_run = 0
        cleaned.append(line)

    return "\n".join(cleaned).strip()


def capture_pane(target: TmuxTarget, *, lines: int = 200, sanitize: bool = True) -> str:
    out = _run_tmux(["capture-pane", "-p", "-t", target.pane_id(), "-S", f"-{lines}"])
    out = out.rstrip("\n")
    if sanitize:
        return _sanitize_capture(out)
    return out


def send_keys(target: TmuxTarget, keys: str, *, enter: bool = True) -> None:
    _run_tmux(["send-keys", "-t", target.pane_id(), keys])
    if enter:
        _run_tmux(["send-keys", "-t", target.pane_id(), "C-m"])


def send_raw_keys(target: TmuxTarget, keys: list[str]) -> None:
    # Útil para mandar una secuencia de teclas (sin Enter).
    for k in keys:
        _run_tmux(["send-keys", "-t", target.pane_id(), k])
