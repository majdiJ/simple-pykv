from flask import jsonify
from classes import system_info

def create_response(message, status_code=200, system_info: system_info = None, data=None):
    response = {
        "status_code": status_code,
        "message": message,
        "System": system_info.get_system_info() if system_info else None,
        "data": data
    }
    return jsonify(response), status_code