#!/usr/bin/env python3
"""Create a new IoT vendor/device playbook from the V2 health template. Never overwrites."""
from __future__ import annotations

import argparse
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "Ansible/iot/_template/Device Class/playbook.yml"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vendor", required=True)
    ap.add_argument("--device", required=True)
    args = ap.parse_args()
    dest = ROOT / "Ansible/iot" / args.vendor / args.device / "playbook.yml"
    if dest.exists():
        print(f"exists, not overwriting: {dest}")
        return 1
    dest.parent.mkdir(parents=True, exist_ok=True)
    text = TEMPLATE.read_text()
    device_id = re.sub(r"[^a-z0-9]+", "_", f"{args.vendor}_{args.device}".lower()).strip("_")
    text = re.sub(r'iot_make: ".*?"', f'iot_make: "{args.vendor}"', text, count=1)
    text = re.sub(r'iot_model: ".*?"', f'iot_model: "{args.device}"', text, count=1)
    text = re.sub(r'iot_device_id: ".*?"', f'iot_device_id: "{device_id}"', text, count=1)
    text = re.sub(r"- name: Manage .*", f"- name: Manage {args.vendor} {args.device} IoT device", text, count=1)
    dest.write_text(text)
    (dest.parent / "README.md").write_text(
        f"# {args.device}\n\nConfiguration entry for **{args.vendor}** / {args.device}.\n"
    )
    print(f"created {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
