"""Dashboard API endpoints"""

from flask import request, jsonify
from flask_restx import Namespace, Resource, fields
from datetime import datetime, timedelta
import structlog

from app.models import db, ChangeRequest, AIAnalysisResult, QualityIssue, User
from app.api.auth import require_auth, require_role

logger = structlog.get_logger(__name__)

api = Namespace('dashboard', description='Dashboard and analytics operations')

# API Models
dashboard_metrics_model = api.model('DashboardMetrics', {
    'total_crs': fields.Integer(description='Total change requests'),
    'active_crs': fields.Integer(description='Active change requests'),
    'completed_crs': fields.Integer(description='Completed change requests'),
    'high_risk_crs': fields.Integer(description='High risk change requests'),
    'avg_quality_score': fields.Float(description='Average quality score'),
    'avg_processing_time': fields.Float(description='Average processing time in hours')
})

chart_data_model = api.model('ChartData', {
    'labels': fields.List(fields.String, description='Chart labels'),
    'data': fields.List(fields.Integer, description='Chart data points')
})


@api.route('/metrics')
class DashboardMetricsResource(Resource):
    @api.doc('get_dashboard_metrics')
    @api.marshal_with(dashboard_metrics_model)
    @api.doc(security='Bearer')
    @require_auth
    def get(self):
        """Get high-level dashboard metrics"""
        try:
            # Get date range (default: last 30 days)
            days = request.args.get('days', 30, type=int)
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Basic counts
            total_crs = ChangeRequest.query.filter(
                ChangeRequest.created_at >= start_date
            ).count()
            
            active_crs = ChangeRequest.query.filter(
                ChangeRequest.created_at >= start_date,
                ChangeRequest.status.in_([
                    'submitted', 'under_review', 'pending_approval', 
                    'approved', 'in_progress', 'testing'
                ])
            ).count()
            
            completed_crs = ChangeRequest.query.filter(
                ChangeRequest.created_at >= start_date,
                ChangeRequest.status == 'completed'
            ).count()
            
            high_risk_crs = ChangeRequest.query.filter(
                ChangeRequest.created_at >= start_date,
                ChangeRequest.risk_level == 'high'
            ).count()
            
            # Quality metrics
            avg_quality = db.session.query(
                db.func.avg(ChangeRequest.quality_score)
            ).filter(
                ChangeRequest.created_at >= start_date,
                ChangeRequest.quality_score.isnot(None)
            ).scalar() or 0
            
            # Processing time (for completed CRs)
            completed_with_dates = ChangeRequest.query.filter(
                ChangeRequest.created_at >= start_date,
                ChangeRequest.status == 'completed',
                ChangeRequest.actual_completion_date.isnot(None)
            ).all()
            
            avg_processing_time = 0
            if completed_with_dates:
                processing_times = []
                for cr in completed_with_dates:
                    if cr.actual_completion_date and cr.created_at:
                        # Convert date to datetime for calculation
                        completion_datetime = datetime.combine(cr.actual_completion_date, datetime.min.time())
                        delta = completion_datetime - cr.created_at
                        processing_times.append(delta.total_seconds() / 3600)  # Convert to hours
                
                if processing_times:
                    avg_processing_time = sum(processing_times) / len(processing_times)
            
            metrics = {
                'total_crs': total_crs,
                'active_crs': active_crs,
                'completed_crs': completed_crs,
                'high_risk_crs': high_risk_crs,
                'avg_quality_score': round(float(avg_quality), 2),
                'avg_processing_time': round(avg_processing_time, 2)
            }
            
            return metrics
            
        except Exception as e:
            logger.error("Failed to get dashboard metrics", error=str(e))
            api.abort(500, 'Failed to retrieve dashboard metrics')


@api.route('/charts/status-distribution')
class StatusDistributionChartResource(Resource):
    @api.doc('get_status_distribution')
    @api.marshal_with(chart_data_model)
    @api.doc(security='Bearer')
    @require_auth
    def get(self):
        """Get status distribution chart data"""
        try:
            days = request.args.get('days', 30, type=int)
            start_date = datetime.utcnow() - timedelta(days=days)
            
            status_data = db.session.query(
                ChangeRequest.status,
                db.func.count(ChangeRequest.id)
            ).filter(
                ChangeRequest.created_at >= start_date
            ).group_by(ChangeRequest.status).all()
            
            labels = [status.replace('_', ' ').title() for status, count in status_data]
            data = [count for status, count in status_data]
            
            return {
                'labels': labels,
                'data': data
            }
            
        except Exception as e:
            logger.error("Failed to get status distribution", error=str(e))
            api.abort(500, 'Failed to retrieve status distribution')


@api.route('/charts/priority-breakdown')
class PriorityBreakdownChartResource(Resource):
    @api.doc('get_priority_breakdown')
    @api.marshal_with(chart_data_model)
    @api.doc(security='Bearer')
    @require_auth
    def get(self):
        """Get priority breakdown chart data"""
        try:
            days = request.args.get('days', 30, type=int)
            start_date = datetime.utcnow() - timedelta(days=days)
            
            priority_data = db.session.query(
                ChangeRequest.priority,
                db.func.count(ChangeRequest.id)
            ).filter(
                ChangeRequest.created_at >= start_date
            ).group_by(ChangeRequest.priority).all()
            
            # Order by priority level
            priority_order = {'low': 0, 'medium': 1, 'high': 2, 'critical': 3}
            sorted_data = sorted(priority_data, key=lambda x: priority_order.get(x[0], 99))
            
            labels = [priority.title() for priority, count in sorted_data]
            data = [count for priority, count in sorted_data]
            
            return {
                'labels': labels,
                'data': data
            }
            
        except Exception as e:
            logger.error("Failed to get priority breakdown", error=str(e))
            api.abort(500, 'Failed to retrieve priority breakdown')


@api.route('/charts/category-trends')
class CategoryTrendsChartResource(Resource):
    @api.doc('get_category_trends')
    @api.doc(security='Bearer')
    @require_auth
    def get(self):
        """Get category trends over time"""
        try:
            days = request.args.get('days', 30, type=int)
            start_date = datetime.utcnow() - timedelta(days=days)
            
            category_data = db.session.query(
                ChangeRequest.category,
                db.func.count(ChangeRequest.id)
            ).filter(
                ChangeRequest.created_at >= start_date
            ).group_by(ChangeRequest.category).all()
            
            labels = [category.replace('_', ' ').title() for category, count in category_data]
            data = [count for category, count in category_data]
            
            return {
                'labels': labels,
                'data': data
            }
            
        except Exception as e:
            logger.error("Failed to get category trends", error=str(e))
            api.abort(500, 'Failed to retrieve category trends')


@api.route('/quality-metrics')
class QualityMetricsResource(Resource):
    @api.doc('get_quality_metrics')
    @api.doc(security='Bearer')
    @require_auth
    def get(self):
        """Get quality-related metrics"""
        try:
            days = request.args.get('days', 30, type=int)
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # Quality score distribution
            quality_ranges = [
                ('0-20', 0, 20),
                ('21-40', 21, 40),
                ('41-60', 41, 60),
                ('61-80', 61, 80),
                ('81-100', 81, 100)
            ]
            
            quality_distribution = []
            for range_name, min_score, max_score in quality_ranges:
                count = ChangeRequest.query.filter(
                    ChangeRequest.created_at >= start_date,
                    ChangeRequest.quality_score >= min_score,
                    ChangeRequest.quality_score <= max_score
                ).count()
                quality_distribution.append({'range': range_name, 'count': count})
            
            # Average quality score over time (weekly)
            weekly_quality = []
            for week in range(4):
                week_start = datetime.utcnow() - timedelta(weeks=week+1)
                week_end = datetime.utcnow() - timedelta(weeks=week)
                
                avg_quality = db.session.query(
                    db.func.avg(ChangeRequest.quality_score)
                ).filter(
                    ChangeRequest.created_at >= week_start,
                    ChangeRequest.created_at < week_end,
                    ChangeRequest.quality_score.isnot(None)
                ).scalar()
                
                weekly_quality.append({
                    'week': f'Week {4-week}',
                    'avg_quality': round(float(avg_quality or 0), 2)
                })
            
            # Quality issues summary
            quality_issues_count = QualityIssue.query.join(ChangeRequest).filter(
                ChangeRequest.created_at >= start_date,
                QualityIssue.resolved == False
            ).count()
            
            critical_issues_count = QualityIssue.query.join(ChangeRequest).filter(
                ChangeRequest.created_at >= start_date,
                QualityIssue.severity == 'critical',
                QualityIssue.resolved == False
            ).count()
            
            return {
                'quality_distribution': quality_distribution,
                'weekly_quality_trend': weekly_quality,
                'open_quality_issues': quality_issues_count,
                'critical_quality_issues': critical_issues_count
            }
            
        except Exception as e:
            logger.error("Failed to get quality metrics", error=str(e))
            api.abort(500, 'Failed to retrieve quality metrics')


@api.route('/ai-performance')
class AIPerformanceResource(Resource):
    @api.doc('get_ai_performance')
    @api.doc(security='Bearer')
    @require_role(['admin', 'manager', 'analyst'])
    def get(self):
        """Get AI performance metrics"""
        try:
            days = request.args.get('days', 30, type=int)
            start_date = datetime.utcnow() - timedelta(days=days)
            
            # AI analysis statistics
            total_analyses = AIAnalysisResult.query.filter(
                AIAnalysisResult.created_at >= start_date
            ).count()
            
            successful_analyses = AIAnalysisResult.query.filter(
                AIAnalysisResult.created_at >= start_date,
                AIAnalysisResult.error_occurred == 'false'
            ).count()
            
            avg_confidence = db.session.query(
                db.func.avg(AIAnalysisResult.confidence_score)
            ).filter(
                AIAnalysisResult.created_at >= start_date,
                AIAnalysisResult.confidence_score.isnot(None)
            ).scalar() or 0
            
            avg_processing_time = db.session.query(
                db.func.avg(AIAnalysisResult.processing_time_ms)
            ).filter(
                AIAnalysisResult.created_at >= start_date,
                AIAnalysisResult.processing_time_ms.isnot(None)
            ).scalar() or 0
            
            # Provider breakdown
            provider_stats = db.session.query(
                AIAnalysisResult.provider,
                db.func.count(AIAnalysisResult.id)
            ).filter(
                AIAnalysisResult.created_at >= start_date
            ).group_by(AIAnalysisResult.provider).all()
            
            # Model usage
            model_stats = db.session.query(
                AIAnalysisResult.ai_model_used,
                db.func.count(AIAnalysisResult.id)
            ).filter(
                AIAnalysisResult.created_at >= start_date
            ).group_by(AIAnalysisResult.ai_model_used).all()
            
            return {
                'total_analyses': total_analyses,
                'successful_analyses': successful_analyses,
                'success_rate': round((successful_analyses / total_analyses * 100) if total_analyses > 0 else 0, 2),
                'avg_confidence_score': round(float(avg_confidence), 2),
                'avg_processing_time_ms': round(float(avg_processing_time), 0),
                'provider_usage': [{'provider': provider, 'count': count} for provider, count in provider_stats],
                'model_usage': [{'model': model, 'count': count} for model, count in model_stats]
            }
            
        except Exception as e:
            logger.error("Failed to get AI performance metrics", error=str(e))
            api.abort(500, 'Failed to retrieve AI performance metrics')


@api.route('/recent-activity')
class RecentActivityResource(Resource):
    @api.doc('get_recent_activity')
    @api.doc(security='Bearer')
    @require_auth
    def get(self):
        """Get recent system activity"""
        try:
            limit = request.args.get('limit', 20, type=int)
            limit = min(limit, 100)  # Cap at 100
            
            # Get recent CRs with basic info
            recent_crs = ChangeRequest.query.order_by(
                ChangeRequest.updated_at.desc()
            ).limit(limit).all()
            
            activities = []
            for cr in recent_crs:
                activities.append({
                    'id': str(cr.id),
                    'type': 'change_request_updated',
                    'cr_number': cr.cr_number,
                    'title': cr.title,
                    'status': cr.status,
                    'priority': cr.priority,
                    'updated_at': cr.updated_at.isoformat() if cr.updated_at else None,
                    'submitter_id': str(cr.submitter_id) if cr.submitter_id else None
                })
            
            return {
                'activities': activities,
                'total_count': len(activities)
            }
            
        except Exception as e:
            logger.error("Failed to get recent activity", error=str(e))
            api.abort(500, 'Failed to retrieve recent activity')


@api.route('/user-workload')
class UserWorkloadResource(Resource):
    @api.doc('get_user_workload')
    @api.doc(security='Bearer')
    @require_role(['admin', 'manager'])
    def get(self):
        """Get user workload statistics"""
        try:
            # Get active CRs per user
            user_workload = db.session.query(
                User.full_name,
                User.email,
                db.func.count(ChangeRequest.id).label('active_crs')
            ).join(
                ChangeRequest, ChangeRequest.submitter_id == User.id
            ).filter(
                ChangeRequest.status.in_([
                    'submitted', 'under_review', 'pending_approval',
                    'approved', 'in_progress', 'testing'
                ])
            ).group_by(User.id, User.full_name, User.email).all()
            
            workload_data = [
                {
                    'user_name': name,
                    'user_email': email,
                    'active_crs': count
                }
                for name, email, count in user_workload
            ]
            
            return {
                'user_workload': workload_data
            }
            
        except Exception as e:
            logger.error("Failed to get user workload", error=str(e))
            api.abort(500, 'Failed to retrieve user workload')