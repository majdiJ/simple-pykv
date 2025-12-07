# Simple PyKV - A Lightweight Key-Value Store Server in Python

from pathlib import Path
import json

from classes.cui import cui
from classes.config import Config
from utils.auth_utils import generate_api_key, hash_api_key, verify_api_key
from classes.server import Server
from classes.project import Project
from classes.system_info import system_info

if __name__ == "__main__":
    print("Simple PyKV - Version 0.0.0 (Beta) - Program starting...")
    cui.print.start_message()

    # Try catch
    print("Verbose: Reading configuration...")
    try:
        config_instance = Config()
    except Exception as e:
        print(f"Error: Failed to initialise configuration: {e}")
        exit(1)

    # Check to see if system authentication is enabled
    if config_instance.get_config_data().get("system", {}).get("authentication", {}).get("enabled", True):
        print("Verbose: System authentication is enabled.")

        # Check to see if API key or hash exist in config for system authentication
        if config_instance.get_config_data().get("system", {}).get("authentication", {}).get("api_key") or config_instance.get_config_data().get("system", {}).get("authentication", {}).get("api_key_hash"):
            # API key or hash found
            print("Verbose: System authentication API key and/or hash found in configuration.")
        else:
            # No API key or hash found - generate new ones
            print("Verbose: No system authentication API key or hash found in configuration. Creating new API key and hash...")
            new_api_key = generate_api_key()
            new_api_key_hash = hash_api_key(new_api_key)

            # Check to see if we should save the new API key to the config file (Hash is always saved)
            if config_instance.get_config_data().get("system", {}).get("authentication", {}).get("save_api_key_to_config", False):
                print("Verbose: Saving new API key to configuration file as per settings")
                new_system_config = {
                    "authentication": {
                        "api_key": new_api_key,
                        "api_key_hash": new_api_key_hash
                    }
                }
                config_instance.update_system_config(new_system_config)
            else:
                print("Verbose: Not saving new API key to configuration file as per settings.")
                print("API key for system will not be saved. You will only see this key once. Please store it securely.")
                print("System API key:", new_api_key)

                new_system_config = {
                    "authentication": {
                        "api_key": None,
                        "api_key_hash": new_api_key_hash
                    }
                }
                config_instance.update_system_config(new_system_config)
    else:
        print("Verbose: System authentication is disabled.")
    
    # Loop through each project and check authentication
    for project in config_instance.get_config_data().get("projects", []):
        project_id = project.get("id", "unknown_project")
        if project.get("authentication", {}).get("enabled", True):
            print(f"Verbose: Project '{project_id}' authentication is enabled.")

            if project.get("authentication", {}).get("api_key") or project.get("authentication", {}).get("api_key_hash"):
                print(f"Verbose: Project '{project_id}' authentication API key and/or hash found in configuration.")
            else:
                print(f"Verbose: No authentication API key or hash found for project '{project_id}'. Creating new API key and hash...")
                new_api_key = generate_api_key()
                new_api_key_hash = hash_api_key(new_api_key)

                if project.get("authentication", {}).get("save_api_key_to_config", False):
                    print(f"Verbose: Saving new API key to configuration file for project '{project_id}' as per settings")
                    new_project_config = {
                        "authentication": {
                            "api_key": new_api_key,
                            "api_key_hash": new_api_key_hash
                        }
                    }
                    config_instance.update_project_config(project_id, new_project_config)
                else:
                    print(f"Verbose: Not saving new API key to configuration file for project '{project_id}' as per settings.")
                    print(f"API key for project '{project_id}' will not be saved. You will only see this key once. Please store it securely.")
                    print(f"Project '{project_id}' API key:", new_api_key)

                    new_project_config = {
                        "authentication": {
                            "api_key": None,
                            "api_key_hash": new_api_key_hash
                        }
                    }
                    config_instance.update_project_config(project_id, new_project_config)
        else:
            print(f"Verbose: Project '{project_id}' authentication is disabled.")
    
    print("Verbose: Configuration processing complete.")

    # Create list to hold project instances
    project_instances = []

    # Loop through each project in config and instantiate Project class
    for project_cfg in config_instance.get_config_data().get("projects", []):
        print(f"Verbose: Initialising project '{project_cfg.get('id', 'unknown_project')}'...")
        try:
            project_instance = Project(config_instance, project_cfg.get("id", "unknown_project"))
            project_instances.append(project_instance)
            print(f"Verbose: Project '{project_cfg.get('id', 'unknown_project')}' initialised successfully.")
        except Exception as e:
            print(f"Error: Failed to initialise project '{project_cfg.get('id', 'unknown_project')}': {e}")
            exit(1)
    
    # Initialise system info module
    print("Verbose: Initialising system information module...")
    system_info_instance = system_info(config_instance)

    # All setup complete - start the server
    print("Verbose: Program setup complete. Proceeding to start server...")
    server_app_instance = Server.create_app(config_instance = config_instance, project_instances = project_instances, system_info_instance = system_info_instance)
    server_port = config_instance.get_config_data().get("server_port")
    server_host = config_instance.get_config_data().get("server_host")
    print(f"Verbose: Starting server on {server_host}:{server_port}...")
    # Run the server
    server_app_instance.run(host=server_host, port=server_port, threaded=True, debug=True, use_reloader=False)