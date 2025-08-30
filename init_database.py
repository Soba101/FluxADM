#!/usr/bin/env python3
"""
Initialize FluxADM database with proper schema and default data
"""
import os
import sys
from flask import Flask

# Add app directory to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def create_app():
    """Create Flask app for database initialization"""
    app = Flask(__name__)
    
    # Configure database
    from config import get_settings
    settings = get_settings()
    
    app.config['SQLALCHEMY_DATABASE_URI'] = settings.DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
    return app

def init_database():
    """Initialize database with all tables and default data"""
    print("🚀 Initializing FluxADM Database")
    print("=" * 50)
    
    app = create_app()
    
    with app.app_context():
        # Import all models to ensure they're registered
        from app.models import db, User, ChangeRequest, AIAnalysisResult
        from app.models import ApprovalWorkflow, QualityIssue, PerformanceMetric
        
        # Initialize database
        db.init_app(app)
        
        print("📊 Creating database tables...")
        try:
            # Drop all tables (fresh start)
            db.drop_all()
            print("  ✅ Dropped existing tables")
            
            # Create all tables
            db.create_all()
            print("  ✅ Created new tables")
            
            # Create default admin user
            print("👤 Creating default admin user...")
            from werkzeug.security import generate_password_hash
            
            admin_user = User(
                email='admin@fluxadm.com',
                full_name='FluxADM Administrator',
                role='admin',
                department='IT',
                password_hash=generate_password_hash('admin123'),
                is_active=True
            )
            
            db.session.add(admin_user)
            db.session.commit()
            print("  ✅ Created admin user (admin@fluxadm.com / admin123)")
            
            # Create sample users
            print("👥 Creating sample users...")
            sample_users = [
                {
                    'email': 'manager@fluxadm.com',
                    'full_name': 'Change Manager',
                    'role': 'manager',
                    'department': 'IT Operations'
                },
                {
                    'email': 'analyst@fluxadm.com', 
                    'full_name': 'System Analyst',
                    'role': 'analyst',
                    'department': 'IT Development'
                },
                {
                    'email': 'user@fluxadm.com',
                    'full_name': 'End User',
                    'role': 'user',
                    'department': 'Business'
                }
            ]
            
            for user_data in sample_users:
                user = User(
                    email=user_data['email'],
                    full_name=user_data['full_name'],
                    role=user_data['role'],
                    department=user_data['department'],
                    password_hash=generate_password_hash('password123'),
                    is_active=True
                )
                db.session.add(user)
            
            db.session.commit()
            print(f"  ✅ Created {len(sample_users)} sample users")
            
            print("\n🎉 Database initialization complete!")
            print("\n📋 Login Credentials:")
            print("  Admin: admin@fluxadm.com / admin123")
            print("  Manager: manager@fluxadm.com / password123") 
            print("  Analyst: analyst@fluxadm.com / password123")
            print("  User: user@fluxadm.com / password123")
            
            return True
            
        except Exception as e:
            print(f"❌ Database initialization failed: {e}")
            return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)