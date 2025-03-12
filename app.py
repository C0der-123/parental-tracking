# app.py (Main Flask Application)
from flask_migrate import Migrate
from flask import Flask, render_template, request, redirect, url_for, session,jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from database import db
from config import SQLALCHEMY_DATABASE_URI, SECRET_KEY
from geopy.distance import geodesic  # To calculate distance
from datetime import datetime, timedelta, timezone
from math import radians, cos, sin, sqrt, atan2

utc_plus_7 = timezone(timedelta(hours=7))

# Get the current time in UTC+7
time_in_utc_plus_7 = datetime.now(utc_plus_7)
# Initialize Flask app
app = Flask(__name__)
migrate = Migrate(app, db)
# Set configurations
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = SECRET_KEY  # Ensure SECRET_KEY is set!

# Initialize database with app
db.init_app(app)

# Import models AFTER initializing db to avoid circular imports
from models import User,Alert

# Create database tables if they do not exist
with app.app_context():
    db.create_all()
#calculate distance 
def calculate_distance(lat1, lon1, lat2, lon2):
    # Haversine formula to calculate distance between two GPS coordinates
    R = 6371000  # Radius of Earth in meters
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c
@app.route('/')
def index():
    return render_template('index.html')

# Registration Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        role = request.form['role']
        hashed_password = generate_password_hash(password)

        # Check if username already exists
        if User.query.filter_by(username=username).first():
            return 'Username already exists!'

        # Create new user
        new_user = User(username=username, password=hashed_password, role=role)
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))

    return render_template('register.html')

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        # Check if user exists
        user = User.query.filter_by(username=username).first()

        # Validate password
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role'] = user.role
            return redirect(url_for('dashboard'))

        return 'Invalid credentials!'

    return render_template('login.html')

#dashboard route
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    if user.role == 'parent':
        children = user.children

        for child in children:
            if child.latitude and child.longitude and child.safe_latitude and child.safe_longitude:
                safe_zone_coords = (child.safe_latitude, child.safe_longitude)
                child_coords = (child.latitude, child.longitude)
                child.distance_from_safe_zone = geodesic(safe_zone_coords, child_coords).meters
            else:
                child.distance_from_safe_zone = None

        alerts = Alert.query.filter_by(parent_id=user.id).order_by(Alert.timestamp.desc()).limit(10).all()

        for alert in alerts:
            child = User.query.get(alert.child_id)
            alert.child_name = child.username if child else "Unknown Child"

        return render_template('dashboard.html', user=user, children=children, alerts=alerts)

    elif user.role == 'child':
        parent = user.parent
        child_data = {
            'latitude': user.latitude,
            'longitude': user.longitude,
            'safe_latitude': user.safe_latitude,
            'safe_longitude': user.safe_longitude,
            'safe_radius': user.safe_radius
        }
        return render_template('dashboard.html', user=user, parent=parent, child_data=child_data)

    return redirect(url_for('login'))

# Logout Route
@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('index'))

#Link child route
@app.route('/link-child', methods=['GET', 'POST'])
def link_child():
    if 'user_id' not in session or session['role'] != 'parent':
        return redirect(url_for('login'))

    parent = User.query.get(session['user_id'])

    if request.method == 'POST':
        child_username = request.form['child_username']
        child = User.query.filter_by(username=child_username, role='child').first()

        if not child:
            return 'Child not found!'

        # Link child if not already linked
        if child.parent_id != parent.id:
            child.parent_id = parent.id
            db.session.commit()

        return redirect(url_for('dashboard'))

    return render_template('link-child.html')

#Unlink child
@app.route('/unlink_child', methods=['POST'])
def unlink_child():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    parent = User.query.get(session['user_id'])
    if parent.role != 'parent':
        return "Unauthorized", 403

    child_id = request.form.get('child_id')
    child = User.query.get(child_id)

    if child and child.parent_id == parent.id:
        child.parent_id = None
        db.session.commit()

    return redirect(url_for('dashboard'))


#update location
@app.route('/update-location', methods=['POST'])
def update_location():
    if 'user_id' not in session or session['role'] != 'child':
        return redirect(url_for('login'))

    child = User.query.get(session['user_id'])
    data = request.get_json()

    latitude = float(data['latitude'])
    longitude = float(data['longitude'])

    print(f"🔍 Updating location for child {child.username}: {latitude}, {longitude}")

    child.latitude = latitude
    child.longitude = longitude

    # Check against the safe zone
    if child.safe_latitude and child.safe_longitude and child.safe_radius:
        safe_zone_center = (child.safe_latitude, child.safe_longitude)
        current_location = (latitude, longitude)
        distance = geodesic(safe_zone_center, current_location).meters

        print(f"📏 Calculated distance: {distance} meters (Safe Zone: {child.safe_radius} meters)")

        # If outside safe zone, create an alert
        if distance > child.safe_radius:
            print(f"🚨 Child {child.username} is OUTSIDE the safe zone!")
            parent = User.query.get(child.parent_id)
            if parent:
                new_alert = Alert(child_id=child.id, parent_id=parent.id, distance=distance, timestamp=(datetime.now(utc_plus_7)))
                db.session.add(new_alert)
                print(f"✅ Alert created for parent {parent.username}.")

    db.session.commit()
    return '', 204


#set distance
@app.route('/set-distance-limit', methods=['POST'])
def set_distance_limit():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if user.role != 'parent':
        return "Unauthorized", 403

    distance_limit = float(request.form.get('distance_limit'))
    user.distance_limit = distance_limit
    db.session.commit()

    return redirect(url_for('dashboard'))

#weekly report
@app.route('/weekly-report/<int:child_id>')
def child_weekly_report(child_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])

    # Ensure only parents can view the report
    if user.role != 'parent':
        return "Unauthorized", 403

    # Validate that the child is linked to the parent
    child = User.query.get(child_id)
    if not child or child.parent_id != user.id:
        return "Invalid child or not linked.", 400

    # Get alerts from the past 7 days
    week_ago = datetime.now(utc_plus_7) - timedelta(days=7)
    alert_count = Alert.query.filter(
        Alert.child_id == child_id,
        Alert.timestamp >= week_ago
    ).count()

    return render_template('child_weekly_report.html', child=child, alert_count=alert_count)

# set safe zone
@app.route('/set_safe_zone', methods=['POST'])
def set_safe_zone():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = User.query.get(session['user_id'])
    if not user or user.role != 'parent':
        return "Unauthorized", 403

    try:
        print(request.form)  # ✅ Debugging output for visibility
        child_id = int(request.form['child_id'])
        latitude = float(request.form['latitude'])
        longitude = float(request.form['longitude'])
        radius = float(request.form['radius'])

        # ✅ Ensure coordinates are valid
        if not (-90 <= latitude <= 90) or not (-180 <= longitude <= 180):
            return "Invalid latitude or longitude.", 400

        if radius <= 0:
            return "Radius must be greater than 0.", 400

    except (KeyError, ValueError) as e:
        return f"Invalid input: {e}", 400

    # ✅ Ensure child exists and is linked to the parent
    child = User.query.get(child_id)
    if not child or child.parent_id != user.id:
        return "Invalid child or not linked.", 400

    # ✅ Update child's safe zone
    child.safe_latitude = latitude
    child.safe_longitude = longitude
    child.safe_radius = radius

    db.session.commit()
    return redirect(url_for('dashboard'))
#get alerts
@app.route('/get_alerts')
def get_alerts():
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized'}), 401

    user = User.query.get(session['user_id'])

    if user and user.role == 'parent':
        alerts = Alert.query.filter_by(parent_id=user.id).order_by(Alert.timestamp.desc()).limit(10).all()
        alert_data = [
            {
                'child_name': User.query.get(alert.child_id).username if alert.child_id else "Unknown",
                'distance': round(alert.distance, 2),
                'timestamp': alert.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            }
            for alert in alerts
        ]
        return jsonify({'alerts': alert_data})

    return jsonify({'error': 'Forbidden'}), 403


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
