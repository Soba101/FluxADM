"""
Performance Metrics model for tracking system and CR performance
"""
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, DECIMAL, Integer, JSON
from .base import GUID
from sqlalchemy.orm import relationship
import uuid
import enum

from . import db


class MetricStatus(enum.Enum):
    """Status of performance metrics"""
    BASELINE = "baseline"
    TARGET_MET = "target_met"
    DEGRADED = "degraded"
    IMPROVED = "improved"
    MONITORING = "monitoring"


class PerformanceMetric(db.Model):
    """Track performance metrics for change requests and system performance"""
    
    __tablename__ = 'performance_metrics'
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    
    # Link to change request
    cr_id = Column(GUID(), ForeignKey('change_requests.id'), nullable=False)
    cr = relationship("ChangeRequest", backref="performance_metrics")
    
    # Metric identification
    metric_name = Column(String(100), nullable=False)
    metric_category = Column(String(50))  # performance, availability, capacity, cost
    metric_description = Column(Text)
    metric_unit = Column(String(20))  # seconds, percent, requests/min, etc.
    
    # Measurement values
    baseline_value = Column(DECIMAL(15, 4))
    target_value = Column(DECIMAL(15, 4))
    actual_value = Column(DECIMAL(15, 4))
    previous_value = Column(DECIMAL(15, 4))  # For trend analysis
    
    # Measurement context
    measurement_timestamp = Column(DateTime, nullable=False)
    measurement_method = Column(String(50))  # automated, manual, estimated
    measurement_environment = Column(String(20))  # dev, staging, production
    
    # Status and analysis
    status = Column(String(20), default=MetricStatus.MONITORING.value)
    variance_percentage = Column(DECIMAL(5, 2))  # Percentage difference from target
    trend_direction = Column(String(10))  # improving, degrading, stable
    
    # Impact assessment
    impact_level = Column(String(10))  # low, medium, high, critical
    impact_description = Column(Text)
    remediation_required = Column(String(5), default='false')  # String for JSON compatibility
    remediation_notes = Column(Text)
    
    # System context
    affected_systems = Column(String(200))
    monitoring_tool = Column(String(50))
    alert_threshold = Column(DECIMAL(15, 4))
    
    # Tracking
    created_by = Column(GUID(), ForeignKey('users.id'))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    creator = relationship("User", foreign_keys=[created_by])
    
    @property
    def is_within_target(self) -> bool:
        """Check if actual value meets target"""
        if not self.target_value or not self.actual_value:
            return False
        
        # Simple threshold check - can be enhanced based on metric type
        variance_threshold = 0.1  # 10% tolerance
        variance = abs(float(self.actual_value - self.target_value)) / float(self.target_value)
        return variance <= variance_threshold
    
    @property
    def performance_score(self) -> int:
        """Calculate performance score (0-100)"""
        if not self.target_value or not self.actual_value:
            return 50  # Default/unknown
        
        if self.is_within_target:
            return 100
        
        # Calculate score based on variance
        variance = abs(float(self.actual_value - self.target_value)) / float(self.target_value)
        
        if variance <= 0.1:  # Within 10%
            return 90
        elif variance <= 0.25:  # Within 25%
            return 70
        elif variance <= 0.5:  # Within 50%
            return 50
        else:
            return 25  # Beyond 50% variance
    
    @property
    def needs_attention(self) -> bool:
        """Check if metric needs attention"""
        return (
            self.status in [MetricStatus.DEGRADED.value] or
            self.impact_level in ['high', 'critical'] or
            self.remediation_required == 'true'
        )
    
    def calculate_variance(self):
        """Calculate and update variance percentage"""
        if self.target_value and self.actual_value:
            variance = ((self.actual_value - self.target_value) / self.target_value) * 100
            self.variance_percentage = variance
            
            # Update status based on variance
            if abs(variance) <= 5:  # Within 5%
                self.status = MetricStatus.TARGET_MET.value
            elif variance > 5:
                self.status = MetricStatus.IMPROVED.value
            else:  # variance < -5
                self.status = MetricStatus.DEGRADED.value
    
    def update_trend(self):
        """Update trend direction based on previous value"""
        if self.previous_value and self.actual_value:
            if self.actual_value > self.previous_value:
                # Determine if higher is better based on metric name
                if any(word in self.metric_name.lower() for word in ['error', 'latency', 'response_time', 'downtime']):
                    self.trend_direction = 'degrading'
                else:
                    self.trend_direction = 'improving'
            elif self.actual_value < self.previous_value:
                if any(word in self.metric_name.lower() for word in ['error', 'latency', 'response_time', 'downtime']):
                    self.trend_direction = 'improving'
                else:
                    self.trend_direction = 'degrading'
            else:
                self.trend_direction = 'stable'
    
    def assess_impact(self):
        """Assess and update impact level"""
        variance = abs(float(self.variance_percentage)) if self.variance_percentage else 0
        
        if variance >= 50:
            self.impact_level = 'critical'
        elif variance >= 25:
            self.impact_level = 'high'
        elif variance >= 10:
            self.impact_level = 'medium'
        else:
            self.impact_level = 'low'
        
        # Set remediation flag for high impact
        if self.impact_level in ['high', 'critical']:
            self.remediation_required = 'true'
    
    def record_measurement(self, value: float, measurement_method: str = 'automated'):
        """Record a new measurement"""
        # Store previous value for trend analysis
        self.previous_value = self.actual_value
        self.actual_value = value
        self.measurement_timestamp = datetime.utcnow()
        self.measurement_method = measurement_method
        self.updated_at = datetime.utcnow()
        
        # Update calculated fields
        self.calculate_variance()
        self.update_trend()
        self.assess_impact()
    
    def to_dict(self, include_details: bool = False) -> dict:
        """Convert to dictionary for JSON serialization"""
        data = {
            'id': str(self.id),
            'cr_id': str(self.cr_id),
            'metric_name': self.metric_name,
            'metric_category': self.metric_category,
            'metric_unit': self.metric_unit,
            'baseline_value': float(self.baseline_value) if self.baseline_value else None,
            'target_value': float(self.target_value) if self.target_value else None,
            'actual_value': float(self.actual_value) if self.actual_value else None,
            'measurement_timestamp': self.measurement_timestamp.isoformat() if self.measurement_timestamp else None,
            'status': self.status,
            'variance_percentage': float(self.variance_percentage) if self.variance_percentage else None,
            'trend_direction': self.trend_direction,
            'impact_level': self.impact_level,
            'performance_score': self.performance_score,
            'is_within_target': self.is_within_target,
            'needs_attention': self.needs_attention,
            'remediation_required': self.remediation_required == 'true'
        }
        
        if include_details:
            data.update({
                'metric_description': self.metric_description,
                'previous_value': float(self.previous_value) if self.previous_value else None,
                'measurement_method': self.measurement_method,
                'measurement_environment': self.measurement_environment,
                'impact_description': self.impact_description,
                'remediation_notes': self.remediation_notes,
                'affected_systems': self.affected_systems,
                'monitoring_tool': self.monitoring_tool,
                'alert_threshold': float(self.alert_threshold) if self.alert_threshold else None,
                'created_by': str(self.created_by) if self.created_by else None,
                'created_at': self.created_at.isoformat() if self.created_at else None
            })
        
        return data
    
    def __repr__(self):
        return f'<PerformanceMetric {self.metric_name} for CR {self.cr_id}>'


class SystemHealthMetric(db.Model):
    """Track overall system health and performance metrics"""
    
    __tablename__ = 'system_health_metrics'
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    
    # Metric identification
    metric_name = Column(String(100), nullable=False)
    component = Column(String(50), nullable=False)  # api, database, ai_service, etc.
    
    # Values
    current_value = Column(DECIMAL(15, 4), nullable=False)
    threshold_warning = Column(DECIMAL(15, 4))
    threshold_critical = Column(DECIMAL(15, 4))
    
    # Status
    status = Column(String(10), nullable=False)  # healthy, warning, critical
    message = Column(String(200))
    
    # Context
    measurement_timestamp = Column(DateTime, nullable=False)
    environment = Column(String(20), default='production')
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    @property
    def is_healthy(self) -> bool:
        """Check if metric indicates healthy status"""
        return self.status == 'healthy'
    
    @property
    def requires_action(self) -> bool:
        """Check if metric requires immediate action"""
        return self.status == 'critical'
    
    def assess_status(self):
        """Assess and update status based on thresholds"""
        if self.threshold_critical and self.current_value >= self.threshold_critical:
            self.status = 'critical'
        elif self.threshold_warning and self.current_value >= self.threshold_warning:
            self.status = 'warning'
        else:
            self.status = 'healthy'
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': str(self.id),
            'metric_name': self.metric_name,
            'component': self.component,
            'current_value': float(self.current_value),
            'threshold_warning': float(self.threshold_warning) if self.threshold_warning else None,
            'threshold_critical': float(self.threshold_critical) if self.threshold_critical else None,
            'status': self.status,
            'message': self.message,
            'is_healthy': self.is_healthy,
            'requires_action': self.requires_action,
            'measurement_timestamp': self.measurement_timestamp.isoformat(),
            'environment': self.environment
        }
    
    def __repr__(self):
        return f'<SystemHealthMetric {self.component}.{self.metric_name}: {self.status}>'