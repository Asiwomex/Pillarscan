"""Assemble the two Lambda packages under build/, for Terraform to zip.

    python scripts/build_lambdas.py

    build/scanner/   the scanner package. boto3 comes with the Lambda runtime.
    build/api/       the API, the scanner package it shares code with, and
                     FastAPI's dependencies built for Lambda's Linux on arm64.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "build"
PYTHON_VERSION = "3.13"
API_DEPENDENCIES = ["fastapi>=0.115", "mangum>=0.19"]

IGNORED = shutil.ignore_patterns("__pycache__", "*.pyc")


def copy_package(name: str, destination: Path) -> None:
    shutil.copytree(ROOT / name, destination / name, ignore=IGNORED)


def build_scanner() -> Path:
    target = BUILD / "scanner"
    copy_package("scanner", target)
    return target


def build_api() -> Path:
    target = BUILD / "api"
    target.mkdir(parents=True)
    # Some dependencies (pydantic-core) are compiled. Asking pip for the
    # Linux arm64 wheels makes the package work on Lambda even when this
    # script runs on Windows or macOS.
    subprocess.run(
        [
            sys.executable, "-m", "pip", "install", "--quiet",
            "--target", str(target),
            "--platform", "manylinux2014_aarch64",
            "--implementation", "cp",
            "--python-version", PYTHON_VERSION,
            "--only-binary=:all:",
            *API_DEPENDENCIES,
        ],
        check=True,
    )
    for cache in target.rglob("__pycache__"):
        shutil.rmtree(cache)
    copy_package("api", target)
    copy_package("scanner", target)
    return target


def size_mb(directory: Path) -> float:
    return sum(f.stat().st_size for f in directory.rglob("*") if f.is_file()) / 1_000_000


def main() -> None:
    if BUILD.exists():
        shutil.rmtree(BUILD)
    for target in (build_scanner(), build_api()):
        print(f"{target.relative_to(ROOT)}: {size_mb(target):.1f} MB")


if __name__ == "__main__":
    main()
