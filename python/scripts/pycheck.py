#!/usr/bin/env python3

import os
import subprocess
import sys
from typing import List

from absl import app, logging
from pathlib import Path


def run_command(cmd: str, description: str, env: dict[str, str] | None = None) -> bool:
    """Run a command and handle errors"""
    logging.info(f"Running {description}...")
    try:
        result = subprocess.run(
            cmd, shell=True, check=True, capture_output=True, text=True, env=env
        )
        if result.stdout.strip():
            logging.info(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        logging.error(f"{description} failed:")
        if e.stdout:
            logging.error(e.stdout)
        if e.stderr:
            logging.error(e.stderr)
        return False


def _is_bazel_generated(path: str) -> bool:
    """Return True if path is inside any Bazel output directory."""
    parts = path.split(os.sep)
    return any(p.startswith("bazel-") for p in parts)


def main(argv: List[str]) -> int:
    repo_root = str(Path(__file__).resolve().parent)
    env_vars = os.environ.copy()
    existing_pythonpath = env_vars.get("PYTHONPATH", "")
    if existing_pythonpath:
        env_vars["PYTHONPATH"] = repo_root + os.pathsep + existing_pythonpath
    else:
        env_vars["PYTHONPATH"] = repo_root

    files = sys.argv[1:] if len(sys.argv) > 1 else []

    if files:
        filtered_files = [f for f in files if not _is_bazel_generated(f)]
        pyrefly_files = filtered_files

        if filtered_files:
            file_list = " ".join(filtered_files)
            checks = []
            if pyrefly_files:
                pyrefly_list = " ".join(pyrefly_files)
                checks.append((f"pyrefly check {pyrefly_list}", "Type checking"))
            checks.extend(
                [
                    (f"ruff check {file_list}", "Linting"),
                    (f"ruff format {file_list}", "Formatting"),
                ]
            )
        else:
            logging.info("Python checks complete (no files to check)")
            return 0
    else:
        try:
            result = subprocess.run(
                ["git", "ls-files", "-m", "-o", "--exclude-standard"],
                check=True,
                capture_output=True,
                text=True,
            )
            changed = [
                line.strip() for line in result.stdout.splitlines() if line.strip()
            ]
        except subprocess.CalledProcessError:
            changed = []

        py_files = [
            f for f in changed if f.endswith(".py") and not _is_bazel_generated(f)
        ]

        if py_files:
            file_list = " ".join(py_files)
            checks = [
                (f"pyrefly check {file_list}", "Type checking"),
                (f"ruff check {file_list}", "Linting"),
                (f"ruff format {file_list}", "Formatting"),
            ]
        else:
            checks = [
                (
                    "pyrefly check $(find python -name '*.py' | sort -u | tr '\n' ' ')",
                    "Type checking",
                ),
                ("ruff check python", "Linting"),
                ("ruff format python", "Formatting"),
            ]

    all_passed = True
    for cmd, description in checks:
        if not run_command(cmd, description, env=env_vars):
            all_passed = False

    if all_passed:
        logging.info("Python checks complete")
        return 0
    else:
        logging.error("Some Python checks failed")
        return 1


if __name__ == "__main__":
    app.run(main)
