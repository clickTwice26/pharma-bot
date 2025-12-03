"""
Main Routes for Web Interface
Handles user-facing pages
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from functools import wraps
from app.models import db
from app.models.user import User
from app.models.prescription import Prescription
from app.models.medicine import Medicine
from app.models.schedule import Schedule
from app.models.iot_device import IoTDevice
from datetime import datetime, timedelta
from app.utils.timezone import now as tz_now, today_start as tz_today_start

main_bp = Blueprint('main', __name__)


def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login to access this page.', 'error')
            return redirect(url_for('main.login'))
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    """Helper to get current logged-in user"""
    if 'user_id' in session:
        return User.query.get(session['user_id'])
    return None


@main_bp.route('/')
def index():
    """Dashboard/Home page"""
    if 'user_id' not in session:
        return redirect(url_for('main.login'))
    
    current_user = get_current_user()
    
    # Get today's schedules
    today_start = tz_today_start()
    today_end = today_start + timedelta(days=1)
    
    today_schedules = Schedule.query.filter(
        Schedule.user_id == current_user.id,
        Schedule.scheduled_time >= today_start,
        Schedule.scheduled_time < today_end
    ).order_by(Schedule.scheduled_time).all()
    
    # Get user's prescriptions
    prescriptions = Prescription.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).order_by(Prescription.created_at.desc()).limit(5).all()
    
    # Get user's devices
    devices = IoTDevice.query.filter_by(
        user_id=current_user.id,
        is_active=True
    ).all()
    
    # Calculate stats
    total_medicines = Medicine.query.join(Prescription).filter(
        Prescription.user_id == current_user.id,
        Medicine.is_active == True
    ).count()
    
    taken_today = Schedule.query.filter(
        Schedule.user_id == current_user.id,
        Schedule.scheduled_time >= today_start,
        Schedule.scheduled_time < today_end,
        Schedule.taken == True
    ).count()
    
    return render_template(
        'dashboard.html',
        current_user=current_user,
        today_schedules=today_schedules,
        prescriptions=prescriptions,
        devices=devices,
        total_medicines=total_medicines,
        taken_today=taken_today,
        total_today=len(today_schedules)
    )


@main_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if 'user_id' in session:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        
        if not username:
            flash('Username is required.', 'error')
            return render_template('register.html')
        
        if len(username) < 3:
            flash('Username must be at least 3 characters.', 'error')
            return render_template('register.html')
        
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists. Please choose another.', 'error')
            return render_template('register.html')
        
        user = User(username=username)
        db.session.add(user)
        db.session.commit()
        
        session['user_id'] = user.id
        session['username'] = user.username
        flash(f'Welcome, {username}! Your account has been created.', 'success')
        return redirect(url_for('main.index'))
    
    return render_template('register.html')


@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if 'user_id' in session:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        
        if not username:
            flash('Username is required.', 'error')
            return render_template('login.html')
        
        user = User.query.filter_by(username=username).first()
        
        if user:
            session['user_id'] = user.id
            session['username'] = user.username
            flash(f'Welcome back, {username}!', 'success')
            return redirect(url_for('main.index'))
        else:
            flash('Username not found. Please register first.', 'error')
            return render_template('login.html')
    
    return render_template('login.html')


@main_bp.route('/logout')
def logout():
    """User logout"""
    username = session.get('username', 'User')
    session.clear()
    flash(f'Goodbye, {username}!', 'success')
    return redirect(url_for('main.login'))


@main_bp.route('/prescriptions')
@login_required
def prescriptions():
    """View all prescriptions"""
    current_user = get_current_user()
    prescriptions = Prescription.query.filter_by(
        user_id=current_user.id
    ).order_by(Prescription.created_at.desc()).all()
    
    return render_template(
        'prescriptions.html',
        current_user=current_user,
        prescriptions=prescriptions
    )


@main_bp.route('/prescription/<int:prescription_id>')
@login_required
def prescription_detail(prescription_id):
    """View prescription details"""
    current_user = get_current_user()
    prescription = Prescription.query.filter_by(
        id=prescription_id,
        user_id=current_user.id
    ).first_or_404()
    
    medicines = Medicine.query.filter_by(
        prescription_id=prescription.id
    ).all()
    
    return render_template(
        'prescription_detail.html',
        current_user=current_user,
        prescription=prescription,
        medicines=medicines
    )


@main_bp.route('/schedules')
@login_required
def schedules():
    """View medication schedule"""
    current_user = get_current_user()
    
    # Get upcoming schedules
    now = tz_now()
    upcoming = Schedule.query.filter(
        Schedule.user_id == current_user.id,
        Schedule.scheduled_time >= now
    ).order_by(Schedule.scheduled_time).limit(20).all()
    
    return render_template(
        'schedules.html',
        current_user=current_user,
        schedules=upcoming,
        now=tz_now,
        timedelta=timedelta
    )


@main_bp.route('/devices')
@login_required
def devices():
    """Manage IoT devices"""
    current_user = get_current_user()
    devices_list = IoTDevice.query.filter_by(
        user_id=current_user.id
    ).all()
    
    # Update online status based on last heartbeat (5 minutes threshold)
    from datetime import datetime, timedelta
    now = tz_now()
    threshold = timedelta(minutes=5)
    
    for device in devices_list:
        if device.last_seen:
            time_diff = now - device.last_seen
            device.is_online = time_diff < threshold
        else:
            device.is_online = False
    
    db.session.commit()
    
    return render_template(
        'devices.html',
        current_user=current_user,
        devices=devices_list
    )


@main_bp.route('/profile')
@login_required
def profile():
    """User profile"""
    current_user = get_current_user()
    
    total_prescriptions = Prescription.query.filter_by(user_id=current_user.id).count()
    total_devices = IoTDevice.query.filter_by(user_id=current_user.id, is_active=True).count()
    
    return render_template(
        'profile.html',
        current_user=current_user,
        total_prescriptions=total_prescriptions,
        total_devices=total_devices
    )


@main_bp.route('/arduino')
@login_required
def arduino_setup():
    """Arduino setup page"""
    current_user = get_current_user()
    return render_template('arduino_setup.html', current_user=current_user)


@main_bp.route('/arduino/download')
@login_required
def arduino_download():
    """Download Arduino code with pre-configured username"""
    from flask import send_file, make_response
    import io
    
    current_user = get_current_user()
    
    # Read the Arduino code template
    arduino_file = 'arduino/medication_dispenser.ino'
    try:
        with open(arduino_file, 'r') as f:
            code = f.read()
        
        # Replace placeholder username with actual username
        code = code.replace('const char* USERNAME = "user1";', 
                          f'const char* USERNAME = "{current_user.username}";')
        
        # Create response
        output = io.BytesIO()
        output.write(code.encode('utf-8'))
        output.seek(0)
        
        response = make_response(output.getvalue())
        response.headers['Content-Type'] = 'text/plain'
        response.headers['Content-Disposition'] = f'attachment; filename=medication_dispenser_{current_user.username}.ino'
        
        return response
    except FileNotFoundError:
        flash('Arduino code file not found. Please contact administrator.', 'error')
        return redirect(url_for('main.arduino_setup'))


@main_bp.route('/arduino/setup-guide')
@login_required
def arduino_guide():
    """Show Arduino setup guide"""
    import re
    from markupsafe import Markup
    
    current_user = get_current_user()
    
    # Read README content
    readme_file = 'arduino/README.md'
    try:
        with open(readme_file, 'r') as f:
            markdown_text = f.read()
        
        # Simple markdown to HTML conversion
        html = markdown_text
        
        # Convert code blocks first
        html = re.sub(r'```(.*?)```', r'<pre><code>\1</code></pre>', html, flags=re.DOTALL)
        
        # Convert headers
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        
        # Convert bold and italic
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
        
        # Convert inline code
        html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)
        
        # Convert unordered lists
        html = re.sub(r'^\- (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        html = re.sub(r'(<li>.*?</li>\n?)+', r'<ul>\g<0></ul>', html, flags=re.DOTALL)
        
        # Convert ordered lists
        html = re.sub(r'^\d+\. (.+)$', r'<li>\1</li>', html, flags=re.MULTILINE)
        
        # Convert line breaks to paragraphs
        html = re.sub(r'\n\n', r'</p><p>', html)
        html = '<p>' + html + '</p>'
        
        # Clean up empty paragraphs
        html = re.sub(r'<p>\s*</p>', '', html)
        html = re.sub(r'<p>(<h[123]>)', r'\1', html)
        html = re.sub(r'(</h[123]>)</p>', r'\1', html)
        html = re.sub(r'<p>(<ul>)', r'\1', html)
        html = re.sub(r'(</ul>)</p>', r'\1', html)
        html = re.sub(r'<p>(<pre>)', r'\1', html)
        html = re.sub(r'(</pre>)</p>', r'\1', html)
        
        readme_content = Markup(html)
    except FileNotFoundError:
        readme_content = Markup("<p>Setup guide not available.</p>")
    
    return render_template('arduino_guide.html', 
                         current_user=current_user,
                         readme_content=readme_content)


@main_bp.route('/health')
def health_check():
    """Health check endpoint for monitoring"""
    from app.models import db
    try:
        # Test database connection
        db.session.execute(db.text('SELECT 1'))
        return {'status': 'healthy', 'database': 'connected'}, 200
    except Exception as e:
        return {'status': 'unhealthy', 'error': str(e)}, 500
