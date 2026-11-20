#!/usr/bin/env python3
"""Build headless_music_player/static/css/app.css with Tailwind CSS and daisyUI.

No Node needed: downloads the Tailwind standalone CLI and the daisyUI plugin files
(pinned versions below) into .tools/ on first run, then compiles input.css.

    python scripts/build_css.py           # build once, minified
    python scripts/build_css.py --watch   # rebuild when templates or JS change
"""

import argparse
import os
import platform
import shutil
import stat
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

TAILWIND_VERSION = "v4.1.11"
DAISYUI_VERSION = "v5.0.43"

ROOT = Path(__file__).resolve().parent.parent
TOOLS = ROOT / ".tools"
CSS_DIR = ROOT / "headless_music_player" / "static" / "css"
VENDOR = CSS_DIR / "vendor"
INPUT = CSS_DIR / "input.css"
OUTPUT = CSS_DIR / "app.css"


def tailwind_asset():
    system = platform.system().lower()
    machine = platform.machine().lower()
    arch = {"x86_64": "x64", "amd64": "x64", "arm64": "arm64", "aarch64": "arm64"}.get(machine)
    if arch is None:
        sys.exit(f"No Tailwind standalone build for {machine}. Build the CSS on another machine.")
    if system == "darwin":
        return f"tailwindcss-macos-{arch}"
    if system == "linux":
        return f"tailwindcss-linux-{arch}"
    if system == "windows":
        return "tailwindcss-windows-x64.exe"
    sys.exit(f"Unsupported system: {system}")


def download(url, dest):
    print(f"Downloading {url}")
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part")
    try:
        with urllib.request.urlopen(url, timeout=120) as res, open(tmp, "wb") as f:
            shutil.copyfileobj(res, f)
    except urllib.error.URLError as e:
        # python.org builds on macOS ship without CA certificates until
        # "Install Certificates.command" is run; curl uses the system store.
        if not shutil.which("curl"):
            raise
        print(f"  urllib failed ({e.reason}), retrying with curl")
        subprocess.run(["curl", "-fsSL", "-o", str(tmp), url], check=True)
    os.replace(tmp, dest)


def ensure_tools():
    asset = tailwind_asset()
    cli = TOOLS / f"{TAILWIND_VERSION}-{asset}"
    if not cli.exists():
        download(f"https://github.com/tailwindlabs/tailwindcss/releases/download/{TAILWIND_VERSION}/{asset}", cli)
        cli.chmod(cli.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    # The plugin files sit next to input.css (gitignored), where @plugin finds them.
    marker = VENDOR / ".version"
    if not marker.exists() or marker.read_text().strip() != DAISYUI_VERSION:
        for name in ("daisyui.mjs", "daisyui-theme.mjs"):
            download(f"https://github.com/saadeghi/daisyui/releases/download/{DAISYUI_VERSION}/{name}", VENDOR / name)
        marker.write_text(DAISYUI_VERSION + "\n")
    return cli


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--watch", action="store_true", help="rebuild on changes")
    args = parser.parse_args()

    cli = ensure_tools()
    cmd = [str(cli), "-i", str(INPUT), "-o", str(OUTPUT)]
    cmd += ["--watch"] if args.watch else ["--minify"]
    sys.exit(subprocess.call(cmd, cwd=CSS_DIR))


if __name__ == "__main__":
    main()
