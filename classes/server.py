from flask import Flask
from routes.main import main_bp
from routes.api_v1 import api_v1_bp

class Server:
    def create_app(config_data = None, database_instance = None):
        app = Flask(__name__)

        # store config & db in the app
        app.config['KV_CONFIG'] = config_data
        app.extensions['kvdb'] = database_instance

        app.register_blueprint(main_bp, url_prefix='/')
        app.register_blueprint(api_v1_bp, url_prefix='/api/v1')
        
        return app