# database.py

import json
import os
import tempfile
import threading
from pathlib import Path
import logging

class ProjectKVStore:
    def __init__(self, project_config, base_dir):
        self.projectConfig = project_config
        self.id = project_config.get("id", "default_project")
        self.store = {}
        self.lock = threading.RLock()  # protect store + file writes
        self.on_disk = project_config.get("storage", {}).get("on_disk", False) # whether to persist KVs to disk

        # prepare file path using base_dir from system config
        base_dir = Path(base_dir)
        base_dir.mkdir(parents=True, exist_ok=True)
        self.filePath = base_dir / f"{self.id}_kvstore.json"

        # load from disk if on_disk is True and file exists
        if self.on_disk:
            self.loadFromFile()

    def loadFromFile(self):
        try:
            with self.filePath.open("r", encoding="utf-8") as f:
                # protect in case other threads try to read while we're loading
                with self.lock:
                    self.store = json.load(f)
        except FileNotFoundError:
            # no existing file is fine — leave store empty - will create on first save
            self.store = {}
        except json.JSONDecodeError as e:
            # corrupted file - log error and start with empty store
            logging.error(f"Failed to decode JSON: {e}")
            self.store = {}

    def saveToFile(self):
        # atomic write: write to temp file then replace
        if not self.on_disk:
            return
        with self.lock:
            tmp = None
            try:
                parent = self.filePath.parent
                tmp_fd, tmp_path = tempfile.mkstemp(dir=str(parent))
                with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                    json.dump(self.store, f, indent=2, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())
                os.replace(tmp_path, str(self.filePath))
            except Exception:
                logging.error("Failed to save KV store to disk", exc_info=True)
                if tmp and os.path.exists(tmp):
                    os.remove(tmp)
                raise

    # KV API
    def getValue(self, key):
        with self.lock:
            return self.store.get(key)

    def setValue(self, key, value):
        with self.lock:
            self.store[key] = value
            # persist if on_disk is true (save KV)
            if self.on_disk:
                self.saveToFile()

    def deleteValue(self, key):
        with self.lock:
            if key in self.store:
                del self.store[key]
                # persist if on_disk is true (delete KV)
                if self.on_disk:
                    self.saveToFile()

    # List all keys
    def listKeys(self):
        if self.projectConfig.get("security", {}).get("key_values_discoverable", True):
            with self.lock:
                return list(self.store.keys())
        else:
            return None

    # List all items
    def listItems(self):
        if self.projectConfig.get("security", {}).get("key_values_discoverable", True):
            with self.lock:
                return list(self.store.items())
        else:
            return None

    # Clear all key-values
    def clearStore(self):
        with self.lock:
            self.store.clear()
            if self.on_disk:
                self.saveToFile()


class Database:
    # Manager that holds multiple ProjectKVStore instances keyed by project id
    def __init__(self, config):
        self.config = config
        self.base_storage = config.get("system", {}).get("storage", {}).get("persistent_file_path", "storage_data")
        self.projects = {}
        for p in config.get("projects", []):
            project_id = p.get("id")
            if not project_id:
                logging.warning("Skipping project with no ID in config - Ensure all projects have a unique ID")
                continue
            if project_id in self.projects:
                logging.warning(f"Duplicate project ID '{project_id}' found in config - Skipping duplicate")
                continue
            store = ProjectKVStore(p, self.base_storage)
            self.projects[project_id] = store

    def get_store(self, project_id):
        return self.projects.get(project_id)

    def list_project_ids(self):
        if self.config.get("system", {}).get("security", {}).get("project_discoverable", True):
            return list(self.projects.keys())
        else:
            return None