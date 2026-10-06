#!/usr/bin/env python3
"""Idempotent: point identical residential requirements.txt at _shared files.

Never deletes device API scripts. Only replaces requirements.txt that exactly
match a shared file with a relative symlink.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root", nargs="?", default=".")
    args = ap.parse_args()
    root = Path(args.root).resolve() / "Ansible" / "residential"
    shared = root / "_shared"
    if not shared.is_dir():
        print("missing Ansible/residential/_shared")
        return 1
    shared_files = list(shared.glob("requirements-*.txt"))
    if not shared_files:
        print("no shared requirements-*.txt")
        return 1
    n = 0
    for p in root.rglob("requirements.txt"):
        if "_shared" in p.parts:
            continue
        if p.is_symlink():
            continue
        raw = p.read_bytes()
        target = next((s for s in shared_files if s.read_bytes() == raw), None)
        if not target:
            continue
        rel = os.path.relpath(target, start=p.parent)
        p.unlink()
        p.symlink_to(rel)
        n += 1
        print(f"linked {p.relative_to(root.parent.parent)} -> {rel}")
    print(f"OK: linked {n}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
