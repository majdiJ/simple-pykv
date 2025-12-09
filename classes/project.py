# Imports
import json
import logging
import threading
from pathlib import Path
import tempfile
import os
from classes.config import Config
import copy
from utils.metadata import get_current_epoch_time, size_bytes

class Project:
    def __init__(self, config: Config, project_id: str):
        self.lock = threading.RLock()  # lock for thread-safe operations
        self.config_data = config.config_data
        self._project_config = config.get_project_config(project_id)
        self.store = {}
        self.id = project_id

        if self._project_config is None:
            raise ValueError(f"Project config for id '{project_id}' not found.")

        # Determine if on_disk storage is enabled for this project, default to False for security
        self._on_disk_boolean = bool(self._project_config.get("storage", {}).get("on_disk", False))

        # Set up file path for persistent storage if on_disk is True
        if self._on_disk_boolean:
            base_dir = Path(self.config_data.get("system", {}).get("storage", {}).get("persistent_file_path", "storage_data"))
            base_dir.mkdir(parents=True, exist_ok=True)
            self.filePath = base_dir / f"{project_id}_store.json"

            # Load existing data from file as on_disk is True
            self.__loadFromFile()

    def __loadFromFile(self):
        with self.lock:
            try:
                if not self.filePath.exists():
                    # Nothing to load
                    self.store = {}
                    return

                with self.filePath.open("r", encoding="utf-8") as f:
                    self.store = json.load(f)

                # ensure store is a dict
                if not isinstance(self.store, dict):
                    logging.error("Store file did not contain a JSON object; resetting to empty dict.")
                    self.store = {}

            except json.JSONDecodeError as e:
                logging.error(f"Failed to decode JSON from {self.filePath}: {e}")
                self.store = {}
            except Exception:
                logging.exception("Unexpected error while loading project store")
                self.store = {}

    def __saveToFile(self):
        if not self._on_disk_boolean:
            return  # Do not save if on_disk is False
        
        with self.lock:
            # ensure parent dir exists (in case it was removed)
            self.filePath.parent.mkdir(parents=True, exist_ok=True)

            # Use mkstemp to get an atomic replace pattern
            tmp_fd, tmp_path = tempfile.mkstemp(dir=str(self.filePath.parent),prefix=self.filePath.name + ".tmp.")

            try:
                # Write JSON to temp file, flush & fsync to ensure durability
                with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                    json.dump(self.store, f, indent=2, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())

                # Atomic replace
                os.replace(tmp_path, str(self.filePath))

            except Exception:
                logging.exception("Failed to save project store to disk")
                # Try remove temp file if it still exists
                try:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                except Exception:
                    logging.exception("Failed to remove temporary file")
                raise

    def getValue(self, key):
        with self.lock:
            return self.store.get(key)
        
    def getValueOnly(self, key):
        with self.lock:
            return self.store.get(key, {}).get("value")

    def setValue(self, key, value):
        with self.lock:
            current_time = get_current_epoch_time()

            if isinstance(value, str):
                try:
                    value = json.loads(value)
                except:
                    pass

            if key in self.store:
                self.store[key]["updated_at"] = current_time
            else:
                self.store[key] = {
                    "created_at": current_time,
                    "updated_at": current_time,
                }

            self.store[key]["size_bytes"] = size_bytes(value)
            self.store[key]["value"] = value

            self.__saveToFile()

    def deleteKey(self, key):
        with self.lock:
            if key in self.store:
                del self.store[key]
                self.__saveToFile() # Save to disk if on_disk is True

    def clearStore(self):
        with self.lock:
            self.store.clear()
            self.__saveToFile() # Save to disk if on_disk is True

    # Getters for listing all keys if discoverable
    @property
    def keys(self):
        if self._project_config.get("security", {}).get("keys_and_values_discoverable", False):
            with self.lock:
                return list(self.store.keys())
        else:
            return None

    # Getter for listing KV items
    @property
    def KeyValueItems(self):
        if self._project_config.get("security", {}).get("keys_and_values_discoverable", False):
            with self.lock:
                # return shallow copy to avoid caller mutating internal dict
                return copy.deepcopy(self.store)
        else:
            return None
    
    # Getter for project configuration
    @property
    def project_config(self) -> dict:
         with self.lock:
             return self._project_config
    
    def delete_store_file(self):
        # Deletes the on-disk store file if it exists.
        if self._on_disk_boolean and self.filePath.exists():
            try:
                self.filePath.unlink()
            except Exception:
                logging.exception("Failed to delete project store file")
