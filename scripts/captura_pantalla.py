from __future__ import annotations

import datetime as dt
import os
from pathlib import Path

from scripts.tmux_io import TmuxTarget, capture_pane


def mundo_dir() -> Path:
    return Path(os.getenv("MUNDO_DIR", "mundo")).resolve()


def log_path_for_today(mundo: Path) -> Path:
    today = dt.date.today().isoformat()
    return mundo / "logs" / f"{today}.md"


def append_snapshot(log_path: Path, snapshot: str) -> None:
    now = dt.datetime.now().strftime("%H:%M:%S")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as f:
        f.write(f"## Snapshot {now}\n\n")
        f.write("```text\n")
        f.write(snapshot)
        f.write("\n```\n\n")


def main() -> int:
    target = TmuxTarget.from_env()
    mundo = mundo_dir()
    snap = capture_pane(target, lines=250)
    append_snapshot(log_path_for_today(mundo), snap)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

