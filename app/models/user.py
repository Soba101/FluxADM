"""
User model for authentication and authorization
"""
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from sqlalchemy import Column, String, DateTime, Boolean, Text
import uuid

from . import db
from .base import BaseModel, GUID


class User(BaseModel, db.Model):
    """User model for authentication and role management"""
    
    __tablename__ = 'users'
    
    # BaseModel already provides id, created_at, updated_at
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False, default='user')  # admin, manager, analyst, user
    department = Column(String(100))
    password_hash = Column(String(255))
    last_login = Column(DateTime)
    is_active = Column(Boolean, default=True)
    
    # Profile information
    phone = Column(String(20))
    title = Column(String(100))
    manager_email = Column(String(255))
    
    def set_password(self, password: str):
        """Set password hash"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """Check password against hash"""
        if not self.password_hash:
            return False
        return check_password_hash(self.password_hash, password)
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()
        db.session.commit()
    
    @property
    def is_admin(self) -> bool:
        """Check if user is admin"""
        return self.role == 'admin'
    
    @property
    def is_manager(self) -> bool:
        """Check if user is manager or admin"""
        return self.role in ['admin', 'manager']
    
    @property
    def can_approve_changes(self) -> bool:
        """Check if user can approve changes"""
        return self.role in ['admin', 'manager']
    
    def to_dict(self) -> dict:
        """Convert user to dictionary for JSON serialization"""
        return {
            'id': str(self.id),
            'email': self.email,
            'full_name': self.full_name,
            'role': self.role,
            'department': self.department,
            'phone': self.phone,
            'title': self.title,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
    
    def __repr__(self):
        return f'<User {self.email}>'