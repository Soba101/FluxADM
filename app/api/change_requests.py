"""Change Request API endpoints"""

from flask import request, jsonify
from flask_restx import Namespace, Resource, fields
from werkzeug.datastructures import FileStorage
import asyncio
import structlog

from app.models import db, ChangeRequest, User
from app.services import FileHandler, AIProcessor
from app.api.auth import require_auth, require_role

logger = structlog.get_logger(__name__)

api = Namespace('change-requests', description='Change Request operations')

# API Models for documentation
cr_model = api.model('ChangeRequest', {
    'id': fields.String(description='CR ID'),
    'cr_number': fields.String(description='CR Number'),
    'title': fields.String(description='CR Title'),
    'description': fields.String(description='Description'),
    'category': fields.String(description='Category'),
    'priority': fields.String(description='Priority'),
    'risk_level': fields.String(description='Risk Level'),
    'status': fields.String(description='Status'),
    'quality_score': fields.Integer(description='Quality Score'),
    'ai_confidence': fields.Float(description='AI Confidence'),
    'created_at': fields.String(description='Creation Date'),
    'updated_at': fields.String(description='Last Update Date')
})

cr_create_model = api.model('ChangeRequestCreate', {
    'title': fields.String(required=True, description='CR Title'),
    'description': fields.String(description='Description'),
    'business_justification': fields.String(description='Business Justification'),
    'technical_details': fields.String(description='Technical Details'),
    'affected_systems': fields.List(fields.String, description='Affected Systems'),
    'target_completion_date': fields.String(description='Target Completion Date (ISO format)')
})

upload_parser = api.parser()
upload_parser.add_argument('file', location='files', type=FileStorage, required=True, help='Document file')
upload_parser.add_argument('title', location='form', type=str, help='Optional CR title')


@api.route('/')
class ChangeRequestListResource(Resource):
    @api.doc('list_change_requests')
    @api.marshal_list_with(cr_model)
    @api.doc(security='Bearer')
    @require_auth
    def get(self):
        """Get list of change requests with filtering"""
        try:
            # Get query parameters
            page = request.args.get('page', 1, type=int)
            per_page = min(request.args.get('per_page', 20, type=int), 100)
            status = request.args.get('status')
            category = request.args.get('category')
            priority = request.args.get('priority')
            risk_level = request.args.get('risk_level')
            
            # Build query
            query = ChangeRequest.query
            
            # Apply filters
            if status:
                query = query.filter(ChangeRequest.status == status)
            if category:
                query = query.filter(ChangeRequest.category == category)
            if priority:
                query = query.filter(ChangeRequest.priority == priority)
            if risk_level:
                query = query.filter(ChangeRequest.risk_level == risk_level)
            
            # Order by creation date (newest first)
            query = query.order_by(ChangeRequest.created_at.desc())
            
            # Paginate
            pagination = query.paginate(
                page=page,
                per_page=per_page,
                error_out=False
            )
            
            crs = [cr.to_dict() for cr in pagination.items]
            
            # Add pagination metadata
            response = jsonify({
                'change_requests': crs,
                'pagination': {
                    'page': page,
                    'per_page': per_page,
                    'total': pagination.total,
                    'pages': pagination.pages,
                    'has_next': pagination.has_next,
                    'has_prev': pagination.has_prev
                }
            })
            
            return response
            
        except Exception as e:
            logger.error("Failed to list change requests", error=str(e))
            api.abort(500, 'Failed to retrieve change requests')
    
    @api.doc('create_change_request')
    @api.expect(cr_create_model)
    @api.marshal_with(cr_model)
    @api.doc(security='Bearer')
    @require_auth
    def post(self):
        """Create new change request"""
        try:
            data = request.get_json()
            
            if not data or not data.get('title'):
                api.abort(400, 'Title is required')
            
            # Generate CR number
            cr_number = ChangeRequest.generate_cr_number()
            
            # Create CR
            cr = ChangeRequest(
                cr_number=cr_number,
                title=data['title'],
                description=data.get('description', ''),
                business_justification=data.get('business_justification', ''),
                technical_details=data.get('technical_details', ''),
                affected_systems=data.get('affected_systems', []),
                submitter_id=request.current_user.id,
                category='normal',  # Default, will be updated by AI analysis
                priority='medium',  # Default, will be updated by AI analysis
                risk_level='medium'  # Default, will be updated by AI analysis
            )
            
            # Set target completion date if provided
            if data.get('target_completion_date'):
                from datetime import datetime
                try:
                    cr.target_completion_date = datetime.fromisoformat(
                        data['target_completion_date'].replace('Z', '+00:00')
                    ).date()
                except ValueError:
                    api.abort(400, 'Invalid target_completion_date format. Use ISO format.')
            
            db.session.add(cr)
            db.session.commit()
            
            logger.info("Change request created", 
                       cr_id=str(cr.id),
                       cr_number=cr.cr_number,
                       submitter=request.current_user.email)
            
            return cr.to_dict(include_sensitive=True), 201
            
        except Exception as e:
            db.session.rollback()
            logger.error("Failed to create change request", error=str(e))
            api.abort(500, 'Failed to create change request')


@api.route('/<string:cr_id>')
class ChangeRequestResource(Resource):
    @api.doc('get_change_request')
    @api.marshal_with(cr_model)
    @api.doc(security='Bearer')
    @require_auth
    def get(self, cr_id):
        """Get specific change request"""
        try:
            cr = ChangeRequest.query.get(cr_id)
            
            if not cr:
                api.abort(404, 'Change request not found')
            
            # Check permissions - users can see their own CRs or if they have appropriate role
            if (cr.submitter_id != request.current_user.id and 
                request.current_user.role not in ['admin', 'manager', 'analyst']):
                api.abort(403, 'Access denied')
            
            return cr.to_dict(include_sensitive=True)
            
        except Exception as e:
            logger.error("Failed to get change request", cr_id=cr_id, error=str(e))
            api.abort(500, 'Failed to retrieve change request')
    
    @api.doc('update_change_request')
    @api.expect(cr_create_model)
    @api.marshal_with(cr_model)
    @api.doc(security='Bearer')
    @require_auth
    def put(self, cr_id):
        """Update change request"""
        try:
            cr = ChangeRequest.query.get(cr_id)
            
            if not cr:
                api.abort(404, 'Change request not found')
            
            # Check permissions
            if (cr.submitter_id != request.current_user.id and 
                request.current_user.role not in ['admin', 'manager']):
                api.abort(403, 'Access denied')
            
            data = request.get_json()
            
            # Update fields
            if 'title' in data:
                cr.title = data['title']
            if 'description' in data:
                cr.description = data['description']
            if 'business_justification' in data:
                cr.business_justification = data['business_justification']
            if 'technical_details' in data:
                cr.technical_details = data['technical_details']
            if 'affected_systems' in data:
                cr.affected_systems = data['affected_systems']
            
            if 'target_completion_date' in data and data['target_completion_date']:
                from datetime import datetime
                try:
                    cr.target_completion_date = datetime.fromisoformat(
                        data['target_completion_date'].replace('Z', '+00:00')
                    ).date()
                except ValueError:
                    api.abort(400, 'Invalid target_completion_date format')
            
            db.session.commit()
            
            logger.info("Change request updated", 
                       cr_id=str(cr.id),
                       updater=request.current_user.email)
            
            return cr.to_dict(include_sensitive=True)
            
        except Exception as e:
            db.session.rollback()
            logger.error("Failed to update change request", cr_id=cr_id, error=str(e))
            api.abort(500, 'Failed to update change request')


@api.route('/<string:cr_id>/status')
class ChangeRequestStatusResource(Resource):
    @api.doc('update_cr_status')
    @api.doc(security='Bearer')
    @require_role(['admin', 'manager', 'analyst'])
    def put(self, cr_id):
        """Update change request status"""
        try:
            cr = ChangeRequest.query.get(cr_id)
            
            if not cr:
                api.abort(404, 'Change request not found')
            
            data = request.get_json()
            new_status = data.get('status')
            
            if not new_status:
                api.abort(400, 'Status is required')
            
            # Validate status
            from app.models.change_request import ChangeRequestStatus
            try:
                status_enum = ChangeRequestStatus(new_status)
            except ValueError:
                valid_statuses = [s.value for s in ChangeRequestStatus]
                api.abort(400, f'Invalid status. Valid options: {valid_statuses}')
            
            # Update status
            cr.update_status(status_enum, request.current_user.id)
            db.session.commit()
            
            logger.info("Change request status updated", 
                       cr_id=str(cr.id),
                       old_status=cr.status,
                       new_status=new_status,
                       updater=request.current_user.email)
            
            return {'message': 'Status updated successfully', 'status': new_status}
            
        except Exception as e:
            db.session.rollback()
            logger.error("Failed to update CR status", cr_id=cr_id, error=str(e))
            api.abort(500, 'Failed to update status')


@api.route('/upload')
class ChangeRequestUploadResource(Resource):
    @api.doc('upload_cr_document')
    @api.expect(upload_parser)
    @api.doc(security='Bearer')
    @require_auth
    def post(self):
        """Upload and analyze change request document"""
        try:
            # Get uploaded file
            if 'file' not in request.files:
                api.abort(400, 'No file uploaded')
            
            uploaded_file = request.files['file']
            
            if uploaded_file.filename == '':
                api.abort(400, 'No file selected')
            
            # Get optional title
            title = request.form.get('title', '')
            
            # Initialize services
            file_handler = FileHandler()
            ai_processor = AIProcessor()
            
            # Read file data
            file_data = uploaded_file.read()
            
            # Validate file
            is_valid, error_msg = file_handler.validate_file(file_data, uploaded_file.filename)
            if not is_valid:
                api.abort(400, error_msg)
            
            # Save file
            file_path, save_error = file_handler.save_file(file_data, uploaded_file.filename)
            if save_error:
                api.abort(500, f'Failed to save file: {save_error}')
            
            # Extract text
            text_content, extract_error, metadata = file_handler.extract_text(file_path)
            if extract_error:
                api.abort(500, f'Failed to extract text: {extract_error}')
            
            # Generate CR number
            cr_number = ChangeRequest.generate_cr_number()
            
            # Create initial CR
            cr = ChangeRequest(
                cr_number=cr_number,
                title=title or f'CR from {uploaded_file.filename}',
                description=text_content[:1000] + '...' if len(text_content) > 1000 else text_content,
                submitter_id=request.current_user.id,
                category='normal',  # Will be updated by AI
                priority='medium',  # Will be updated by AI
                risk_level='medium',  # Will be updated by AI
                file_paths=[file_path]
            )
            
            db.session.add(cr)
            db.session.commit()
            
            # Perform AI analysis asynchronously (in a real app, this would be a background job)
            try:
                # For now, we'll run it synchronously but in production this should be async
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                analysis_result = loop.run_until_complete(
                    ai_processor.analyze_change_request(str(cr.id), text_content)
                )
                loop.close()
                
                # Update CR with AI analysis results
                if analysis_result.get('categorization'):
                    cat_result = analysis_result['categorization']
                    cr.category = cat_result.get('category', 'normal')
                    cr.priority = cat_result.get('priority', 'medium')
                    if not title:
                        cr.title = cat_result.get('title', cr.title)
                    if not cr.description or len(cr.description) < 100:
                        cr.description = cat_result.get('description', cr.description)
                
                if analysis_result.get('risk_assessment'):
                    risk_result = analysis_result['risk_assessment']
                    cr.risk_level = risk_result.get('risk_level', 'medium')
                    cr.risk_score = risk_result.get('risk_score', 4)
                
                if analysis_result.get('quality_check'):
                    quality_result = analysis_result['quality_check']
                    cr.quality_score = quality_result.get('quality_score', 50)
                
                cr.ai_confidence = analysis_result.get('overall_confidence', 0.5)
                cr.ai_analysis_summary = analysis_result
                
                db.session.commit()
                
                logger.info("Document uploaded and analyzed", 
                           cr_id=str(cr.id),
                           filename=uploaded_file.filename,
                           text_length=len(text_content),
                           ai_confidence=cr.ai_confidence)
                
            except Exception as ai_error:
                # AI analysis failed, but CR is still created
                logger.error("AI analysis failed for uploaded CR", 
                           cr_id=str(cr.id), 
                           error=str(ai_error))
                cr.ai_confidence = 0.0
                db.session.commit()
            
            response_data = cr.to_dict(include_sensitive=True)
            response_data['file_metadata'] = metadata
            
            return response_data, 201
            
        except Exception as e:
            db.session.rollback()
            logger.error("Failed to upload and process document", error=str(e))
            api.abort(500, 'Failed to process uploaded document')


@api.route('/stats')
class ChangeRequestStatsResource(Resource):
    @api.doc('get_cr_statistics')
    @api.doc(security='Bearer')
    @require_auth
    def get(self):
        """Get change request statistics"""
        try:
            # Basic statistics
            total_crs = ChangeRequest.query.count()
            
            # Status breakdown
            status_stats = db.session.query(
                ChangeRequest.status, 
                db.func.count(ChangeRequest.id)
            ).group_by(ChangeRequest.status).all()
            
            # Priority breakdown
            priority_stats = db.session.query(
                ChangeRequest.priority,
                db.func.count(ChangeRequest.id)
            ).group_by(ChangeRequest.priority).all()
            
            # Risk level breakdown
            risk_stats = db.session.query(
                ChangeRequest.risk_level,
                db.func.count(ChangeRequest.id)
            ).group_by(ChangeRequest.risk_level).all()
            
            # Category breakdown
            category_stats = db.session.query(
                ChangeRequest.category,
                db.func.count(ChangeRequest.id)
            ).group_by(ChangeRequest.category).all()
            
            # Quality metrics
            avg_quality = db.session.query(
                db.func.avg(ChangeRequest.quality_score)
            ).scalar() or 0
            
            avg_ai_confidence = db.session.query(
                db.func.avg(ChangeRequest.ai_confidence)
            ).scalar() or 0
            
            stats = {
                'total_change_requests': total_crs,
                'average_quality_score': round(float(avg_quality), 2),
                'average_ai_confidence': round(float(avg_ai_confidence), 2),
                'status_breakdown': {status: count for status, count in status_stats},
                'priority_breakdown': {priority: count for priority, count in priority_stats},
                'risk_breakdown': {risk: count for risk, count in risk_stats},
                'category_breakdown': {category: count for category, count in category_stats}
            }
            
            return stats
            
        except Exception as e:
            logger.error("Failed to get CR statistics", error=str(e))
            api.abort(500, 'Failed to retrieve statistics')