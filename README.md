# Hayabusa Infrastructure Templates

Default **OpenTofu** (Creation) and **Ansible** (Configuration) trees for the Hayabusa Fleet crafting console.

## Layout

```
OpenTofu/                 # Creation tab
  environments/
  modules/
  ztp/<vendor>/           # Creation-side vendor ZTP (canonical)
  …

Ansible/                  # Configuration tab
  inventory/              # single inventory home
  ztp/<vendor>/           # Configuration-side vendor ZTP (canonical)
  iot/                    # IoT vendors
  scada/                  # SCADA / PLC (includes openplc)
  residential/            # residential routers & switches (+ APIs)
  security-fire/          # security & fire systems
  Security/               # SECops playbooks
  bare-metal-ztp/         # PXE / image recipes
  playbooks/, roles/, group_vars/
```

## Vendors (ZTP)

Cisco, Arista, Aruba, Juniper, Palo Alto — plus Proxmox / VMware under Ansible ZTP where present.

## Hygiene

```bash
python3 scripts/check_iac_tree.py .              # CI / local; never mutates
python3 scripts/cleanup_iac_defaults_tree.py .   # idempotent re-canonicalize only
```

Locally (and in CI once `.github/workflows/iac-hygiene.yml` is on `main`): run `check_iac_tree.py` on every change. Forbidden nests fail the check.
Duplicate-content warnings list paths for review; they do **not** auto-delete. Working `OpenTofu/ztp` / `Ansible/ztp` mirrors are ignored as intentional pairs.

## Notes

- Do **not** nest Ansible under `OpenTofu/` or OpenTofu under `Ansible/`.
- `OpenTofu/ztp/` and `Ansible/ztp/` are an intentional Creation/Configuration pair.
  Working vendor dispatch scripts and device defaults live there — do not “dedupe”
  them away. Exact mirrors across those two roots are expected.
- Design & Deploy library snippets (`catalog.json`) are a separate surface from this
  console workspace seed.
- Controller ↔ Core defaults sync is out of scope for this repo’s hygiene CI.
