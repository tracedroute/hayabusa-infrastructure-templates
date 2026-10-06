<!-- PEREGRINE_GENERATED_IOT_README_V2 -->
# IoT Devices

Tenant-scoped Ansible workspace for Internet of Things devices.

Directory flow is:

`IoT Devices/<Make>/<Model>/playbook.yml`

Playbooks here are safe starters. They support common Ansible control paths: Home Assistant REST, direct local HTTP APIs, MQTT or protocol bridges, and vendor cloud APIs when a vendor supports them.

Keep credentials in environment variables, Ansible Vault, or Fleet secrets. Do not commit plaintext tokens or passwords.
