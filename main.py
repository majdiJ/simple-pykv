# Simple PyKV - A Lightweight Key-Value Store Server in Python

from pathlib import Path
import json

from classes.cui import cui
from classes.config import config
from utils.auth_utils import generate_api_key, hash_api_key, verify_api_key
from classes.database import Database
from classes.server import Server

# Global variables
CONFIG_FILE = Path("config.json")
DEFAULT_PORT = 23849

if __name__ == "__main__":
    print("Simple PyKV - Version 0.0.0 (Beta) - Program starting...")
    cui.print.start_message()

    # initialize config class
    config_instance = config(CONFIG_FILE)
    
    attempts = 0
    while attempts < 2:
        attempts += 1

        # Load config file or create default one
        config_data = config_instance.read_config_file()

        if config_data == None:
            print("Verbose: Configuration file not found. Creating default configuration...")
            config_instance.make_default_file(DEFAULT_PORT)
            print("Verbose: Default configuration file created.")
        else:
            print("Verbose: Configuration file loaded successfully.")
            break
    
    # Check to see if API key or hash exist in config for system authentication
    if config_data.get("system", {}).get("authentication", {}).get("api_key") or config_data.get("system", {}).get("authentication", {}).get("api_key_hash"):
        print("Verbose: System authentication API key and/or hash found in configuration.")
    else:
        print("Verbose: No system authentication API key or hash found in configuration.Creating new API key and hash...")
        from utils.auth_utils import generate_api_key, hash_api_key
        new_api_key = generate_api_key()
        new_api_key_hash = hash_api_key(new_api_key)
        print("Verbose: New API key and hash generated for system authentication.")

        # Check to see if we should save the new API key to the config file (Hash is always saved)
        if config_data.get("system", {}).get("authentication", {}).get("save_api_key_to_config", False):
            print("Verbose: Saving new API key to configuration file as per settings...")
            config_data["system"]["authentication"]["api_key"] = new_api_key
        else:
            print("Verbose: Not saving new API key to configuration file as per settings.")
            print("API key for system will not be saved. You will only see this key once. Please store it securely.")
            print("System API key:", new_api_key)
            print("To generate a new key make `api_key` and `api_key_hash` set to null in config and restart the program.")
            print("To save keys to config in the future, set `save_api_key_to_config` to true in config and restart the program.")
        
        # Save the new API key hash to config data
        print("Verbose: Saving new API key hash to configuration file...")
        config_data["system"]["authentication"]["api_key_hash"] = new_api_key_hash

    # Check to see if API key or hash exist in config for every project authentication (Do the same as system auth but for each project)
    for project in config_data.get("projects", []):
        project_id = project.get("id", "unknown_project")
        if project.get("authentication", {}).get("api_key") or project.get("authentication", {}).get("api_key_hash"):
            print(f"Verbose: Project '{project_id}' authentication API key and/or hash found in configuration.")
        else:
            print(f"Verbose: No authentication API key or hash found for project '{project_id}'.Creating new API key and hash...")
            new_api_key = generate_api_key()
            new_api_key_hash = hash_api_key(new_api_key)
            print(f"Verbose: New API key and hash generated for project '{project_id}' authentication.")

            # Check to see if we should save the new API key to the config file (Hash is always saved)
            if project.get("authentication", {}).get("save_api_key_to_config", False):
                print(f"Verbose: Saving new API key to configuration file for project '{project_id}' as per settings...")
                project["authentication"]["api_key"] = new_api_key
            else:
                print(f"Verbose: Not saving new API key to configuration file for project '{project_id}' as per settings.")
                print(f"API key for project '{project_id}' will not be saved. You will only see this key once. Please store it securely.")
                print(f"Project '{project_id}' API key:", new_api_key)
                print("To generate a new key make `api_key` and `api_key_hash` set to null in config and restart the program.")
                print("To save keys to config in the future, set `save_api_key_to_config` to true in config and restart the program.")
            
            # Save the new API key hash to config data
            print(f"Verbose: Saving new API key hash to configuration file for project '{project_id}' as per settings...")
            project["authentication"]["api_key_hash"] = new_api_key_hash

    # Write updated config data back to file
    print("Verbose: Writing updated configuration to file...")
    config_instance.write_config_file(config_data)

    # Initialise database structure
    print("Verbose: instantiating database structure")
    database_instance = Database(config_data)

    # Start server
    print("Verbose: Program setup complete. Proceeding to start server...")
    server_app_instance = Server.create_app(config_data = config_data, database_instance = database_instance)
    server_port = config_data.get("system", {}).get("server", {}).get("port", DEFAULT_PORT)
    server_host = config_data.get("system", {}).get("server", {}).get("host", "0.0.0.0")
    server_app_instance.run(host=server_host, port=server_port, threaded=True, debug=True)