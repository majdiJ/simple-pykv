# Imports
import json

class config:
    def __init__(self, config_file):
        self.config_file = config_file
    
    # Read `config.json` file and return its content
    def read_config_file(self) -> dict:
        if not self.config_file.exists():
            return None
        with open(self.config_file, "r") as config_file:
            config_data = json.load(config_file)
        return config_data
    
    # Write `config_data` to `config.json` file
    def write_config_file(self, config_data: dict) -> None:
        with open(self.config_file, "w") as config_file:
            json.dump(config_data, config_file, indent=4)
    
    # Make `config.json` file
    def make_default_file(self, DEFAULT_PORT) -> None:
        default_config = {
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
                {
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
                        "key_values_discoverable": True
                    }
                }
            ]
        }

        with open(self.config_file, "w") as config_file:
            json.dump(default_config, config_file, indent=4)
        print("Verbose: config.json has been created!")

    # functions related to config authentication
    class auth:
        pass
