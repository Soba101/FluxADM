#!/usr/bin/env python3
"""
FluxADM Setup Script
Initializes the project for first-time development setup
"""
import os
import sys
import subprocess
from pathlib import Path


def print_header():
    """Print welcome header"""
    print("=" * 60)
    print("🚀 FluxADM Setup - AI-Powered Change Request Analyzer")
    print("=" * 60)
    print()


def check_python_version():
    """Check Python version"""
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher required")
        print(f"Current version: {sys.version}")
        sys.exit(1)
    print(f"✅ Python {sys.version.split()[0]} - OK")



def install_dependencies():
    """Install Python dependencies"""
    print("📦 Installing dependencies...")
    try:
        # Use the current Python interpreter to install dependencies
        subprocess.run([
            sys.executable, "-m", "pip", "install", "--upgrade", "pip"
        ], check=True)

        subprocess.run([
            sys.executable, "-m", "pip", "install", "-r", "requirements.txt"
        ], check=True)

        print("✅ Dependencies installed successfully")
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies")
        sys.exit(1)


def create_env_file():
    """Create .env file from template"""
    env_file = Path(".env")
    env_template = Path(".env.example")
    
    if env_file.exists():
        print("✅ .env file already exists")
        return
    
    if env_template.exists():
        try:
            with open(env_template, 'r') as template:
                content = template.read()
            
            with open(env_file, 'w') as env:
                env.write(content)
            
            print("✅ Created .env file from template")
            print("⚠️  Please edit .env and add your API keys")
        except Exception as e:
            print(f"❌ Failed to create .env file: {e}")
    else:
        print("⚠️  No .env.example template found")


def create_sample_data():
    """Create sample CR documents for testing"""
    sample_dir = Path("data/sample_crs")
    sample_dir.mkdir(parents=True, exist_ok=True)
    
    sample_crs = [
        {
            "filename": "emergency_outage.txt",
            "content": """
EMERGENCY CHANGE REQUEST - PRODUCTION DATABASE OUTAGE

Change Request Title: Restore Production Database Service After Critical Failure
Priority: CRITICAL
Category: Emergency

Business Impact:
- Complete service outage affecting all customer-facing applications
- Estimated revenue loss: $50,000 per hour
- Customer satisfaction impact: SEVERE
- SLA breach in progress

Technical Details:
- Primary database server (DB-PROD-01) has suffered hardware failure
- Secondary replica is available but requires manual failover
- Root cause: Storage controller failure on primary server
- Affected systems: Customer Portal, Mobile App, API Gateway, Reporting Systems

Implementation Plan:
1. Immediate failover to secondary database server (DB-PROD-02)
2. Update load balancer configuration to route traffic
3. Verify application connectivity and data integrity
4. Monitor system performance and error rates
5. Implement temporary monitoring alerts

Rollback Plan:
- If failover fails, restore from latest backup (RPO: 15 minutes)
- Switch back to repaired primary server once hardware is fixed

Business Justification:
Critical service restoration to minimize business impact and maintain customer trust.
Every minute of downtime costs approximately $833 in lost revenue.

Approval: Emergency approval requested from IT Director
Implementation Window: IMMEDIATE
            """
        },
        {
            "filename": "enhancement_dashboard.txt", 
            "content": """
ENHANCEMENT REQUEST - User Dashboard Improvements

Change Request Title: Implement Advanced Analytics Dashboard for Customer Portal
Priority: MEDIUM
Category: Enhancement

Business Justification:
Current customer dashboard lacks advanced analytics capabilities that customers have been requesting.
Enhancement will improve customer satisfaction and potentially increase platform usage by 20%.
Competitive advantage through better user experience and data visualization.

Technical Details:
- Add new React components for chart visualization
- Integrate with existing analytics API endpoints
- Implement real-time data refresh using WebSocket connections
- Add export functionality for reports (PDF, Excel)
- Mobile responsive design improvements

Affected Systems:
- Customer Portal Frontend (React application)
- Analytics API Service
- Database views for aggregated reporting
- CDN configuration for new assets

Implementation Plan:
Phase 1 (2 weeks): Backend API enhancements and database optimizations
Phase 2 (3 weeks): Frontend component development and testing
Phase 3 (1 week): Integration testing and performance optimization
Phase 4 (1 week): User acceptance testing and deployment

Testing Strategy:
- Unit tests for all new components (target: 90% coverage)
- Integration testing with staging environment
- Performance testing with simulated load
- User acceptance testing with beta customer group
- Cross-browser compatibility testing

Rollback Plan:
- Feature flags to disable new dashboard components
- Database migration rollback scripts available
- Previous frontend version available for quick deployment

Risk Assessment:
- Technical Risk: LOW - Using proven technologies and existing infrastructure
- Business Risk: LOW - Optional feature that doesn't affect core functionality
- Timeline Risk: MEDIUM - Dependent on third-party charting library updates

Resources Required:
- 2 Frontend Developers (6 weeks)
- 1 Backend Developer (2 weeks)
- 1 QA Engineer (2 weeks)
- 1 UX Designer (1 week)

Expected Completion: 8 weeks from approval date
            """
        },
        {
            "filename": "security_patch.txt",
            "content": """
SECURITY CHANGE REQUEST - Critical Vulnerability Patch

Change Request Title: Apply Critical Security Patches for OpenSSL and Node.js
Priority: HIGH  
Category: Security

Security Impact:
- CVE-2023-XXXX: OpenSSL vulnerability (CVSS Score: 8.1 - HIGH)
- CVE-2023-YYYY: Node.js vulnerability (CVSS Score: 7.5 - HIGH)
- Potential for remote code execution and data breach
- Compliance requirement for SOC2 and PCI-DSS certifications

Affected Systems:
- All production web servers (12 instances)
- API gateway servers (4 instances)  
- Load balancers (2 instances)
- Development and staging environments

Technical Implementation:
1. Update OpenSSL to version 3.0.10 (from 3.0.8)
2. Update Node.js to version 18.17.1 (from 18.16.0)
3. Rebuild and redeploy affected Docker containers
4. Update base OS packages on all servers
5. Perform security scans to verify patch effectiveness

Testing Plan:
- Vulnerability scanning before and after patches
- Application functionality testing in staging
- Performance benchmarking to ensure no regression
- SSL certificate validation and cipher suite testing

Implementation Schedule:
- Non-production environments: This weekend (Saturday 2-6 AM)
- Production environment: Next Tuesday during maintenance window (2-4 AM)
- Total estimated downtime: 30 minutes per environment

Rollback Strategy:
- Maintain previous Docker image versions for immediate rollback
- Database backup before implementation
- Monitoring alerts configured for immediate issue detection
- Automated rollback triggers if error rates exceed 1%

Compliance Requirements:
- Document patch implementation for audit trail
- Update security baseline documentation
- Notify security team and compliance officer
- Update vulnerability management dashboard

Business Justification:
Immediate patching required to maintain security posture and compliance.
Failure to patch within 30 days may result in compliance violations and potential security breach.

Risk Assessment:
- Security Risk if NOT implemented: CRITICAL
- Implementation Risk: LOW (well-tested patches, established process)
- Business Impact: MINIMAL (during maintenance window)

Approval Required:
- Security Team Lead: APPROVED
- Infrastructure Manager: PENDING
- CISO: PENDING
            """
        }
    ]
    
    for sample in sample_crs:
        file_path = sample_dir / sample["filename"]
        if not file_path.exists():
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(sample["content"])
    
    print(f"✅ Created {len(sample_crs)} sample CR documents")


def display_next_steps():
    """Display next steps for user"""
    print("\n" + "=" * 60)
    print("✅ FluxADM Setup Complete!")
    print("=" * 60)
    print()
    print("📋 Next Steps:")
    print("1. Edit .env file and add your API keys:")
    print("   - OPENAI_API_KEY=your-openai-key")
    print("   - DATABASE_URL=your-database-url (optional, defaults to SQLite)")
    print()
    print("2. (Optional) Create and activate a virtual environment if desired:")
    if os.name == 'nt':
        print("   python -m venv venv && venv\\Scripts\\activate")
    else:
        print("   python3 -m venv venv && source venv/bin/activate")
    print()
    print("3. Start the development server:")
    print("   python app/main.py")
    print()
    print("4. Or run with Docker:")
    print("   docker-compose up --build")
    print()
    print("5. Access the application:")
    print("   - API: http://localhost:5000")
    print("   - Health: http://localhost:5000/health")
    print()
    print("📁 Sample CR documents created in data/sample_crs/")
    print("📚 Documentation available in docs/")
    print()
    print("🆘 Need help? Check the README.md or run: python -m pytest tests/")


def main():
    """Main setup function"""
    print_header()
    
    # Verify we're in the right directory
    if not Path("requirements.txt").exists():
        print("❌ Please run this script from the FluxADM project root directory")
        sys.exit(1)
    
    try:
        check_python_version()
        install_dependencies()
        create_env_file()
        create_sample_data()
        display_next_steps()
        
    except KeyboardInterrupt:
        print("\n❌ Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()