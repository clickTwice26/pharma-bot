from flask import Flask
from app.models import db
from app.config import Config
from flask_migrate import Migrate

migrate = Migrate()


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize database
    db.init_app(app)
    
    # Initialize Flask-Migrate
    migrate.init_app(app, db)
    
    # Register blueprints
    from app.routes.main import main_bp
    from app.api.routes import api_bp
    app.register_blueprint(main_bp)
    app.register_blueprint(api_bp)
    
    # Import models to register them with SQLAlchemy
    with app.app_context():
        from app.models.user import User
        from app.models.prescription import Prescription
        from app.models.medicine import Medicine
        from app.models.schedule import Schedule
        from app.models.iot_device import IoTDevice
        db.create_all()
    
    return app
