# routes/main.py
from ast import List
from flask import Blueprint, Config, request, jsonify, abort, current_app
from classes.project import Project
from classes.system_info import system_info
from routes.api_v1 import verify_authentication
import logging
from utils.http_response import create_response

root_bp = Blueprint('root', __name__)

@root_bp.route('/status', methods=['GET'])
def server_status():
    config_instance: Config = current_app.extensions.get('config_instance')
    project_instances: List[Project] = current_app.extensions.get('project_instances')
    system_info_instance : system_info = current_app.extensions.get('system_info_instance')

    config_data = config_instance.config_data if config_instance else None
    authentication_config = config_data.get('system', {}).get('authentication', {}) if config_data else {}

    # Require authentication for full system info
    verified, auth_response = verify_authentication(authentication_config, request)
    if not verified:
        return auth_response

    status_code = 200
    message = "Simple PyKV server is fully operational."
    return create_response(message, status_code, system_info=system_info_instance)