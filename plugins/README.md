# Mai Plugins

Plugin system layout, CLI, and marketplace documentation (Phase 2d).

## Directory layout (canonical)

```
plugins/
├── plugins.json          # Discovery manifest — names the plugins the loader loads at boot
├── registry.json         # MARKETPLACE catalog (registry_url + plugin entries with package_url/checksum)
├── <name>/               # CANONICAL installed-plugin layout (what the loader prefers)
│   ├── manifest.json     # Validated by PluginManifestValidator
│   └── <name>.py         # Plugin code (module imported by bare name)
├── calendar/             # Package-style plugin (__init__.py + manifest) — same rules
├── data/                 # Plugin data + lifecycle_registry.json (installed-plugin records)
├── cli.py                # Plugin manager CLI (python -m plugins.cli)
├── marketplace_client.py # Marketplace client (fetch/download/checksum/install)
├── lifecycle.py          # Install/enable/disable/uninstall lifecycle
└── plugin_manifest.py, dependency_resolver.py, sandbox.py, signing.py
```

**Dedup policy (Phase 2d):** the `<name>/<name>.py` copies are the canonical ones —
`PluginLoader.load()` prefers a directory with `manifest.json` and only falls back to a
flat `plugins/<name>.py` when no manifest dir exists. Flat copies of manifest-backed
plugins were byte-identical shadows and have been deleted. Do not re-create them;
edit the copy inside `<name>/` (or reinstall from the marketplace package).

## Plugin manager CLI

```bash
# List installed plugins (lifecycle registry: plugins/data/lifecycle_registry.json)
python -m plugins.cli --plugin-dir plugins list
python -m plugins.cli --plugin-dir plugins --json list

# Search the marketplace catalog (defaults to the remote registry; use --registry
# to point at the local file registry for offline use)
python -m plugins.cli --registry "file:///<repo>/plugins/registry.json" search weather
python -m plugins.cli --registry "file:///<repo>/plugins/registry.json" search --tag utility

# Install / enable / disable / uninstall / info
python -m plugins.cli --plugin-dir <dir> --registry "file:///<repo>/plugins/registry.json" install example_plugin
python -m plugins.cli --plugin-dir <dir> enable example_plugin
python -m plugins.cli --plugin-dir <dir> info example_plugin --json
python -m plugins.cli --plugin-dir <dir> uninstall example_plugin --purge
```

Notes:
- Parent-level flags (`--plugin-dir`, `--registry`, `--json`) must come **before**
  the subcommand.
- `install` downloads the package (file:// or https), verifies the SHA-256 checksum,
  resolves dependencies, extracts to `<plugin-dir>/<name>/`, and records it in the
  lifecycle registry.
- The default `--plugin-dir` is `~/.config/mai/plugins` (user-installed plugins);
  the bundled repo plugins live in `<repo>/plugins/` and are loaded at boot from
  `plugins.json`.

## Marketplace REST API

All mutating endpoints require auth (JWT access token from `/api/auth/login`, or the
legacy static `API_AUTH_TOKEN`). Read endpoints are open.

| Method | Path | Purpose |
|--------|------|---------|
| GET  | `/api/plugins/installed` | Installed plugins + lifecycle state |
| GET  | `/api/plugins/installed/{name}` | Installed plugin detail |
| PUT  | `/api/plugins/installed/{name}/config` | Update plugin config (auth) |
| GET  | `/api/plugins/marketplace/search?q=&tags=&category=&page=&limit=` | Search catalog |
| GET  | `/api/plugins/marketplace/{name}` | Catalog entry detail |
| POST | `/api/plugins/marketplace/install` | Install via marketplace client (auth) |
| POST | `/api/plugins/marketplace/{name}/enable` | DISCOVERED/DEACTIVATED → ACTIVATED (auth) |
| POST | `/api/plugins/marketplace/{name}/disable` | ACTIVATED → DEACTIVATED/UNLOADED (auth) |
| POST | `/api/plugins/marketplace/{name}/uninstall` | Remove plugin (auth) |
| POST | `/api/plugins/marketplace/publish` | Publish .mpkg (X-API-Key) |

When the registry file cannot be read, search/detail fall back to a built-in catalog
and log a warning — the API never fails because the catalog is offline.
