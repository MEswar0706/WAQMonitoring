# initialize_db.py
from app import app
from models import db

# Ensure the app context is available
with app.app_context():
    try:
        db.create_all()  # Create the tables
        print("Tables created successfully!")
    except Exception as e:
        print(f"Error while creating tables: {str(e)}")
