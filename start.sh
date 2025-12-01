#!/bin/bash

# MediTrack Production Start Script
# This script starts the application using Gunicorn for production deployment

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}MediTrack Production Startup${NC}"
echo -e "${GREEN}================================${NC}"
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Upgrade pip
echo -e "${YELLOW}Upgrading pip...${NC}"
pip install --upgrade pip -q
echo -e "${GREEN}✓ Pip upgraded${NC}"

# Install/update dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install -r requirements.txt -q
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Install Gunicorn if not present
if ! pip show gunicorn > /dev/null 2>&1; then
    echo -e "${YELLOW}Installing Gunicorn...${NC}"
    pip install gunicorn -q
    echo -e "${GREEN}✓ Gunicorn installed${NC}"
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠ .env file not found. Creating from .env.example...${NC}"
    cp .env.example .env
    echo -e "${RED}⚠ Please edit .env and add your GEMINI_API_KEY${NC}"
fi

# Create necessary directories
echo -e "${YELLOW}Creating directories...${NC}"
mkdir -p instance
mkdir -p app/static/uploads/prescriptions
mkdir -p logs
echo -e "${GREEN}✓ Directories created${NC}"

# Initialize database
echo -e "${YELLOW}Initializing database...${NC}"
python3 << EOF
from app import create_app
app = create_app()
with app.app_context():
    from app.models import db
    db.create_all()
    print('Database initialized')
EOF
echo -e "${GREEN}✓ Database initialized${NC}"

# Configuration
HOST="0.0.0.0"
PORT="7878"
WORKERS=4
THREADS=2
TIMEOUT=120

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Starting MediTrack Server${NC}"
echo -e "${GREEN}================================${NC}"
echo -e "Host: ${YELLOW}${HOST}${NC}"
echo -e "Port: ${YELLOW}${PORT}${NC}"
echo -e "Workers: ${YELLOW}${WORKERS}${NC}"
echo -e "Threads per worker: ${YELLOW}${THREADS}${NC}"
echo -e "Access URL: ${YELLOW}http://localhost:${PORT}${NC}"
echo -e "${GREEN}================================${NC}"
echo ""

# Start Gunicorn
exec gunicorn \
    --bind ${HOST}:${PORT} \
    --workers ${WORKERS} \
    --threads ${THREADS} \
    --timeout ${TIMEOUT} \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log \
    --log-level info \
    --preload \
    'app:create_app()'
