from database import db
import datetime
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(10), nullable=False)  # 'parent' or 'child'
    parent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)

    # Location Data (for children)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    # Distance Limit (for parents)
    distance_limit = db.Column(db.Float, nullable=True, default=1.0)  # Default: 1km

    parent = db.relationship('User', remote_side=[id], backref='children')
    # Safe Zone (Parent sets for their child)
    safe_latitude = db.Column(db.Float, nullable=True)
    safe_longitude = db.Column(db.Float, nullable=True)
    safe_radius = db.Column(db.Float, nullable=True)  # in meters
    distance_from_safe_zone = db.Column(db.Float, nullable=True)

    
class Alert(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    child_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.timezone.utc)
    distance = db.Column(db.Float, nullable=False)
