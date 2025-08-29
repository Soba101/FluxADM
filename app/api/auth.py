"""Authentication API endpoints"""

from flask import request, jsonify
from flask_restx import Namespace, Resource, fields
import jwt
from datetime import datetime, timedelta
from werkzeug.security import check_password_hash
import structlog

from config import get_settings
from app.models import db, User

logger = structlog.get_logger(__name__)
settings = get_settings()

api = Namespace('auth', description='Authentication operations')

# API Models for documentation
login_model = api.model('Login', {
    'email': fields.String(required=True, description='User email address'),
    'password': fields.String(required=True, description='User password')
})

token_response_model = api.model('TokenResponse', {
    'access_token': fields.String(description='JWT access token'),
    'token_type': fields.String(description='Token type (Bearer)'),
    'expires_in': fields.Integer(description='Token expiration time in seconds'),
    'user': fields.Raw(description='User information')
})

user_model = api.model('User', {
    'id': fields.String(description='User ID'),
    'email': fields.String(description='User email'),
    'full_name': fields.String(description='Full name'),
    'role': fields.String(description='User role'),
    'department': fields.String(description='Department'),
    'is_active': fields.Boolean(description='Active status')
})


@api.route('/login')
class LoginResource(Resource):
    @api.expect(login_model)
    @api.marshal_with(token_response_model)
    def post(self):
        """User login and JWT token generation"""
        try:
            data = request.get_json()
            
            if not data or not data.get('email') or not data.get('password'):
                api.abort(400, 'Email and password are required')
            
            email = data['email'].lower().strip()
            password = data['password']
            
            # Find user
            user = User.query.filter_by(email=email).first()
            
            if not user or not user.is_active:
                logger.warning("Login attempt for inactive/nonexistent user", email=email)
                api.abort(401, 'Invalid credentials')
            
            # Check password
            if not user.check_password(password):
                logger.warning("Failed login attempt", email=email, user_id=str(user.id))
                api.abort(401, 'Invalid credentials')
            
            # Generate JWT token
            token_payload = {
                'user_id': str(user.id),
                'email': user.email,
                'role': user.role,
                'exp': datetime.utcnow() + timedelta(hours=settings.JWT_ACCESS_TOKEN_EXPIRES),
                'iat': datetime.utcnow()
            }
            
            access_token = jwt.encode(
                token_payload, 
                settings.JWT_SECRET_KEY, 
                algorithm='HS256'
            )
            
            # Update last login
            user.update_last_login()
            
            logger.info("User login successful", 
                       email=email, 
                       user_id=str(user.id),
                       role=user.role)
            
            return {
                'access_token': access_token,
                'token_type': 'Bearer',
                'expires_in': settings.JWT_ACCESS_TOKEN_EXPIRES * 3600,
                'user': user.to_dict()
            }
            
        except Exception as e:
            logger.error("Login error", error=str(e))
            api.abort(500, 'Login failed')


@api.route('/me')
class UserProfileResource(Resource):
    @api.doc('get_current_user')
    @api.marshal_with(user_model)
    @api.doc(security='Bearer')
    def get(self):
        """Get current user profile"""
        try:
            # Get token from header
            auth_header = request.headers.get('Authorization')
            if not auth_header or not auth_header.startswith('Bearer '):
                api.abort(401, 'Authorization header required')
            
            token = auth_header.split(' ')[1]
            
            # Decode token
            try:
                payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=['HS256'])
                user_id = payload['user_id']
            except jwt.ExpiredSignatureError:
                api.abort(401, 'Token has expired')
            except jwt.InvalidTokenError:
                api.abort(401, 'Invalid token')
            
            # Get user
            user = User.query.get(user_id)
            if not user or not user.is_active:
                api.abort(401, 'User not found or inactive')
            
            return user.to_dict()
            
        except Exception as e:
            logger.error("Get user profile error", error=str(e))
            api.abort(500, 'Failed to get user profile')


@api.route('/logout')
class LogoutResource(Resource):
    @api.doc('logout')
    @api.doc(security='Bearer')
    def post(self):
        """Logout (client-side token invalidation)"""
        # In a real implementation, you might want to maintain a token blacklist
        # For now, we'll rely on client-side token removal
        return {'message': 'Logout successful'}, 200


def require_auth(f):
    """Decorator to require authentication"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            api.abort(401, 'Authorization header required')
        
        token = auth_header.split(' ')[1]
        
        try:
            payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=['HS256'])
            current_user = User.query.get(payload['user_id'])
            
            if not current_user or not current_user.is_active:
                api.abort(401, 'Invalid user')
            
            # Add current user to request context
            request.current_user = current_user
            
        except jwt.ExpiredSignatureError:
            api.abort(401, 'Token has expired')
        except jwt.InvalidTokenError:
            api.abort(401, 'Invalid token')
        
        return f(*args, **kwargs)
    
    return decorated_function


def require_role(required_roles):
    """Decorator to require specific roles"""
    from functools import wraps
    
    if isinstance(required_roles, str):
        required_roles = [required_roles]
    
    def decorator(f):
        @wraps(f)
        @require_auth
        def decorated_function(*args, **kwargs):
            if request.current_user.role not in required_roles:
                api.abort(403, f'Role required: {", ".join(required_roles)}')
            return f(*args, **kwargs)
        return decorated_function
    
    return decorator