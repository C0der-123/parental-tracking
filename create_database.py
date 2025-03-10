from app import app, db

# Push the app context
with app.app_context():
    db.create_all()
    print("Database recreated successfully!")