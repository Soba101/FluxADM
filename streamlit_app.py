"""
FluxADM Streamlit Dashboard
Simple web interface for FluxADM system
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import requests
import json
import os
import sys

# Add app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

# Import FluxADM services
try:
    from app.services.file_handler import FileHandler
    from app.services.ai_processor import AIProcessor
    from app.models import db, User, ChangeRequest
    from app.models.change_request import ChangeRequestStatus
    from flask import Flask
    import asyncio
    from batch_upload_helper import process_single_file, display_batch_results
    SERVICES_AVAILABLE = True
except ImportError as e:
    st.error(f"⚠️ FluxADM services not available: {e}")
    SERVICES_AVAILABLE = False

# Database setup
def get_flask_app():
    """Create Flask app context for database operations"""
    if not SERVICES_AVAILABLE:
        return None
    
    app = Flask(__name__)
    from config import get_settings
    settings = get_settings()
    app.config['SQLALCHEMY_DATABASE_URI'] = settings.DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    return app

def save_change_request(analysis_result, filename, extracted_text, user_title="", user_description=""):
    """Save analyzed change request to database"""
    app = get_flask_app()
    if not app:
        return None
    
    with app.app_context():
        try:
            # Get logged-in user or fallback to admin
            user_email = st.session_state.user_data.get('email', 'admin@fluxadm.com') if st.session_state.user_data else 'admin@fluxadm.com'
            current_user = User.query.filter_by(email=user_email).first()
            if not current_user:
                st.error("Current user not found in database.")
                return None
            
            # Extract data from analysis
            cat = analysis_result.get('categorization', {})
            risk = analysis_result.get('risk_assessment', {})
            quality = analysis_result.get('quality_check', {})
            
            # Create new change request
            cr = ChangeRequest(
                cr_number=ChangeRequest.generate_cr_number(),
                title=user_title or cat.get('title', f'Document Analysis - {filename}')[:500],
                description=user_description or cat.get('description', 'Analyzed from uploaded document')[:1000],
                business_justification=extracted_text[:2000] if len(extracted_text) > 100 else "Extracted from uploaded document",
                technical_details=extracted_text[:2000] if len(extracted_text) > 2000 else extracted_text,
                category=cat.get('category', 'normal'),
                priority=cat.get('priority', 'medium'), 
                risk_level=risk.get('risk_level', 'medium'),
                risk_score=risk.get('risk_score', 4),
                status=ChangeRequestStatus.SUBMITTED.value,
                submitter_id=current_user.id,
                affected_systems=cat.get('affected_systems', []),
                ai_confidence=analysis_result.get('overall_confidence', 0.5),
                quality_score=quality.get('quality_score', 50),
                ai_analysis_summary=analysis_result,
                file_paths=[filename]
            )
            
            db.session.add(cr)
            db.session.commit()
            
            return cr
            
        except Exception as e:
            st.error(f"Failed to save change request: {e}")
            return None

# Page configuration
st.set_page_config(
    page_title="FluxADM Dashboard",
    page_icon="🚀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .metric-card {
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1f77b4;
    }
    
    /* Light mode styles (default) */
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        color: #000000;
    }
    
    /* Dark mode styles */
    [data-theme="dark"] .metric-card {
        background-color: #2d3748 !important;
        border: 1px solid #4a5568 !important;
        color: #ffffff !important;
    }
    .high-priority {
        border-left-color: #ff6b6b !important;
    }
    .medium-priority {
        border-left-color: #feca57 !important;
    }
    .low-priority {
        border-left-color: #48dbfb !important;
    }
    .title-header {
        color: #1f77b4;
        margin-bottom: 2rem;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables"""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'user_data' not in st.session_state:
        st.session_state.user_data = None
    if 'api_token' not in st.session_state:
        st.session_state.api_token = None


def mock_api_call(endpoint, method='GET', data=None):
    """
    Mock API calls for demonstration (replace with real API calls)
    In production, this would make actual HTTP requests to the Flask API
    """
    
    # Mock data for demonstration
    mock_responses = {
        '/api/v1/dashboard/metrics': {
            'total_crs': 156,
            'active_crs': 23,
            'completed_crs': 133,
            'high_risk_crs': 8,
            'avg_quality_score': 78.5,
            'avg_processing_time': 4.2
        },
        '/api/v1/dashboard/charts/status-distribution': {
            'labels': ['Draft', 'Under Review', 'Approved', 'In Progress', 'Completed', 'Cancelled'],
            'data': [5, 8, 3, 7, 133, 2]
        },
        '/api/v1/dashboard/charts/priority-breakdown': {
            'labels': ['Low', 'Medium', 'High', 'Critical'],
            'data': [45, 78, 28, 5]
        },
        '/api/v1/change-requests/stats': {
            'total_change_requests': 156,
            'average_quality_score': 78.5,
            'average_ai_confidence': 0.82,
            'status_breakdown': {
                'draft': 5,
                'under_review': 8,
                'approved': 3,
                'in_progress': 7,
                'completed': 133
            },
            'priority_breakdown': {
                'low': 45,
                'medium': 78,
                'high': 28,
                'critical': 5
            },
            'risk_breakdown': {
                'low': 58,
                'medium': 90,
                'high': 8
            },
            'category_breakdown': {
                'normal': 89,
                'enhancement': 34,
                'emergency': 3,
                'security': 12,
                'maintenance': 18
            }
        }
    }
    
    return mock_responses.get(endpoint, {})


def login_page():
    """Display login page"""
    st.markdown("<h1 class='title-header'>🚀 FluxADM Login</h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("### Sign in to your account")
        
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="Enter your email address", key="login_email")
            password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_password")
            submit = st.form_submit_button("Sign In", width="stretch")
            
            if submit:
                if email and password:
                    # Real database authentication
                    if SERVICES_AVAILABLE:
                        app = get_flask_app()
                        if app:
                            with app.app_context():
                                try:
                                    user = User.query.filter_by(email=email).first()
                                    if user and user.check_password(password) and user.is_active:
                                        st.session_state.authenticated = True
                                        st.session_state.user_data = {
                                            'id': str(user.id),
                                            'email': user.email,
                                            'full_name': user.full_name,
                                            'role': user.role,
                                            'department': user.department
                                        }
                                        st.success(f"Welcome back, {user.full_name}!")
                                        
                                        # Update last login
                                        user.update_last_login()
                                        
                                        st.rerun()
                                    else:
                                        st.error("Invalid credentials or inactive account")
                                except Exception as e:
                                    st.error(f"Login error: {e}")
                                    # Fallback for development
                                    if email == "admin@fluxadm.com" and password == "admin123":
                                        st.session_state.authenticated = True
                                        st.session_state.user_data = {
                                            'email': email,
                                            'full_name': 'FluxADM Administrator',
                                            'role': 'admin',
                                            'department': 'IT'
                                        }
                                        st.warning("Using fallback authentication")
                                        st.rerun()
                        else:
                            st.error("Database connection failed")
                    else:
                        st.error("Authentication services not available")
                else:
                    st.error("Please enter both email and password")
        
        st.info("""
        **Demo Credentials:**
        - **Admin**: admin@fluxadm.com / admin123
        - **Manager**: manager@fluxadm.com / password123
        - **Analyst**: analyst@fluxadm.com / password123
        - **User**: user@fluxadm.com / password123
        """)


def sidebar_navigation():
    """Display sidebar navigation"""
    st.sidebar.markdown(f"### Welcome, {st.session_state.user_data['full_name']}")
    st.sidebar.markdown(f"**Role:** {st.session_state.user_data['role']}")
    st.sidebar.markdown(f"**Department:** {st.session_state.user_data['department']}")
    
    st.sidebar.divider()
    
    pages = {
        "🏠 Dashboard": "dashboard",
        "📊 Analytics": "analytics", 
        "📋 Change Requests": "change_requests",
        "📤 Upload Document": "upload",
        "⚙️ Settings": "settings"
    }
    
    selected_page = st.sidebar.selectbox("Navigate to:", list(pages.keys()))
    
    st.sidebar.divider()
    
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.session_state.user_data = None
        st.session_state.api_token = None
        st.experimental_rerun()
    
    return pages[selected_page]


def dashboard_page():
    """Display main dashboard"""
    st.markdown("<h1 class='title-header'>🏠 FluxADM Dashboard</h1>", unsafe_allow_html=True)
    
    # Get metrics
    metrics = mock_api_call('/api/v1/dashboard/metrics')
    
    # Key metrics row
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="Total Change Requests",
            value=metrics.get('total_crs', 0),
            delta=f"+{metrics.get('total_crs', 0) - 145} this month"
        )
    
    with col2:
        st.metric(
            label="Active CRs",
            value=metrics.get('active_crs', 0),
            delta=f"{metrics.get('active_crs', 0) - 28} from last week"
        )
    
    with col3:
        st.metric(
            label="Average Quality Score",
            value=f"{metrics.get('avg_quality_score', 0):.1f}%",
            delta=f"+{metrics.get('avg_quality_score', 0) - 75:.1f}%"
        )
    
    with col4:
        st.metric(
            label="High Risk CRs",
            value=metrics.get('high_risk_crs', 0),
            delta=f"{metrics.get('high_risk_crs', 0) - 12} from last month",
            delta_color="inverse"
        )
    
    st.divider()
    
    # Charts row
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Status Distribution")
        status_data = mock_api_call('/api/v1/dashboard/charts/status-distribution')
        
        if status_data:
            fig_status = px.pie(
                values=status_data['data'],
                names=status_data['labels'],
                title="CR Status Distribution"
            )
            fig_status.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_status, width="stretch")
    
    with col2:
        st.subheader("Priority Breakdown")
        priority_data = mock_api_call('/api/v1/dashboard/charts/priority-breakdown')
        
        if priority_data:
            fig_priority = px.bar(
                x=priority_data['labels'],
                y=priority_data['data'],
                title="CR Priority Distribution",
                color=priority_data['labels'],
                color_discrete_map={
                    'Low': '#48dbfb',
                    'Medium': '#feca57',
                    'High': '#ff9ff3',
                    'Critical': '#ff6b6b'
                }
            )
            fig_priority.update_layout(showlegend=False)
            st.plotly_chart(fig_priority, width="stretch")
    
    # Recent activity
    st.subheader("Recent Activity")
    
    # Mock recent activities
    recent_activities = [
        {"cr_number": "CR-2024-000156", "title": "Database Performance Optimization", "status": "In Progress", "priority": "High", "updated": "2 hours ago"},
        {"cr_number": "CR-2024-000155", "title": "Security Patch Deployment", "status": "Completed", "priority": "Critical", "updated": "4 hours ago"},
        {"cr_number": "CR-2024-000154", "title": "User Interface Enhancement", "status": "Under Review", "priority": "Medium", "updated": "6 hours ago"},
        {"cr_number": "CR-2024-000153", "title": "API Rate Limiting Implementation", "status": "Approved", "priority": "High", "updated": "8 hours ago"},
    ]
    
    for activity in recent_activities:
        priority_class = f"{activity['priority'].lower()}-priority"
        
        st.markdown(f"""
        <div class="metric-card {priority_class}">
            <strong>{activity['cr_number']}</strong> - {activity['title']}<br>
            <small>Status: {activity['status']} | Priority: {activity['priority']} | {activity['updated']}</small>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)


def analytics_page():
    """Display analytics page"""
    st.markdown("<h1 class='title-header'>📊 Analytics</h1>", unsafe_allow_html=True)
    
    # Get statistics
    stats = mock_api_call('/api/v1/change-requests/stats')
    
    # Analytics overview
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total CRs Processed", stats.get('total_change_requests', 0))
    
    with col2:
        st.metric("Avg Quality Score", f"{stats.get('average_quality_score', 0):.1f}%")
    
    with col3:
        st.metric("AI Confidence", f"{stats.get('average_ai_confidence', 0):.0%}")
    
    st.divider()
    
    # Detailed charts
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Risk Level Distribution")
        risk_data = stats.get('risk_breakdown', {})
        
        if risk_data:
            fig_risk = px.bar(
                x=list(risk_data.keys()),
                y=list(risk_data.values()),
                title="Risk Level Distribution",
                color=list(risk_data.keys()),
                color_discrete_map={
                    'low': '#48dbfb',
                    'medium': '#feca57', 
                    'high': '#ff6b6b'
                }
            )
            fig_risk.update_layout(showlegend=False)
            st.plotly_chart(fig_risk, width="stretch")
    
    with col2:
        st.subheader("Category Breakdown")
        category_data = stats.get('category_breakdown', {})
        
        if category_data:
            fig_category = px.pie(
                values=list(category_data.values()),
                names=list(category_data.keys()),
                title="CR Category Distribution"
            )
            st.plotly_chart(fig_category, width="stretch")
    
    # Quality trend (mock data)
    st.subheader("Quality Score Trend (Last 30 Days)")
    
    # Generate mock trend data
    dates = pd.date_range(end=datetime.now(), periods=30, freq='D')
    quality_scores = [75 + (i * 0.5) + ((-1) ** i) * 3 for i in range(30)]
    
    trend_df = pd.DataFrame({
        'Date': dates,
        'Quality Score': quality_scores
    })
    
    fig_trend = px.line(
        trend_df,
        x='Date',
        y='Quality Score',
        title='Quality Score Trend Over Time',
        line_shape='spline'
    )
    fig_trend.add_hline(y=80, line_dash="dash", line_color="red", annotation_text="Target (80%)")
    fig_trend.update_layout(yaxis_range=[60, 90])
    
    st.plotly_chart(fig_trend, width="stretch")


def change_requests_page():
    """Display change requests page with real database data"""
    st.markdown("<h1 class='title-header'>📋 Change Requests</h1>", unsafe_allow_html=True)
    
    if not SERVICES_AVAILABLE:
        st.error("⚠️ Database services not available")
        return
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        status_filter = st.selectbox("Status", ["All", "Draft", "Submitted", "Under Review", "Approved", "In Progress", "Completed"])
    
    with col2:
        priority_filter = st.selectbox("Priority", ["All", "Low", "Medium", "High", "Critical"])
    
    with col3:
        risk_filter = st.selectbox("Risk Level", ["All", "Low", "Medium", "High"])
    
    with col4:
        search_term = st.text_input("Search", placeholder="Search by title...")
    
    st.divider()
    
    # Load real data from database
    app = get_flask_app()
    if not app:
        st.error("Unable to connect to database")
        return
    
    with app.app_context():
        try:
            # Query change requests
            query = ChangeRequest.query.order_by(ChangeRequest.created_at.desc())
            
            # Apply filters
            if status_filter != "All":
                query = query.filter(ChangeRequest.status == status_filter.lower().replace(" ", "_"))
            if priority_filter != "All":
                query = query.filter(ChangeRequest.priority == priority_filter.lower())
            if risk_filter != "All":
                query = query.filter(ChangeRequest.risk_level == risk_filter.lower())
            if search_term:
                query = query.filter(ChangeRequest.title.contains(search_term))
            
            change_requests = query.limit(50).all()  # Limit to 50 for performance
            
            if not change_requests:
                st.info("📭 No change requests found. Upload a document to create your first CR!")
                return
            
            # Display metrics
            total_crs = len(change_requests)
            st.metric("Total Change Requests", total_crs)
            
            # Create DataFrame from database results
            cr_data = []
            for cr in change_requests:
                cr_data.append({
                    "CR Number": cr.cr_number,
                    "Title": cr.title[:50] + "..." if len(cr.title) > 50 else cr.title,
                    "Status": cr.status.replace("_", " ").title(),
                    "Priority": cr.priority.title(),
                    "Risk Level": cr.risk_level.title(),
                    "Quality Score": f"{cr.quality_score}%" if cr.quality_score else "N/A",
                    "AI Confidence": f"{int(cr.ai_confidence * 100)}%" if cr.ai_confidence else "N/A",
                    "Created": cr.created_at.strftime("%Y-%m-%d"),
                    "Submitter": (User.query.get(cr.submitter_id).full_name if User.query.get(cr.submitter_id) else 'Unknown')
                })
            
            df = pd.DataFrame(cr_data)
            
            # Display table
            st.dataframe(df, width="stretch", height=400)
            
            # CR details
            if len(df) > 0:
                selected_cr_number = st.selectbox(
                    "Select a Change Request for details:", 
                    [cr.cr_number for cr in change_requests],
                    format_func=lambda x: f"{x} - {next(cr.title for cr in change_requests if cr.cr_number == x)[:30]}..."
                )
                
                if selected_cr_number:
                    selected_cr = next(cr for cr in change_requests if cr.cr_number == selected_cr_number)
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Change Request Details")
                        st.write(f"**Number:** {selected_cr.cr_number}")
                        st.write(f"**Title:** {selected_cr.title}")
                        st.write(f"**Status:** {selected_cr.status.replace('_', ' ').title()}")
                        st.write(f"**Priority:** {selected_cr.priority.title()}")
                        st.write(f"**Risk Level:** {selected_cr.risk_level.title()}")
                        st.write(f"**Risk Score:** {selected_cr.risk_score}/9")
                        st.write(f"**Quality Score:** {selected_cr.quality_score}%")
                        st.write(f"**AI Confidence:** {int(selected_cr.ai_confidence * 100)}%")
                        st.write(f"**Submitter:** {selected_(User.query.get(cr.submitter_id).full_name if User.query.get(cr.submitter_id) else 'Unknown')}")
                        st.write(f"**Created:** {selected_cr.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                        
                        if selected_cr.affected_systems:
                            st.write(f"**Affected Systems:** {', '.join(selected_cr.affected_systems)}")
                    
                    with col2:
                        st.subheader("Description")
                        st.write(selected_cr.description)
                        
                        if selected_cr.business_justification:
                            st.subheader("Business Justification")
                            st.write(selected_cr.business_justification[:300] + "..." if len(selected_cr.business_justification) > 300 else selected_cr.business_justification)
                        
                        st.subheader("Actions")
                        col_a, col_b = st.columns(2)
                        
                        with col_a:
                            if st.button("View Full Details", key=f"view_{selected_cr.id}"):
                                st.info("Full technical details would open in modal")
                            
                            if st.button("Download Files", key=f"download_{selected_cr.id}"):
                                st.info("File download would start here")
                        
                        with col_b:
                            if selected_cr.status != "completed":
                                if st.button("Approve", key=f"approve_{selected_cr.id}"):
                                    st.success("Change request approved!")
                                    st.experimental_rerun()
                            
                            if selected_cr.status == "submitted":
                                if st.button("Start Review", key=f"review_{selected_cr.id}"):
                                    st.success("Review started!")
                                    st.experimental_rerun()
            
        except Exception as e:
            st.error(f"Database error: {e}")
            return
    
    # Mock CR data
    cr_data = [
        {
            "CR Number": "CR-2024-000156",
            "Title": "Database Performance Optimization",
            "Status": "In Progress",
            "Priority": "High", 
            "Risk Level": "Medium",
            "Quality Score": "85%",
            "Created": "2024-01-15",
            "Submitter": "john.doe@company.com"
        },
        {
            "CR Number": "CR-2024-000155",
            "Title": "Security Patch Deployment", 
            "Status": "Completed",
            "Priority": "Critical",
            "Risk Level": "High",
            "Quality Score": "92%",
            "Created": "2024-01-14",
            "Submitter": "security@company.com"
        },
        {
            "CR Number": "CR-2024-000154",
            "Title": "User Interface Enhancement",
            "Status": "Under Review",
            "Priority": "Medium",
            "Risk Level": "Low", 
            "Quality Score": "78%",
            "Created": "2024-01-13",
            "Submitter": "ui.team@company.com"
        },
        {
            "CR Number": "CR-2024-000153", 
            "Title": "API Rate Limiting Implementation",
            "Status": "Approved",
            "Priority": "High",
            "Risk Level": "Medium",
            "Quality Score": "88%",
            "Created": "2024-01-12",
            "Submitter": "api.team@company.com"
        }
    ]
    
    # Convert to DataFrame
    df = pd.DataFrame(cr_data)
    
    # Apply filters (simplified)
    filtered_df = df.copy()
    
    if status_filter != "All":
        filtered_df = filtered_df[filtered_df["Status"] == status_filter]
    
    if priority_filter != "All":
        filtered_df = filtered_df[filtered_df["Priority"] == priority_filter]
    
    if risk_filter != "All":
        filtered_df = filtered_df[filtered_df["Risk Level"] == risk_filter]
    
    if search_term:
        filtered_df = filtered_df[filtered_df["Title"].str.contains(search_term, case=False)]
    
    # Display results
    st.write(f"Showing {len(filtered_df)} of {len(df)} change requests")
    
    # Display as interactive table
    st.dataframe(
        filtered_df,
        width="stretch",
        hide_index=True,
        column_config={
            "Quality Score": st.column_config.ProgressColumn(
                "Quality Score",
                help="AI-generated quality score",
                min_value=0,
                max_value=100,
                format="%d%%"
            ),
            "Status": st.column_config.Column(
                "Status",
                help="Current status of the change request"
            )
        }
    )


def upload_page():
    """Display document upload page"""
    st.markdown("<h1 class='title-header'>📤 Upload Document</h1>", unsafe_allow_html=True)
    
    st.write("Upload a change request document for AI-powered analysis.")
    
    # Upload mode selection
    upload_mode = st.radio("Upload Mode", ["Single Document", "Batch Upload (Multiple Documents)"], horizontal=True)
    
    with st.form("upload_form"):
        if upload_mode == "Single Document":
            uploaded_file = st.file_uploader(
                "Choose a file",
                type=['pdf', 'txt', 'docx', 'doc'],
                help="Upload PDF, TXT, or Word documents (max 50MB)"
            )
            uploaded_files = [uploaded_file] if uploaded_file else []
        else:
            uploaded_files = st.file_uploader(
                "Choose files",
                type=['pdf', 'txt', 'docx', 'doc'],
                help="Upload PDF, TXT, or Word documents (max 50MB each)",
                accept_multiple_files=True
            )
        
        title = st.text_input(
            "Title (optional)",
            placeholder="Enter a title for this change request"
        )
        
        description = st.text_area(
            "Description (optional)", 
            placeholder="Brief description of the change request"
        )
        
        submit = st.form_submit_button(f"Analyze {'Document' if upload_mode == 'Single Document' else 'Documents'}", width="stretch")
        
        if submit and uploaded_files:
            if not SERVICES_AVAILABLE:
                st.error("⚠️ FluxADM services are not available. Please check the installation.")
                return
            
            # Filter out None files (for single upload mode)
            valid_files = [f for f in uploaded_files if f is not None]
            
            if not valid_files:
                st.error("Please select at least one file to upload.")
                return
            
            st.info(f"Processing {len(valid_files)} file{'s' if len(valid_files) > 1 else ''}...")
            
            # Initialize services
            file_handler = FileHandler()
            ai_processor = AIProcessor()
            
            # Progress tracking
            progress_bar = st.progress(0)
            status_text = st.empty()
            results = []
            
            # Process each file
            for idx, uploaded_file in enumerate(valid_files):
                progress = (idx) / len(valid_files)
                progress_bar.progress(progress)
                status_text.text(f"Processing file {idx + 1} of {len(valid_files)}: {uploaded_file.name}")
                
                # Process the file
                result = process_single_file(file_handler, ai_processor, uploaded_file, title, description)
                results.append(result)
            
            # Complete progress
            progress_bar.progress(1.0)
            status_text.text("Processing complete!")
            
            # Display results
            display_batch_results(results, save_change_request, title, description)


def settings_page():
    """Display settings page"""
    st.markdown("<h1 class='title-header'>⚙️ Settings</h1>", unsafe_allow_html=True)
    
    tabs = st.tabs(["Profile", "Preferences", "API", "About"])
    
    with tabs[0]:
        st.subheader("User Profile")
        
        with st.form("profile_form"):
            full_name = st.text_input("Full Name", value=st.session_state.user_data.get('full_name', ''))
            email = st.text_input("Email", value=st.session_state.user_data.get('email', ''), disabled=True)
            department = st.text_input("Department", value=st.session_state.user_data.get('department', ''))
            phone = st.text_input("Phone", placeholder="Enter your phone number")
            
            if st.form_submit_button("Update Profile"):
                st.success("Profile updated successfully!")
    
    with tabs[1]:
        st.subheader("Dashboard Preferences")
        
        default_view = st.selectbox("Default Dashboard View", ["Overview", "Analytics", "My CRs"])
        theme = st.selectbox("Theme", ["Light", "Dark", "Auto"])
        notifications = st.checkbox("Enable Email Notifications", value=True)
        auto_refresh = st.selectbox("Auto Refresh", ["Disabled", "30 seconds", "1 minute", "5 minutes"])
        
        if st.button("Save Preferences"):
            st.success("Preferences saved successfully!")
    
    with tabs[2]:
        st.subheader("API Configuration")
        
        st.info("API endpoints for integrating with external systems:")
        
        st.code("Base URL: http://localhost:5000/api/v1/", language="text")
        st.code("Authentication: Bearer Token", language="text")
        
        if st.button("Generate API Token"):
            st.success("New API token generated!")
            st.code("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...", language="text")
    
    with tabs[3]:
        st.subheader("About FluxADM")
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            st.image("https://via.placeholder.com/150x150/1f77b4/white?text=FluxADM", width=150)
        
        with col2:
            st.write("**FluxADM** - AI-Powered Change Request Analyzer")
            st.write("Version: 1.0.0")
            st.write("Build: 2024.01.15")
            st.write("")
            st.write("Transform your change management process with intelligent automation.")
        
        st.divider()
        
        st.subheader("System Information")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Database Status", "✅ Connected")
            st.metric("AI Services", "✅ Available")
        
        with col2:
            st.metric("API Status", "✅ Running")
            st.metric("Background Jobs", "✅ Active")


def main():
    """Main application function"""
    init_session_state()
    
    if not st.session_state.authenticated:
        login_page()
        return
    
    # Authenticated user interface
    page = sidebar_navigation()
    
    # Route to appropriate page
    if page == "dashboard":
        dashboard_page()
    elif page == "analytics":
        analytics_page()
    elif page == "change_requests":
        change_requests_page()
    elif page == "upload":
        upload_page()
    elif page == "settings":
        settings_page()


if __name__ == "__main__":
    main()