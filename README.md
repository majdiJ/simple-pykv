# Simple PyKV

<img src="assets/simple-pykv-logo.png" alt="Simple PyKV logo" width="350" />

Simple, lightweight Python-based key-value storage server that exposes a small RESTful HTTP API for saving and retrieving **project-scoped** key/value pairs.

Designed for simplicity and predictable behaviour, perfect for small-to-medium projects, personal projects, internal tools, demos, or anywhere you need a tiny secure persistent or in-memory key/value store without a heavy database.

![Build](https://img.shields.io/badge/build-passing-brightgreen)
![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![License](https://img.shields.io/badge/license-Apache%202.0-lightgrey)
![GitHub stars](https://img.shields.io/github/stars/majdiJ/simple-pykv?style=social)

## Features

* Lightweight - minimal dependencies and easy to deploy.
* RESTful API - predictable HTTP endpoints for project and store management.
* Multiple project - isolated namespaces for different projects with unique API keys per project.
* Basic CRUD operations for key-value pairs.
* In-memory fast access with optional on-disk persistence per project.
* Small, explicit configuration (`config.json`) with apropriate defaults.
* Simple authentication via API keys (system-level and per-project).
* Key and value discovery controls for security.
* Metadata support for stored keys (timestamps, size, type).
* Thread-safe operations for concurrent API access.
* Multiple authentication header support (`Authorization`, `X-API-Key`, `Api-Key`).

---

## Table of contents

1. [Quickstart](#quickstart)
2. [Configuration](#configuration)
3. [Running the server](#running-the-server)
4. [Terminal logging / CUI](#terminal-logging--cui)
5. [Ensuring security](#ensuring-security)
6. [API overview](#api-overview)
7. [Examples](#examples)
8. [Client tips](#client-tips)
9. [Troubleshooting](#troubleshooting)
10. [Contributing](#contributing)
11. [License](#license)

## Additional documentation
1. [Routes](routes.md) - Detailed API reference
2. [License](LICENSE) - Full license text

---

## Quickstart

Requirements: Python 3.8+.

1. **Clone the repo**
    ```bash
    git clone https://github.com/majdiJ/simple-pykv.git
    ```

2. **Change to project directory**
    ```bash
    cd simple-pykv
    ```

3. **Install dependencies**
    ```bash
    python -m pip install -r requirements.txt
    ```
    (*Optional:* create and activate a virtual environment before installing dependencies to avoid conflicts with other Python packages.)

4. **Run the server**
    Within the `simple-pykv` directory, run:

    For windows, MacOs, or Linux:
    ```bash
    waitress-serve --listen=127.0.0.1:23849 main:app
    ```

    or, for Linux/MacOS with Gunicorn:
    ```bash
    gunicorn -w 4 -b 127.0.0.1:23849 main:app
    ```
    *Gunicorn provides better performance and is recommended for production use if using Linux or MacOS. However, if running the server for small projects, performance gains may be minimal.*

The server will start using the default configuration.

On first server run, if `config.json` is missing, a default config file will be created in the current directory (`simple-pykv`) along with a storage folder for on-disk projects.

If authentication is enabled, API keys will be generated and shown in the console. If `save_api_key_to_config` is `true`, the plaintext API keys will also be saved in `config.json`. Otherwise, they will only be shown in the console once,  **store them safely!** (Read the [Configuration](#configuration) section for details and information about API key management.)

> **Important:** Running the server without proper configuration, security settings, and API key management will expose your server to potential security risks. Please read the [Configuration](#configuration), [Running the server](#running-the-server) and [Ensuring security](#ensuring-security) sections carefully before deploying the server publicly.

### Run using docker (optional)

You can also run Simple PyKV using Docker. Make sure you have Docker installed and running.

1. **Clone the repo**
    ```bash
    git clone https://github.com/majdiJ/simple-pykv.git
    ```

2. **Change to project directory**
    ```bash
    cd simple-pykv
    ```

3. **Build the Docker image**
    ```bash
    docker build -t simple-pykv:latest .
    ```

4. **Run with a host bind mount (easy to inspect on host)**
    ```bash
    mkdir -p ./pykv_data
    ```

    ```bash
    docker run -d --name simple-pykv \
    -p 23849:23849 \
    -v "$(pwd)/pykv_data:/data" \
    simple-pykv:latest
    ```

---

## Configuration

The server is configured by a single JSON file (`config.json`). Below is a **sanitised** example.

```json
{
  "version": 1,
  "server_port": 23849,
  "server_host": "127.0.0.1",
  "system": {
    "storage": {
      "persistent_file_path": "storage_data"
    },
    "authentication": {
      "enabled": true,
      "save_api_key_to_config": true,
      "api_key": "If `save_api_key_to_config` is true, the plaintext API key will be here otherwise it will be null",
      "api_key_hash": "If `authentication.enabled` is true, the hashed API key will be here otherwise it will be null"
    },
    "security": {
      "project_discoverable": true
    }
  },
  "projects": [
    {
      "id": "first_project",
      "storage": {
        "on_disk": true
      },
      "authentication": {
        "enabled": true,
        "save_api_key_to_config": true,
        "api_key": "If `save_api_key_to_config` is true, the plaintext API key will be here otherwise it will be null",
        "api_key_hash": "If `authentication.enabled` is true, the hashed API key will be here otherwise it will be null"
      },
      "security": {
        "keys_and_values_discoverable": true
      },
      "api_key": "test"
    }
  ]
}
```
**DO NOT COMMIT REAL API KEYS TO PUBLIC REPOSITORIES!**

### Config options

Here are the main configuration options:

* `version` - What version of the config schema is being used (currently `1`).

* `server_port` - Port number to bind the HTTP server to (default `23849`).

* `server_host` - Host/IP to bind the HTTP server to (default `127.0.0.1`).

* `system.storage.persistent_file_path` - Directory path for on-disk project storage files. Recommended to keep as `storage_data`.

* `system.authentication.enabled` - Whether a system/global API key is required for administrative routes (create/delete projects, list projects, etc). Recommended to keep as `true`.

* `system.authentication.save_api_key_to_config` - Whether to save the raw system API key in plaintext in `config.json`. By default, this is `false` for security. If `false`, the generated API key will be shown once in the console on first run and never shown again  (**store it safely!**). If `true`, the API key will be saved in `config.json` under `system.authentication.api_key`.

* `system.authentication.api_key` - The system/global API key in plaintext (if `save_api_key_to_config` is `true`), otherwise `null`. You can set to your own API key, but not recommended for security. Instead, let the server generate a secure random key on first run.

* `system.authentication.api_key_hash` - The hashed system/global API key (if `authentication.enabled` is `true`), otherwise `null`. Used for verifying incoming API keys.

* `system.security.project_discoverable` - Whether `GET /api/v1/projects` can list all projects that exist. If `false`, that endpoint returns `403 Forbidden`. Useful for hiding project existence.

* `projects` - An array of project configurations. Each project has:
    * `id` - Unique project identifier string (Must be alphanumeric with underscores or hyphens, and unique id).

    * `storage.on_disk` - Whether this project's key/value store is persisted to disk (`true`) or kept in memory only (`false`) (All projects will be kept in memory while the server is running).
    
    * `authentication.enabled` - Whether this project requires an API key for access. Recommended to keep as `true` for security.
    
    * `authentication.save_api_key_to_config` - Whether to save the raw project API key in plaintext in `config.json`. By default, this is `false` for security. If `false`, the generated API key will be shown once in the console on first run and never shown again (**store it safely!**). If `true`, the API key will be saved in `config.json` under the project's `authentication.api_key`.

    * `authentication.api_key` - The project API key in plaintext (if `save_api_key_to_config` is `true`), otherwise `null`. You can set to your own API key, but not recommended for security. Instead, let the server generate a secure random key on first run.

    * `authentication.api_key_hash` - The hashed project API key (if `authentication.enabled` is `true`), otherwise `null`. Used for verifying incoming API keys.
    
    * `security.keys_and_values_discoverable` - Whether `GET /api/v1/projects/<project_id>/store` can list all keys in this project's store. If `false`, that endpoint returns `403 Forbidden`. Useful for hiding key existence.


Important config notes:

* `system.authentication.enabled` and `projects[].authentication.enabled` control whether API keys are required for system-level and project-level routes respectively. If disabled, no API key is needed for those routes. Recommended to keep authentication enabled for both for security, unless you wish to have an unsecured server/project.
* `save_api_key_to_config` options control whether plaintext API keys are saved in `config.json`. For security, it is recommended to keep these as `false` so that keys are not stored on disk.
* API keys are always hashed and stored in `api_key_hash` fields for verification, regardless of `save_api_key_to_config` settings.

---

## Running the server

1. Run the server
  
    You can run the server using a WSGI server like Gunicorn or Waitress for production use (See the [Quickstart](#quickstart) section for detailed instructions). You can also run in development mode using Flask's built-in server, but this is **NOT recommended for production** due to security and performance reasons.

    a. using Waitress (cross-platform):
    ```bash
    waitress-serve --listen=127.0.0.1:23849 main:app
    ```

    or in devlelopment mode (NOT recommended for production):

    b. using Flask's built-in server:
    ```bash
    python main.py
    ```
  
2. The server will start and use the configuration in config.json (if it exists) or create a default config if missing

3. The server listens on the configured host and port (default `127.0.0.1:23849`).

4. You can interact with the API using HTTP clients like curl, Postman, or custom scripts.

You can stop the server with `CTRL+C` in the terminal.

---

## Terminal logging / CUI
The server includes a simple Console User Interface (CUI) for logging important events and messages to the terminal.

Common tyoes if logging messages:
1. **INFO** - General informational messages about server status and operations.
2. **ERROR** - Error messages indicating problems or failures.
3. **SUCCESS** - Messages indicating successful operations.
4. **VERBOSE** - Detailed debug messages (shown only if verbose mode is enabled in config).
5. **WARNING** - Warning messages indicating potential issues.

---

## Ensuring security

Running the server as is and without additional security measures for public deployment is **NOT recommended**. Here are some tips to enhance security:

1. **Enable authentication** - Ensure `system.authentication.enabled` and `projects[].authentication.enabled` are set to `true` in `config.json` to require API keys for access (By default, authentication is enabled but double-check).
2. **Use strong API keys** - Let the server generate secure random API keys on first run. Avoid setting weak or guessable API keys manually.
3. **Restrict network access** - Use firewalls or reverse proxies to restrict access to trusted clients only.
4. **Use HTTPS** - Deploy behind a reverse proxy (e.g., Nginx) with SSL/TLS to encrypt traffic.
5. **Regularly rotate API keys** - Regenerate API keys periodically and update clients accordingly.
6. **Monitor logs** - Regularly check server logs for suspicious activity.
7. **Keep software updated** - Regularly update Python and dependencies to patch security vulnerabilities.

---

## API overview

Root paths:

* Health/status: `/status`
* API prefix: `/api/v1` (project management and store routes)

### Authentication headers supported

* `Authorization: Bearer <api-key>`
* `X-API-Key: <api-key>`
* `Api-Key: <api-key>`

### Response envelope (most endpoints)

Most endpoints return an envelope like:

```json
{
  "System": <object|null>,
  "data": <object|null>,
  "message": "<string>",
  "status_code": <int>
}
```

**Exception:** `GET /api/v1/projects/<project_id>/store/<key>/value` returns the raw stored value with no envelope (JSON or plain text).

### Status codes used

`200`, `201`, `400`, `401`, `403`, `404`, `500`.

---

## Endpoints (concise)

> See [`routes.md`](routes.md) for the full, detailed API reference (example requests/responses and troubleshooting). The README contains a compact summary for common usage.

**System / project management (system/global API key required):**

* `GET /status` — health & system info.
* `GET /api/v1/projects` — list projects (requires `project_discoverable: true`).
* `POST /api/v1/projects` — create a new project. JSON body must include `{ "id": "<project_id>" }`. Do not include `api_key`/`api_key_hash`.
* `POST /api/v1/projects/<project_id>/config/regenerate-api-key` — regenerate project API key (plaintext may be returned once).
* `DELETE /api/v1/projects/<project_id>` — delete a project and its on-disk store file.

**Project-level (project API key required when project auth enabled):**

* `GET /api/v1/projects/<project_id>` — get scrubbed project configuration.
* `PUT /api/v1/projects/<project_id>` — update project settings (rejects `id` and `authentication`).

**Store operations (project API key required when auth enabled):**

* `GET /api/v1/projects/<project_id>/store` — list keys with metadata (requires `keys_and_values_discoverable = true`).
* `PUT /api/v1/projects/<project_id>/store/<key>` — create/update a key (JSON or raw text body).
* `GET /api/v1/projects/<project_id>/store/<key>` — retrieve key with metadata.
* `GET /api/v1/projects/<project_id>/store/<key>/value` — retrieve raw value only (no envelope).
* `DELETE /api/v1/projects/<project_id>/store/<key>` — delete a key.
* `DELETE /api/v1/projects/<project_id>/store` — clear a project's store.

---

## Examples

### cURL — read raw value

```bash
curl -H "Authorization: Bearer <PROJECT_API_KEY>" \
  http://127.0.0.1:23849/api/v1/projects/first_project/store/example_key6/value
```

### Python `requests` — read raw value

```python
import requests

project = 'first_project'
key = 'example_key6'
api = '<PROJECT_API_KEY>'
url = f'http://127.0.0.1:23849/api/v1/projects/{project}/store/{key}/value'

resp = requests.get(url, headers={'Authorization': f'Bearer {api}'}, timeout=5)
if resp.status_code == 200:
    try:
        value = resp.json()
    except ValueError:
        value = resp.text
    print('value:', value)
else:
    print('error', resp.status_code, resp.text)
```

### Create a project
*(Requires system/global API key if system authentication is enabled.)*
```bash
curl -X POST http://127.0.0.1:23849/api/v1/projects \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <SYSTEM_API_KEY>" \
  -d '{"id":"my_project"}'
```

If `save_api_key_to_config` is `false` for project a plaintext API key may be returned once in `data.new_api_key`. Securely store this key as it will not be shown again.

---

## Client tips

* Always set `Content-Type: application/json` when sending JSON; the server attempts JSON parse first and preserves JSON values.
* Use the **project** API key for project-level calls and the **system/global** API key for administrative actions.
* Be prepared to handle two kinds of responses: the envelope and raw-value responses (for `GET .../store/<key>/value`).

---

## Troubleshooting / common pitfalls

* **401 Unauthorised**: check you are using the correct API key (system vs project) and header form.
* **403 Forbidden** on `GET /api/v1/projects`: check `system.security.project_discoverable`.
* **PUT /api/v1/projects/<id>** rejects `id` and `authentication` fields - update other fields only.
* **GET .../store/<key>/value** returns raw content (no envelope); handle JSON/text accordingly.
* For `500` errors consult server logs for internal messages.

---

## Contributing

Contributions are welcome! Suggested process:

1. Open an issue describing the change or bug.
2. Submit a PR against `main` with tests (where applicable) and a short description of the change.

And or contact me directly at [contact@majdij.com](mailto:contact@majdij.com) or on [majdij.com/#contact](https://majdij.com/#contact).

---

## License

This project is licensed under the Apache License 2.0. See the `LICENSE` file for details. Click [here](/LICENSE) for the full license text.
**Note:** Trademarks and logos are not included in the license.