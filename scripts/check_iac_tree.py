#!/usr/bin/env python3
"""CI checks for Hayabusa infrastructure-templates tree hygiene.

Does not modify files. Creation/Configuration ZTP pairs
(OpenTofu/ztp ↔ Ansible/ztp) are intentional and are not treated as
duplicate-content failures. Symlinks to shared templates are preferred
over byte-identical copies.
"""
from __future__ import annotations

import hashlib
import json
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
    "Ansible/residential/_shared",
    "Ansible/security-fire",
    "Ansible/Security",  # SECops — capital S required by Core
]

INTENTIONAL_PAIR_ROOTS = (
    ("OpenTofu/ztp/", "Ansible/ztp/"),
)

VENDOR_FROM_PATH = ("cisco", "juniper", "arista", "aruba", "paloalto", "proxmox", "vmware")


def _is_intentional_pair(paths: list[str]) -> bool:
    if len(paths) != 2:
        return False
    a, b = sorted(paths)
    for left, right in INTENTIONAL_PAIR_ROOTS:
        if a.startswith(left) and b.startswith(right):
            return a[len(left) :] == b[len(right) :]
    return False


def _dup_bucket_paths(paths: list[str]) -> list[str]:
    if _is_intentional_pair(paths):
        return []
    return paths


def _vendor_from_rel(rel: str) -> str | None:
    parts = Path(rel).parts
    for p in parts:
        pl = p.lower()
        if pl in VENDOR_FROM_PATH:
            return pl
    return None


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

    # ZTP default.json vendor/device_type must match path (do not silently ship cross-vendor clones)
    for base in ("OpenTofu/ztp", "Ansible/ztp"):
        base_p = root / base
        if not base_p.is_dir():
            continue
        for p in base_p.rglob("default.json"):
            if p.is_symlink() or not p.is_file():
                continue
            rel = str(p.relative_to(root))
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                errors.append(f"invalid ZTP default JSON {rel}: {exc}")
                continue
            if not isinstance(data, dict):
                errors.append(f"ZTP default must be object: {rel}")
                continue
            path_vendor = _vendor_from_rel(rel)
            file_vendor = str(data.get("vendor") or "").strip().lower()
            if path_vendor and file_vendor and path_vendor != file_vendor:
                errors.append(
                    f"ZTP vendor mismatch in {rel}: path={path_vendor} json.vendor={file_vendor}"
                )
            path_dtype = None
            for part in Path(rel).parts:
                if part in {"router", "switch", "firewall"}:
                    path_dtype = part
                    break
            file_dtype = str(data.get("device_type") or "").strip().lower()
            if path_dtype and file_dtype and path_dtype != file_dtype:
                errors.append(
                    f"ZTP device_type mismatch in {rel}: path={path_dtype} json.device_type={file_dtype}"
                )

    by_hash: dict[str, list[str]] = defaultdict(list)
    for p in root.rglob("*"):
        if ".git" in p.parts or p.is_symlink() or not p.is_file():
            continue
        try:
            size = p.stat().st_size
        except OSError:
            continue
        if size > 512_000 or size == 0:
            continue
        # Skip shared sources themselves from "duplicate" noise when many linkers exist
        rel = str(p.relative_to(root))
        if "/_shared/" in rel.replace("\\", "/") or rel.startswith("OpenTofu/templates/"):
            continue
        h = hashlib.sha256(p.read_bytes()).hexdigest()
        by_hash[h].append(rel)

    review: list[tuple[str, list[str]]] = []
    for h, paths in by_hash.items():
        kept = _dup_bucket_paths(paths)
        if len(kept) >= 3:
            review.append((h[:12], sorted(kept)))

    if review:
        warnings.append(
            f"{len(review)} content hashes appear 3+ times outside intentional "
            f"OpenTofu/ztp↔Ansible/ztp pairs and shared templates (review; do not auto-delete)"
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
