# routes/main.py
from ast import List
from flask import Blueprint, Config, request, jsonify, abort, current_app
from classes.project import Project
from classes.system_info import system_info
from routes.api_v1 import verify_authentication
import logging

root_bp = Blueprint('root', __name__)

@root_bp.route('/status', methods=['GET'])
def server_status():
    config_instance: Config = current_app.extensions.get('config_instance')
    project_instances: List[Project] = current_app.extensions.get('project_instances')
    system_info_instance : system_info = current_app.extensions.get('system_info_instance')

    config_data = config_instance.get_config_data() if config_instance else None
    system_authentication_config = config_data.get('system', {}).get('authentication', {}) if config_data else {}

    # Require authentication for full system info, otherwise return minimal info
    try:
        if verify_authentication(system_authentication_config, request) is False:
            message = {
                "status": "running",
                "message": "Simple PyKV server is operational. Provide correct API key for full system information.",
            }
            return jsonify(message), 200
    except ValueError as ve:
        message = {
                "status": "running",
                "message": "Simple PyKV server is operational. Internal server error during authentication. View server logs for details.",
            }
        return jsonify(message), 500

    return system_info_instance.get_system_info()