# Offline-Capable PyPI Caching Proxy (PEP 503)

PythonDepot ships a standalone FastAPI proxy that fronts the PyPI simple index with a persistent SQLite-backed cache. Point `pip` at it once and every `pip install` is served through the cache: the first request proxies upstream PyPI and stores the result, every later request is served from cache — even with the network disconnected (air-gapped / offline installs). The proxy speaks the [PEP 503](https://peps.python.org/pep-0503/) simple-index protocol, so it works with `pip`, `uv`, and any other client that understands `--index-url`.

```mermaid
flowchart LR
    P[pip / uv / any PEP 503 client] --> S[GET /simple/{package}/]
    S --> C{PyPICacheService}
    C -->|hit| DB[(SQLite version lists)]
    C -->|miss + online| U[pypi.org]
    U --> C
    C --> A[GET /simple/{package}/{file}]
    A --> D[ArtifactStore<br/>disk cache]
    D -->|miss + online| F[files.pythonhosted.org]
    D --> C2[analytics counters<br/>hit rate / bytes]
```

- **PEP 503 simple index** — `GET /simple/{package}/` returns the same link HTML pip expects; links are rewritten to the proxy's own artifact endpoint so downloads flow through the cache and stay installable offline.
- **Artifact caching** — wheel/sdist bytes are stored on disk (with SQLite metadata) and served with zero upstream traffic on a hit.
- **Offline mode** — `PYTHONDEPOT_OFFLINE_MODE=1` makes the proxy cache-only: it never touches the network and answers `503` for anything not cached.
- **Warm-up** — prefetch popular packages ahead of time via `POST /api/v1/cache/warmup` or the programmatic warm-up CLI, so a cold or air-gapped proxy is ready on first use.
- **Analytics** — `GET /api/v1/cache/analytics` reports hit rate and bytes served vs proxied, per package.

---

## Running the proxy

The proxy is a standalone app, independent from the main PythonDepot API:

```bash
uvicorn python_depot.routers.pep503:create_proxy_app --factory --port 8765
```

Startup creates the cache tables (`init_db()`); no other configuration is required. The proxy shares the repo-wide SQLite database (`PYTHON_DEPOT_DATABASE_URL`, default `sqlite:////tmp/python_depot.db`).

> The production app factory `create_app()` deliberately does **not** mount the proxy routers (`tests/test_pre_dev_contract.py` pins the full app route set). Deployments that want the proxy on the main app should include `pep503.router` and `pep503.artifact_router` explicitly.

---

## Quickstart — install through the proxy

```bash
# 1. Start the proxy (port 8765 in this example)
uvicorn python_depot.routers.pep503:create_proxy_app --factory --port 8765

# 2. Point pip at it (in another terminal)
pip config set global.index-url http://127.0.0.1:8765/simple/
pip config set global.trusted-host 127.0.0.1

# 3. Install — first run proxies + caches, later runs are served from cache
pip install requests
```

Because the proxy listens on plain `http`, pip must trust the host (`--trusted-host 127.0.0.1` on the command line, or the `global.trusted-host` config above). The equivalent one-shot command is:

```bash
pip install --index-url http://127.0.0.1:8765/simple/ --trusted-host 127.0.0.1 requests
```

Verified end-to-end with a real `pip install "requests==2.32.4"` through the proxy while the proxy was in offline mode — installed entirely from cache.

---

## Offline / air-gapped usage

The proxy supports cache-only operation for networks with no PyPI access. Start it with:

```bash
PYTHONDEPOT_OFFLINE_MODE=1 uvicorn python_depot.routers.pep503:create_proxy_app --factory --port 8765
```

In offline mode the proxy **never opens an upstream connection**:

- Cached packages → served from cache (`200`).
- Cached artifacts → served from cache (`200`).
- Anything not cached → `503` with a descriptive JSON detail:

```json
{"detail": "cache miss: package not cached and upstream unreachable (offline mode)"}
```

### Building an offline cache

1. On a machine with network access, run the proxy and warm it up (see below) for the packages your project needs.
2. Stop the proxy.
3. Copy the SQLite database (the `PYTHON_DEPOT_DATABASE_URL` file, default `/tmp/python_depot.db`) and the cache directory (`PYTHONDEPOT_CACHE_DIR`, default `.pypi_cache/`) to the air-gapped host.
4. Start the proxy there with `PYTHONDEPOT_OFFLINE_MODE=1`.

Installs on the isolated host are then served entirely from the transported cache. Entries that went stale during transport are *not* refetched in offline mode — they are treated as misses and answered with `503` (the fallback never silently degrades to the public internet).

---

## Cache warm-up

### API — `POST /api/v1/cache/warmup`

Prefetches the top-N packages from the seed corpus, or an explicit package list. Failures are recorded, never raised — a partially successful warm-up still returns a useful result.

**Example request (explicit list):**

```bash
curl -X POST http://127.0.0.1:8765/api/v1/cache/warmup \
  -H "Content-Type: application/json" \
  -d '{"packages": ["six"]}'
```

**Example response:**

```json
{"requested": 1, "cached": 1, "failed": []}
```

**Example request (top-N from the seed corpus):**

```bash
curl -X POST http://127.0.0.1:8765/api/v1/cache/warmup \
  -H "Content-Type: application/json" \
  -d '{"top_n": 3}'
```

**Example response:**

```json
{"requested": 3, "cached": 3, "failed": []}
```

**Request fields:**

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `top_n` | int | `10` | Prefetch the first N packages of the seed corpus (1–1000). The shipped seed corpus is `requests`, `numpy`, `pandas`, so `top_n` beyond 3 prefetches at most those 3. |
| `packages` | array of strings | `null` | Explicit package list; takes precedence over `top_n` when both are present. |

**Response fields:**

| Field | Type | Description |
|-------|------|-------------|
| `requested` | int | Number of packages requested |
| `cached` | int | Number successfully cached |
| `failed` | array of strings | Package names that could not be cached (upstream unreachable, etc.) |

### CLI — `python-depot-cache-warmup`

The same prefetch is available from the command line. The package installs a `python-depot-cache-warmup` console script:

```bash
python-depot-cache-warmup --top 10
```

It can also be run as a module (useful without installation):

```bash
python -m python_depot.warmup --top 10
```

The CLI initializes the cache tables itself on startup, so it works standalone against a fresh database — no separate `init_db()` step is needed. `main()` returns `0` when at least one package was cached (partial success counts) and `1` when nothing was cached, so automation can detect a failed warm-up; the console script and module invocation exit with that code. Programmatic use:

```python
from python_depot.warmup import main

raise SystemExit(main(["--top", "10"]))
```

`WarmupService` also accepts a richer corpus (`WarmupService(top_packages=[...])`) than the shipped 3-package seed.

---

## Cache analytics

### GET `/api/v1/cache/analytics`

Returns hit rate, bytes served vs proxied, and per-package counters in a single query.

**Example request:**

```bash
curl http://127.0.0.1:8765/api/v1/cache/analytics
```

**Example response** (real output after one proxied fetch + one cache hit + one artifact download, truncated `per_package.versions`):

```json
{
  "hit_rate": 0.42857142857142855,
  "bytes_served": 64847,
  "bytes_proxied": 64847,
  "per_package": {
    "requests": {
      "hits": 3,
      "misses": 1,
      "bytes_served": 64847,
      "bytes_proxied": 64847,
      "versions": ["0.10.0", "0.10.1", "2.32.4"]
    }
  }
}
```

**Response fields:**

| Field | Type | Description |
|-------|------|-------------|
| `hit_rate` | float | `hits / (hits + misses)` across all packages; `0.0` when there is no traffic yet |
| `bytes_served` | int | Total artifact bytes served from cache |
| `bytes_proxied` | int | Total artifact bytes proxied from upstream |
| `per_package` | object | Keyed by PEP 503-normalized package name; each value has `hits`, `misses`, `bytes_served`, `bytes_proxied`, and the cached `versions` list |

---

## Security notes

The proxy is **not an open proxy** — it can only ever fetch from PyPI itself:

- **Host allowlist** — `validate_upstream_url()` accepts only `http`/`https` URLs whose hostname is exactly `pypi.org`, `pypi.python.org`, or `files.pythonhosted.org` (no subdomain or trailing-dot tricks). Every upstream URL is built from the pinned `PYPI_SIMPLE_URL` template or the persisted link map, then validated against this allowlist.
- **IP-range SSRF check (defense in depth)** — before any network fetch, the repo-wide `python_depot.api.validate_url()` IP-range check runs as well; a URL passing the host allowlist but resolving to a private/loopback/link-local IP is refused.
- **Artifact path-traversal guards** — artifact filenames are sanitized (`_safe_relative`), so a crafted `GET /simple/{package}/{filename}` cannot escape the cache directory.
- **Reflected/stored XSS guard** — every value interpolated into the simple-index HTML (package names, filenames) is HTML-escaped.
- **Deployment** — the proxy has no authentication. Bind it to a private interface or put it behind a firewall / VPN in production; do not expose it on a public IP.

---

## Configuration

| Setting | Env var | Default | Description |
|---------|---------|---------|-------------|
| Cache directory | `PYTHONDEPOT_CACHE_DIR` | `.pypi_cache` | Root for artifact bytes on disk (stored under `artifacts/<package>/`) |
| Entry TTL | `PYTHONDEPOT_CACHE_TTL` | `300` | Seconds a simple-index version list is considered fresh before refetch |
| Max cache size | `PYTHONDEPOT_CACHE_MAX_BYTES` | `5368709120` (5 GiB) | Size cap for the on-disk artifact store |
| Offline mode | `PYTHONDEPOT_OFFLINE_MODE` | unset | `1`, `true` or `yes` enables cache-only fallback (never touches the network) |
| Database | `PYTHON_DEPOT_DATABASE_URL` | `sqlite:////tmp/python_depot.db` | Shared SQLite DB holding version lists, artifact metadata, and analytics counters |

## Modules

### PyPICacheService

`python_depot.pep503_cache.PyPICacheService` — the caching proxy core: serves cached version lists on a hit, proxies upstream PyPI on a miss, persists the fetched list, applies the per-entry TTL, and tracks analytics counters.

| Method | Description |
|--------|-------------|
| `get_simple_index(package)` | Cached version list, or proxy upstream and persist; raises `CacheMissError` in offline mode when uncached |
| `fetch_upstream_index(package)` | Raw upstream simple-index HTML (SSRF-guarded); wraps all transport/status failures in `CacheMissError` |
| `get_artifact(package, filename)` | Cached wheel/sdist bytes, or `None` |
| `fetch_artifact(package, filename)` | Proxy a missing artifact from upstream, store it, return bytes (or `None`) |
| `get_cached_versions(package)` / `is_cached(package)` | Cached version-list introspection |
| `set_offline_mode(offline)` / `is_offline_mode()` | Toggle / read cache-only fallback |
| `hit_rate()` / `bytes_served()` / `bytes_proxied()` | Aggregate analytics accessors |
| `package_stats(package)` / `overall_stats()` | Per-package / single-query aggregate stats (the analytics endpoint) |

### CacheConfig

`python_depot.pep503_cache.CacheConfig` — dataclass of cache knobs; every default is overridable via the `PYTHONDEPOT_*` env vars in the configuration table above.

### ArtifactStore

`python_depot.artifact_store.ArtifactStore` — on-disk wheel/sdist storage with size/TTL caps and path-traversal guards; lazily created by `PyPICacheService` (keeps tests side-effect free).

### WarmupService

`python_depot.warmup.WarmupService` — prefetches top-N packages (or an explicit list) through the cache; failures are recorded in `WarmupResult.failed`, never raised. `TOP_PACKAGES` is the shipped seed corpus (`requests`, `numpy`, `pandas`).

### Cache miss semantics

- Online + uncached → proxy upstream, persist, serve (`200`).
- Offline + cached → serve from cache (`200`), bump the hit counter.
- Offline + uncached → `503` (`CacheMissError`); the DB session is rolled back so a failed fetch never leaves a pending row behind.
