from flask import Flask
from app.config import Config
from app.extensions import db, scheduler

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize Flask extensions
    db.init_app(app)
    scheduler.init_app(app)

    # Register blueprints
    from app.web import bp as web_bp
    app.register_blueprint(web_bp)

    # Create database tables
    with app.app_context():
        db.create_all()

    # Register scheduled jobs
    from app.core.scheduler_jobs import register_jobs
    register_jobs(scheduler, app)

    # Start scheduler
    scheduler.start()

    return app
