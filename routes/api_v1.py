from werkzeug.exceptions import HTTPException
from flask import Blueprint, current_app, jsonify, request, abort
from utils.auth_utils import generate_api_key, hash_api_key, verify_api_key, compare_api_key
from classes.config import Config
from classes.project import Project
from typing import List
import logging
from utils.security_utils import scrub_secrets
from classes.system_info import system_info
from utils.http_response import create_response

api_v1_bp = Blueprint('api_v1', __name__)

# API key verification helpers
# Extract API key from request headers either from Authorization Bearer, X-API-Key or Api-Key
def extract_api_key(req=None):
    req = req or request
    auth = req.headers.get("Authorization", "")
    if auth:
        parts = auth.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
    # fallback header names
    return req.headers.get("X-API-Key") or req.headers.get("Api-Key")

# Verify request API key against config authentication data (for system or project)
def verify_authentication(config_data_authentication, req=None) -> bool:
    try:
        req = req or request
        
        if not config_data_authentication:
            logging.error("Configuration data / instance is missing")
            status_code = 500
            message = "Internal server error: View server logs for details."
            return False, create_response(message=message, status_code=status_code)

        if not config_data_authentication.get('enabled', True):
            return True, None  # No authentication required
        else:
            system_api_key = config_data_authentication.get('api_key')
            system_api_key_hash = config_data_authentication.get('api_key_hash')
            req_api_key = extract_api_key(req)

            # Construct failed API key response
            status_code = 401
            message = "Invalid or missing API key"

            # Use api_key if available, else use api_key_hash
            if system_api_key: 
                if req_api_key and compare_api_key(req_api_key, system_api_key):
                    return True, None
                else:
                    return False, create_response(message=message, status_code=status_code)
            elif system_api_key_hash:
                if req_api_key and verify_api_key(req_api_key, system_api_key_hash):
                    return True, None
                else:
                    return False, create_response(message=message, status_code=status_code)
            else:
                logging.error("Authentication is enabled but no API key or hash is configured")
                status_code = 500
                message = "Internal server error: View server logs for details."
                return False, create_response(message=message, status_code=status_code)
            
    except ValueError as ve:
        logging.error(f"Authentication error: {ve}")
        status_code = 500
        message = "Internal server error during authentication. View server logs for details."
        return False, create_response(message=message, status_code=status_code)
       
# ROUTE>>> List all projects
@api_v1_bp.route('/projects', methods=['GET'])
def list_projects():
    config_instance : Config = current_app.extensions.get('config_instance')
    project_instances : List[Project]  = current_app.extensions.get('project_instances')
    system_info_instance : system_info = current_app.extensions.get('system_info_instance')

    config_data = config_instance.get_config_data() if config_instance else None
    authentication_config = config_data.get('system', {}).get('authentication', {}) if config_data else {}
    
    verified, auth_response = verify_authentication(authentication_config, request)
    if not verified:
        return auth_response
    
    try:
        discoverability = config_data.get('system', {}).get('security', {}).get('project_discoverable', False) if config_data else False
        if not discoverability:
            status_code = 403
            message = "Project listing is disabled"
            return create_response(message=message, status_code=status_code, system_info=system_info_instance)

        projects = {}
        for project in project_instances or []:
            config = project.get_project_config() or {}
            project_id = (
                config.get("id")
                or getattr(project, "id", None)
                or f"project_{len(projects) + 1}"
            )

            safe_config = scrub_secrets(config)

            if isinstance(safe_config, dict):
                safe_config.pop("id", None)

            item = {}
            if isinstance(safe_config, dict):
                item.update(safe_config)
            else:
                item["config"] = safe_config

            projects[project_id] = item

        status_code = 200
        message = "Project listing fetched successfully"
        data = projects
        return create_response(message=message, status_code=status_code, system_info=system_info_instance, data=data)
    
    except Exception as e:
        logging.exception("Unexpected error during project listing")
        status_code = 500
        message = "Internal server error during project listing. View server logs for details."
        return create_response(message=message, status_code=status_code, system_info=system_info_instance)

# ROUTE>>> Create a new project
@api_v1_bp.route('/projects', methods=['POST'])
def create_project():
    config_instance : Config = current_app.extensions.get('config_instance')
    project_instances : List[Project]  = current_app.extensions.get('project_instances')
    system_info_instance : system_info = current_app.extensions.get('system_info_instance')

    config_data = config_instance.get_config_data() if config_instance else None
    authentication_config = config_data.get('system', {}).get('authentication', {}) if config_data else {}

    verified, auth_response = verify_authentication(authentication_config, request)
    if not verified:
        return auth_response

    try:
        payload = request.get_json(silent=True)

        if payload is None:
            status_code = 400
            message = "Request body must be valid JSON (Content-Type: application/json)"
            return create_response(message=message, status_code=status_code, system_info=system_info_instance)

        project_id = payload.get("id")

        if not project_id:
            status_code = 400
            message = "Project 'id' is required in the request body"
            return create_response(message=message, status_code=status_code, system_info=system_info_instance)

        api_key = config_instance.add_project(payload)

        new_project_instance = Project(config_instance, project_id)
        if project_instances is not None:
            project_instances.append(new_project_instance)

        if api_key is not None:
            status_code = 201
            message = "Project created successfully. Store the returned API key securely as it may not be shown again."
            data = {
                "new_api_key": api_key
            }
            return create_response(message=message, status_code=status_code, system_info=system_info_instance, data=data)
        else:
            status_code = 201
            message = "Project created successfully. No API key generated (authentication for this project may be disabled)."
            return create_response(message=message, status_code=status_code, system_info=system_info_instance)
    
    except ValueError as ve:
        logging.error(f"Project creation error: {ve}")
        msg = str(ve)

        if "already exists in configuration" in msg:
            status_code = 400
            message = msg
            return create_response(message=message, status_code=status_code, system_info=system_info_instance)
        
        status_code = 500
        message = "Internal server error during project creation. View server logs for details."
        return create_response(message=message, status_code=status_code, system_info=system_info_instance)

    except Exception as e:
        logging.exception("Unexpected error during project creation")

        status_code = 500
        message = "Internal server error during project creation. View server logs for details."
        return create_response(message=message, status_code=status_code, system_info=system_info_instance)

# ROUTE>>> Regenerate and return a new API key for the specified project (updates API key hash, requires global API key)
@api_v1_bp.route('/projects/<string:project_id>/config/regenerate-api-key', methods=['POST'])
def regenerate_project_api_key(project_id):
    config_instance: Config = current_app.extensions.get('config_instance')
    project_instances: List[Project] = current_app.extensions.get('project_instances')
    system_info_instance : system_info = current_app.extensions.get('system_info_instance')

    config_data = config_instance.get_config_data() if config_instance else None
    authentication_config = config_data.get('system', {}).get('authentication', {}) if config_data else {}

    verified, auth_response = verify_authentication(authentication_config, request)
    if not verified:
        return auth_response

    try:
        project_instance = next(
            (project for project in project_instances or [] if getattr(project, "id", None) == project_id), None
        )

        if not project_instance:
            status_code = 404
            message = f"Project with id '{project_id}' not found"
            return create_response(message=message, status_code=status_code, system_info=system_info_instance)

        new_api_key = config_instance.regenerate_project_api_key(project_id)

        if new_api_key is None:
            logging.error(f"API key regeneration failed for project '{project_id}'")
            status_code = 500
            message = f"Failed to regenerate API key for the project (authentication may be disabled for `{project_id}`)"
            return create_response(message=message, status_code=status_code, system_info=system_info_instance)

        status_code = 200
        message = f"API key regenerated successfully for project '{project_id}'"
        data = {
            "new_api_key": new_api_key
        }
        return create_response(message=message, status_code=status_code, data=data, system_info=system_info_instance)
    
    except HTTPException:
        raise

    except Exception as e:
        logging.exception("Unexpected error during API key regeneration")
        status_code = 500
        message = "Internal server error during API key regeneration. View server logs for details."
        return create_response(message=message, status_code=status_code, system_info=system_info_instance)

# ROUTE>>> Delete a project
@api_v1_bp.route('/projects/<string:project_id>', methods=['DELETE'])
def delete_project(project_id):
    config_instance : Config = current_app.extensions.get('config_instance')
    project_instances : List[Project]  = current_app.extensions.get('project_instances')
    system_info_instance : system_info = current_app.extensions.get('system_info_instance')

    config_data = config_instance.get_config_data() if config_instance else None
    authentication_config = config_data.get('system', {}).get('authentication', {}) if config_data else {}

    verified, auth_response = verify_authentication(authentication_config, request)
    if not verified:
        return auth_response
    
    try:
        project_instance = next(
            (project for project in project_instances or [] if getattr(project, "id", None) == project_id), None
        )
        
        if project_instance:
            config_instance.delete_project_config(project_id)
            project_instance.delete_store_file()
            project_instances.remove(project_instance)
            status_code = 200
            message = f"Project '{project_id}' deleted successfully"
            return create_response(message=message, status_code=status_code, system_info=system_info_instance)
        else:
            status_code = 404
            message = f"Project with id '{project_id}' not found"
            return create_response(message=message, status_code=status_code, system_info=system_info_instance)
    
    except HTTPException:
        raise

    except Exception as e:
        logging.exception("Unexpected error during project deletion")
        status_code = 500
        message = "Internal server error during project deletion. View server logs for details."
        return create_response(message=message, status_code=status_code, system_info=system_info_instance)

# Project Management (requires project API key when that project's authentication is enabled)
# ROUTE>>> Get project details
@api_v1_bp.route('/projects/<string:project_id>', methods=['GET'])
def get_project_details(project_id):
    config_instance : Config = current_app.extensions.get('config_instance')
    project_instances : List[Project]  = current_app.extensions.get('project_instances')
    system_info_instance : system_info = current_app.extensions.get('system_info_instance')

    project_instance = next(
        (project for project in project_instances or [] if getattr(project, "id", None) == project_id), None
    )

    if not project_instance:
        status_code = 404
        message = f"Project with id '{project_id}' not found"
        return create_response(message=message, status_code=status_code, system_info=system_info_instance)

    project_config = project_instance.get_project_config()
    authentication_config = project_config.get('authentication', {}) if project_config else {}

    try:
        if verify_authentication(authentication_config, request) is False:
            status_code = 401
            message = "Invalid or missing API key"
            return create_response(message=message, status_code=status_code, system_info=system_info_instance)
    except ValueError as ve:
        logging.error(f"Project details authentication error: {ve}")
        status_code = 500
        message = "Internal server error during authentication. View server logs for details."
        return create_response(message=message, status_code=status_code, system_info=system_info_instance)
    
    try:
        safe_config = scrub_secrets(project_config)

        if isinstance(safe_config, dict):
            safe_config.pop("id", None)

        item = {"id": project_id}
        if isinstance(safe_config, dict):
            item.update(safe_config)
        else:
            item["config"] = safe_config

        status_code = 200
        message = f"Project '{project_id}' details fetched successfully"
        data = item
        return create_response(message=message, status_code=status_code, system_info=system_info_instance, data=data)

    except Exception as e:
        logging.exception("Unexpected error during fetching project details")
        status_code = 500
        message = "Internal server error during fetching project details. View server logs for details."
        return create_response(message=message, status_code=status_code, system_info=system_info_instance)

# ROUTE>>> Update project settings excluding API key, API hash ID (requires project API key if authentication is enabled)
@api_v1_bp.route('/projects/<string:project_id>', methods=['PUT'])
def update_project_settings(project_id):
    config_instance : Config = current_app.extensions.get('config_instance')
    project_instances : List[Project]  = current_app.extensions.get('project_instances')

    project_instance = next(
        (project for project in project_instances or [] if getattr(project, "id", None) == project_id), None
    )

    if not project_instance:
        status_code = 404
        message = f"Project with id '{project_id}' not found"
        return create_response(message=message, status_code=status_code)

    project_config = project_instance.get_project_config()
    authentication_config = project_config.get('authentication', {}) if project_config else {}

    verified, auth_response = verify_authentication(authentication_config, request)
    if not verified:
        return auth_response

    try:
        payload = request.get_json(silent=True)

        if payload is None:
            status_code = 400
            message = "Request body must be valid JSON (Content-Type: application/json)"
            return create_response(message=message, status_code=status_code)
        
        if "authentication" in payload:
            status_code = 400
            message = "Updating authentication settings via this route is not allowed. Use the regenerate API key route instead."
            return create_response(message=message, status_code=status_code)
        
        if "id" in payload:
            status_code = 400
            message = "Updating project ID via this route is not allowed."
            return create_response(message=message, status_code=status_code)

        config_instance.update_project_config(project_id, payload)
        status_code = 200
        message = f"Project '{project_id}' updated successfully"
        return create_response(message=message, status_code=status_code)

    except Exception as e:
        logging.exception("Unexpected error during project update")
        status_code = 500
        message = "Internal server error during project update. View server logs for details."
        return create_response(message=message, status_code=status_code)

# ROUTE>>> Retrieve all keys and values for the project (requires project API key if authentication is enabled)
@api_v1_bp.route('/projects/<string:project_id>/store', methods=['GET'])
def get_project_store(project_id):
    config_instance : Config = current_app.extensions.get('config_instance')
    project_instances : List[Project]  = current_app.extensions.get('project_instances')

    project_instance = next(
        (project for project in project_instances or [] if getattr(project, "id", None) == project_id), None
    )

    if not project_instance:
        status_code = 404
        message = f"Project with id '{project_id}' not found"
        return create_response(message=message, status_code=status_code)

    project_config = project_instance.get_project_config()
    authentication_config = project_config.get('authentication', {}) if project_config else {}

    verified, auth_response = verify_authentication(authentication_config, request)
    if not verified:
        return auth_response

    try:
        discoverability = project_config.get('security', {}).get('keys_and_values_discoverable', False) if project_config else False
        if discoverability:
            value = project_instance.listItems()
            return create_response(message="", status_code=200, data=value)
        else:
            status_code = 403
            message = "Retrieving all keys and values is disabled for this project"
            return create_response(message=message, status_code=status_code)        

    except Exception as e:
        logging.exception("Unexpected error during fetching project store")
        status_code = 500
        message = "Internal server error during fetching project store. View server logs for details."
        return create_response(message=message, status_code=status_code)

# ROUTE>>> Create or update a key-value pair for the project (requires project API key if authentication is enabled)
@api_v1_bp.route('/projects/<string:project_id>/store/<string:key>', methods=['PUT'])
def put_project_store_key_value(project_id, key):
    project_instances : List[Project]  = current_app.extensions.get('project_instances')
    config_instance : Config = current_app.extensions.get('config_instance')
    system_info_instance : system_info = current_app.extensions.get('system_info_instance')

    project_instance = next(
        (project for project in project_instances or [] if getattr(project, "id", None) == project_id), None
    )

    if not project_instance:
        status_code = 404
        message = f"Project with id '{project_id}' not found"
        return create_response(message=message, status_code=status_code, system_info=None)

    project_config = project_instance.get_project_config()
    authentication_config = project_config.get('authentication', {}) if project_config else {}

    verified, auth_response = verify_authentication(authentication_config, request)
    if not verified:
        return auth_response

    try:
        payload = request.get_json(silent=True)
        if payload is None:
            raw = request.get_data(as_text=True)
            if not raw:
                status_code = 400
                message = "Request body must be valid JSON or non-empty plain text"
                return create_response(message=message, status_code=status_code, system_info=system_info_instance)
            payload = raw

        project_instance.setValue(key, payload)

        status_code = 200
        message = f"Key '{key}' set successfully in project '{project_id}' store"
        return create_response(message=message, status_code=status_code, system_info=system_info_instance)
    except Exception as e:
        logging.exception("Unexpected error during updating project store key-value")
        status_code = 500
        message = "Internal server error during updating project store key-value. View server logs for details."
        return create_response(message=message, status_code=status_code, system_info=system_info_instance)

# ROUTE>>> Retrieve the value and metadata for a specific key (requires project API key if authentication is enabled)
@api_v1_bp.route('/projects/<string:project_id>/store/<string:key>', methods=['GET'])
def get_project_store_key_value(project_id, key):
    project_instances : List[Project]  = current_app.extensions.get('project_instances')
    system_info_instance : system_info = current_app.extensions.get('system_info_instance')

    project_instance = next(
        (project for project in project_instances or [] if getattr(project, "id", None) == project_id), None
    )

    if not project_instance:
        status_code = 404
        message = f"Project with id '{project_id}' not found"
        return create_response(message=message, status_code=status_code, system_info=None)

    project_config = project_instance.get_project_config()
    authentication_config = project_config.get('authentication', {}) if project_config else {}

    verified, auth_response = verify_authentication(authentication_config, request)
    if not verified:
        return auth_response

    try:
        if key in project_instance.store:
            message = f"Key '{key}' fetched successfully from project '{project_id}' store"
            value = project_instance.getValue(key)
            return create_response(message=message, status_code=200, data=value, system_info=system_info_instance)
        else:
            status_code = 404
            message = f"Key '{key}' not found in project '{project_id}' store"
            return create_response(message=message, status_code=status_code, system_info=system_info_instance)
    except Exception as e:
        logging.exception("Unexpected error during fetching project store key-value")
        status_code = 500
        message = "Internal server error during fetching project store key-value. View server logs for details."
        return create_response(message=message, status_code=status_code, system_info=system_info_instance)

# ROUTE>>> Retrieve only the value for a specific key (requires project API key if authentication is enabled)
@api_v1_bp.route('/projects/<string:project_id>/store/<string:key>/value', methods=['GET'])
def get_project_store_key_value_only(project_id, key):
    project_instances : List[Project]  = current_app.extensions.get('project_instances')

    project_instance = next(
        (project for project in project_instances or [] if getattr(project, "id", None) == project_id), None
    )

    if not project_instance:
        status_code = 404
        message = f"Project with id '{project_id}' not found"
        return create_response(message=message, status_code=status_code)

    project_config = project_instance.get_project_config()
    authentication_config = project_config.get('authentication', {}) if project_config else {}

    verified, auth_response = verify_authentication(authentication_config, request)
    if not verified:
        return auth_response

    try:
        if key in project_instance.store:
            # This route response will only include the value, will not use `create_response` method
            return project_instance.getValueOnly(key)
        else:
            status_code = 404
            message = f"Key '{key}' not found in project '{project_id}' store"
            return create_response(message=message, status_code=status_code)
    except Exception as e:
        logging.exception("Unexpected error during fetching project store key value-only")
        status_code = 500
        message = "Internal server error during fetching project store key value-only. View server logs for details."
        return create_response(message=message, status_code=status_code)

# ROUTE>>> Delete a specific key-value pair (requires project API key if authentication is enabled)
@api_v1_bp.route('/projects/<string:project_id>/store/<string:key>', methods=['DELETE'])
def delete_project_store_key_value(project_id, key):
    project_instances : List[Project]  = current_app.extensions.get('project_instances')

    project_instance = next(
        (project for project in project_instances or [] if getattr(project, "id", None) == project_id), None
    )

    if not project_instance:
        status_code = 404
        message = f"Project with id '{project_id}' not found"
        return create_response(message=message, status_code=status_code)

    project_config = project_instance.get_project_config()
    authentication_config = project_config.get('authentication', {}) if project_config else {}

    verified, auth_response = verify_authentication(authentication_config, request)
    if not verified:
        return auth_response

    try:
        if key in project_instance.store:
            project_instance.deleteKey(key)
            status_code = 200
            message = f"Key '{key}' deleted successfully from project '{project_id}' store"
            return create_response(message=message, status_code=status_code)
        else:
            status_code = 404
            message = f"Key '{key}' not found in project '{project_id}' store"
            return create_response(message=message, status_code=status_code)
    except Exception as e:
        logging.exception("Unexpected error during deleting project store key-value")
        status_code = 500
        message = "Internal server error during deleting project store key-value. View server logs for details."
        return create_response(message=message, status_code=status_code)

# ROUTE>>> Delete all key-value pairs for the project (requires project API key if authentication is enabled)
@api_v1_bp.route('/projects/<string:project_id>/store', methods=['DELETE'])
def delete_project_store_all_key_values(project_id):
    project_instances : List[Project]  = current_app.extensions.get('project_instances')

    project_instance = next(
        (project for project in project_instances or [] if getattr(project, "id", None) == project_id), None
    )

    if not project_instance:
        status_code = 404
        message = f"Project with id '{project_id}' not found"
        return create_response(message=message, status_code=status_code)

    project_config = project_instance.get_project_config()
    authentication_config = project_config.get('authentication', {}) if project_config else {}

    verified, auth_response = verify_authentication(authentication_config, request)
    if not verified:
        return auth_response

    try:
        project_instance.clearStore()
        status_code = 200
        message = f"All key-value pairs deleted successfully from project '{project_id}' store"
        return create_response(message=message, status_code=status_code)
    except Exception as e:
        logging.exception("Unexpected error during deleting all project store key-values")
        status_code = 500
        message = "Internal server error during deleting all project store key-values. View server logs for details."
        return create_response(message=message, status_code=status_code)
