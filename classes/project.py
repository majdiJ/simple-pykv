# imports
import json
import logging
import threading
from pathlib import Path
import tempfile
import os

class Project:
    def __init__(self, config : object, project_id : str):
        # Config will be a `config_instance` class. Use `config.get_config_data()` to get full config dict.
        # Get project config from full config using `config.get_project_config(project_id)`
        self.lock = threading.RLock()  # lock for thread-safe operations
        self.config_data = config.get_config_data()
        self.project_config = config.get_project_config(project_id)
        self.store = {}

        base_dir = Path(self.config_data.get("storage", {}).get("persistent_file_path", "storage_data"))
        base_dir.mkdir(parents=True, exist_ok=True)
        self.filePath = base_dir / f"{self.config_data.get('id')}_store.json"

        # Load existing data from file if on_disk is True
        if self.config_data.get("storage", {}).get("on_disk", False):
            self.loadFromFile()

    def loadFromFile(self):
        # Protect file read with lock
        with self.lock:
            try:
                with self.filePath.open("r", encoding="utf-8") as f:
                    self.store = json.load(f)
            except FileNotFoundError:
                # no existing file is fine — leave store empty - will create on first save
                self.store = {}
            except json.JSONDecodeError as e:
                # corrupted file - log error and start with empty store
                logging.error(f"Failed to decode JSON: {e}")
                self.store = {}
 
    def saveToFile(self):
        # Protect file write with lock
        with self.lock:
            tmp_fd, tmp_path = tempfile.mkstemp(dir=str(self.filePath.parent), prefix=self.filePath.name + ".tmp.")
            try:
                # write JSON to the temp file
                with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                    json.dump(self.store, f, indent=2, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())

                # atomic replace
                os.replace(tmp_path, str(self.filePath))

            except Exception:
                logging.exception("Failed to save KV store to disk")
                # try remove temp file if it still exists
                try:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                except Exception:
                    logging.exception("Failed to remove temporary file")
                raise  # re-raise so caller can react (optional)
    
    def getValue(self, key):
        with self.lock:
            return self.store.get(key)

    def setValue(self, key, value):
        with self.lock:
            self.store[key] = value

            # Save to disk if enabled in project config
            if self.config_data.get("storage", {}).get("on_disk", False):
                self.saveToFile()
    
    def deleteValue(self, key):
        with self.lock:
            if key in self.store:
                del self.store[key]
                
                # Save to disk if enabled in project config
                if self.config_data.get("storage", {}).get("on_disk", False):
                    self.saveToFile()
    
    def clearStore(self):
        with self.lock:
            self.store.clear()
            if self.config_data.get("storage", {}).get("on_disk", False):
                self.saveToFile()
    
    def listKeys(self):
        if self.config_data.get("security", {}).get("keys_and_values_discoverable", False):
            with self.lock:
                return list(self.store.keys())
        else:
            return None
    
    def listItems(self):
        if self.config_data.get("security", {}).get("keys_and_values_discoverable", False):
            with self.lock:
                return {k: v for k, v in self.store.items()}
        else:
            return None