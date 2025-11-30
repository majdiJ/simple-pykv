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
    
    # Merge with default project config
    def merge_defaults(self, target, defaults):
        for key, value in defaults.items():
            if key not in target:
                target[key] = value
            else:
                # Recurse into nested dicts
                if isinstance(value, dict) and isinstance(target[key], dict):
                    self.merge_defaults(target[key], value)
    
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
    
    def get_config_data(self) -> dict:
        with self.lock:
            return self.config_data
    
    def update_system_config(self, new_system_config: dict) -> None:
        # Update system config in config data and save to file. Only allow update fields: api_key, api_key_hash and project_discoverable
        # Protect file write with lock
        with self.lock:
            system_config = self.config_data.get("system", {})
            for key, value in new_system_config.items():
                if key in ["authentication", "security"]:
                    if key not in system_config:
                        system_config[key] = {}
                    for sub_key, sub_value in value.items():
                        if sub_key in ["api_key", "api_key_hash", "project_discoverable"]:
                            system_config[key][sub_key] = sub_value
            self.config_data["system"] = system_config
            self.saveToFile()
        
    # Make a new project entry in config and save to file=
    def add_project(self, project_data: dict) -> None:
        # Must have an id
        if "id" not in project_data:
            raise ValueError("Project data must include an 'id' field.")

        self.merge_defaults(project_data, DEFAULT_PROJECT_CONFIG)

        # Protect file write with lock
        with self.lock:
            if "projects" not in self.config_data:
                self.config_data["projects"] = []

            self.config_data["projects"].append(project_data)
            self.saveToFile()
    
    def get_project_config(self, project_id: str) -> dict | None:
        with self.lock:
            for project in self.config_data.get("projects", []):
                if project.get("id") == project_id:
                    return project
        return None
    
    def update_project_config(self, project_id: str, new_project_data: dict) -> None:
        # Update project config in config data and save to file. Project ID cannot be changed, evry other field can be updated.
        with self.lock:
            for i, project in enumerate(self.config_data.get("projects", [])):
                if project.get("id") == project_id:
                    # Update fields except for id
                    for key, value in new_project_data.items():
                        if key != "id":
                            project[key] = value
                    self.config_data["projects"][i] = project
                    self.saveToFile()
                    return
            raise ValueError(f"Project with ID '{project_id}' not found in configuration.")

    def delete_project_config(self, project_id: str) -> None:
        # Delete project config from config data and save to file
        with self.lock:
            for i, project in enumerate(self.config_data.get("projects", [])):
                if project.get("id") == project_id:
                    del self.config_data["projects"][i]
                    self.saveToFile()
                    return
            raise ValueError(f"Project with ID '{project_id}' not found in configuration.")