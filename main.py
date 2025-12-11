# Simple PyKV - A Lightweight Key-Value Store Server in Python

from pathlib import Path
import json
import traceback
from classes.config import Config
from utils.auth_utils import generate_api_key, hash_api_key, verify_api_key
from classes.server import Server
from classes.project import Project
from classes.system_info import system_info
from classes.cui import cui

def initialise_config():
    try:
        config_instance = Config()
    except Exception as e:
        print(f"ERROR: Failed to initialise configuration: {e}")
        # Re-raise so a production runner sees the failure on import
        raise

    cui_instance = cui(config_instance)

    # Check to see if system authentication is enabled
    if config_instance.config_data.get("system", {}).get("authentication", {}).get("enabled", True):
        cui_instance.print("System authentication is enabled", type="INFO")

        # Check to see if API key or hash exist in config for system authentication
        if config_instance.config_data.get("system", {}).get("authentication", {}).get("api_key") or config_instance.config_data.get("system", {}).get("authentication", {}).get("api_key_hash"):
            # API key or hash found
            cui_instance.print("System authentication API key and/or hash found in configuration", type="INFO")

        else:
            # No API key or hash found - generate new ones
            cui_instance.print("No system authentication API key or hash found in configuration", type="INFO")
            cui_instance.print("Attempting to create new API key and hash for system authentication...", type="INFO")
            new_api_key = generate_api_key()
            new_api_key_hash = hash_api_key(new_api_key)

            # Check to see if we should save the new API key to the config file (Hash is always saved)
            if config_instance.config_data.get("system", {}).get("authentication", {}).get("save_api_key_to_config", False):
                cui_instance.print("New API key generated. Both API key and hash will be saved to configuration file as per settings", type="SUCCESS")
                cui_instance.print("For maximum security, please consider disabling 'save_api_key_to_config' after initial setup to avoid storing the API key in plain text.", type="WARNING")
                cui_instance.print(f"System API key: {new_api_key}", type="INFO")
                
                new_system_config = {
                    "authentication": {
                        "api_key": new_api_key,
                        "api_key_hash": new_api_key_hash
                    }
                }
                config_instance.update_system_config(new_system_config)
            else:
                cui_instance.print("New API key generated. Only API key hash will be saved to configuration file as per settings", type="SUCCESS")
                cui_instance.print("You will only see this API key once. Please store this API key securely:", type="WARNING")
                cui_instance.print(f"System API key: {new_api_key}", type="INFO")

                new_system_config = {
                    "authentication": {
                        "api_key": None,
                        "api_key_hash": new_api_key_hash
                    }
                }
                config_instance.update_system_config(new_system_config)
    else:
        cui_instance.print("System authentication is disabled. No API key or hash will be used. (This is not secure!)", type="WARNING")
    
    # Loop through each project and check authentication
    for project in config_instance.config_data.get("projects", []):
        project_id = project.get("id", "unknown_project")
        if project.get("authentication", {}).get("enabled", True):
            cui_instance.print(f"Project '{project_id}' authentication is enabled.", type="INFO")

            if project.get("authentication", {}).get("api_key") or project.get("authentication", {}).get("api_key_hash"):
                cui_instance.print(f"Project '{project_id}' authentication API key and/or hash found in configuration.", type="INFO")
            else:
                cui_instance.print(f"No project authentication API key or hash found in configuration for '{project_id}'", type="INFO")
                cui_instance.print(f"Attempting to create new API key and hash for project {project_id} authentication...", type="INFO")

                new_api_key = generate_api_key()
                new_api_key_hash = hash_api_key(new_api_key)

                if project.get("authentication", {}).get("save_api_key_to_config", False):
                    print(f"Verbose: Saving new API key to configuration file for project '{project_id}' as per settings")

                    cui_instance.print("New API key generated. Both API key and hash for project will be saved to configuration file as per settings", type="SUCCESS")
                    cui_instance.print("For maximum security, please consider disabling 'save_api_key_to_config' after initial setup to avoid storing the API key in plain text.", type="WARNING")
                    cui_instance.print(f"Project '{project_id}' API key: {new_api_key}", type="INFO")

                    new_project_config = {
                        "authentication": {
                            "api_key": new_api_key,
                            "api_key_hash": new_api_key_hash
                        }
                    }
                    config_instance.update_project_config(project_id, new_project_config)
                else:
                    cui_instance.print("New API key generated. Only API key hash for project will be saved to configuration file as per settings", type="SUCCESS")
                    cui_instance.print("You will only see this API key once. Please store this API key securely:", type="WARNING")
                    cui_instance.print(f"Project '{project_id}' API key: {new_api_key}", type="INFO")

                    new_project_config = {
                        "authentication": {
                            "api_key": None,
                            "api_key_hash": new_api_key_hash
                        }
                    }
                    config_instance.update_project_config(project_id, new_project_config)
        else:
            cui_instance.print(f"Project '{project_id}' authentication is disabled. No API key or hash will be used. (This is not secure!)", type="WARNING")

    return config_instance, cui_instance

def initialise_projects(config_instance, cui_instance):
    # Create list to hold project instances
    project_instances = []

    # Loop through each project in config and instantiate Project class
    for project_cfg in config_instance.config_data.get("projects", []):
        cui_instance.print(f"Initialising project '{project_cfg.get('id', 'unknown_project')}'...", "INFO")
        try:
            project_instance = Project(config_instance, project_cfg.get("id", "unknown_project"))
            project_instances.append(project_instance)
            cui_instance.print(f"Project '{project_cfg.get('id', 'unknown_project')}' initialised successfully.", "INFO")
        except Exception as e:
            cui_instance.print(f"Failed to initialise project '{project_cfg.get('id', 'unknown_project')}': {e}", "ERROR")
            exit(1)

    return project_instances

def initialize_server():
    print("Simple PyKV - Version 0.0.0 (Beta) - Program starting...")

    # Initialise configuration and CUI
    config_instance, cui_instance = initialise_config()

    # Initialise projects
    project_instances = initialise_projects(config_instance, cui_instance)

    # Initialise system info module
    cui_instance.print("Initialising system information module...", "INFO")
    system_info_instance = system_info(config_instance)

    cui_instance.print("Configuration start-up initialisation complete!", "SUCCESS")

    # All setup complete - start the server
    cui_instance.print("Starting server...", "INFO")
    try:
        server_app_instance = Server.create_app(config_instance, project_instances, system_info_instance)
        return server_app_instance, config_instance, cui_instance
    except Exception as e:
        cui_instance.print(f"Failed to start server: {e}", "ERROR")
        return None, config_instance, cui_instance

# Expose `app` so WSGI servers can import `main:app`
try:
    app, _CONFIG, cui_instance = initialize_server()
except Exception:
    # If initialisation fails during import, print a traceback and re-raise so a process manager sees it.
    traceback.print_exc()
    raise

if __name__ == "__main__":
    # Development run — ALWAYS run with debug=False here to avoid the Werkzeug debugger in production.
    server_host = _CONFIG.config_data.get("server_host") or "127.0.0.1"
    server_port = _CONFIG.config_data.get("server_port") or 23849
    debug_mode = _CONFIG.config_data.get("system", {}).get("debugging", {}).get("flask_debug_mode", False)

    cui_instance.print(f"You are running Simple PyKV in development mode. This is NOT recommended for production use.", "WARNING")
    cui_instance.print(f"For production, please use a WSGI server like Gunicorn or uWSGI to serve the application.", "WARNING")
    cui_instance.print(f"Using development mode can expose severe security risks, potentially allowing remote code execution and data breaches. Please review the documentation for safe deployment practices.", "WARNING")
    cui_instance.print(f"Starting server on {server_host}:{server_port} (development mode)", "INFO")

    # NOTE: debug MUST be False for safety. Use a WSGI server in production instead of this.
    app.run(host=server_host, port=server_port, threaded=True, debug=debug_mode, use_reloader=False)