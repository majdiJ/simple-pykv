# routes/users.py
from flask import Blueprint, request, jsonify, abort
import threading
from itertools import count

users_bp = Blueprint('users', __name__)

# in-memory store and a lock for safe concurrent writes
_users = {}
_users_lock = threading.Lock()
_user_id_counter = count(1)

@users_bp.route('/', methods=['GET'])
def list_users():
    """GET /users/ -> list all users"""
    return jsonify(list(_users.values())), 200

@users_bp.route('/', methods=['POST'])
def create_user():
    """POST /users/ -> create a new user (expects JSON {'name': '...'})"""
    data = request.get_json(silent=True) or {}
    name = data.get('name')
    if not name:
        return jsonify({'error': 'name required'}), 400

    with _users_lock:
        new_id = str(next(_user_id_counter))
        user = {'id': new_id, 'name': name}
        _users[new_id] = user

    return jsonify(user), 201

@users_bp.route('/<user_id>', methods=['GET'])
def get_user(user_id):
    user = _users.get(user_id)
    if not user:
        return jsonify({'error': 'not found'}), 404
    return jsonify(user), 200

@users_bp.route('/<user_id>', methods=['PUT'])
def update_user(user_id):
    """Replace user data"""
    data = request.get_json(silent=True) or {}
    name = data.get('name')
    if not name:
        return jsonify({'error': 'name required'}), 400

    with _users_lock:
        if user_id not in _users:
            return jsonify({'error': 'not found'}), 404
        _users[user_id]['name'] = name
        user = _users[user_id]

    return jsonify(user), 200

@users_bp.route('/<user_id>', methods=['DELETE'])
def delete_user(user_id):
    with _users_lock:
        if user_id not in _users:
            return jsonify({'error': 'not found'}), 404
        del _users[user_id]
    return '', 204
