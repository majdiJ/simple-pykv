# routes/main.py
from flask import Blueprint, request, jsonify, abort

main_bp = Blueprint('main', __name__)

@main_bp.route('/', methods=['GET'])
def list_main():
    return "Server is active and running", 200