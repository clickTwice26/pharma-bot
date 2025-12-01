# MediTrack Deployment Guide

## Quick Start (Development)

```bash
# Simple development server
python3 run.py
```

## Production Deployment

### 1. Using the Start Script

```bash
# Make script executable
chmod +x start.sh

# Run the application
./start.sh
```

This will:
- Create/activate virtual environment
- Install all dependencies including Gunicorn
- Initialize database
- Start Gunicorn on port 7878 with 4 workers

### 2. Setup Nginx (Recommended for Production)

```bash
# Install Nginx
sudo apt update
sudo apt install nginx

# Copy nginx configuration
sudo cp nginx.conf /etc/nginx/sites-available/meditrack

# Edit the configuration
sudo nano /etc/nginx/sites-available/meditrack
# Change 'your-domain.com' to your actual domain or IP

# Enable the site
sudo ln -s /etc/nginx/sites-available/meditrack /etc/nginx/sites-enabled/

# Remove default site (optional)
sudo rm /etc/nginx/sites-enabled/default

# Test nginx configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

### 3. Setup Systemd Service (Auto-start on Boot)

```bash
# Copy service file
sudo cp meditrack.service /etc/systemd/system/

# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable meditrack

# Start the service
sudo systemctl start meditrack

# Check status
sudo systemctl status meditrack

# View logs
sudo journalctl -u meditrack -f
```

### 4. Firewall Configuration

```bash
# Allow HTTP traffic
sudo ufw allow 80/tcp

# Allow direct access to app (optional, for testing)
sudo ufw allow 7878/tcp

# Allow SSH (important!)
sudo ufw allow 22/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

## Service Management Commands

```bash
# Start service
sudo systemctl start meditrack

# Stop service
sudo systemctl stop meditrack

# Restart service
sudo systemctl restart meditrack

# View status
sudo systemctl status meditrack

# View logs
sudo journalctl -u meditrack -n 100

# Follow logs in real-time
sudo journalctl -u meditrack -f
```

## Nginx Commands

```bash
# Test configuration
sudo nginx -t

# Reload (without downtime)
sudo systemctl reload nginx

# Restart
sudo systemctl restart nginx

# View logs
sudo tail -f /var/log/nginx/meditrack_access.log
sudo tail -f /var/log/nginx/meditrack_error.log
```

## Application Logs

```bash
# Application logs location
cd /home/raju/dld_project_backend/logs

# View access logs
tail -f access.log

# View error logs
tail -f error.log
```

## Troubleshooting

### Check if application is running
```bash
sudo systemctl status meditrack
curl http://localhost:7878
```

### Check if Nginx is working
```bash
sudo systemctl status nginx
curl http://localhost
```

### Port already in use
```bash
# Find process using port 7878
sudo lsof -i :7878

# Kill the process (replace PID)
sudo kill -9 <PID>
```

### Database issues
```bash
# Recreate database
cd /home/raju/dld_project_backend
rm -rf instance/app.db
python3 -c "from app import create_app; app = create_app(); app.app_context().push(); from app.models import db; db.create_all()"
```

### Permission issues
```bash
# Fix ownership
sudo chown -R raju:www-data /home/raju/dld_project_backend
sudo chmod -R 755 /home/raju/dld_project_backend

# Fix log directory
sudo chown -R raju:www-data /home/raju/dld_project_backend/logs
sudo chmod -R 755 /home/raju/dld_project_backend/logs
```

## Performance Tuning

### Adjust Gunicorn workers
Edit `start.sh` or `meditrack.service`:
```bash
# Formula: (2 x CPU cores) + 1
# For 2 CPU cores: --workers 5
# For 4 CPU cores: --workers 9
```

### Increase upload size
Edit `nginx.conf`:
```nginx
client_max_body_size 50M;  # Increase to 50MB
```

## Security Recommendations

1. **Use HTTPS**: Add SSL certificate with Let's Encrypt
2. **Firewall**: Only expose necessary ports
3. **Environment Variables**: Keep .env file secure
4. **Regular Updates**: Update dependencies regularly
5. **Backup Database**: Regular backups of instance/app.db

## Monitoring

### Check application health
```bash
curl http://localhost:7878/
```

### Monitor system resources
```bash
# CPU and memory usage
htop

# Disk usage
df -h

# Network connections
sudo netstat -tlnp | grep 7878
```

## Updating the Application

```bash
# Pull latest changes
cd /home/raju/dld_project_backend
git pull

# Activate virtual environment
source venv/bin/activate

# Update dependencies
pip install -r requirements.txt

# Restart service
sudo systemctl restart meditrack

# Or if using start script
./start.sh
```

## Access URLs

- **Direct Access**: http://your-server-ip:7878
- **Through Nginx**: http://your-domain.com
- **API Endpoints**: http://your-domain.com/api/*

## Environment Variables

Required in `.env` file:
```bash
SECRET_KEY=your-secret-key-here
GEMINI_API_KEY=your-gemini-api-key
DATABASE_URL=sqlite:///instance/app.db
FLASK_ENV=production
PORT=7878
```

## Need Help?

Check logs first:
```bash
# Application logs
tail -f logs/error.log

# Systemd logs
sudo journalctl -u meditrack -n 50

# Nginx logs
sudo tail -f /var/log/nginx/meditrack_error.log
```
