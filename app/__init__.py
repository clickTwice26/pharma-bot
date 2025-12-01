from flask import Flask
from app.models import db
from app.config import Config


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize database
    db.init_app(app)
    
    # Register blueprints
    from app.routes.main import main_bp
    from app.api.routes import api_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    
    # Create tables
    with app.app_context():
        # Import all models
        from app.models.user import User
        from app.models.prescription import Prescription
        from app.models.medicine import Medicine
        from app.models.schedule import Schedule
        from app.models.iot_device import IoTDevice
        
        db.create_all()
    
    return app
