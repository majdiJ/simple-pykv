# Simple PyKV | Project Documentation
Simple PyKV will be a lightweight Python-based key-value storage server designed to facilitate the saving and retrieval of project-specific data through a RESTful HTTP API.

## Project Overview
The goal of Simple PyKV is to provide an easy-to-setup and maintain solution for managing key-value pairs without the complexity of a full database system. It is intended for small to medium-sized projects that need a straightforward way to handle data storage.

## Feature requirements
- Must be accessible via a RESTful HTTP API.
- Have different storage namespaces for different projects so there can multiple projects using the same server without data collision.
- Support in-memory storage for fast access, with an option to persist data to disk.
- Minimal dependencies to ensure lightweight deployment.
- Simple and intuitive API design for ease of use.
- Ability to handle basic CRUD operations (Create, Read, Update, Delete) for key-value pairs.
- Must use API keys or tokens for basic authentication and access control of overall system and per project. 
- config.json file to manage server settings such as port number, persistence options (global or per project), and authentication settings.

## Questions to address
- How will data persistence be handled? Will it use flat files, SQLite, or another method?
- How will per-project configuration be managed?:
    - How will projects be created and deleted? - via API or config file, or both?
    - How will project-specific settings (like persistence options) be defined and stored? - in config file or via API?
- What authentication mechanism will be implemented to secure access to the API? And for per-project access control?
- How will error handling and logging be implemented to ensure reliability and ease of debugging?

## Configuration File Design
I'm thinkng that maybe the user firrst runs the python program, it will create a default config.json file with settings such as:
```json
{
    "version": 1,
    "server_port": 23849,
    "default": {
        "storage": {
            "persistent_file_path": "storage_data/"
        },
        "authentication": {
            "enabled": true,
            "save_api_key_to_file": false,
            "api_key": null,
            "api_key_hash": "[Will be generated and stored here if api_key is null during first run]"
        },
    },
    "projects": [
        {
            "id": "first_project",
            "storage": {
                "on_disk": true,
                "cache_in_memory": true
            },
            "authentication": {
                "enabled": true,
                "save_api_key_to_file": false,
                "api_key": null,
                "api_key_hash": "[Will be generated and stored here if api_key is null during first run]"
            }
        }
    ]
}
```

When the program is first run, it will create the config.json file if it does not exist. The file includes a top-level "version" and a global API key (stored in `default.authentication.api_key`) that will be used to create/delete projects and manage global settings. The generated config will also include a default project in the `projects` array (example id: "first_project") with its own settings.

Projects can be created either via the API using the global API key for authentication, or by manually editing the config file and restarting the server. Authentication can be enabled or disabled globally (under `default.authentication.enabled`) and per project (under each project’s `authentication.enabled`).

Each project will have its own API key (the `api_key` field inside the project object) if authentication is enabled. By default API keys are `null` and `save_api_key_to_file` is `false` for security, so keys will not be written into the config file unless you change `save_api_key_to_file` to `true` (either in `default.authentication` or in a project’s `authentication`). If you enable key saving, the keys will be stored in plain text in the config file under each `api_key` field. `api_key_hash` will always store the hashed version of the key for verification purposes. Even if `save_api_key_to_file` is `false`, the generated API keys will be printed to the console when the server starts for the first time or when a new project is created. The hash will update automatically whenever the `api_key` field is changed.

For data persistence/storage, the global setting `default.storage.persistent_file_path` defines where on disk persistent data files are stored. Each project that has `on_disk` set to `true` will have its own file in that directory named after the project id (for example: `first_project.json`) where key-value pairs are stored in a simple format (JSON or plain text). Projects with `cache_in_memory` set to `true` will also keep an in-memory copy for faster access and will sync to disk as needed. If a project has `on_disk` set to `false`, all data is kept in memory only and will be lost when the server stops.

`server_port` defines what port the HTTP server listens on. Each project’s `id` is the project identifier used for filenames and API paths.

## API Design

The API will follow RESTful principles using GET, POST, PUT, and DELETE methods. 

base URL: `http://<server_address>:<server_port>/api/v1/`

### Endpoints

### General
- `GET /status`  
  - Check server status.  
  - Response: `200` with `{"status":"running"}`.  
  - Errors: `500` if server has issues.

#### Global Project Management (requires **system/global** API key)
- `GET /projects`  
  - List all projects and their configurations (API keys & API key hashes are scrubbed).  
  - Requires system authentication (configured at `system.authentication` in config).  
  - Requires `system.security.project_discoverable` to be `true` — otherwise returns `403`.  
  - Response: JSON object where top-level keys are `project_id` and values are the scrubbed config (the inner `id` is removed).  
  - Errors: `401` for missing/invalid global API key, `403` if discoverability disabled, `500` for internal errors.

- `POST /projects`  
  - Create a new project. Request body **must** be valid JSON and include at minimum an `"id"` field.  
  - The route generates/stores API key hash server-side; if `config_instance.add_project(...)` returns a plaintext API key it will be returned in the response (useful for immediate display).  
  - Requires system authentication.  
  - Response: `201` with `{"message":"Project created successfully", "new_project_api_key": "<key>"}` (api key field present only if created and returned).  
  - Errors: `400` for invalid JSON or missing `id` or duplicate id, `401` for auth, `500` for internal errors.

- `POST /projects/<project_id>/config/regenerate-api-key`  
  - Regenerate and return a new API key for the specified project (updates the stored API key hash).  
  - Requires system authentication (global API key).  
  - Response: `200` with `{"message":"API key regenerated successfully","api_key":"<new-api-key>"}`.  
  - Errors: `401` for auth, `404` if project not found, `500` if regeneration failed (e.g. authentication disabled for that project) or internal errors.

- `DELETE /projects/<project_id>`  
  - Delete a project from configuration and remove its project store file.  
  - Requires system authentication.  
  - Response: `200` with `{"message":"Project '<project_id>' deleted successfully"}`.  
  - Errors: `401` for auth, `404` if project not found, `500` for internal errors.

#### Project Management (requires **project** API key when that project's authentication is enabled)
- `GET /projects/<project_id>`  
  - Get project details (API key & API key hash are scrubbed / not returned).  
  - Auth: verifies against the project's `authentication` config (project-level auth).  
  - Response: JSON object containing `{"id":"<project_id>", ...scrubbed project config...}`.  
  - Errors: `401` for missing/invalid project API key, `404` if project not found, `500` for internal errors.

- `PUT /projects/<project_id>`  
  - Update project settings (request body must be valid JSON). **This route prevents updating the project's `authentication` section** (payload `authentication` is popped/ignored).  
  - Auth: verifies against the project's `authentication` config.  
  - Response: `200` with `{"message":"Project '<project_id>' updated successfully"}`.  
  - Errors: `400` for invalid JSON, `401` for auth, `404` if project not found, `500` for internal errors.

- `GET /projects/<project_id>/store`  
  - Retrieve all key/value pairs for a project (the project store).  
  - Auth: verifies against the project's `authentication` config.  
  - Requires project-level discoverability: `project_config.security.keys_and_values_discoverable` must be `true` — otherwise returns `403`.  
  - Response: `200` with the project's store contents (JSON).  
  - Errors: `401` for auth, `403` if discoverability disabled, `404` if project not found, `500` for internal errors.

- `PUT /projects/<project_id>/store/<key>`  
  - Create or update a key/value in the project store.  
  - Auth: verifies against the project's `authentication` config.  
  - Accepts **JSON** body (preferred) or plain text (if JSON absent, the raw request body is used).  
  - Response: `200` with `{"message":"Key '<key>' set successfully in project '<project_id>' store"}`.  
  - Errors: `400` if missing body (neither JSON nor non-empty plain text), `401` for auth, `404` if project not found, `500` for internal errors.

- `GET /projects/<project_id>/store/<key>`  
  - Retrieve the value and metadata for a specific key in the project store.
  - Auth: verifies against the project's `authentication` config.  
  - Response: `200` with the stored value (JSON).  
  - Errors: `401` for auth, `404` if project or key not found, `500` for internal errors.

- `GET /projects/<project_id>/store/<key>/value`  
  - Retrieve only the raw value for a specific key in the project store (no metadata).
  - Auth: verifies against the project's `authentication` config.  
  - Response: `200` with the raw stored value (plain text or JSON as originally stored).  
  - Errors: `401` for auth, `404` if project or key not found, `500` for internal errors.

- `DELETE /projects/<project_id>/store/<key>`  
  - Delete a specific key-value pair from the project store.  
  - Auth: verifies against the project's `authentication` config.  
  - Response: `200` with `{"message":"Key '<key>' deleted successfully from project '<project_id>' store"}`.  
  - Errors: `401` for auth, `404` if project or key not found, `500` for internal errors.

- `DELETE /projects/<project_id>/store`  
  - Delete all key-value pairs for the project (clear the store).  
  - Auth: verifies against the project's `authentication` config.  
  - Response: `200` with `{"message":"All key-value pairs deleted successfully from project '<project_id>' store"}`.  
  - Errors: `401` for auth, `404` if project not found, `500` for internal errors.

## Data Storage Format
For persistent storage, each project’s data will be stored in a folder defined by `persistent_file_path` in the config file. Each project will have its own file named `{project_id}.json`. The format will be JSON for simplicity and ease of parsing. Example content of `first_project.json`:

```json
{
    "key1": "value1",
    "key2": "value2",
    "key3": "value3"
}
```

(Keys may have other object types as values, not just strings)

## Implement authentication
Authentication will be handled using API keys. Each project can have its own API key if authentication is enabled. The server will verify the API key provided in the request headers against the stored hash in the config file: If save api_key_to_file is false, the server will only store and compare the hash of the API key for security, otherwise it will store the plain text key in the config file and compare directly.