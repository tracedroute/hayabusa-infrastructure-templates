#!/usr/bin/env python3
"""CI checks for Hayabusa infrastructure-templates tree hygiene.

Does not modify files. Creation/Configuration ZTP pairs
(OpenTofu/ztp ↔ Ansible/ztp) are intentional and are not treated as
duplicate-content failures.
"""
from __future__ import annotations

import hashlib
import sys
from collections import defaultdict
from pathlib import Path


FORBIDDEN = [
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

EXPECTED = [
    "OpenTofu/ztp",
    "Ansible/ztp",
    "Ansible/inventory",
    "Ansible/iot",
    "Ansible/scada",
    "Ansible/residential",
    "Ansible/security-fire",
    "Ansible/Security",
]

# Exact-copy pairs across these roots are expected (working ZTP lives in both tabs).
INTENTIONAL_PAIR_ROOTS = (
    ("OpenTofu/ztp/", "Ansible/ztp/"),
)


def _is_intentional_pair(paths: list[str]) -> bool:
    """True when every path is under a Creation↔Configuration ZTP pair and
    each relative-under-ztp appears at most once per side."""
    if len(paths) != 2:
        return False
    a, b = sorted(paths)
    for left, right in INTENTIONAL_PAIR_ROOTS:
        if a.startswith(left) and b.startswith(right):
            return a[len(left) :] == b[len(right) :]
    return False


def _dup_bucket_paths(paths: list[str]) -> list[str]:
    """Drop intentional Creation↔Configuration ZTP pairs from a hash group."""
    if _is_intentional_pair(paths):
        return []
    # If a larger group is only OT/ztp + AN/ztp mirrors plus extras, keep all
    # for visibility — do not silently hide extras.
    return paths


def main(root: Path) -> int:
    root = root.resolve()
    errors: list[str] = []
    warnings: list[str] = []

    for required in ("OpenTofu", "Ansible"):
        if not (root / required).is_dir():
            errors.append(f"missing required root: {required}/")

    for p in root.rglob("*"):
        if ".git" in p.parts:
            continue
        if p.is_symlink() and not p.exists():
            errors.append(f"broken symlink: {p.relative_to(root)}")

    for rel in FORBIDDEN:
        if (root / rel).exists():
            errors.append(f"legacy/forbidden path still present: {rel}")

    for rel in EXPECTED:
        if not (root / rel).exists():
            warnings.append(f"expected path missing: {rel}")

    by_hash: dict[str, list[str]] = defaultdict(list)
    for p in root.rglob("*"):
        if ".git" in p.parts or not p.is_file() or p.is_symlink():
            continue
        try:
            size = p.stat().st_size
        except OSError:
            continue
        if size > 512_000 or size == 0:
            continue
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        by_hash[h].append(str(p.relative_to(root)))

    review: list[tuple[str, list[str]]] = []
    for h, paths in by_hash.items():
        kept = _dup_bucket_paths(paths)
        if len(kept) >= 3:
            review.append((h[:12], sorted(kept)))

    if review:
        warnings.append(
            f"{len(review)} content hashes appear 3+ times outside intentional "
            f"OpenTofu/ztp↔Ansible/ztp pairs (review; do not auto-delete)"
        )
        for h, paths in sorted(review, key=lambda x: -len(x[1]))[:12]:
            sample = paths[:8]
            more = f" (+{len(paths) - 8} more)" if len(paths) > 8 else ""
            warnings.append(f"  hash {h} x{len(paths)}: " + "; ".join(sample) + more)

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
