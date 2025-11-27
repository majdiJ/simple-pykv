from flask import Blueprint, current_app, jsonify, request, abort
from utils.auth_utils import generate_api_key, hash_api_key, verify_api_key, compare_api_key

api_v1_bp = Blueprint('api_v1', __name__)

def extract_api_key(req=None):
    # Return the API key string from the request, or None if not present.
    # Looks for either Authorization: Bearer <key>, X-API-Key, or Api-Key
    req = req or request
    auth = req.headers.get("Authorization", "")
    if auth:
        parts = auth.split()
        if len(parts) == 2 and parts[0].lower() == "bearer":
            return parts[1]
    # fallback header names
    return req.headers.get("X-API-Key") or req.headers.get("Api-Key")

# List all projects (Requires system API key and discoverability enabled)
@api_v1_bp.route('/projects', methods=['GET'])
def list_projects():
    config_data = current_app.config.get('KV_CONFIG')
    database_instance = current_app.extensions.get('kvdb')

    # Verify system API key if configured
    system_auth_enabled = config_data.get('system_auth_enabled', False) if config_data else False
    system_api_key = config_data.get('system_api_key') if config_data else None
    system_api_key_hash = config_data.get('system_api_key_hash') if config_data else None

    # Use api_key if available, else use api_key_hash
    if system_auth_enabled:
        # If both are set, prefer api_key
        if system_api_key: 
            req_api_key = extract_api_key()
            if not req_api_key or not compare_api_key(req_api_key, system_api_key):
                abort(401, "Invalid or missing API key")
        # If only api_key_hash is set
        elif system_api_key_hash:
            req_api_key = extract_api_key()
            if not req_api_key or not verify_api_key(req_api_key, system_api_key_hash):
                abort(401, "Invalid or missing API key")

    # Ensure database instance is available
    if database_instance is None:
        abort(500, "Internal error: Key-Value database not configured")

    # Check config has 'discoverability' setting enabled for listing projects
    discoverability = config_data.get('discoverability', False) if config_data else False
    if not discoverability:
        abort(403, "Project listing is disabled")
    
    # example: list project IDs (db.list_project_ids respects discoverability)
    projects = database_instance.list_project_ids() or []
    return jsonify(projects)

# Create a new project (Requires system API key)
@api_v1_bp.route('/projects', methods=['POST'])
def create_project():
    config_data = current_app.config.get('KV_CONFIG')
    database_instance = current_app.extensions.get('kvdb')

    # Verify system API key if configured
    system_auth_enabled = config_data.get('system_auth_enabled', False) if config_data else False
    system_api_key = config_data.get('system_api_key') if config_data else None
    system_api_key_hash = config_data.get('system_api_key_hash') if config_data else None

    # Use api_key if available, else use api_key_hash
    if system_auth_enabled:
        # If both are set, prefer api_key
        if system_api_key: 
            req_api_key = extract_api_key()
            if not req_api_key or not compare_api_key(req_api_key, system_api_key):
                abort(401, "Invalid or missing API key")
        # If only api_key_hash is set
        elif system_api_key_hash:
            req_api_key = extract_api_key()
            if not req_api_key or not verify_api_key(req_api_key, system_api_key_hash):
                abort(401, "Invalid or missing API key")
    
    # Ensure database instance is available
    if database_instance is None:
        abort(500, "Internal error: Key-Value database not configured")
    
    # Parse JSON body for project creation
    # Must contain at least a 'project_id' field, will accept optional fields:
    """
        {
            "id": "first_project",
            "storage": {
                "on_disk": true
            },
            "authentication": {
                "enabled": true,
                "save_api_key_to_config": false
            },
            "security": {
                "key_values_discoverable": true
            }
        }
    """
    # Return success/failure with the API key (if generated)

    # parse JSON body
    payload = request.get_json(silent=True)
    if payload is None:
        # invalid or missing JSON
        abort(400, "Request body must be valid JSON (Content-Type: application/json)")
    # Ensure project_id is present
    project_id = payload.get('id')
    if not project_id:
        abort(400, "Missing required field: id (optional fields: storage, authentication, security)")
    try:
        result = database_instance.create_project(payload)

        # Set default values for optional fields if not provided
        defaults = {
            "storage": {"on_disk": True},
            "authentication": {
                "enabled": False,
                "save_api_key_to_config": False
            },
            "security": {"key_values_discoverable": False}
        }
        for field, default in defaults.items():
            if field not in payload or payload[field] is None:
                payload[field] = default
        
        # Genorate API key if authentication is enabled
        if payload['authentication'].get('enabled', False):
            if payload['authentication'].get('save_api_key_to_config', False):
                # Generate and save API key to config
                result['api_key']  = generate_api_key()
            result['api_key_hash'] = hash_api_key(result['api_key'])

        return jsonify(result), 201
    except Exception as e:
        abort(500, f"Error creating project: {str(e)}")

@api_v1_bp.route('/projects/<project_id>/keys/<key>', methods=['GET', 'POST', 'DELETE'])
def key_ops(project_id, key):
    db = current_app.extensions.get('kvdb')
    store = db.get_store(project_id) if db else None
    if store is None:
        abort(404, "Project not found")

    if request.method == 'GET':
        val = store.getValue(key)
        if val is None:
            return ('', 404)
        return jsonify({'key': key, 'value': val})

    if request.method == 'POST':
        # accept JSON body {"value": ...} or raw body as fallback
        data = request.get_json(silent=True)
        if data and 'value' in data:
            value = data['value']
        else:
            value = request.get_data(as_text=True)
        store.setValue(key, value)
        return jsonify({'key': key, 'value': value}), 201

    if request.method == 'DELETE':
        store.deleteValue(key)
        return ('', 204)
