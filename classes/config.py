# Imports
import json
import threading
from pathlib import Path
import logging
import tempfile
import os

CONFIG_FILE_PATH = ("config.json")
DEFAULT_PORT = 23849
DEFAULT_PROJECT_CONFIG = {
    "id": "first_project",
    "storage": {
        "on_disk": True
    },
    "authentication": {
        "enabled": True,
        "save_api_key_to_config": False,
        "api_key": None,
        "api_key_hash": None
    },
    "security": {
        "keys_and_values_discoverable": True
    }
}
DEFAULT_CONFIG = {
    "version": 1,
    "server_port": DEFAULT_PORT,
    "server_host": "0.0.0.0",
    "system": {
        "storage": {
            "persistent_file_path": "storage_data"
        },
        "authentication": {
            "enabled": True,
            "save_api_key_to_config": False,
            "api_key": None,
            "api_key_hash": None
        },
        "security": {
            "project_discoverable": True
        }
    },
    "projects": [
        DEFAULT_PROJECT_CONFIG
    ]
}

class config:
    def __init__(self):
        self.lock = threading.RLock() 
        self.filePath = Path(CONFIG_FILE_PATH)

        while True:
            try:
                # Attempt to load config file
                self.config_data = self.loadFromFile()

                # If config file does not exist, create default one
                if self.config_data == None:
                    self.make_default_file()
                # If config file loaded successfully, break loop
                else:
                    break
            
            # If config file is invalid JSON, log error and raise exception
            except ValueError as ve:
                logging.error(f"Configuration file is invalid: {ve}")
                raise ve
            except Exception:
                logging.error("Configuration file could not be loaded and is required.")
                raise RuntimeError("Configuration file is required but could not be loaded.")
    
    def loadFromFile(self) -> dict | None:
        # Protect file read with lock
        with self.lock:
            try:
                with self.filePath.open("r", encoding="utf-8") as filePath:
                    config_data = json.load(filePath)
                    return config_data
            except FileNotFoundError:
                logging.error("Configuration file not found.")
                return None
            except json.JSONDecodeError as e:
                raise ValueError(f"Configuration file is not valid JSON: {e}") from e
            except Exception:
                logging.exception("Failed to load configuration from disk")
                return None
    
    def saveToFile(self) -> None:
        # Protect file write with lock
        with self.lock:
            tmp_fd, tmp_path = tempfile.mkstemp(dir=str(self.filePath.parent), prefix=self.filePath.name + ".tmp.")
            try:
                # write JSON to the temp file
                with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                    json.dump(self.config_data, f, indent=2, ensure_ascii=False)
                    f.flush()
                    os.fsync(f.fileno())

                # atomic replace
                os.replace(tmp_path, str(self.filePath))

            except Exception:
                logging.exception("Failed to save configuration to disk")
                # try remove temp file if it still exists
                try:
                    if os.path.exists(tmp_path):
                        os.unlink(tmp_path)
                except Exception:
                    logging.exception("Failed to remove temporary file for configuration")
                raise  # re-raise so caller can react (optional)
    
    # Make `config.json` file
    def make_default_file(self) -> None:
        # Protect file write with lock
        with self.lock:
            self.config_data = DEFAULT_CONFIG.copy()
            self.saveToFile()

    # Make a new project entry in config and save to file=
    def add_new_project(self, project_data: dict) -> None:

        # Must have an id
        if "id" not in project_data:
            raise ValueError("Project data must include an 'id' field.")

        # Merge with default project config
        def merge_defaults(target, defaults):
            for key, value in defaults.items():
                if key not in target:
                    target[key] = value
                else:
                    # Recurse into nested dicts
                    if isinstance(value, dict) and isinstance(target[key], dict):
                        merge_defaults(target[key], value)

        merge_defaults(project_data, DEFAULT_PROJECT_CONFIG)

        # Protect file write with lock
        with self.lock:
            if "projects" not in self.config_data:
                self.config_data["projects"] = []

            self.config_data["projects"].append(project_data)
            self.saveToFile()
