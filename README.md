# TTermite v1.6.0

TTermite v1.0.0 baseline feature overview

- [Added] A standalone macOS terminal with TTermite bundle, database and Keychain namespaces; requires macOS 15 or later and stores data separately from Berth.

- [Added] Local shells run interactive commands through a PTY with configurable executable and working directory; running processes do not survive app termination.

- [Added] SSH supports passwords, private keys, agents, keyboard-interactive authentication, host-key confirmation, jump hosts, proxies, liveness checks and automatic reconnection; compatibility depends on the server and network.

- [Added] Host groups, quick connections, search, ssh_config import and local directory bookmarks organize frequently used destinations.

- [Added] Tabbed terminals provide horizontal and vertical splits, focus switching and broadcast input; broadcast sends input to multiple panes, so users must check their destinations.

- [Added] Terminal rendering supports ANSI colors, font and size selection, cursor shape and blinking, copy-on-select, middle-click paste, themes and translucent chrome; later Nerd Font bundles are not yet included.

- [Added] Terminal text search, command navigation, copying the last command output and working-directory markers are available; navigation depends on shell integration markers and the later persistent search database is absent.

- [Added] The SFTP panel browses remote directories and supports transfers, drag-and-drop and external editing; remote permissions, file formats and network conditions constrain operations.

- [Added] Saved SSH tunnels provide local, remote and dynamic forwarding; the server must permit forwarding and local ports must be available.

- [Added] Server information, resource monitoring and dashboards show host status, with a Docker panel and Wake-on-LAN support; these depend on remote tools, permissions and networking.

- [Added] Saved workspaces and session templates reopen connections, with startup tab and directory restoration settings; later complete pane and screen-snapshot restoration is not included.

- [Added] Command snippets, output-triggered actions, session logging and background-command or bell notifications automate repeated tasks; configuration and notification permissions are required.

- [Added] A command palette, keyboard shortcuts and menu-bar access offer quick navigation and common operations, with optional host reachability probes.

- [Added] Keychain stores keys and passwords, with optional Touch ID/password approval before key use, paste protection and privacy masking; users must still review commands.

- [Added] Host, group and forwarding structures can be backed up and restored; backups exclude Keychain passwords, passphrases and private keys, which must be supplied again.

- [Added] The original baseline includes iCloud synchronization settings and data models; availability depends on signing, entitlements and account state, and this ad-hoc reconstruction does not claim working cloud synchronization.

- [Added] The historical baseline includes an AI assistant, provider/model settings, questions about selected content and suggested-command workflows; a compatible service and credentials are required, and this precedes its later removal.

- [Added] The baseline contains its original English and Simplified Chinese resources, system-language selection and About/acknowledgements; complete Traditional Chinese support comes later, and inherited update checking does not authorize automatic upstream code integration.

- [Other] This is a new 2026-10-30 reconstruction of the earliest TTermite source as v1.0.0, not a relabeled binary; source, dependency and license provenance is in source-rebuild-map.json. Build checks and version policy are reconstruction infrastructure. Independent validation and publication are recorded separately; it is not notarized and does not claim live SSH, Docker, cloud, AI-service or Intel execution acceptance.

```sh
bash scripts/release.sh
```

[GPL-3.0](LICENSE) · [Source provenance](source-rebuild-map.json) · [Version policy](docs/VERSIONING.md)
