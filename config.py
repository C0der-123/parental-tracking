import os

SQLALCHEMY_DATABASE_URI = 'sqlite:///database.db'
SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_secret_key'
SQLALCHEMY_TRACK_MODIFICATIONS = False