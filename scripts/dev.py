"""
Кроссплатформенный дев-лаунчер. Запускает control-plane, node_service и frontend
одной командой из терминала PyCharm:

    python scripts/dev.py

Подхватывает переменные из .env и node_service/.env.node, корректно завершает
процессы по Ctrl+C.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parent.parent


def load_env_file(path: Path) -> None:
    """Простейший парсер .env без зависимостей."""
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value)


def start_process(cmd: Iterable[str], cwd: Path) -> subprocess.Popen:
    return subprocess.Popen(
        cmd,
        cwd=str(cwd),
        env=os.environ.copy(),
    )


def main() -> int:
    load_env_file(ROOT / ".env")
    load_env_file(ROOT / "node_service" / ".env.node")

    processes = []
    try:
        print("[dev] control-plane -> http://127.0.0.1:8000")
        processes.append(
            start_process([sys.executable, "-m", "uvicorn", "app.main:app", "--reload", "--port", "8000"], ROOT)
        )

        print("[dev] node_service -> http://127.0.0.1:9000")
        processes.append(
            start_process(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "node_service.app.main:app",
                    "--reload",
                    "--host",
                    "0.0.0.0",
                    "--port",
                    "9000",
                ],
                ROOT,
            )
        )

        print("[dev] frontend -> http://127.0.0.1:5173")
        processes.append(start_process(["npm", "run", "dev", "--", "--host", "--port", "5173"], ROOT / "frontend"))

        print("[dev] Все процессы запущены. Нажмите Ctrl+C для остановки.")
        for proc in processes:
            proc.wait()
    except KeyboardInterrupt:
        pass
    finally:
        for proc in processes:
            if proc.poll() is None:
                try:
                    if os.name == "nt":
                        proc.send_signal(signal.CTRL_BREAK_EVENT)
                    else:
                        proc.terminate()
                except Exception:
                    proc.kill()
        for proc in processes:
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
        print("[dev] Завершено")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
