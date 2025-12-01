#!/usr/bin/env python3
"""
Development server runner for PharmaBot
Runs the application in development mode with debug and reload enabled
"""
import os
import sys
import subprocess
from pathlib import Path


def check_virtual_environment():
    """Check if running in virtual environment"""
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    
    if not in_venv:
        print("⚠️  Not running in a virtual environment!")
        venv_path = Path(__file__).parent / 'venv'
        
        if venv_path.exists():
            print(f"✓ Virtual environment found at: {venv_path}")
            
            # Determine python executable in venv
            if os.name == 'nt':
                venv_python = venv_path / 'Scripts' / 'python.exe'
            else:
                venv_python = venv_path / 'bin' / 'python'
            
            if venv_python.exists():
                print("🔄 Restarting with virtual environment...\n")
                os.execv(str(venv_python), [str(venv_python)] + sys.argv)
        else:
            print("\n❌ No virtual environment found!")
            print("Creating virtual environment...")
            subprocess.check_call([sys.executable, '-m', 'venv', str(venv_path)])
            print(f"✓ Virtual environment created at: {venv_path}")
            
            if os.name == 'nt':
                venv_python = venv_path / 'Scripts' / 'python.exe'
            else:
                venv_python = venv_path / 'bin' / 'python'
            
            print("🔄 Restarting with virtual environment...\n")
            os.execv(str(venv_python), [str(venv_python)] + sys.argv)
    
    return True


def install_dependencies():
    """Install required packages"""
    base_dir = Path(__file__).parent
    requirements_file = base_dir / 'requirements.txt'
    
    if not requirements_file.exists():
        print("⚠️  requirements.txt not found")
        return
    
    print("📦 Checking dependencies...")
    
    # Install all requirements
    try:
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', '-q', '-r', str(requirements_file)
        ])
        print("✓ All dependencies installed")
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        sys.exit(1)


def load_environment():
    """Load environment variables"""
    env_file = Path(__file__).parent / '.env'
    
    if env_file.exists():
        try:
            from dotenv import load_dotenv
            load_dotenv()
            print("✓ Environment variables loaded from .env")
        except ImportError:
            print("⚠️  python-dotenv not installed, skipping .env file")
    else:
        print("ℹ️  No .env file found (using defaults)")
    
    # Set defaults for development
    if not os.environ.get('FLASK_ENV'):
        os.environ['FLASK_ENV'] = 'development'
    if not os.environ.get('FLASK_APP'):
        os.environ['FLASK_APP'] = 'app:create_app()'


def initialize_app():
    """Initialize Flask application with Flask-Migrate"""
    print("\n📦 Initializing application...")
    
    # Ensure required directories exist
    base_dir = Path(__file__).parent
    instance_dir = base_dir / 'instance'
    uploads_dir = base_dir / 'app' / 'static' / 'uploads'
    
    instance_dir.mkdir(exist_ok=True)
    uploads_dir.mkdir(parents=True, exist_ok=True)
    print(f"✓ Required directories created")
    
    from app import create_app
    
    app = create_app()
    print("✓ Application initialized with Flask-Migrate")
    
    return app


def run_development_server(app):
    """Run Flask development server with debug and reload"""
    port = int(os.environ.get('PORT', 7878))
    host = os.environ.get('HOST', '0.0.0.0')
    
    print("\n" + "="*60)
    print("🚀 Starting PharmaBot Development Server")
    print("="*60)
    print(f"Environment: {os.environ.get('FLASK_ENV', 'development')}")
    print(f"Debug: True")
    print(f"Auto-reload: True")
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Access URL: http://localhost:{port}")
    print("="*60 + "\n")
    
    try:
        app.run(
            host=host,
            port=port,
            debug=True,
            use_reloader=True
        )
    except KeyboardInterrupt:
        print("\n\n👋 Server stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Server error: {e}")
        sys.exit(1)


def main():
    """Main entry point"""
    print("\n🔧 PharmaBot Development Setup\n")
    
    try:
        check_virtual_environment()
        install_dependencies()
        load_environment()
        app = initialize_app()
        run_development_server(app)
    except KeyboardInterrupt:
        print("\n\n👋 Setup interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
