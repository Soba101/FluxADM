"""
Approval Workflow model for managing multi-stage approvals
"""
from datetime import datetime, timedelta
from typing import List
from sqlalchemy import Column, String, Text, DateTime, Integer, Boolean, ForeignKey, JSON
from .base import GUID
from sqlalchemy.orm import relationship
import uuid
import enum

from . import db


class ApprovalStatus(enum.Enum):
    """Approval workflow status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress" 
    APPROVED = "approved"
    REJECTED = "rejected"
    ESCALATED = "escalated"
    EXPIRED = "expired"


class ApprovalWorkflow(db.Model):
    """Multi-stage approval workflow for change requests"""
    
    __tablename__ = 'approval_workflows'
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    
    # Link to change request
    cr_id = Column(GUID(), ForeignKey('change_requests.id'), nullable=False)
    cr = relationship("ChangeRequest", backref="approval_workflows")
    
    # Workflow stage information
    stage_number = Column(Integer, nullable=False)  # 1, 2, 3, etc.
    stage_name = Column(String(100), nullable=False)  # "Technical Review", "Manager Approval", etc.
    stage_description = Column(Text)
    
    # Approval requirements
    required_approvers = Column(JSON, nullable=False)  # List of user IDs
    minimum_approvals = Column(Integer, default=1)  # How many approvals needed
    approval_type = Column(String(20), default='any')  # 'any', 'all', 'majority'
    
    # Current approvers who have responded
    actual_approvers = Column(JSON, default=[])  # Users who approved
    rejectors = Column(JSON, default=[])  # Users who rejected
    
    # Workflow status
    status = Column(String(20), default=ApprovalStatus.PENDING.value)
    
    # Timing
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    due_date = Column(DateTime)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Escalation
    escalated = Column(Boolean, default=False)
    escalated_at = Column(DateTime)
    escalated_to = Column(GUID(), ForeignKey('users.id'))
    escalation_reason = Column(Text)
    
    # Comments and notes
    comments = Column(Text)
    rejection_reason = Column(Text)
    
    # Relationships
    # escalation_user = relationship("User", foreign_keys=[escalated_to])  # Disabled to avoid circular imports
    
    @property
    def is_overdue(self) -> bool:
        """Check if workflow stage is overdue"""
        if not self.due_date:
            return False
        return datetime.utcnow() > self.due_date and self.status in [
            ApprovalStatus.PENDING.value, 
            ApprovalStatus.IN_PROGRESS.value
        ]
    
    @property
    def time_remaining_hours(self) -> float:
        """Calculate hours remaining until due date"""
        if not self.due_date:
            return float('inf')
        delta = self.due_date - datetime.utcnow()
        return delta.total_seconds() / 3600
    
    @property
    def approval_count(self) -> int:
        """Count of actual approvals received"""
        return len(self.actual_approvers) if self.actual_approvers else 0
    
    @property
    def rejection_count(self) -> int:
        """Count of rejections received"""
        return len(self.rejectors) if self.rejectors else 0
    
    @property
    def pending_approvers(self) -> List[str]:
        """List of user IDs who haven't responded yet"""
        responded = set(self.actual_approvers or []) | set(self.rejectors or [])
        required = set(self.required_approvers or [])
        return list(required - responded)
    
    def add_approval(self, user_id: uuid.UUID, comments: str = None) -> bool:
        """
        Add approval from a user
        Returns True if workflow stage is now complete
        """
        if str(user_id) not in self.required_approvers:
            return False
        
        # Initialize lists if None
        if self.actual_approvers is None:
            self.actual_approvers = []
        if self.rejectors is None:
            self.rejectors = []
        
        # Remove from rejectors if previously rejected
        if str(user_id) in self.rejectors:
            self.rejectors.remove(str(user_id))
        
        # Add to approvers if not already there
        if str(user_id) not in self.actual_approvers:
            self.actual_approvers.append(str(user_id))
        
        if comments:
            self.comments = f"{self.comments or ''}\n[{datetime.utcnow()}] {user_id}: {comments}"
        
        self.updated_at = datetime.utcnow()
        
        # Check if stage is complete
        return self._check_completion()
    
    def add_rejection(self, user_id: uuid.UUID, reason: str = None) -> bool:
        """
        Add rejection from a user
        Returns True if workflow stage is now rejected
        """
        if str(user_id) not in self.required_approvers:
            return False
        
        # Initialize lists if None
        if self.actual_approvers is None:
            self.actual_approvers = []
        if self.rejectors is None:
            self.rejectors = []
        
        # Remove from approvers if previously approved
        if str(user_id) in self.actual_approvers:
            self.actual_approvers.remove(str(user_id))
        
        # Add to rejectors if not already there
        if str(user_id) not in self.rejectors:
            self.rejectors.append(str(user_id))
        
        if reason:
            self.rejection_reason = f"{self.rejection_reason or ''}\n[{datetime.utcnow()}] {user_id}: {reason}"
        
        self.status = ApprovalStatus.REJECTED.value
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        return True
    
    def _check_completion(self) -> bool:
        """Check if workflow stage meets completion criteria"""
        approval_count = len(self.actual_approvers or [])
        
        if self.approval_type == 'any' and approval_count >= 1:
            self._complete_stage(ApprovalStatus.APPROVED)
            return True
        elif self.approval_type == 'all' and approval_count >= len(self.required_approvers):
            self._complete_stage(ApprovalStatus.APPROVED)
            return True
        elif self.approval_type == 'majority':
            required_majority = (len(self.required_approvers) // 2) + 1
            if approval_count >= required_majority:
                self._complete_stage(ApprovalStatus.APPROVED)
                return True
        elif approval_count >= self.minimum_approvals:
            self._complete_stage(ApprovalStatus.APPROVED)
            return True
        
        return False
    
    def _complete_stage(self, status: ApprovalStatus):
        """Mark stage as complete"""
        self.status = status.value
        self.completed_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def escalate(self, escalated_to: uuid.UUID, reason: str = None):
        """Escalate workflow to higher authority"""
        self.escalated = True
        self.escalated_at = datetime.utcnow()
        self.escalated_to = escalated_to
        self.escalation_reason = reason
        self.status = ApprovalStatus.ESCALATED.value
        self.updated_at = datetime.utcnow()
        
        # Add escalation target to required approvers
        if str(escalated_to) not in self.required_approvers:
            self.required_approvers.append(str(escalated_to))
    
    def set_due_date(self, hours_from_now: int):
        """Set due date relative to now"""
        self.due_date = datetime.utcnow() + timedelta(hours=hours_from_now)
    
    def start_workflow(self):
        """Start the workflow stage"""
        if not self.started_at:
            self.started_at = datetime.utcnow()
            self.status = ApprovalStatus.IN_PROGRESS.value
            self.updated_at = datetime.utcnow()
    
    def to_dict(self, include_details: bool = False) -> dict:
        """Convert to dictionary for JSON serialization"""
        data = {
            'id': str(self.id),
            'cr_id': str(self.cr_id),
            'stage_number': self.stage_number,
            'stage_name': self.stage_name,
            'status': self.status,
            'approval_count': self.approval_count,
            'rejection_count': self.rejection_count,
            'required_approver_count': len(self.required_approvers or []),
            'pending_approver_count': len(self.pending_approvers),
            'is_overdue': self.is_overdue,
            'time_remaining_hours': self.time_remaining_hours if self.time_remaining_hours != float('inf') else None,
            'escalated': self.escalated,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
        
        if include_details:
            data.update({
                'stage_description': self.stage_description,
                'required_approvers': self.required_approvers,
                'actual_approvers': self.actual_approvers,
                'rejectors': self.rejectors,
                'pending_approvers': self.pending_approvers,
                'minimum_approvals': self.minimum_approvals,
                'approval_type': self.approval_type,
                'comments': self.comments,
                'rejection_reason': self.rejection_reason,
                'escalation_reason': self.escalation_reason,
                'escalated_to': str(self.escalated_to) if self.escalated_to else None
            })
        
        return data
    
    def __repr__(self):
        return f'<ApprovalWorkflow Stage {self.stage_number} for CR {self.cr_id}>'