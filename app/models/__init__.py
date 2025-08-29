"""
Database models and initialization for FluxADM
"""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.ext.declarative import declarative_base

# Global SQLAlchemy instance
db = SQLAlchemy()

# Base class for all models
Base = declarative_base()

# Import all models to ensure they're registered
from .user import User
from .change_request import ChangeRequest, ChangeRequestStatus, ChangeRequestCategory, ChangeRequestPriority, ChangeRequestRisk
from .ai_analysis import AIAnalysisResult
from .approval_workflow import ApprovalWorkflow, ApprovalStatus
from .quality_issue import QualityIssue
from .performance_metric import PerformanceMetric


def init_db(app):
    """Initialize database with Flask app"""
    db.init_app(app)
    
    with app.app_context():
        # Create all tables
        db.create_all()
        
        # Create default admin user if none exists
        create_default_admin()


def create_default_admin():
    """Create default admin user for initial setup"""
    from werkzeug.security import generate_password_hash
    
    if not User.query.filter_by(email='admin@fluxadm.com').first():
        admin_user = User(
            email='admin@fluxadm.com',
            full_name='FluxADM Administrator',
            role='admin',
            department='IT',
            password_hash=generate_password_hash('admin123'),
            is_active=True
        )
        db.session.add(admin_user)
        db.session.commit()


__all__ = [
    'db', 'init_db',
    'User', 'ChangeRequest', 'AIAnalysisResult', 
    'ApprovalWorkflow', 'QualityIssue', 'PerformanceMetric'
]