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
    import asyncio
    SERVICES_AVAILABLE = True
except ImportError as e:
    st.error(f"⚠️ FluxADM services not available: {e}")
    SERVICES_AVAILABLE = False

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
                    # Mock authentication (replace with real API call)
                    if email == "admin@fluxadm.com" and password == "admin123":
                        st.session_state.authenticated = True
                        st.session_state.user_data = {
                            'email': email,
                            'full_name': 'FluxADM Administrator',
                            'role': 'admin',
                            'department': 'IT'
                        }
                        st.success("Login successful!")
                        st.rerun()
                    else:
                        st.error("Invalid credentials. Try admin@fluxadm.com / admin123")
                else:
                    st.error("Please enter both email and password")
        
        st.info("Demo credentials: admin@fluxadm.com / admin123")


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
    """Display change requests page"""
    st.markdown("<h1 class='title-header'>📋 Change Requests</h1>", unsafe_allow_html=True)
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        status_filter = st.selectbox("Status", ["All", "Draft", "Under Review", "Approved", "In Progress", "Completed"])
    
    with col2:
        priority_filter = st.selectbox("Priority", ["All", "Low", "Medium", "High", "Critical"])
    
    with col3:
        risk_filter = st.selectbox("Risk Level", ["All", "Low", "Medium", "High"])
    
    with col4:
        search_term = st.text_input("Search", placeholder="Search by title...")
    
    st.divider()
    
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
    
    with st.form("upload_form"):
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=['pdf', 'txt', 'docx', 'doc'],
            help="Upload PDF, TXT, or Word documents (max 50MB)"
        )
        
        title = st.text_input(
            "Title (optional)",
            placeholder="Enter a title for this change request"
        )
        
        description = st.text_area(
            "Description (optional)", 
            placeholder="Brief description of the change request"
        )
        
        submit = st.form_submit_button("Analyze Document", width="stretch")
        
        if submit and uploaded_file:
            if not SERVICES_AVAILABLE:
                st.error("⚠️ FluxADM services are not available. Please check the installation.")
                return
            
            with st.spinner("Processing document..."):
                try:
                    # Step 1: Save and extract text from uploaded file
                    file_handler = FileHandler()
                    
                    # Get file data
                    file_data = uploaded_file.read()
                    filename = uploaded_file.name
                    
                    # Validate file
                    is_valid, error_msg = file_handler.validate_file(file_data, filename)
                    if not is_valid:
                        st.error(f"❌ File validation failed: {error_msg}")
                        return
                    
                    # Save file
                    file_path, save_error = file_handler.save_file(file_data, filename)
                    if save_error:
                        st.error(f"❌ Failed to save file: {save_error}")
                        return
                    
                    # Extract text
                    with st.spinner("Extracting text from document..."):
                        extracted_text, extract_error, metadata = file_handler.extract_text(file_path)
                        if extract_error:
                            st.error(f"❌ Text extraction failed: {extract_error}")
                            return
                        
                        if not extracted_text or len(extracted_text.strip()) < 50:
                            st.warning("⚠️ Very little text was extracted from the document. Analysis may be limited.")
                    
                    # Step 2: AI Analysis
                    with st.spinner("Analyzing document with AI..."):
                        ai_processor = AIProcessor()
                        
                        # Check if local LLM is available
                        if not ai_processor.local_llm_available:
                            st.error("❌ Local LLM is not available. Please ensure LM Studio is running at http://127.0.0.1:1234")
                            return
                        
                        # Run async analysis
                        import uuid
                        test_cr_id = str(uuid.uuid4())
                        
                        # Use asyncio to run the async function
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            analysis_result = loop.run_until_complete(
                                ai_processor.analyze_change_request(test_cr_id, extracted_text)
                            )
                        finally:
                            loop.close()
                    
                    # Step 3: Display Results
                    st.success("✅ Document processed and analyzed successfully!")
                    
                    # Analysis results
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("🤖 AI Analysis Results")
                        
                        # Categorization results
                        if 'categorization' in analysis_result:
                            cat = analysis_result['categorization']
                            st.metric("Category", cat.get('category', 'Unknown').title())
                            st.metric("Priority", cat.get('priority', 'Unknown').title())
                            st.metric("AI Confidence", f"{int(cat.get('confidence', 0) * 100)}%")
                        
                        # Risk assessment
                        if 'risk_assessment' in analysis_result:
                            risk = analysis_result['risk_assessment']
                            st.metric("Risk Level", risk.get('risk_level', 'Unknown').title())
                            st.metric("Risk Score", f"{risk.get('risk_score', 0)}/9")
                        
                        # Quality check
                        if 'quality_check' in analysis_result:
                            quality = analysis_result['quality_check']
                            st.metric("Quality Score", f"{quality.get('quality_score', 0)}%")
                    
                    with col2:
                        st.subheader("📄 Extracted Information")
                        
                        # Document info
                        st.write(f"**Original Filename:** {filename}")
                        st.write(f"**File Size:** {len(file_data):,} bytes")
                        st.write(f"**Text Length:** {len(extracted_text):,} characters")
                        st.write(f"**Extraction Method:** {metadata.get('extraction_method', 'Unknown')}")
                        
                        # Show categorization details
                        if 'categorization' in analysis_result:
                            cat = analysis_result['categorization']
                            if cat.get('title'):
                                st.write(f"**Suggested Title:** {cat['title'][:100]}...")
                            if cat.get('affected_systems'):
                                systems = ', '.join(cat['affected_systems'][:3])
                                st.write(f"**Affected Systems:** {systems}")
                            if cat.get('reasoning'):
                                st.write(f"**AI Reasoning:** {cat['reasoning'][:200]}...")
                    
                    # Quality issues
                    if 'quality_check' in analysis_result:
                        quality = analysis_result['quality_check']
                        issues = quality.get('quality_issues', [])
                        
                        if issues:
                            st.subheader("⚠️ Quality Issues Found")
                            for issue in issues[:5]:  # Show up to 5 issues
                                severity = issue.get('severity', 'medium')
                                description = issue.get('description', 'Unknown issue')
                                if severity == 'high':
                                    st.error(f"• {description}")
                                elif severity == 'medium':
                                    st.warning(f"• {description}")
                                else:
                                    st.info(f"• {description}")
                    
                    # Overall assessment
                    overall_confidence = analysis_result.get('overall_confidence', 0)
                    providers_used = analysis_result.get('providers_used', [])
                    
                    if overall_confidence > 0.7:
                        st.success(f"🎯 High confidence analysis ({int(overall_confidence * 100)}%) using {', '.join(providers_used)}")
                    elif overall_confidence > 0.5:
                        st.warning(f"⚠️ Medium confidence analysis ({int(overall_confidence * 100)}%) using {', '.join(providers_used)}")
                    else:
                        st.error(f"❌ Low confidence analysis ({int(overall_confidence * 100)}%) using {', '.join(providers_used)}")
                    
                    # Text preview
                    with st.expander("📖 Extracted Text Preview"):
                        st.text_area("Document Content", extracted_text[:2000] + ("..." if len(extracted_text) > 2000 else ""), height=200)
                        
                except Exception as e:
                    st.error(f"❌ Processing failed: {str(e)}")
                    st.exception(e)


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