# Simple PyKV — API Reference (v1)

**Purpose:** A single markdown file used to provide references for the Simple PyKV HTTP API. It describes every route, requirements, example requests, example responses (success and common errors), useful notes, and common pitfalls.

> Root paths:
>
> * Health/status: `/status`
> * API prefix: `/api/v1` (all project management routes)

---

## Table of contents

1. [Global notes](#global-notes)
2. [`GET /status`](#get-status)
3. [`GET /api/v1/projects`](#get-apiv1projects)
4. [`POST /api/v1/projects`](#post-apiv1projects)
5. [`POST /api/v1/projects/<project_id>/config/regenerate-api-key`](#post-apiv1projectsproject_idconfigregenerate-api-key)
6. [`DELETE /api/v1/projects/<project_id>`](#delete-apiv1projectsproject_id)
7. [`GET /api/v1/projects/<project_id>`](#get-apiv1projectsproject_id)
8. [`PUT /api/v1/projects/<project_id>`](#put-apiv1projectsproject_id)
9. [`GET /api/v1/projects/<project_id>/store`](#get-apiv1projectsproject_idstore)
10. [`PUT /api/v1/projects/<project_id>/store/<key>`](#put-apiv1projectsproject_idstorekey)
11. [`GET /api/v1/projects/<project_id>/store/<key>`](#get-apiv1projectsproject_idstorekey)
12. [`GET /api/v1/projects/<project_id>/store/<key>/value`](#get-apiv1projectsproject_idstorekeyvalue)
13. [`DELETE /api/v1/projects/<project_id>/store/<key>`](#delete-apiv1projectsproject_idstorekey)
14. [`DELETE /api/v1/projects/<project_id>/store`](#delete-apiv1projectsproject_idstore)
15. [Example `config.json`](#example-configjson)
16. [Client snippets & recommendations](#client-snippets--recommendations)
17. [Common pitfalls & troubleshooting checklist](#common-pitfalls--troubleshooting)

---

## Global notes

* **Authentication headers supported**:

  * `Authorization: Bearer <api-key>`
  * `X-API-Key: <api-key>`
  * `Api-Key: <api-key>`

* **Envelope format (most endpoints)** — successful and error responses (except the *raw value* endpoint) use the `create_response` envelope:

```json
{
  "System": { /* optional system info object or null */ },
  "data": <object | null>,
  "message": "<string>",
  "status_code": <int>
}
```

* **Status codes used**: `200`, `201`, `400`, `401`, `403`, `404`, `500`.
* **Important:** do **not** send `api_key` or `api_key_hash` in project create/update payloads - the server will either ignore or reject them.
* **Key storage behavior**:

  * When writing values (`PUT /projects/<project>/store/<key>`) the server stores timestamps and size metadata.
  * Values stored as JSON (sent with `Content-Type: application/json`) will be preserved and returned as JSON where possible.
  * If JSON parsing fails/absent, the raw request body will be stored as a plain string.
* **One-time-returned plaintext API key**: If `save_api_key_to_config` is `false`, a plaintext API key may be returned once by project creation/regeneration. **Save it immediately** — it may not be shown again.

---

## GET /status

* **Name / short description / use**: Health/status endpoint — returns system info and server status.
* **Requirements**: Requires system-level API key if `system.authentication.enabled` is `true`.

### Example request

```bash
curl -H "Authorization: Bearer <SYSTEM_API_KEY>" http://0.0.0.0:23849/status
```

### Example successful response (200)

```json
{
  "System": {
    "memory_usage_bytes": 43057152,
    "number_of_projects": 3,
    "storage_usage_bytes": 858,
    "uptime": 38,
    "version": "0.0.0 (Beta)"
  },
  "data": null,
  "message": "Simple PyKV server is fully operational.",
  "status_code": 200
}
```

### Example unauthorized (401)

```json
{
  "System": null,
  "data": null,
  "message": "Invalid or missing API key",
  "status_code": 401
}
```

### Notes / what not to do

* Do not call without the system API key when system auth is enabled.
* Good for readiness/liveness probes in orchestration.

---

## GET /api/v1/projects

* **Name / short description / use**: List all projects and scrubbed configs.
* **Requirements**:

  * Requires **system/global** API key.
  * `system.security.project_discoverable` must be `true` in `config.json`.

### Example request

```bash
curl -H "X-API-Key: <SYSTEM_API_KEY>" http://0.0.0.0:23849/api/v1/projects
```

### Example successful response (200) — abridged

```json
{
  "System": { "memory_usage_bytes": 43057152, "number_of_projects": 3, "version": "0.0.0 (Beta)" },
  "data": {
    "New_project": {
      "authentication": { "enabled": true, "save_api_key_to_config": false },
      "security": { "keys_and_values_discoverable": true },
      "storage": { "on_disk": true }
    },
    "first_project": { /* ... */ }
  },
  "message": "Project listing fetched successfully",
  "status_code": 200
}
```

### Discoverability disabled (403)

```json
{
  "System": { /* ... */ },
  "data": null,
  "message": "Project listing is disabled",
  "status_code": 403
}
```

### Errors / what not to do

* `401` — missing/invalid system API key.
* `403` — `project_discoverable` is `false`.

### Notes

* Returned project configs are run through `scrub_secrets()` so api keys/hashes are scrubbed.
* The top-level keys of `data` are `project_id` values; the inner `id` field is removed.

---

## POST /api/v1/projects

* **Name / short description / use**: Create a new project. Server generates stores/hashes API key server-side.
* **Requirements**:

  * Requires **system/global** API key.
  * Request body must be valid JSON and include at minimum: `{ "id": "<project_id>" }`.
  * Do not include `api_key` or `api_key_hash` in the body.

### Example request

```bash
curl -X POST http://0.0.0.0:23849/api/v1/projects \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <SYSTEM_API_KEY>" \
  -d '{"id":"New_project3"}'
```

### Example successful response (201) — key returned

```json
{
  "System": { /* ... */ },
  "data": { "new_api_key": "Pigv880NVfH_LfkxQPr-df1_tFuJVFjXcYwUVq6wm4o" },
  "message": "Project created successfully. Store the returned API key securely as it may not be shown again.",
  "status_code": 201
}
```

### Example successful response (201) — no key returned

```json
{
  "System": { /* ... */ },
  "data": null,
  "message": "Project created successfully. No API key generated (authentication for this project may be disabled).",
  "status_code": 201
}
```

### Errors

* `400` — invalid JSON, missing `id`, duplicate id.
* `401` — missing/invalid system API key.
* `500` — internal error.

### Notes

* If `save_api_key_to_config` is `false`, the API key may be returned once in `data.new_api_key`. **Store it immediately.**
* The payload can contain `storage`, `security`, and `authentication` sections (except the `api_key`/`api_key_hash`), e.g.:

```json
{
  "id": "myproject",
  "storage": { "on_disk": true },
  "authentication": { "enabled": true, "save_api_key_to_config": false },
  "security": { "keys_and_values_discoverable": true }
}
```

---

## POST /api/v1/projects/<project_id>/config/regenerate-api-key

* **Name / short description / use**: Regenerate the project's API key and return plaintext when generated.
* **Requirements**: Requires **system/global** API key. No request body.

### Example request

```bash
curl -X POST -H "Authorization: Bearer <SYSTEM_API_KEY>" \
  http://0.0.0.0:23849/api/v1/projects/New_project2/config/regenerate-api-key
```

### Example successful response (200)

```json
{
  "System": { /* ... */ },
  "data": { "new_api_key": "-TCHeO-yL5vvyJQT0zlHBVLrOzE9hLz-IK-9rHp90-A" },
  "message": "API key regenerated successfully for project 'New_project2'",
  "status_code": 200
}
```

### Errors

* `401` — missing/invalid system API key.
* `404` — project not found.
* `500` — regeneration failed (e.g., authentication disabled for that project) or internal error.

### Notes

* If project authentication is disabled, regeneration may fail with a `500` and helpful message.
* Save the returned key immediately if present.

---

## DELETE /api/v1/projects/<project_id>

* **Name / short description / use**: Delete a project and its store file.
* **Requirements**: Requires **system/global** API key.

### Example request

```bash
curl -X DELETE -H "X-API-Key: <SYSTEM_API_KEY>" \
  http://0.0.0.0:23849/api/v1/projects/New_project3
```

### Example successful response (200)

```json
{
  "System": { /* ... */ },
  "data": null,
  "message": "Project 'New_project3' deleted successfully",
  "status_code": 200
}
```

### Errors

* `401` — missing/invalid system API key.
* `404` — project not found.
* `500` — internal error while deleting.

### Notes

* Deletion will remove project config and delete the on-disk store file if present.
* After deletion the project’s API key (if any) is invalid.

---

## GET /api/v1/projects/<project_id>

* **Name / short description / use**: Retrieve one project's scrubbed configuration.
* **Requirements**: Requires the **project** API key when the project has authentication enabled.

### Example request

```bash
curl -H "Authorization: Bearer <PROJECT_API_KEY>" \
  http://0.0.0.0:23849/api/v1/projects/first_project
```

### Example successful response (200)

```json
{
  "System": { /* ... */ },
  "data": {
    "authentication": { "enabled": true, "save_api_key_to_config": true },
    "id": "first_project",
    "security": { "keys_and_values_discoverable": true },
    "storage": { "on_disk": true }
  },
  "message": "Project 'first_project' details fetched successfully",
  "status_code": 200
}
```

### Errors

* `401` — missing/invalid project API key.
* `404` — project not found.
* `500` — internal error.

### Notes

* The result is scrubbed (no `api_key`/`api_key_hash`).

---

## PUT /api/v1/projects/<project_id>

* **Name / short description / use**: Update project settings (excluding authentication and id).
* **Requirements**:

  * Requires project API key when project authentication is enabled.
  * Body must be valid JSON.
  * `authentication` and `id` fields are rejected.

### Example request

```bash
curl -X PUT http://0.0.0.0:23849/api/v1/projects/first_project \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <PROJECT_API_KEY>" \
  -d '{"storage": {"on_disk": true}}'
```

### Example successful response (200)

```json
{
  "System": null,
  "data": null,
  "message": "Project 'first_project' updated successfully",
  "status_code": 200
}
```

### Errors

* `400` — invalid JSON, or if payload contains `id` or `authentication`.

  * Example when `id` provided:

    ```json
    {"message":"Updating project ID via this route is not allowed.","status_code":400}
    ```
  * Example when `authentication` provided:

    ```json
    {"message":"Updating authentication settings via this route is not allowed. Use the regenerate API key route instead.","status_code":400}
    ```
* `401` — missing/invalid project API key.
* `404` — project not found.
* `500` — internal error.

### Notes

* Use `POST /projects/<project_id>/config/regenerate-api-key` to change API keys.
* `config_instance.update_project_config(project_id, payload)` will be called with the incoming payload after validation.

---

## GET /api/v1/projects/<project_id>/store

* **Name / short description / use**: List all key/value pairs and metadata for a project.
* **Requirements**:

  * Requires project API key when project authentication is enabled.
  * Project config must have `security.keys_and_values_discoverable: true`.

### Example request

```bash
curl -H "X-API-Key: <PROJECT_API_KEY>" \
  http://0.0.0.0:23849/api/v1/projects/first_project/store
```

### Example successful response (200) — abridged

```json
{
  "System": null,
  "data": {
    "example_key3": { "created_at": 1764992220, "size_bytes": 4, "updated_at": 1764992286, "value": "test" },
    "example_key6": { "created_at": 1764992680, "size_bytes": 79, "updated_at": 1765075342, "value": { /* json */ } }
  },
  "message": "",
  "status_code": 200
}
```

### Errors

* `401` — missing/invalid project API key.
* `403` — discoverability disabled for project.
* `404` — project not found.
* `500` — internal error.

### Notes

* Values keep their original format where possible (JSON vs string).
* If discoverability disabled, response is `403` with message: "Retrieving all keys and values is disabled for this project".

---

## PUT /api/v1/projects/<project_id>/store/<key>

* **Name / short description / use**: Create or update a key/value in project store.
* **Requirements**:

  * Requires project API key when project authentication is enabled.
  * Accepts JSON body (preferred) with `Content-Type: application/json` or plain text body. If JSON parsing returns `None`, server uses raw body.

### Example request (JSON value)

```bash
curl -X PUT http://0.0.0.0:23849/api/v1/projects/first_project/store/example_key6 \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <PROJECT_API_KEY>" \
  -d '{"example":{"data":"Hellow world!","wow":"Wow! signal NASA"},"super_cool":true}'
```

### Example request (plain-text value)

```bash
curl -X PUT http://0.0.0.0:23849/api/v1/projects/first_project/store/example_key3 \
  -H "Authorization: Bearer <PROJECT_API_KEY>" \
  --data "test"
```

### Example successful response (200)

```json
{
  "System": { /* ... */ },
  "data": null,
  "message": "Key 'example_key6' set successfully in project 'first_project' store",
  "status_code": 200
}
```

### Errors

* `400` — body missing (neither JSON nor non-empty plain text).
* `401` — missing/invalid project API key.
* `404` — project not found.
* `500` — internal error.

### Notes

* Server stores metadata such as `created_at`, `updated_at`, and `size_bytes`.
* For JSON use `Content-Type: application/json` to preserve structured data.

---

## GET /api/v1/projects/<project_id>/store/<key>

* **Name / short description / use**: Retrieve a key's value with metadata.
* **Requirements**: Requires project API key when project authentication is enabled.

### Example request

```bash
curl -H "Api-Key: <PROJECT_API_KEY>" \
  http://0.0.0.0:23849/api/v1/projects/first_project/store/example_key6
```

### Example successful response (200)

```json
{
  "System": { /* ... */ },
  "data": {
    "created_at": 1764992680,
    "size_bytes": 79,
    "updated_at": 1765075342,
    "value": {
      "example": { "data": "Hellow world!", "wow": "Wow! signal NASA" },
      "super_cool": true
    }
  },
  "message": "Key 'example_key6' fetched successfully from project 'first_project' store",
  "status_code": 200
}
```

### Errors

* `401` — missing/invalid project API key.
* `404` — project not found or key not found.
* `500` — internal error.

---

## GET /api/v1/projects/<project_id>/store/<key>/value

* **Name / short description / use**: Retrieve only the raw stored value (no envelope, no metadata).
* **Requirements**: Requires project API key when project authentication is enabled.

### Example request

```bash
curl -H "Api-Key: <PROJECT_API_KEY>" \
  http://0.0.0.0:23849/api/v1/projects/first_project/store/example_key6/value
```

### Example successful response (raw JSON)

```json
{
  "example": { "data": "Hellow world!", "wow": "Wow! signal NASA" },
  "super_cool": true
}
```

### Errors

* `401` — missing/invalid project API key.
* `404` — project or key not found.
* `500` — internal error.

### Important notes

* This endpoint returns **raw content** (no standard envelope). Client must be prepared to parse JSON or text directly.

---

## DELETE /api/v1/projects/<project_id>/store/<key>

* **Name / short description / use**: Delete a single key from a project's store.
* **Requirements**: Requires project API key when authentication is enabled.

### Example request

```bash
curl -X DELETE -H "X-API-Key: <PROJECT_API_KEY>" \
  http://0.0.0.0:23849/api/v1/projects/first_project/store/example_key3
```

### Example successful response (200)

```json
{
  "System": null,
  "data": null,
  "message": "Key 'example_key3' deleted successfully from project 'first_project' store",
  "status_code": 200
}
```

### Errors

* `401` — missing/invalid project API key.
* `404` — project or key not found.
* `500` — internal error.

---

## DELETE /api/v1/projects/<project_id>/store

* **Name / short description / use**: Delete all key/value pairs for a project (clear store).
* **Requirements**: Requires project API key when authentication is enabled.

### Example request

```bash
curl -X DELETE -H "Authorization: Bearer <PROJECT_API_KEY>" \
  http://0.0.0.0:23849/api/v1/projects/first_project/store
```

### Example successful response (200)

```json
{
  "System": null,
  "data": null,
  "message": "All key-value pairs deleted successfully from project 'first_project' store",
  "status_code": 200
}
```

### Errors

* `401` — missing/invalid project API key.
* `404` — project not found.
* `500` — internal error.

### Notes

* This operation clears the project's store file on disk (if on-disk storage is used).

---

## Example `config.json`

Use this to seed a running instance for testing. Remove plaintext API keys in production; keep only hashes where desired.

```json
{
  "version": 1,
  "server_port": 23849,
  "server_host": "0.0.0.0",
  "system": {
    "storage": { "persistent_file_path": "storage_data" },
    "authentication": {
      "enabled": true,
      "save_api_key_to_config": true,
      "api_key": "UlFjO27ZBHiZoeeTdBBPsRqz0rnYUeltW3PtC_QOtFE",
      "api_key_hash": "pbkdf2_sha256$200000$0qAVJ8kOh22lhJOA2PGpGA$ldIsEwBQOFLRt_uRElpUX_1tjXARvDN72sbP7hKHcag"
    },
    "security": { "project_discoverable": true }
  },
  "projects": [
    {
      "id": "first_project",
      "storage": { "on_disk": true },
      "authentication": {
        "enabled": true,
        "save_api_key_to_config": true,
        "api_key": "1EmoHoumfnJ62-OaYCPxmpoHEv4t9fjWOlJURnZu-Kw",
        "api_key_hash": "pbkdf2_sha256$200000$CqDlbUPkgvU-Y6u36_oVBQ$-0Pxe7veNGVVq8x1x8DQGZ3q-ZDVZd7X_np10s3o70E"
      },
      "security": { "keys_and_values_discoverable": true }
    }
  ]
}
```

---

## Client snippets & recommendations

### Python `requests` (example: read raw value)

```python
import requests

project = 'first_project'
key = 'example_key6'
api = '1EmoHoumfnJ62-OaYCPxmpoHEv4t9fjWOlJURnZu-Kw'
url = f'http://0.0.0.0:23849/api/v1/projects/{project}/store/{key}/value'

resp = requests.get(url, headers={'Authorization': f'Bearer {api}'}, timeout=5)
if resp.status_code == 200:
    # endpoint returns raw JSON or text depending on stored value
    try:
        value = resp.json()
    except ValueError:
        value = resp.text
    print('value:', value)
else:
    print('error', resp.status_code, resp.text)
```

### cURL tips

* Always set `Content-Type: application/json` when sending JSON. The server will attempt JSON parse first.
* For project-level calls use the project API key; for administrative actions use the system API key.

### Postman / Insomnia

* Import these routes and add two environments: `system_api_key` and `project_api_key` for quick switching.

---

## Common pitfalls & troubleshooting checklist

* **401**: check that you are sending the right API key (project vs system) and header name. `extract_api_key()` supports three header forms.
* **403** on `GET /projects`: check `system.security.project_discoverable` in `config.json`.
* **When creating projects**: do not expect `api_key` to be saved in `config.json` if `save_api_key_to_config` is `false` — copy the returned key.
* **PUT /projects/<id>**: will reject `id` and `authentication` fields — update only allowed parts.
* **GET .../store/<key>/value**: returns raw content (no envelope) — handle accordingly.
* **Internal errors (500)**: review server logs; `verify_authentication()` logs helpful internal messages in edge cases (e.g. authentication enabled but no api key configured).

---

## Next steps & suggestions

* Convert this document to an OpenAPI v3 YAML if you want autogenerated client SDKs / interactive docs.
* Add example Postman collection and a small test-suite (pytest) that validates the happy-path for each route.

---

*End of document.*
