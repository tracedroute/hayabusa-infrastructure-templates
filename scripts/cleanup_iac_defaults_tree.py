#!/usr/bin/env python3
"""One-shot cleanup of Hayabusa OpenTofu/Ansible default workspace trees.

Canonical layout (Creation / Configuration):
  OpenTofu/          — Creation (keep ztp/ here)
  Ansible/           — Configuration
    inventory/       — single inventory dir
    ztp/<vendor>/    — single Ansible ZTP home
    residential/     — merged residential API + device trees
    iot/             — was IoT Devices
    scada/           — was SCADA & PLC (+ openPLC)
    security/
    security-fire/   — was Security & Fire Systems
    bare-metal-ztp/
    playbooks/, roles/, group_vars/

Removes cross-engine nests, legacy ZTP copies, and broken symlinks.
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path


def _merge_into(src: Path, dst: Path) -> None:
    if not src.exists():
        return
    if src.is_symlink():
        # Prefer resolving; if broken, drop
        try:
            target = src.resolve(strict=True)
        except Exception:
            src.unlink(missing_ok=True)
            return
        if not dst.exists():
            if target.is_dir():
                shutil.copytree(target, dst, dirs_exist_ok=True)
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(target, dst)
        src.unlink(missing_ok=True)
        return
    if not src.is_dir():
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            shutil.move(str(src), str(dst))
        else:
            src.unlink(missing_ok=True)
        return
    dst.mkdir(parents=True, exist_ok=True)
    for child in list(src.iterdir()):
        _merge_into(child, dst / child.name)
    try:
        src.rmdir()
    except OSError:
        # leftover non-empty; force
        shutil.rmtree(src, ignore_errors=True)


def _rm(path: Path) -> None:
    if not path.exists() and not path.is_symlink():
        return
    if path.is_symlink() or path.is_file():
        path.unlink(missing_ok=True)
    else:
        shutil.rmtree(path, ignore_errors=True)


def _norm_vendor_ztp_layout(ztp_root: Path) -> None:
    """Prefer router/switch singular dirs; merge routers->router, switches->switch."""
    if not ztp_root.is_dir():
        return
    for vendor in list(ztp_root.iterdir()):
        if not vendor.is_dir():
            continue
        for plural, singular in (("routers", "router"), ("switches", "switch")):
            src = vendor / plural
            dst = vendor / singular
            if src.exists():
                _merge_into(src, dst)


def cleanup(root: Path) -> None:
    root = root.resolve()
    ot = root / "OpenTofu"
    an = root / "Ansible"
    if not ot.is_dir() or not an.is_dir():
        raise SystemExit(f"expected OpenTofu/ and Ansible/ under {root}")

    # --- OpenTofu: keep Creation ZTP; drop nested Ansible and zerotouch dup ---
    _merge_into(ot / "modules" / "zerotouch" / "ztp", ot / "ztp")
    _rm(ot / "modules" / "zerotouch")
    # OpenTofu/ansible is Configuration contamination — merge its ztp into Ansible/ztp, rest into Ansible
    ot_ansible = ot / "ansible"
    if ot_ansible.is_dir():
        _merge_into(ot_ansible / "ztp", an / "ztp")
        for name in ("playbooks", "inventory", "roles", "group_vars"):
            _merge_into(ot_ansible / name, an / name)
        # leftover files (ansible.cfg, README)
        for f in list(ot_ansible.iterdir()):
            if f.is_file():
                f.unlink(missing_ok=True)
        _rm(ot_ansible)
    _norm_vendor_ztp_layout(ot / "ztp")

    # --- Ansible: collapse all ZTP variants into Ansible/ztp ---
    for extra in (
        an / "OpenTofu" / "vendor-ztp",
        an / "OpenTofu" / "ztp",
        an / "ztp-legacy-root",
        an / "ztp-device-defaults",
    ):
        _merge_into(extra, an / "ztp")
    # Remaining Ansible/OpenTofu (playbooks/inventory stubs) -> Ansible
    an_ot = an / "OpenTofu"
    if an_ot.is_dir():
        for name in ("playbooks", "inventory", "roles", "group_vars"):
            _merge_into(an_ot / name, an / name)
        for f in list(an_ot.iterdir()):
            if f.is_file():
                f.unlink(missing_ok=True)
        _rm(an_ot)

    # Fix broken / materialize paloalto under Ansible/ztp from OpenTofu if needed
    palo_an = an / "ztp" / "paloalto"
    palo_ot = ot / "ztp" / "paloalto"
    if palo_an.is_symlink() or (palo_an.exists() and not any(palo_an.iterdir()) if palo_an.is_dir() and not palo_an.is_symlink() else False):
        _rm(palo_an)
    if palo_ot.is_dir() and not palo_an.exists():
        shutil.copytree(palo_ot, palo_an)
    elif palo_an.is_symlink():
        _rm(palo_an)
        if palo_ot.is_dir():
            shutil.copytree(palo_ot, palo_an)

    _norm_vendor_ztp_layout(an / "ztp")

    # --- inventory merge ---
    _merge_into(an / "inventories", an / "inventory")

    # --- residential merge ---
    residential = an / "residential"
    _merge_into(an / "residential-routers-and-switches-apis", residential)
    _merge_into(an / "residential-routers-and-switches", residential)

    # --- domain renames ---
    _merge_into(an / "IoT Devices", an / "iot")
    scada = an / "scada"
    _merge_into(an / "SCADA & PLC", scada)
    _merge_into(an / "openPLC", scada / "openplc")
    _merge_into(an / "Security & Fire Systems", an / "security-fire")
    # Keep capital-S Security/ for SECops console tab paths.
    if (an / "Security").is_dir() and (an / "security").is_dir():
        _merge_into(an / "security", an / "Security")
    elif (an / "security").is_dir() and not (an / "Security").exists():
        (an / "security").rename(an / "Security")
    # Ensure Security exists if neither (no-op otherwise)
    if not (an / "Security").exists() and (an / "security").exists():
        (an / "security").rename(an / "Security")

    # Drop empty stray dirs
    for p in (
        an / "ztp-legacy-root",
        an / "ztp-device-defaults",
        an / "inventories",
        an / "OpenTofu",
        an / "IoT Devices",
        an / "SCADA & PLC",
        an / "Security & Fire Systems",
        an / "residential-routers-and-switches",
        an / "residential-routers-and-switches-apis",
        an / "openPLC",
        ot / "ansible",
        ot / "modules" / "zerotouch",
    ):
        _rm(p)

    # README pointers for renamed domains
    readmes = {
        an / "iot" / "README.md": "# IoT (Configuration)\n\nFormer `IoT Devices/` catalog. Device playbooks by vendor.\n",
        an / "scada" / "README.md": "# SCADA & PLC (Configuration)\n\nFormer `SCADA & PLC/` and `openPLC/` trees.\n",
        an / "security-fire" / "README.md": "# Security & Fire Systems (Configuration)\n\nFormer `Security & Fire Systems/`.\n",
        an / "residential" / "README.md": "# Residential routers & switches (Configuration)\n\nMerged former `residential-routers-and-switches` + `-apis` trees.\n",
        an / "ztp" / "README.md": "# Vendor ZTP (Configuration)\n\nCanonical Ansible-side ZTP. Creation-side ZTP lives under `OpenTofu/ztp/`.\n",
        ot / "ztp" / "README.md": "# Vendor ZTP (Creation)\n\nCanonical OpenTofu-side ZTP. Configuration-side ZTP lives under `Ansible/ztp/`.\n",
    }
    for path, text in readmes.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists():
            path.write_text(text, encoding="utf-8")

    print("cleanup complete:", root)
    print("OpenTofu children:", sorted(p.name for p in ot.iterdir()))
    print("Ansible children:", sorted(p.name for p in an.iterdir()))


if __name__ == "__main__":
    target = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
    cleanup(target)
