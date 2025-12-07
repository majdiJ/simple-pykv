from flask import Flask
from routes.root import root_bp
from routes.api_v1 import api_v1_bp
from classes.config import Config
from classes.project import Project
from typing import List

class Server:
    @staticmethod
    def create_app(config_instance : Config | None = None, project_instances: List[Project] | None = None, system_info_instance = None) -> Flask:
        app = Flask(__name__)

        # attach config and project instances to app for access in routes
        app.extensions['config_instance'] = config_instance
        app.extensions['project_instances'] = project_instances
        app.extensions['system_info_instance'] = system_info_instance

        # register blueprints
        app.register_blueprint(root_bp, url_prefix='/')
        app.register_blueprint(api_v1_bp, url_prefix='/api/v1')

        return app