#!/usr/bin/env python3
"""CI checks for Hayabusa infrastructure-templates tree hygiene."""
from __future__ import annotations

import hashlib
import os
import sys
from collections import defaultdict
from pathlib import Path


def main(root: Path) -> int:
    root = root.resolve()
    errors: list[str] = []
    warnings: list[str] = []

    for required in ("OpenTofu", "Ansible"):
        if not (root / required).is_dir():
            errors.append(f"missing required root: {required}/")

    # Broken symlinks
    for dirpath, _, filenames in os.walk(root):
        if "/.git/" in dirpath or dirpath.endswith("/.git"):
            continue
        for name in filenames:
            p = Path(dirpath) / name
        # also check dirs that are symlinks via scandir
    for p in root.rglob("*"):
        if ".git" in p.parts:
            continue
        if p.is_symlink() and not p.exists():
            errors.append(f"broken symlink: {p.relative_to(root)}")

    # Forbidden nests / legacy names
    forbidden = [
        "Ansible/OpenTofu",
        "OpenTofu/ansible",
        "Ansible/ztp-legacy-root",
        "Ansible/ztp-device-defaults",
        "Ansible/inventories",
        "Ansible/IoT Devices",
        "Ansible/SCADA & PLC",
        "Ansible/Security & Fire Systems",
        "Ansible/residential-routers-and-switches",
        "Ansible/residential-routers-and-switches-apis",
        "OpenTofu/modules/zerotouch",
    ]
    for rel in forbidden:
        if (root / rel).exists():
            errors.append(f"legacy/forbidden path still present: {rel}")

    # Expected canonical dirs
    for rel in (
        "OpenTofu/ztp",
        "Ansible/ztp",
        "Ansible/inventory",
        "Ansible/iot",
        "Ansible/scada",
        "Ansible/residential",
        "Ansible/security-fire",
        "Ansible/Security",
    ):
        if not (root / rel).exists():
            warnings.append(f"expected path missing: {rel}")

    # Duplicate content across Creation/Configuration ZTP is OK (intentionally paired),
    # but flag 3+ exact copies of the same file basename under different parents.
    by_hash: dict[str, list[str]] = defaultdict(list)
    for p in root.rglob("*"):
        if ".git" in p.parts or not p.is_file() or p.is_symlink():
            continue
        if p.stat().st_size > 512_000:
            continue
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        by_hash[h].append(str(p.relative_to(root)))
    multi = {h: paths for h, paths in by_hash.items() if len(paths) >= 3}
    if multi:
        warnings.append(f"{len(multi)} content hashes appear 3+ times (review duplicates)")

    for w in warnings:
        print("WARN:", w)
    for e in errors:
        print("ERROR:", e)
    if errors:
        return 1
    print("OK: tree hygiene checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(Path(sys.argv[1] if len(sys.argv) > 1 else ".")))
