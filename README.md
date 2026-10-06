# Hayabusa Infrastructure Templates

Default **OpenTofu** and **Ansible** trees seeded into the Hayabusa Fleet crafting console (DevOps IaC workspace).

## Layout

- `OpenTofu/` — Creation / OpenTofu project root (environments, modules, ZTP helpers)
- `Ansible/` — Configuration content (playbooks, inventories, vendor ZTP, IoT, SCADA, security, residential, …)

These match what Core copies into each user/org workspace from `devops_iac_defaults` (no-clobber seed of `OpenTofu/` + `Ansible/`).

## Network / ZTP vendors

Cisco, Arista, Aruba, Juniper, Palo Alto, plus Proxmox and VMware under ZTP defaults.

## Note

The Design & Deploy **library catalog** (`catalog.json` + starter snippets) is a separate Hayabusa surface. This repository holds the **console workspace defaults**.
