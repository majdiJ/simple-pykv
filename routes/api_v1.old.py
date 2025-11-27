from flask import Blueprint, current_app, jsonify, request, abort
from utils.auth_utils import verify_api_key, generate_api_key, hash_api_key
# We need to import the class to instantiate new projects dynamically
from classes.database import ProjectKVStore
import os

api_v1_bp = Blueprint('api_v1', __name__)

# --- Auth Helpers ---

def check_global_auth():
    """Verifies the global API key found in X-API-Key header."""
    config = current_app.config['KV_CONFIG']['system']
    auth_conf = config.get('authentication', {})
    
    if not auth_conf.get('enabled', True):
        return True # Auth disabled

    api_key_header = request.headers.get('X-API-Key')
    if not api_key_header:
        abort(401, "Missing X-API-Key header")

    stored_hash = auth_conf.get('api_key_hash')
    if not stored_hash or not verify_api_key(api_key_header, stored_hash):
        abort(403, "Invalid Global API Key")

def check_project_auth(project_store):
    """Verifies project-specific API key."""
    auth_conf = project_store.projectConfig.get('authentication', {})
    
    if not auth_conf.get('enabled', True):
        return True # Auth disabled for this project

    api_key_header = request.headers.get('X-API-Key')
    if not api_key_header:
        abort(401, "Missing X-API-Key header")
        
    stored_hash = auth_conf.get('api_key_hash')
    if not stored_hash or not verify_api_key(api_key_header, stored_hash):
        abort(403, "Invalid Project API Key")

def _scrub_config(config_dict):
    """Helper to remove sensitive data (hashes/keys) from response."""
    clean = dict(config_dict)
    if 'authentication' in clean:
        clean['authentication'] = dict(clean['authentication'])
        clean['authentication'].pop('api_key', None)
        clean['authentication'].pop('api_key_hash', None)
    return clean

# --- Global Project Management Routes ---

@api_v1_bp.route('/projects', methods=['GET'])
def list_projects():
    check_global_auth()
    db = current_app.extensions.get('kvdb')
    if db is None:
        abort(500, "DB not configured")

    project_ids = db.list_project_ids()
    if project_ids is None:
        abort(403, "Project discovery is disabled")

    projects = []
    for pid in project_ids:
        store = db.get_store(pid)
        if store:
            projects.append(_scrub_config(store.projectConfig))
            
    return jsonify(projects)

@api_v1_bp.route('/projects', methods=['POST'])
def create_project():
    check_global_auth()
    db = current_app.extensions.get('kvdb')
    data = request.get_json()
    
    if not data:
        abort(400, "Invalid JSON")
        
    # Generate ID if not provided
    if 'id' not in data:
        import uuid
        data['id'] = str(uuid.uuid4())
        
    project_id = data['id']
    
    # Check for duplicate
    if db.get_store(project_id):
        abort(409, f"Project ID '{project_id}' already exists")

    # Handle Auth generation for the new project
    new_api_key = None
    if 'authentication' not in data:
        data['authentication'] = {'enabled': True}
    
    if data['authentication'].get('enabled', True):
        new_api_key = generate_api_key()
        # Hash it for storage
        data['authentication']['api_key_hash'] = hash_api_key(new_api_key)
        # Handle "save_api_key_to_file" logic (usually false for security)
        if data['authentication'].get('save_api_key_to_config', False):
             data['authentication']['api_key'] = new_api_key
        else:
             data['authentication']['api_key'] = None

    # Instantiate the Store
    base_storage = db.base_storage
    new_store = ProjectKVStore(data, base_storage)
    
    # Add to DB manager
    db.projects[project_id] = new_store
    
    # Add to Global Config (RAM only - requires system config save implementation)
    current_app.config['KV_CONFIG']['projects'].append(data)
    
    # Response
    response_data = _scrub_config(data)
    if new_api_key:
        response_data['api_key'] = new_api_key  # Return the raw key once
        
    return jsonify(response_data), 201

@api_v1_bp.route('/projects/<project_id>', methods=['DELETE'])
def delete_project(project_id):
    check_global_auth()
    db = current_app.extensions.get('kvdb')
    store = db.get_store(project_id)
    
    if not store:
        abort(404, "Project not found")
        
    # 1. Remove from DB (Memory)
    del db.projects[project_id]
    
    # 2. Remove from Config (Memory)
    current_app.config['KV_CONFIG']['projects'] = [
        p for p in current_app.config['KV_CONFIG']['projects'] if p['id'] != project_id
    ]
    
    # 3. Clean up disk file
    if store.on_disk and store.filePath.exists():
        try:
            os.remove(store.filePath)
        except OSError:
            pass # Log error in real prod
            
    return ('', 204)

@api_v1_bp.route('/projects/<project_id>/api-key/regenerate', methods=['POST'])
def regenerate_project_key(project_id):
    check_global_auth()
    db = current_app.extensions.get('kvdb')
    store = db.get_store(project_id)
    
    if not store:
        abort(404, "Project not found")

    new_key = generate_api_key()
    new_hash = hash_api_key(new_key)
    
    # Update Store
    store.projectConfig['authentication']['api_key_hash'] = new_hash
    store.projectConfig['authentication']['api_key'] = None # Ensure cleartext is gone
    
    return jsonify({
        "project_id": project_id,
        "api_key": new_key,
        "message": "Key regenerated. Store this key safely, it will not be shown again."
    })

# --- Single Project Management Routes ---

@api_v1_bp.route('/projects/<project_id>', methods=['GET'])
def get_project_details(project_id):
    db = current_app.extensions.get('kvdb')
    store = db.get_store(project_id)
    if not store:
        abort(404, "Project not found")
    
    check_project_auth(store)
    return jsonify(_scrub_config(store.projectConfig))

@api_v1_bp.route('/projects/<project_id>', methods=['PUT'])
def update_project_settings(project_id):
    db = current_app.extensions.get('kvdb')
    store = db.get_store(project_id)
    if not store:
        abort(404, "Project not found")
        
    check_project_auth(store)
    
    data = request.get_json()
    if not data:
        abort(400, "Invalid JSON")

    # Prevent updating ID or Auth via this route
    data.pop('id', None)
    data.pop('authentication', None) 
    
    # Deep merge or shallow update? Doing shallow update for now
    store.projectConfig.update(data)
    
    # Note: If changing 'storage' -> 'on_disk', logic needed to trigger file creation
    
    return jsonify(_scrub_config(store.projectConfig))

# --- Key Value Operations ---

@api_v1_bp.route('/projects/<project_id>/keys', methods=['GET'])
def list_all_keys(project_id):
    db = current_app.extensions.get('kvdb')
    store = db.get_store(project_id)
    if not store:
        abort(404, "Project not found")

    check_project_auth(store)
    
    # Check discoverability in project config
    keys = store.listItems() # returns list of tuples (key, val)
    if keys is None:
        abort(403, "Key discovery disabled for this project")
        
    # Convert list of tuples to dict or list of objects
    result = {k: v for k, v in keys}
    return jsonify(result)

@api_v1_bp.route('/projects/<project_id>/keys', methods=['DELETE'])
def delete_all_keys(project_id):
    db = current_app.extensions.get('kvdb')
    store = db.get_store(project_id)
    if not store:
        abort(404, "Project not found")
    
    check_project_auth(store)
    
    store.clearStore()
    return ('', 204)

@api_v1_bp.route('/projects/<project_id>/keys/<path:key>', methods=['GET', 'POST', 'DELETE'])
def key_ops(project_id, key):
    # Using <path:key> allows keys to contain slashes e.g. "users/settings/theme"
    db = current_app.extensions.get('kvdb')
    store = db.get_store(project_id)
    if not store:
        abort(404, "Project not found")

    check_project_auth(store)

    if request.method == 'GET':
        val = store.getValue(key)
        if val is None:
            abort(404, "Key not found")
        return jsonify({'key': key, 'value': val})

    if request.method == 'POST':
        # logic: Accept JSON {"value": ...} OR raw string body
        data = request.get_json(silent=True)
        if data and isinstance(data, dict) and 'value' in data:
            value = data['value']
        else:
            # Fallback to raw data (good for simple string storage)
            value = request.get_data(as_text=True)
            
        store.setValue(key, value)
        return jsonify({'key': key, 'value': value}), 201

    if request.method == 'DELETE':
        store.deleteValue(key)
        return ('', 204)