"""
AI Analysis Results model for tracking AI processing history and performance
"""
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey, DECIMAL, JSON
from .base import GUID
from sqlalchemy.orm import relationship
import uuid

from . import db


class AIAnalysisResult(db.Model):
    """Track AI analysis results and performance metrics"""
    
    __tablename__ = 'ai_analysis_results'
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    
    # Link to change request
    cr_id = Column(GUID(), ForeignKey('change_requests.id'), nullable=False)
    cr = relationship("ChangeRequest", backref="ai_analyses")
    
    # Analysis metadata
    analysis_type = Column(String(50), nullable=False)  # categorization, risk_assessment, quality_check
    ai_model_used = Column(String(100), nullable=False)  # gpt-4, gpt-3.5-turbo, claude-3, etc.
    provider = Column(String(50), nullable=False)  # openai, anthropic, local
    
    # Performance metrics
    input_tokens = Column(Integer)
    output_tokens = Column(Integer)
    processing_time_ms = Column(Integer)
    api_cost = Column(DECIMAL(8, 4))  # Cost in USD
    
    # Analysis results
    confidence_score = Column(DECIMAL(3, 2), nullable=False)  # 0.00 to 1.00
    raw_response = Column(JSON)  # Store full AI response
    structured_result = Column(JSON)  # Processed/structured result
    
    # Quality and validation
    human_validated = Column(String(20))  # correct, incorrect, partial, pending
    validation_notes = Column(Text)
    validated_by = Column(GUID(), ForeignKey('users.id'))
    validated_at = Column(DateTime)
    
    # Error handling
    error_occurred = Column(String(10), default='false')  # Use string for JSON compatibility
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    # validator = relationship("User", foreign_keys=[validated_by])  # Disabled to avoid circular imports
    
    @property
    def was_successful(self) -> bool:
        """Check if analysis completed successfully"""
        return self.error_occurred == 'false' and self.confidence_score is not None
    
    @property
    def processing_time_seconds(self) -> float:
        """Get processing time in seconds"""
        return self.processing_time_ms / 1000.0 if self.processing_time_ms else 0.0
    
    @property
    def tokens_per_second(self) -> float:
        """Calculate processing speed in tokens per second"""
        if not self.processing_time_ms or not self.output_tokens:
            return 0.0
        return (self.output_tokens / self.processing_time_ms) * 1000
    
    def mark_as_validated(self, user_id: uuid.UUID, validation_result: str, notes: str = None):
        """Mark analysis as human-validated"""
        self.human_validated = validation_result
        self.validated_by = user_id
        self.validated_at = datetime.utcnow()
        if notes:
            self.validation_notes = notes
        self.updated_at = datetime.utcnow()
    
    def record_error(self, error_message: str):
        """Record analysis error"""
        self.error_occurred = 'true'
        self.error_message = error_message
        self.updated_at = datetime.utcnow()
    
    def increment_retry(self):
        """Increment retry counter"""
        self.retry_count += 1
        self.updated_at = datetime.utcnow()
    
    def to_dict(self, include_raw_response: bool = False) -> dict:
        """Convert to dictionary for JSON serialization"""
        data = {
            'id': str(self.id),
            'cr_id': str(self.cr_id),
            'analysis_type': self.analysis_type,
            'ai_model_used': self.ai_model_used,
            'provider': self.provider,
            'confidence_score': float(self.confidence_score) if self.confidence_score else None,
            'processing_time_ms': self.processing_time_ms,
            'processing_time_seconds': self.processing_time_seconds,
            'tokens_per_second': self.tokens_per_second,
            'input_tokens': self.input_tokens,
            'output_tokens': self.output_tokens,
            'api_cost': float(self.api_cost) if self.api_cost else None,
            'was_successful': self.was_successful,
            'human_validated': self.human_validated,
            'validation_notes': self.validation_notes,
            'validated_at': self.validated_at.isoformat() if self.validated_at else None,
            'error_occurred': self.error_occurred == 'true',
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'structured_result': self.structured_result
        }
        
        if include_raw_response:
            data['raw_response'] = self.raw_response
        
        return data
    
    def __repr__(self):
        return f'<AIAnalysisResult {self.analysis_type} for CR {self.cr_id}>'


class AIModelPerformance(db.Model):
    """Track aggregate AI model performance metrics"""
    
    __tablename__ = 'ai_model_performance'
    
    id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    
    # Model identification
    model_name = Column(String(100), nullable=False)
    provider = Column(String(50), nullable=False)
    analysis_type = Column(String(50), nullable=False)
    
    # Performance metrics (daily aggregates)
    date = Column(DateTime, nullable=False)
    total_requests = Column(Integer, default=0)
    successful_requests = Column(Integer, default=0)
    failed_requests = Column(Integer, default=0)
    avg_confidence_score = Column(DECIMAL(3, 2))
    avg_processing_time_ms = Column(Integer)
    total_tokens = Column(Integer, default=0)
    total_cost = Column(DECIMAL(10, 4), default=0)
    
    # Accuracy metrics (when validation data available)
    validated_requests = Column(Integer, default=0)
    correct_predictions = Column(Integer, default=0)
    accuracy_rate = Column(DECIMAL(3, 2))
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_requests == 0:
            return 0.0
        return self.successful_requests / self.total_requests
    
    @property
    def avg_cost_per_request(self) -> float:
        """Calculate average cost per request"""
        if self.total_requests == 0:
            return 0.0
        return float(self.total_cost) / self.total_requests
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'id': str(self.id),
            'model_name': self.model_name,
            'provider': self.provider,
            'analysis_type': self.analysis_type,
            'date': self.date.isoformat() if self.date else None,
            'total_requests': self.total_requests,
            'successful_requests': self.successful_requests,
            'failed_requests': self.failed_requests,
            'success_rate': self.success_rate,
            'avg_confidence_score': float(self.avg_confidence_score) if self.avg_confidence_score else None,
            'avg_processing_time_ms': self.avg_processing_time_ms,
            'total_tokens': self.total_tokens,
            'total_cost': float(self.total_cost) if self.total_cost else None,
            'avg_cost_per_request': self.avg_cost_per_request,
            'validated_requests': self.validated_requests,
            'correct_predictions': self.correct_predictions,
            'accuracy_rate': float(self.accuracy_rate) if self.accuracy_rate else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    def __repr__(self):
        return f'<AIModelPerformance {self.model_name} {self.analysis_type} {self.date}>'