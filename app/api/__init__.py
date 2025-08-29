"""FluxADM REST API Package"""

from flask import Blueprint
from flask_restx import Api

from .change_requests import api as cr_api
from .auth import api as auth_api
from .dashboard import api as dashboard_api


def create_api_blueprint():
    """Create API blueprint with all namespaces"""
    
    blueprint = Blueprint('api', __name__)
    
    api = Api(
        blueprint,
        title='FluxADM API',
        version='1.0.0',
        description='AI-Powered Change Request Analyzer API',
        doc='/doc/',  # Swagger UI endpoint
        authorizations={
            'Bearer': {
                'type': 'apiKey',
                'in': 'header',
                'name': 'Authorization',
                'description': 'JWT token. Example: "Bearer your-jwt-token"'
            }
        },
        security='Bearer'
    )
    
    # Register namespaces
    api.add_namespace(auth_api, path='/auth')
    api.add_namespace(cr_api, path='/change-requests')
    api.add_namespace(dashboard_api, path='/dashboard')
    
    return blueprint