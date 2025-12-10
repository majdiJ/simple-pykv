# Imports
import copy
import json
import threading
from pathlib import Path
import logging
import tempfile
import os

from utils.auth_utils import generate_api_key, hash_api_key

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
        },
        "debuging": {
            "verbose_mode": False
        }
    },
    "projects": [
        DEFAULT_PROJECT_CONFIG
    ]
}

class Config:
    def __init__(self):
        self.lock = threading.RLock() 
        self.filePath = Path(CONFIG_FILE_PATH)

        while True:
            try:
                # Attempt to load config file
                self._config_data = self.__loadFromFile()

                # If config file does not exist, create default one
                if self._config_data == None:
                    self.__make_default_file()
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
    def __merge_defaults(self, target, defaults):
        for key, value in defaults.items():
            if key not in target:
                target[key] = value
            else:
                # Recurse into nested dicts
                if isinstance(value, dict) and isinstance(target[key], dict):
                    self.__merge_defaults(target[key], value)
    
    def __loadFromFile(self) -> dict | None:
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
    
    def __saveToFile(self) -> None:
        # Protect file write with lock
        with self.lock:
            tmp_fd, tmp_path = tempfile.mkstemp(dir=str(self.filePath.parent), prefix=self.filePath.name + ".tmp.")
            try:
                # write JSON to the temp file
                with os.fdopen(tmp_fd, "w", encoding="utf-8") as f:
                    json.dump(self._config_data, f, indent=2, ensure_ascii=False)
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

    def __make_default_file(self) -> None:
        # Protect file write with lock
        with self.lock:
            # deep copy to avoid sharing nested dict references
            self._config_data = copy.deepcopy(DEFAULT_CONFIG)
            self.__saveToFile()
    
    # Getter for config data
    @property
    def config_data(self) -> dict:
        with self.lock:
            return dict(self._config_data)
    
    def update_system_config(self, new_system_config: dict) -> None:
        with self.lock:
            system_config = self._config_data.setdefault("system", {})
            # Ensure system defaults exist (so enabled/save_api_key_to_config aren't lost)
            self.__merge_defaults(system_config, DEFAULT_CONFIG.get("system", {}))

            for key, value in new_system_config.items():
                if key in ["authentication", "security"]:
                    target = system_config.setdefault(key, {})
                    if isinstance(value, dict) and isinstance(target, dict):
                        for sub_key, sub_value in value.items():
                            if sub_key in ["api_key", "api_key_hash", "project_discoverable"]:
                                target[sub_key] = sub_value

            self._config_data["system"] = system_config
            self.__saveToFile()

        
    # Make a new project entry in config and save to file=
    def add_project(self, project_data: dict) -> str | None:
        # Must have an id
        if "id" not in project_data:
            raise ValueError("Project data must include an 'id' field.")
        
        # Ensure project_data dosen't have api_key or api_key_hash
        if "authentication" in project_data:
            project_data["authentication"].pop("api_key", None)
            project_data["authentication"].pop("api_key_hash", None)

        # Merge with default project config to ensure all keys exist
        self.__merge_defaults(project_data, DEFAULT_PROJECT_CONFIG)

        # Generate API key and hash if authentication is enabled and save_api_key_to_config is true
        auth_config = project_data.get("authentication", {})
        if auth_config.get("enabled", True):
            api_key = generate_api_key()
            api_key_hash = hash_api_key(api_key)

            auth_config["api_key_hash"] = api_key_hash
        
            if auth_config.get("save_api_key_to_config", False):
                auth_config["api_key"] = api_key
            
            project_data["authentication"] = auth_config

        # Protect file write with lock
        with self.lock:

            # Ensure project ID is unique
            existing_ids = {project.get("id") for project in self._config_data.get("projects", [])}
            if project_data["id"] in existing_ids:
                raise ValueError(f"Project with ID '{project_data['id']}' already exists in configuration.")

            if "projects" not in self._config_data:
                self._config_data["projects"] = []

            self._config_data["projects"].append(project_data)
            self.__saveToFile()
        
        if api_key:
            return api_key
        return None

    # Getter for number of projects
    @property
    def number_of_projects(self) -> int:
        with self.lock:
            return len(self._config_data.get("projects", []))
    
    def get_project_config(self, project_id: str) -> dict | None:
        with self.lock:
            for project in self._config_data.get("projects", []):
                if project.get("id") == project_id:
                    return project
        return None
    
    def update_project_config(self, project_id: str, new_project_data: dict) -> None:
        # Update project config in config data and save to file. Project ID cannot be changed.
        with self.lock:
            for i, project in enumerate(self._config_data.get("projects", [])):
                if project.get("id") == project_id:
                    # For each key, merge dicts where appropriate instead of overwriting them
                    for key, value in new_project_data.items():
                        if key == "id":
                            continue
                        if isinstance(value, dict) and isinstance(project.get(key), dict):
                            # update only provided subkeys, keep existing keys
                            project[key].update(value)
                        else:
                            # replace non-dict or replace missing key
                            project[key] = value
                    self._config_data["projects"][i] = project
                    self.__saveToFile()
                    return
            raise ValueError(f"Project with ID '{project_id}' not found in configuration.")
    
    def regenerate_project_api_key(self, project_id: str) -> str | None:
        # Regenerate API key for the specified project, update hash in config, and save to file
        with self.lock:
            for i, project in enumerate(self._config_data.get("projects", [])):
                if project.get("id") == project_id:
                    auth_config = project.get("authentication", {})
                    if not auth_config.get("enabled", True):
                        return None  # Authentication not enabled, nothing to do

                    # Generate new API key and hash
                    new_api_key = generate_api_key()
                    new_api_key_hash = hash_api_key(new_api_key)

                    auth_config["api_key_hash"] = new_api_key_hash

                    if auth_config.get("save_api_key_to_config", False):
                        auth_config["api_key"] = new_api_key
                    else:
                        auth_config.pop("api_key", None)  # Remove api_key if it exists

                    project["authentication"] = auth_config
                    self._config_data["projects"][i] = project
                    self.__saveToFile()
                    return new_api_key
            raise ValueError(f"Project with ID '{project_id}' not found in configuration.")

    def delete_project_config(self, project_id: str) -> None:
        # Delete project config from config data and save to file
        with self.lock:
            for i, project in enumerate(self._config_data.get("projects", [])):
                if project.get("id") == project_id:
                    del self._config_data["projects"][i]
                    self.__saveToFile()
                    return
            raise ValueError(f"Project with ID '{project_id}' not found in configuration.")