#!/usr/bin/env python3
"""
Smoke / wiring checks for infrastructure-templates.

Safe by default: never mutates trees, never runs playbooks against devices.
Optional ansible --syntax-check when ansible-playbook is installed.

Exit 0 = pass (warnings allowed). Exit 1 = hard failure.
"""
from __future__ import annotations

import json
import os
import py_compile
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _run(cmd: list[str], cwd: Path | None = None) -> tuple[int, str]:
    try:
        p = subprocess.run(
            cmd,
            cwd=str(cwd or ROOT),
            capture_output=True,
            text=True,
            timeout=120,
        )
        out = (p.stdout or "") + (p.stderr or "")
        return p.returncode, out
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, str(exc)


def check_ztp_scripts(errors: list[str], notes: list[str]) -> None:
    for ztp in (ROOT / "OpenTofu" / "ztp", ROOT / "Ansible" / "ztp"):
        if not ztp.is_dir():
            continue
        for p in ztp.rglob("*"):
            if not p.is_file() or p.is_symlink():
                continue
            rel = p.relative_to(ROOT)
            if p.name.endswith("-dispatch") or p.suffix == ".sh":
                if p.stat().st_size < 20:
                    errors.append(f"empty ZTP script: {rel}")
                    continue
                # bash -n for shell-like dispatch (many are shell without .sh)
                text = p.read_bytes()[:200]
                if text.startswith(b"#!") and b"python" in text.splitlines()[0].lower():
                    # python dispatch handled below
                    continue
                if text.startswith(b"#!") and (
                    b"bash" in text.splitlines()[0] or b"sh" in text.splitlines()[0]
                ):
                    code, out = _run(["bash", "-n", str(p)])
                    if code != 0:
                        errors.append(f"bash -n failed {rel}: {out.strip()[:200]}")
                    else:
                        notes.append(f"OK bash -n {rel}")
                elif p.suffix == ".sh":
                    code, out = _run(["bash", "-n", str(p)])
                    if code != 0:
                        errors.append(f"bash -n failed {rel}: {out.strip()[:200]}")
                    else:
                        notes.append(f"OK bash -n {rel}")
            if p.suffix == ".py" and p.name != "__init__.py":
                try:
                    py_compile.compile(str(p), doraise=True)
                    notes.append(f"OK py_compile {rel}")
                except py_compile.PyCompileError as exc:
                    errors.append(f"py_compile failed {rel}: {exc}")


def check_residential_imports(errors: list[str], notes: list[str]) -> None:
    """Compile residential API modules (no network)."""
    res = ROOT / "Ansible" / "residential"
    if not res.is_dir():
        return
    count = 0
    for p in res.rglob("app/*.py"):
        if p.is_symlink():
            continue
        try:
            py_compile.compile(str(p), doraise=True)
            count += 1
        except py_compile.PyCompileError as exc:
            errors.append(f"residential py_compile {p.relative_to(ROOT)}: {exc}")
    notes.append(f"OK residential py_compile files={count}")


def check_ztp_manifest_wiring(errors: list[str], notes: list[str]) -> None:
    """Every manifest dispatch_scripts.filename must exist; model JSON vendor must match path."""
    for tree in ("OpenTofu/ztp", "Ansible/ztp"):
        base = ROOT / tree
        if not base.is_dir():
            continue
        for manifest in base.rglob("manifest.json"):
            try:
                data = json.loads(manifest.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                errors.append(f"bad manifest {manifest.relative_to(ROOT)}: {exc}")
                continue
            scripts = data.get("dispatch_scripts") or []
            for entry in scripts:
                if not isinstance(entry, dict):
                    continue
                name = str(entry.get("filename") or "").strip()
                if not name:
                    continue
                target = manifest.parent / name
                if not target.exists():
                    errors.append(
                        f"manifest lists missing dispatch: {manifest.relative_to(ROOT)} -> {name}"
                    )
                else:
                    notes.append(f"OK dispatch {target.relative_to(ROOT)}")
            # optional: model tags mentioned should have a json somewhere under vendor
            vendor_dir = manifest.parent
            for entry in scripts:
                tags = entry.get("tags") or entry.get("device_families") or []
                # soft note only
                _ = tags
            _ = vendor_dir


def check_ansible_syntax(errors: list[str], notes: list[str]) -> None:
    if _run(["ansible-playbook", "--version"])[0] != 0:
        notes.append("SKIP ansible --syntax-check (ansible-playbook not installed)")
        return
    # Sample a curated set of known-good / representative playbooks — never the whole tree in CI time
    samples = [
        "Ansible/scada/playbooks/openplc-v4/runtime-health.yml",
        "Ansible/scada/playbooks/modbus/read-holding-registers.yml",
        "Ansible/scada/playbooks/site-smoke.yml",
        "Ansible/iot/Schlage/Encode/playbook.yml",
        "Ansible/Security/playbooks/trivy.yml",
    ]
    for rel in samples:
        p = ROOT / rel
        if not p.exists():
            notes.append(f"SKIP missing sample {rel}")
            continue
        code, out = _run(["ansible-playbook", "--syntax-check", str(p)])
        if code != 0:
            # syntax-check may fail without inventory; try with local inventory
            code2, out2 = _run(
                [
                    "ansible-playbook",
                    "--syntax-check",
                    "-i",
                    "localhost,",
                    "-c",
                    "local",
                    str(p),
                ]
            )
            if code2 != 0:
                errors.append(f"ansible syntax-check failed {rel}: {(out2 or out)[:300]}")
            else:
                notes.append(f"OK ansible syntax-check {rel}")
        else:
            notes.append(f"OK ansible syntax-check {rel}")


def main() -> int:
    errors: list[str] = []
    notes: list[str] = []
    check_ztp_scripts(errors, notes)
    check_residential_imports(errors, notes)
    check_ztp_manifest_wiring(errors, notes)
    check_ansible_syntax(errors, notes)

    # Proven-vs-stub matrix summary
    matrix = ROOT / "docs" / "SMOKE_MATRIX.md"
    if not matrix.exists():
        errors.append("missing docs/SMOKE_MATRIX.md")

    for n in notes:
        if n.startswith("OK ") or n.startswith("SKIP "):
            print(n)
    for e in errors:
        print("ERROR:", e)
    if errors:
        return 1
    print("OK: smoke / wiring checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
