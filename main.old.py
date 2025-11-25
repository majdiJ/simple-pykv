# Simple PyKV - A Lightweight Key-Value Store Server in Python

from pathlib import Path
import json

from utils.cui_util import program_start_message
from utils.config_util import make_config_file, read_config_file, system_authentication_api_key_exist, system_authentication_api_key_hash_exist, system_authentication_save_api_key_to_config, system_authentication_save_api_key_to_config_enabled, system_authentication_save_api_key_to_config, system_authentication_save_api_key_hash_to_config
from utils.auth_utils import generate_api_key, hash_api_key, verify_api_key

# Global variables
CONFIG_FILE = Path("config.json")
DEFAULT_PORT = 23849

if __name__ == "__main__":
    # Start of program
    print("Simple PyKV - Version 0.0.0")
    program_start_message()

    # Check for configuration file or create one
    print("Checking for configuration file...")
    if CONFIG_FILE.exists():
        print("Configuration file found. Proceeding...")
    else:
        print("Configuration file not found. Creating default configuration...")
        make_config_file(CONFIG_FILE, DEFAULT_PORT)
        print("Default configuration file created.")
    
    # Read configuration file
    config_json = read_config_file(CONFIG_FILE)
    print("Configuration loaded successfully.")

    # Check to see if API key or hash exist in config for system authentication
    if system_authentication_api_key_exist(config_json) or system_authentication_api_key_hash_exist(config_json):
        print("System authentication API key and/or hash found in configuration.")
    else:
        print("No system authentication API key or hash found in configuration.\nCreating new API key and hash...")
        new_api_key = generate_api_key()
        new_api_key_hash = hash_api_key(new_api_key)
        print("New API key generated:", new_api_key)
        print("New API key hash:", new_api_key_hash)

        # Check to see if we should save the new API key to the config file (Hash is always saved)
        if system_authentication_save_api_key_to_config_enabled(config_json):
            print("Saving new API key to configuration file...")
            system_authentication_save_api_key_to_config(config_json, CONFIG_FILE, new_api_key)
            print("New API key saved to configuration file.")
        else:
            print("Not saving new API key to configuration file as per settings.")
            print("Please store the new API key securely, as it will not be saved in the configuration file. You will not be able to retrieve it later unless you disable this setting and generate a new key!!!\nSafely store this key:", new_api_key)
        
        # Save the new API key hash to config file
        print("Saving new API key hash to configuration file...")
        system_authentication_save_api_key_hash_to_config(config_json, CONFIG_FILE, new_api_key_hash)
        print("New API key hash saved to configuration file.")
    
    # FOr every project, check to see if API key or hash exist in config for project authentication
    for project in config_json.get("projects", []):
        project_id = project.get("id", "unknown_project")
        if project.get("authentication", {}).get("api_key") or project.get("authentication", {}).get("api_key_hash"):
            print(f"Project '{project_id}' authentication API key and/or hash found in configuration.")
        else:
            print(f"No authentication API key or hash found for project '{project_id}'.\nCreating new API key and hash...")
            new_api_key = generate_api_key()
            new_api_key_hash = hash_api_key(new_api_key)
            print(f"New API key generated for project '{project_id}':", new_api_key)
            print(f"New API key hash for project '{project_id}':", new_api_key_hash)

            # Check to see if we should save the new API key to the config file (Hash is always saved)
            if project.get("authentication", {}).get("save_api_key_to_config", False):
                print(f"Saving new API key for project '{project_id}' to configuration file...")
                project["authentication"]["api_key"] = new_api_key
                with open(CONFIG_FILE, "w") as config_file:
                    json.dump(config_json, config_file, indent=4)
                print(f"New API key for project '{project_id}' saved to configuration file.")
            else:
                print(f"Not saving new API key for project '{project_id}' to configuration file as per settings.")
                print(f"Please store the new API key for project '{project_id}' securely, as it will not be saved in the configuration file. You will not be able to retrieve it later unless you disable this setting and generate a new key!!!\nSafely store this key:", new_api_key)
            
            # Save the new API key hash to config file
            print(f"Saving new API key hash for project '{project_id}' to configuration file...")
            project["authentication"]["api_key_hash"] = new_api_key_hash
            with open(CONFIG_FILE, "w") as config_file:
                json.dump(config_json, config_file, indent=4)
            print(f"New API key hash for project '{project_id}' saved to configuration file.")