#!/usr/bin/env python3
"""
FluxADM Startup Script
Launches both Flask API and Streamlit dashboard
"""
import os
import sys
import subprocess
import signal
import time
import threading
from pathlib import Path


class FluxADMLauncher:
    """Launch and manage FluxADM services"""
    
    def __init__(self):
        self.processes = {}
        self.running = True
        
        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
        self.running = False
        self.shutdown_services()
        sys.exit(0)
    
    def check_environment(self):
        """Check if environment is properly set up"""
        print("🔍 Checking environment...")
        
        # Check if we're in the right directory
        if not Path("requirements.txt").exists():
            print("❌ Please run this script from the FluxADM project root directory")
            return False
        
        # Check if we're in a virtual environment (venv or conda)
        if not (hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix) or os.environ.get('CONDA_DEFAULT_ENV')):
            print("❌ Virtual environment not detected. Please activate your environment first")
            return False
        
        # Check if .env file exists
        env_file = Path(".env")
        if not env_file.exists():
            print("⚠️  .env file not found. Using default configuration.")
            print("   For full functionality, please create .env and add your OpenAI API key")
        
        print("✅ Environment check passed")
        return True
    
    def initialize_database(self):
        """Initialize database with default data"""
        print("🗄️  Initializing database...")
        
        try:
            # Import after setting up the path
            sys.path.append('app')
            
            from app.main import create_app
            from app.models import db, User
            from werkzeug.security import generate_password_hash
            
            app = create_app()
            
            with app.app_context():
                # Create all tables
                db.create_all()
                
                # Create default admin user if doesn't exist
                admin = User.query.filter_by(email='admin@fluxadm.com').first()
                if not admin:
                    admin = User(
                        email='admin@fluxadm.com',
                        full_name='FluxADM Administrator',
                        role='admin',
                        department='IT',
                        password_hash=generate_password_hash('admin123'),
                        is_active=True
                    )
                    db.session.add(admin)
                    db.session.commit()
                    print("✅ Created default admin user (admin@fluxadm.com / admin123)")
                else:
                    print("✅ Database already initialized")
                    
        except Exception as e:
            print(f"⚠️  Database initialization failed: {e}")
            print("   The application will still start, but you may need to set up the database manually")
    
    def start_flask_api(self):
        """Start Flask API server"""
        print("🚀 Starting Flask API server...")
        
        try:
            # Use the virtual environment Python
            python_executable = self.get_venv_python()
            
            env = os.environ.copy()
            env['PYTHONPATH'] = os.path.abspath('.')
            
            process = subprocess.Popen(
                [str(python_executable), '-m', 'app.main'],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            self.processes['flask'] = process
            
            # Monitor Flask startup in a separate thread
            threading.Thread(target=self.monitor_process, args=('Flask API', process)).start()
            
            # Wait a moment for Flask to start
            time.sleep(3)
            print("✅ Flask API server started on http://localhost:5000")
            
        except Exception as e:
            print(f"❌ Failed to start Flask API: {e}")
    
    def start_streamlit_dashboard(self):
        """Start Streamlit dashboard"""
        print("🎨 Starting Streamlit dashboard...")
        
        try:
            python_executable = self.get_venv_python()
            
            env = os.environ.copy()
            env['PYTHONPATH'] = os.path.abspath('.')
            
            process = subprocess.Popen(
                [str(python_executable), '-m', 'streamlit', 'run', 'streamlit_app.py', 
                 '--server.port', '8501', '--server.headless', 'true'],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            self.processes['streamlit'] = process
            
            # Monitor Streamlit startup in a separate thread
            threading.Thread(target=self.monitor_process, args=('Streamlit Dashboard', process)).start()
            
            # Wait a moment for Streamlit to start
            time.sleep(5)
            print("✅ Streamlit dashboard started on http://localhost:8501")
            
        except Exception as e:
            print(f"❌ Failed to start Streamlit dashboard: {e}")
    
    def monitor_process(self, name, process):
        """Monitor a process and log its output"""
        try:
            for line in iter(process.stdout.readline, ''):
                if line.strip():
                    print(f"[{name}] {line.strip()}")
                if not self.running:
                    break
        except Exception as e:
            if self.running:  # Only log if we're still supposed to be running
                print(f"[{name}] Process monitoring error: {e}")
    
    def get_venv_python(self):
        """Get path to virtual environment Python executable"""
        # Use current Python executable (works for both venv and conda)
        return sys.executable
    
    def wait_for_services(self):
        """Wait for services to be ready"""
        print("⏳ Waiting for services to be ready...")
        
        # Wait a bit longer for everything to fully start
        time.sleep(8)
        
        print("\n" + "="*60)
        print("🎉 FluxADM is now running!")
        print("="*60)
        print()
        print("📡 Services:")
        print("   • Flask API:        http://localhost:5000")
        print("   • API Documentation: http://localhost:5000/api/v1/doc/")
        print("   • Streamlit Dashboard: http://localhost:8501")
        print()
        print("🔐 Default Login:")
        print("   • Email:    admin@fluxadm.com")
        print("   • Password: admin123")
        print()
        print("📁 Sample Documents: data/sample_crs/")
        print("📚 Documentation:    docs/")
        print()
        print("💡 Tips:")
        print("   • Add your OpenAI API key to .env for full AI functionality")
        print("   • Use Ctrl+C to stop all services")
        print("   • Check logs above for any startup issues")
        print()
        print("="*60)
    
    def monitor_services(self):
        """Monitor running services"""
        while self.running:
            try:
                # Check if processes are still running
                for name, process in list(self.processes.items()):
                    if process.poll() is not None:  # Process has terminated
                        print(f"⚠️  {name} process has stopped")
                        if self.running:  # Only restart if we're supposed to be running
                            print(f"🔄 Restarting {name}...")
                            if name == 'flask':
                                self.start_flask_api()
                            elif name == 'streamlit':
                                self.start_streamlit_dashboard()
                
                time.sleep(5)  # Check every 5 seconds
                
            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"Service monitoring error: {e}")
                time.sleep(10)
    
    def shutdown_services(self):
        """Shutdown all services gracefully"""
        print("🔄 Shutting down services...")
        
        for name, process in self.processes.items():
            if process.poll() is None:  # Process is still running
                print(f"   Stopping {name}...")
                
                try:
                    # Try graceful shutdown first
                    process.terminate()
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if graceful shutdown fails
                    print(f"   Force killing {name}...")
                    process.kill()
                    process.wait()
                except Exception as e:
                    print(f"   Error stopping {name}: {e}")
        
        print("✅ All services stopped")
    
    def run(self):
        """Main run method"""
        print("🚀 Starting FluxADM...")
        print("="*50)
        
        # Check environment
        if not self.check_environment():
            return 1
        
        # Initialize database
        self.initialize_database()
        
        # Start services
        self.start_flask_api()
        self.start_streamlit_dashboard()
        
        # Wait for services and display info
        self.wait_for_services()
        
        try:
            # Monitor services
            self.monitor_services()
        except KeyboardInterrupt:
            pass
        finally:
            self.shutdown_services()
        
        return 0


def main():
    """Main function"""
    launcher = FluxADMLauncher()
    return launcher.run()


if __name__ == "__main__":
    sys.exit(main())