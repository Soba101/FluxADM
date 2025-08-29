"""
Change Request model - Core entity for the FluxADM system
"""
from datetime import datetime, date
from typing import List, Optional
from sqlalchemy import Column, String, Text, DateTime, Date, Integer, Boolean, ForeignKey, DECIMAL, JSON
from .base import GUID
from sqlalchemy.orm import relationship
import uuid
import enum

from . import db


class ChangeRequestCategory(enum.Enum):
    """Change request categories aligned with Panasonic standards"""
    EMERGENCY = "emergency"
    STANDARD = "standard" 
    NORMAL = "normal"
    ENHANCEMENT = "enhancement"
    INFRASTRUCTURE = "infrastructure"
    SECURITY = "security"
    MAINTENANCE = "maintenance"
    ROLLBACK = "rollback"


class ChangeRequestPriority(enum.Enum):
    """Change request priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ChangeRequestRisk(enum.Enum):
    """Risk assessment levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ChangeRequestStatus(enum.Enum):
    """Comprehensive status model for CR lifecycle"""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    PENDING_APPROVAL = "pending_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_PROGRESS = "in_progress"
    TESTING = "testing"
    DEPLOYED = "deployed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    POST_IMPLEMENTATION_REVIEW = "post_implementation_review"


class ChangeRequest(db.Model):
    """Core Change Request model"""
    
    __tablename__ = 'change_requests'
    
    # Primary identification
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    cr_number = Column(String(20), unique=True, nullable=False)  # Auto-generated CR number
    title = Column(String(500), nullable=False)
    description = Column(Text)
    
    # Business information
    business_justification = Column(Text)
    success_criteria = Column(Text)
    affected_systems = Column(JSON, default=[])
    impacted_users = Column(Text)
    
    # Technical details
    technical_details = Column(Text)
    implementation_plan = Column(Text)
    rollback_plan = Column(Text)
    testing_plan = Column(Text)
    
    # Classification
    category = Column(String(20), nullable=False)  # Using string for enum compatibility
    priority = Column(String(10), nullable=False)
    risk_level = Column(String(10), nullable=False)
    risk_score = Column(Integer)  # 1-9 scale from risk matrix
    
    # Status and workflow
    status = Column(String(30), default=ChangeRequestStatus.DRAFT.value)
    
    # Relationships
    submitter_id = Column(GUID(), ForeignKey('users.id'), nullable=False)
    assignee_id = Column(GUID(), ForeignKey('users.id'))
    
    # Relationships
    submitter = relationship("User", foreign_keys=[submitter_id], backref="submitted_crs")
    assignee = relationship("User", foreign_keys=[assignee_id], backref="assigned_crs")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    submitted_at = Column(DateTime)
    approved_at = Column(DateTime)
    target_completion_date = Column(Date)
    actual_completion_date = Column(Date)
    
    # File attachments
    file_paths = Column(JSON, default=[])
    
    # AI analysis results
    ai_confidence = Column(DECIMAL(3, 2))  # 0.00 to 1.00
    ai_analysis_summary = Column(JSON)
    quality_score = Column(Integer)  # 0-100
    
    # SLA and compliance
    sla_breached = Column(Boolean, default=False)
    emergency_approved_by = Column(GUID(), ForeignKey('users.id'))
    compliance_flags = Column(JSON)  # Store compliance-related metadata
    
    # Cost and effort estimation
    estimated_effort_hours = Column(Integer)
    estimated_cost = Column(DECIMAL(10, 2))
    actual_effort_hours = Column(Integer)
    actual_cost = Column(DECIMAL(10, 2))
    
    @property
    def cr_age_days(self) -> int:
        """Calculate age of CR in days"""
        return (datetime.utcnow() - self.created_at).days
    
    @property
    def is_overdue(self) -> bool:
        """Check if CR is past target completion date"""
        if not self.target_completion_date:
            return False
        return date.today() > self.target_completion_date
    
    @property
    def status_enum(self) -> ChangeRequestStatus:
        """Get status as enum"""
        return ChangeRequestStatus(self.status)
    
    @property
    def category_enum(self) -> ChangeRequestCategory:
        """Get category as enum"""
        return ChangeRequestCategory(self.category)
    
    @property
    def priority_enum(self) -> ChangeRequestPriority:
        """Get priority as enum"""
        return ChangeRequestPriority(self.priority)
    
    @property
    def risk_enum(self) -> ChangeRequestRisk:
        """Get risk level as enum"""
        return ChangeRequestRisk(self.risk_level)
    
    def update_status(self, new_status: ChangeRequestStatus, user_id: uuid.UUID):
        """Update status and record status history"""
        old_status = self.status
        self.status = new_status.value
        self.updated_at = datetime.utcnow()
        
        # Record status change in history
        # This will be implemented when we create the StatusHistory model
        
        # Update specific timestamps
        if new_status == ChangeRequestStatus.SUBMITTED:
            self.submitted_at = datetime.utcnow()
        elif new_status == ChangeRequestStatus.APPROVED:
            self.approved_at = datetime.utcnow()
        elif new_status == ChangeRequestStatus.COMPLETED:
            self.actual_completion_date = date.today()
    
    def add_file(self, file_path: str):
        """Add file path to attachments"""
        if not self.file_paths:
            self.file_paths = []
        if file_path not in self.file_paths:
            self.file_paths.append(file_path)
    
    def remove_file(self, file_path: str):
        """Remove file path from attachments"""
        if self.file_paths and file_path in self.file_paths:
            self.file_paths.remove(file_path)
    
    def calculate_risk_score(self, impact: int, probability: int) -> int:
        """Calculate risk score using 3x3 matrix (1-9 scale)"""
        # Risk matrix: impact (1-3) × probability (1-3) = risk score (1-9)
        score = impact * probability
        self.risk_score = score
        
        # Update risk level based on score
        if score <= 2:
            self.risk_level = ChangeRequestRisk.LOW.value
        elif score <= 6:
            self.risk_level = ChangeRequestRisk.MEDIUM.value
        else:
            self.risk_level = ChangeRequestRisk.HIGH.value
        
        return score
    
    def to_dict(self, include_sensitive: bool = False) -> dict:
        """Convert CR to dictionary for JSON serialization"""
        data = {
            'id': str(self.id),
            'cr_number': self.cr_number,
            'title': self.title,
            'description': self.description,
            'category': self.category,
            'priority': self.priority,
            'risk_level': self.risk_level,
            'risk_score': self.risk_score,
            'status': self.status,
            'submitter_id': str(self.submitter_id),
            'assignee_id': str(self.assignee_id) if self.assignee_id else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'target_completion_date': self.target_completion_date.isoformat() if self.target_completion_date else None,
            'actual_completion_date': self.actual_completion_date.isoformat() if self.actual_completion_date else None,
            'quality_score': self.quality_score,
            'ai_confidence': float(self.ai_confidence) if self.ai_confidence else None,
            'sla_breached': self.sla_breached,
            'cr_age_days': self.cr_age_days,
            'is_overdue': self.is_overdue
        }
        
        if include_sensitive:
            data.update({
                'business_justification': self.business_justification,
                'technical_details': self.technical_details,
                'implementation_plan': self.implementation_plan,
                'rollback_plan': self.rollback_plan,
                'testing_plan': self.testing_plan,
                'affected_systems': self.affected_systems,
                'file_paths': self.file_paths,
                'ai_analysis_summary': self.ai_analysis_summary,
                'compliance_flags': self.compliance_flags
            })
        
        return data
    
    def __repr__(self):
        return f'<ChangeRequest {self.cr_number}: {self.title[:50]}>'
    
    @classmethod
    def generate_cr_number(cls) -> str:
        """Generate unique CR number"""
        from datetime import datetime
        
        # Format: CR-YYYY-NNNNNN
        year = datetime.now().year
        
        # Get latest CR number for this year
        latest_cr = cls.query.filter(
            cls.cr_number.like(f'CR-{year}-%')
        ).order_by(cls.cr_number.desc()).first()
        
        if latest_cr:
            # Extract sequence number and increment
            sequence = int(latest_cr.cr_number.split('-')[2]) + 1
        else:
            sequence = 1
        
        return f'CR-{year}-{sequence:06d}'