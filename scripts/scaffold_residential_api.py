#!/usr/bin/env python3
"""Scaffold a new residential device API from _shared/fastapi_skeleton. Never overwrites."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKEL = ROOT / "Ansible/residential/_shared/fastapi_skeleton"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--kind", choices=("routers", "switches"), required=True)
    ap.add_argument("--vendor", required=True)
    ap.add_argument("--slug", required=True, help="folder name, e.g. example-widget-router-api")
    ap.add_argument("--title", required=True)
    args = ap.parse_args()
    dest = ROOT / "Ansible/residential" / args.kind / args.vendor / args.slug
    if dest.exists():
        print(f"exists, not overwriting: {dest}")
        return 1
    shutil.copytree(SKEL, dest, symlinks=True)
    main_py = dest / "app" / "main.py"
    main_py.write_text(main_py.read_text().replace("DEVICE_TITLE", args.title))
    # requirements symlink to shared
    req = dest / "requirements.txt"
    if req.exists() or req.is_symlink():
        req.unlink()
    rel = Path(os_rel := __import__("os").path.relpath(ROOT / "Ansible/residential/_shared/requirements-api.txt", dest))
    req.symlink_to(rel)
    print(f"created {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
