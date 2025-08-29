"""
Quality Issue model for tracking CR quality problems and improvements
"""
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, Boolean, Integer
from .base import GUID
from sqlalchemy.orm import relationship
import uuid
import enum

from . import db


class QualityIssueSeverity(enum.Enum):
    """Quality issue severity levels"""
    LOW = "low"
    MEDIUM = "medium" 
    HIGH = "high"
    CRITICAL = "critical"


class QualityIssueType(enum.Enum):
    """Types of quality issues that can be detected"""
    MISSING_REQUIREMENTS = "missing_requirements"
    UNCLEAR_SCOPE = "unclear_scope"
    INSUFFICIENT_TESTING = "insufficient_testing"
    MISSING_ROLLBACK_PLAN = "missing_rollback_plan"
    INADEQUATE_RISK_ASSESSMENT = "inadequate_risk_assessment"
    MISSING_APPROVALS = "missing_approvals"
    INCOMPLETE_DOCUMENTATION = "incomplete_documentation"
    UNREALISTIC_TIMELINE = "unrealistic_timeline"
    RESOURCE_CONFLICTS = "resource_conflicts"
    COMPLIANCE_GAPS = "compliance_gaps"
    SECURITY_CONCERNS = "security_concerns"
    PERFORMANCE_RISKS = "performance_risks"


class QualityIssue(db.Model):
    """Track quality issues found in change requests"""
    
    __tablename__ = 'quality_issues'
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    
    # Link to change request
    cr_id = Column(GUID(), ForeignKey('change_requests.id'), nullable=False)
    cr = relationship("ChangeRequest", backref="quality_issues")
    
    # Issue classification
    issue_type = Column(String(50), nullable=False)
    severity = Column(String(10), nullable=False)
    category = Column(String(50))  # documentation, technical, process, compliance
    
    # Issue details
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    location = Column(String(100))  # Which section/field has the issue
    
    # Detection information
    detected_by = Column(String(20), nullable=False)  # ai_analysis, human_review, automated_check
    detected_at = Column(DateTime, default=datetime.utcnow)
    detection_confidence = Column(Integer)  # 0-100 for AI-detected issues
    
    # AI analysis details (if AI-detected)
    ai_analysis_id = Column(GUID(), ForeignKey('ai_analysis_results.id'))
    ai_analysis = relationship("AIAnalysisResult", backref="quality_issues_found")
    
    # Resolution tracking
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime)
    resolver_id = Column(GUID(), ForeignKey('users.id'))
    resolution_notes = Column(Text)
    resolution_method = Column(String(50))  # fixed, accepted_risk, false_positive, duplicate
    
    # Impact assessment
    impact_score = Column(Integer)  # 1-10 scale
    blocks_approval = Column(Boolean, default=False)
    estimated_fix_time_hours = Column(Integer)
    
    # Workflow integration
    requires_review = Column(Boolean, default=True)
    reviewed_by = Column(GUID(), ForeignKey('users.id'))
    reviewed_at = Column(DateTime)
    review_notes = Column(Text)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    resolver = relationship("User", foreign_keys=[resolver_id], backref="resolved_issues")
    reviewer = relationship("User", foreign_keys=[reviewed_by], backref="reviewed_issues")
    
    @property
    def age_hours(self) -> float:
        """Calculate age of issue in hours"""
        return (datetime.utcnow() - self.detected_at).total_seconds() / 3600
    
    @property
    def resolution_time_hours(self) -> float:
        """Calculate time taken to resolve issue"""
        if not self.resolved or not self.resolved_at:
            return 0.0
        return (self.resolved_at - self.detected_at).total_seconds() / 3600
    
    @property
    def severity_enum(self) -> QualityIssueSeverity:
        """Get severity as enum"""
        return QualityIssueSeverity(self.severity)
    
    @property
    def issue_type_enum(self) -> QualityIssueType:
        """Get issue type as enum"""
        return QualityIssueType(self.issue_type)
    
    @property
    def is_critical_blocker(self) -> bool:
        """Check if this is a critical issue that blocks progress"""
        return self.severity == QualityIssueSeverity.CRITICAL.value and self.blocks_approval
    
    def resolve_issue(self, user_id: uuid.UUID, resolution_method: str, notes: str = None):
        """Mark issue as resolved"""
        self.resolved = True
        self.resolved_at = datetime.utcnow()
        self.resolver_id = user_id
        self.resolution_method = resolution_method
        if notes:
            self.resolution_notes = notes
        self.updated_at = datetime.utcnow()
    
    def mark_as_reviewed(self, user_id: uuid.UUID, notes: str = None):
        """Mark issue as reviewed by human"""
        self.reviewed_by = user_id
        self.reviewed_at = datetime.utcnow()
        if notes:
            self.review_notes = notes
        self.requires_review = False
        self.updated_at = datetime.utcnow()
    
    def update_impact_assessment(self, impact_score: int, blocks_approval: bool = None, fix_time_hours: int = None):
        """Update impact assessment"""
        self.impact_score = impact_score
        if blocks_approval is not None:
            self.blocks_approval = blocks_approval
        if fix_time_hours is not None:
            self.estimated_fix_time_hours = fix_time_hours
        self.updated_at = datetime.utcnow()
    
    def to_dict(self, include_details: bool = False) -> dict:
        """Convert to dictionary for JSON serialization"""
        data = {
            'id': str(self.id),
            'cr_id': str(self.cr_id),
            'issue_type': self.issue_type,
            'severity': self.severity,
            'category': self.category,
            'title': self.title,
            'description': self.description,
            'location': self.location,
            'detected_by': self.detected_by,
            'detected_at': self.detected_at.isoformat() if self.detected_at else None,
            'detection_confidence': self.detection_confidence,
            'resolved': self.resolved,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'resolution_method': self.resolution_method,
            'impact_score': self.impact_score,
            'blocks_approval': self.blocks_approval,
            'estimated_fix_time_hours': self.estimated_fix_time_hours,
            'requires_review': self.requires_review,
            'reviewed_at': self.reviewed_at.isoformat() if self.reviewed_at else None,
            'age_hours': self.age_hours,
            'resolution_time_hours': self.resolution_time_hours,
            'is_critical_blocker': self.is_critical_blocker
        }
        
        if include_details:
            data.update({
                'resolution_notes': self.resolution_notes,
                'review_notes': self.review_notes,
                'resolver_id': str(self.resolver_id) if self.resolver_id else None,
                'reviewed_by': str(self.reviewed_by) if self.reviewed_by else None,
                'ai_analysis_id': str(self.ai_analysis_id) if self.ai_analysis_id else None
            })
        
        return data
    
    def __repr__(self):
        return f'<QualityIssue {self.issue_type} ({self.severity}) for CR {self.cr_id}>'


class QualityMetrics(db.Model):
    """Aggregate quality metrics for reporting and trending"""
    
    __tablename__ = 'quality_metrics'
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    
    # Time period
    date = Column(DateTime, nullable=False)
    period_type = Column(String(10), nullable=False)  # daily, weekly, monthly
    
    # Issue counts by severity
    critical_issues = Column(Integer, default=0)
    high_issues = Column(Integer, default=0)
    medium_issues = Column(Integer, default=0)
    low_issues = Column(Integer, default=0)
    total_issues = Column(Integer, default=0)
    
    # Resolution metrics
    issues_resolved = Column(Integer, default=0)
    avg_resolution_time_hours = Column(Integer)
    issues_pending_review = Column(Integer, default=0)
    
    # Quality scores
    avg_cr_quality_score = Column(Integer)
    crs_below_quality_threshold = Column(Integer, default=0)
    total_crs_analyzed = Column(Integer, default=0)
    
    # Detection method breakdown
    ai_detected_issues = Column(Integer, default=0)
    human_detected_issues = Column(Integer, default=0)
    automated_check_issues = Column(Integer, default=0)
    
    # Impact metrics
    blocking_issues = Column(Integer, default=0)
    total_estimated_fix_hours = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def quality_improvement_rate(self) -> float:
        """Calculate quality improvement rate"""
        if self.total_crs_analyzed == 0:
            return 0.0
        return (self.total_crs_analyzed - self.crs_below_quality_threshold) / self.total_crs_analyzed
    
    @property
    def resolution_rate(self) -> float:
        """Calculate issue resolution rate"""
        if self.total_issues == 0:
            return 0.0
        return self.issues_resolved / self.total_issues
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': str(self.id),
            'date': self.date.isoformat() if self.date else None,
            'period_type': self.period_type,
            'critical_issues': self.critical_issues,
            'high_issues': self.high_issues,
            'medium_issues': self.medium_issues,
            'low_issues': self.low_issues,
            'total_issues': self.total_issues,
            'issues_resolved': self.issues_resolved,
            'avg_resolution_time_hours': self.avg_resolution_time_hours,
            'issues_pending_review': self.issues_pending_review,
            'avg_cr_quality_score': self.avg_cr_quality_score,
            'crs_below_quality_threshold': self.crs_below_quality_threshold,
            'total_crs_analyzed': self.total_crs_analyzed,
            'ai_detected_issues': self.ai_detected_issues,
            'human_detected_issues': self.human_detected_issues,
            'automated_check_issues': self.automated_check_issues,
            'blocking_issues': self.blocking_issues,
            'total_estimated_fix_hours': self.total_estimated_fix_hours,
            'quality_improvement_rate': self.quality_improvement_rate,
            'resolution_rate': self.resolution_rate
        }
    
    def __repr__(self):
        return f'<QualityMetrics {self.period_type} {self.date}>'