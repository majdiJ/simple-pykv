# imports
import json

# Make `config.json` file
def make_config_file(CONFIG_FILE, DEFAULT_PORT) -> None:
    default_config = {
        "version": 1,
        "server_port": DEFAULT_PORT,
        "system": {
            "storage": {
                "persistent_file_path": "storage_data"
            },
            "authentication": {
                "enabled": True,
                "save_api_key_to_config": False,
                "api_key": None,
                "api_key_hash": None
            }
        },
        "projects": [
            {
                "id": "first_project",
                "storage": {
                    "on_disk": True,
                    "cache_in_memory": True
                },
                "authentication": {
                    "enabled": True,
                    "save_api_key_to_config": False,
                    "api_key": None,
                    "api_key_hash": None
                }
            }
        ]
    }

    with open(CONFIG_FILE, "w") as config_file:
        json.dump(default_config, config_file, indent=4)
    print("config.json has been created!")

# Read `config.json` file and return its content
def read_config_file(CONFIG_FILE) -> dict:
    with open(CONFIG_FILE, "r") as config_file:
        config_data = json.load(config_file)
    return config_data

# Check if config `system.authentication.api_key` is set
def system_authentication_api_key_exist(CONFIG_JSON) -> bool:
    api_key = CONFIG_JSON.get("system", {}).get("authentication", {}).get("api_key")
    return api_key is not None

# Check if config `system.authentication.api_key_hash` is set
def system_authentication_api_key_hash_exist(CONFIG_JSON) -> bool:
    api_key_hash = CONFIG_JSON.get("system", {}).get("authentication", {}).get("api_key_hash")
    return api_key_hash is not None

# Check to see if `save_api_key_to_config` is enabled for system authentication - if so, we save the new API key to config
def system_authentication_save_api_key_to_config_enabled(CONFIG_JSON) -> bool:
    save_to_config = CONFIG_JSON.get("system", {}).get("authentication", {}).get("save_api_key_to_config", False)
    return save_to_config

# Save system API key to config file
def system_authentication_save_api_key_to_config(CONFIG_JSON, CONFIG_FILE, new_api_key) -> None:
    CONFIG_JSON["system"]["authentication"]["api_key"] = new_api_key
    with open(CONFIG_FILE, "w") as config_file:
        json.dump(CONFIG_JSON, config_file, indent=4)
    print("System API key and hash have been saved to config file.")

# Save system API key hash to config file
def system_authentication_save_api_key_hash_to_config(CONFIG_JSON, CONFIG_FILE, new_api_key_hash) -> None:
    CONFIG_JSON["system"]["authentication"]["api_key_hash"] = new_api_key_hash
    with open(CONFIG_FILE, "w") as config_file:
        json.dump(CONFIG_JSON, config_file, indent=4)
    print("System API key hash has been saved to config file.")