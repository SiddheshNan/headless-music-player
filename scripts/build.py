#!/usr/bin/env python3
"""Release build: write the version, build the CSS and the Docker image, optionally deploy.

    python scripts/build.py                      # asks for the version
    python scripts/build.py --version 0.3.0      # non-interactive
    python scripts/build.py --version 0.3.0 --no-image
    python scripts/build.py --deploy             # also (re)start it with docker compose
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMAGE = "headless-music-player"
VERSION_FILES = {
    ROOT / "headless_music_player" / "__init__.py": (r'__version__ = "[^"]+"', '__version__ = "{v}"'),
    ROOT / "pyproject.toml": (r'(?m)^version = "[^"]+"', 'version = "{v}"'),
}


def current_version():
    text = (ROOT / "headless_music_player" / "__init__.py").read_text()
    return re.search(r'__version__ = "([^"]+)"', text).group(1)


def set_version(version):
    for path, (pattern, template) in VERSION_FILES.items():
        text = path.read_text()
        new_text, count = re.subn(pattern, template.format(v=version), text, count=1)
        if count != 1:
            sys.exit(f"Could not find the version in {path}")
        path.write_text(new_text)
    print(f"Version set to {version}")


def run(cmd):
    print(f"\n$ {' '.join(cmd)}")
    if subprocess.call(cmd, cwd=ROOT) != 0:
        sys.exit(f"Failed: {' '.join(cmd)}")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--version", help="version to release, e.g. 0.3.0 (a leading v is dropped)")
    parser.add_argument("--no-image", action="store_true", help="only write the version and build the CSS")
    parser.add_argument("--deploy", action="store_true", help="run `docker compose up -d` afterwards")
    args = parser.parse_args()

    version = args.version
    if version is None:
        version = input(f"Version [{current_version()}]: ").strip() or current_version()
    version = version.removeprefix("v")
    if not re.fullmatch(r"\d+\.\d+\.\d+", version):
        sys.exit(f"Not a version: {version}")

    set_version(version)
    run([sys.executable, "scripts/build_css.py"])

    if args.no_image:
        return
    run(["docker", "build", "-t", f"{IMAGE}:{version}", "-t", f"{IMAGE}:latest", "."])

    if args.deploy:
        run(["docker", "compose", "up", "-d"])
        print("\nRunning at http://<raspberry-pi-ip>:8000")


if __name__ == "__main__":
    main()
