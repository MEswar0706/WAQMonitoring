from flask_sqlalchemy import SQLAlchemy

# Initialize SQLAlchemy
db = SQLAlchemy()

# Users Table
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    logged_in = db.Column(db.Boolean, default=False)
    city = db.Column(db.String(100), nullable=True)
    carbonemitted = db.Column(db.Float, default=0.0)
    username = db.Column(db.String(50), nullable=False)

    # Relationships
    carbon_tracking = db.relationship('UserCarbonTracking', backref='user', lazy=True)
    posts = db.relationship('Post', backref='user', lazy=True)
    leaderboard = db.relationship('Leaderboard', backref='user', lazy=True)

# User Carbon Tracking Table
class UserCarbonTracking(db.Model):
    __tablename__ = 'user_carbon_tracking'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    today_date = db.Column(db.Date, nullable=False)
    transportation = db.Column(db.Float, default=0.0)
    water = db.Column(db.Float, default=0.0)
    electricity = db.Column(db.Float, default=0.0)
    totalCarbonFootprint = db.Column(db.Float, default=0.0)

# Leaderboard Table
class Leaderboard(db.Model):
    __tablename__ = 'LeaderBoard'
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), primary_key=True, nullable=False)
    today_date = db.Column(db.Date, primary_key=True, nullable=False)
    totalCarbonFootprint = db.Column(db.Float, default=0.0)
    city = db.Column(db.String(100), nullable=True)
    username = db.Column(db.String(50), nullable=True)

# Posts Table
class Post(db.Model):
    __tablename__ = 'Posts'
    
    post_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    likes = db.Column(db.Integer, default=0)
    comments = db.Column(db.String(255), nullable=True)
    title = db.Column(db.String(100), nullable=True)

