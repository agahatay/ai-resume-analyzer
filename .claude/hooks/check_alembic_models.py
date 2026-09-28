"""PostToolUse hook: warns (non-blocking) when backend/app/models/*.py is
edited without a matching Alembic migration. Runs `alembic check` from
backend/; any failure (DB unreachable, alembic not installed, etc.) is
swallowed silently so this never blocks or errors out on a dev machine
with no local Postgres running.
"""

import json
import os
import socket
import subprocess
import sys

_HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
_BACKEND_DIR = os.path.normpath(os.path.join(_HOOKS_DIR, "..", "..", "backend"))
_MODELS_DIR = os.path.normpath(os.path.join(_BACKEND_DIR, "app", "models"))
_ENV_PATH = os.path.join(_BACKEND_DIR, ".env")


def _touches_models(file_path: str) -> bool:
    if not file_path:
        return False
    abs_path = os.path.normpath(os.path.abspath(file_path))
    return abs_path.startswith(_MODELS_DIR + os.sep) or abs_path == _MODELS_DIR


def _read_env_var(key: str) -> str | None:
    # Read-only: this hook must never write to backend/.env (see block_env.py,
    # the PreToolUse hook that already refuses Claude's own edits to it).
    try:
        with open(_ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                if k.strip() == key:
                    return v.strip().strip('"').strip("'")
    except OSError:
        return None
    return None


def _db_reachable() -> bool:
    # Cheap pre-flight before paying for a full `alembic check` (which can
    # hang well past a normal TCP timeout when the configured host doesn't
    # respond at all). A plain 1s socket connect is enough to tell "nothing
    # is listening" from "something's there" without waiting on Postgres.
    host = _read_env_var("DB_HOST")
    port_str = _read_env_var("DB_PORT")
    if not host or not port_str:
        return False
    try:
        port = int(port_str)
    except ValueError:
        return False
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def _alembic_command():
    # Invoke the venv's own alembic console script, not `python -m alembic`:
    # backend/ contains an `alembic/` directory (the migrations package), and
    # running with cwd=backend puts that directory on sys.path ahead of the
    # real installed package, shadowing it (`No module named alembic.__main__`).
    # A console-script exe doesn't add cwd to sys.path, so it imports the real
    # package correctly.
    venv_dir = os.path.join(_BACKEND_DIR, ".venv")
    for candidate in (
        os.path.join(venv_dir, "Scripts", "alembic.exe"),  # Windows venv
        os.path.join(venv_dir, "bin", "alembic"),  # POSIX venv, just in case
    ):
        if os.path.isfile(candidate):
            return [candidate, "check"]
    return None  # no venv alembic found - stay silent rather than guessing


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return

    file_path = data.get("tool_input", {}).get("file_path", "")
    if not _touches_models(file_path):
        return

    command = _alembic_command()
    if command is None:
        return

    if not _db_reachable():
        return

    # PGCONNECT_TIMEOUT bounds libpq's own connection attempt. Without it,
    # a DB_HOST like "localhost" that resolves IPv6 (::1) before IPv4 can
    # make libpq hang for a very long time on the dead IPv6 candidate before
    # falling back - independent of and much longer than our own socket
    # preflight above (which uses Python's socket module, not libpq).
    env = dict(os.environ)
    env.setdefault("PGCONNECT_TIMEOUT", "2")

    try:
        result = subprocess.run(
            command,
            cwd=_BACKEND_DIR,
            capture_output=True,
            text=True,
            timeout=8,
            env=env,
        )
    except Exception:
        return  # DB unreachable / timed out / etc. - stay silent

    combined = f"{result.stdout}\n{result.stderr}"
    if result.returncode != 0 and "New upgrade operations detected" in combined:
        print(json.dumps({
            "systemMessage": (
                "alembic check: model changes detected with no matching migration. "
                'Run: cd backend && alembic revision --autogenerate -m "<message>"'
            )
        }))


if __name__ == "__main__":
    main()
