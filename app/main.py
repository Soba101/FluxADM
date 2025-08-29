"""
Main Flask application factory for FluxADM
Creates and configures the Flask app with all extensions and blueprints
"""
from flask import Flask
from flask_cors import CORS
from flask_restx import Api
import logging
import structlog

from config import get_settings
from app.models import init_db
from app.api import create_api_blueprint


def create_app(config_override=None):
    """
    Application factory pattern for creating Flask app
    
    Args:
        config_override: Optional configuration overrides for testing
    
    Returns:
        Configured Flask application instance
    """
    app = Flask(__name__)
    
    # Load configuration
    settings = get_settings()
    if config_override:
        settings = config_override
    
    app.config['SECRET_KEY'] = settings.SECRET_KEY
    app.config['DEBUG'] = settings.DEBUG
    app.config['SQLALCHEMY_DATABASE_URI'] = settings.DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAX_CONTENT_LENGTH'] = settings.max_file_size_bytes
    
    # Configure structured logging
    configure_logging(settings)
    
    # Initialize extensions
    CORS(app)
    
    # Initialize database
    init_db(app)
    
    # Register API blueprints
    api_blueprint = create_api_blueprint()
    app.register_blueprint(api_blueprint, url_prefix='/api/v1')
    
    # Health check endpoint
    @app.route('/health')
    def health_check():
        """Simple health check endpoint"""
        return {
            'status': 'healthy',
            'version': app.config.get('VERSION', '1.0.0'),
            'service': 'FluxADM'
        }
    
    # Root redirect to API documentation
    @app.route('/')
    def index():
        """Redirect to API documentation"""
        return {
            'message': 'FluxADM API',
            'version': '1.0.0',
            'documentation': '/api/v1/',
            'health': '/health'
        }
    
    return app


def configure_logging(settings):
    """Configure structured logging for the application"""
    
    logging.basicConfig(
        format='%(message)s',
        level=getattr(logging, settings.LOG_LEVEL.upper())
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="ISO"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
            if settings.LOG_FORMAT == "json"
            else structlog.dev.ConsoleRenderer()
        ],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )


if __name__ == '__main__':
    app = create_app()
    settings = get_settings()
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=settings.DEBUG
    )