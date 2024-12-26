from flask import Flask, render_template, redirect, url_for, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity, set_access_cookies
from flask_bcrypt import Bcrypt
from flask_dance.contrib.google import make_google_blueprint, google
from models import db, User, Post, UserCarbonTracking, Leaderboard
from config import Config
import requests
from datetime import datetime
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from flask_jwt_extended import get_jwt_identity
from flask import g



app = Flask(__name__)
app.config.from_object(Config)
app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
app.config["JWT_COOKIE_CSRF_PROTECT"] = False
app.config["JWT_ACCESS_COOKIE_NAME"] = "access_token_cookie"

API_KEY = "5f6c9d7e7f16f04d6b55942614817b69"
YOUTUBE_API_KEY = 'AIzaSyAmXWhLn-6rBUjQzgpxo79onTS11iOZMDM'

def get_weather_videos(city):
    youtube_url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={city}+weather&key={YOUTUBE_API_KEY}&maxResults=3&type=video"
    response = requests.get(youtube_url)
    video_data = response.json()

    videos = []
    if "items" in video_data:
        for item in video_data["items"]:
            video = {
                "title": item["snippet"]["title"],
                "video_id": item["id"]["videoId"],
                "thumbnail": item["snippet"]["thumbnails"]["high"]["url"],
                "description": item["snippet"]["description"]
            }
            videos.append(video)
    
    return videos

# Function to fetch weather data from OpenWeatherMap API
def get_weather(city):
    weather_url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "q": city,
        "appid": API_KEY,
        "units": "metric"
    }
    response = requests.get(weather_url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print("Error fetching weather data:", response.json())  # Debugging output
        return {"error": response.json().get("message", f"HTTP {response.status_code} error")}
    


def get_aqi(lat, lon):
    """Fetch AQI data from OpenWeatherMap API."""
    aqi_url = "https://api.openweathermap.org/data/2.5/air_pollution"
    params = {
        "lat": lat,
        "lon": lon,
        "appid": API_KEY
    }
    response = requests.get(aqi_url, params=params)
    if response.status_code == 200:
        return response.json()
    else:
        print("Error fetching AQI data:", response.json())  # Debugging output
        return None

def get_aqi_description(aqi_level):
    """Map AQI level to a description."""
    if aqi_level == 1:
        return "Good", "green"
    elif aqi_level == 2:
        return "Satisfactory", "lightgreen"
    elif aqi_level == 3:
        return "Moderate", "yellow"
    elif aqi_level == 4:
        return "Poor", "orange"
    elif aqi_level == 5:
        return "Very Poor", "red"
    elif aqi_level == 6:
        return "Severe", "darkred"
    else:
        return "Unknown", "gray"
    
db.init_app(app)
bcrypt = Bcrypt(app)
jwt = JWTManager(app)



@app.before_request
def before_request():
    access_token = request.cookies.get('access_token_cookie')
    if access_token:
        g.headers = {'Authorization': f'Bearer {access_token}'}
    else:
        g.headers = {}

# Function to retrieve headers in routes
def get_headers():
    return getattr(g, 'headers', {})


# Google OAuth Setup
google_bp = make_google_blueprint(
    client_id=app.config['GOOGLE_OAUTH_CLIENT_ID'],
    client_secret=app.config['GOOGLE_OAUTH_CLIENT_SECRET'],
    redirect_to='google_login',
    scope=["profile", "email"]
)
app.register_blueprint(google_bp, url_prefix='/google')

# Home Route
@app.route('/', methods=["GET", "POST"])
def home():
    # Check if a city is passed in the form, otherwise set a default city
    city = None
    if request.method == 'POST':
        city = request.form['city']
    else:
        city = "New York"  # Set a default city if no city is provided

    # Get weather data for the city
    weather_data = get_weather(city)
    
    if "error" in weather_data:
        return render_template('weather_dashboard.html', weather_info={})

    # Extract latitude and longitude from weather data
    lat = weather_data["coord"]["lat"]
    lon = weather_data["coord"]["lon"]
    
    # Fetch AQI data
    aqi_data = get_aqi(lat, lon)
    if aqi_data and "list" in aqi_data:
        aqi_level = aqi_data["list"][0]["main"]["aqi"]
        aqi_description, aqi_color = get_aqi_description(aqi_level)
    else:
        aqi_level = None
        aqi_description, aqi_color = "Unavailable", "gray"
        
    # Extract all weather details
    weather_info = {
        "temperature": weather_data["main"]["temp"],
        "humidity": weather_data["main"]["humidity"],
        "wind_speed": weather_data["wind"]["speed"],
        "feels_like": weather_data["main"]["feels_like"],
        "visibility": weather_data.get("visibility", 0) / 1000 if "visibility" in weather_data else "N/A",
        "pressure": weather_data["main"]["pressure"],
        "sunrise": datetime.utcfromtimestamp(weather_data["sys"]["sunrise"]).strftime('%I:%M:%S %p'),
        "sunset": datetime.utcfromtimestamp(weather_data["sys"]["sunset"]).strftime('%I:%M:%S %p'),
        "aqi_level": aqi_level,  # AQI value fetched from the Air Pollution API
        "aqi_description": aqi_description,  # AQI category description
        "aqi_color": aqi_color
    }

    NEWS_API_KEY = "pub_605655cd986cb585931ba91afa9ded253026a"
    url = f"https://newsdata.io/api/1/news?apikey={NEWS_API_KEY}&country=in&language=en&q={city}"
    response = requests.get(url)
    news_data = response.json()
    articles = news_data.get("results", [])
    weather_articles = [
        article for article in articles
        if (
            (article.get('title') and 'weather' in article['title'].lower()) or
            (article.get('description') and 'weather' in article['description'].lower())
        )
    ]   
    weather_articles = weather_articles[:3]
    
    weather_videos = get_weather_videos(city)

    return render_template('weather_dashboard.html', weather_info=weather_info, city=city, articles=weather_articles, videos=weather_videos)

# User Registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Extract form data
        name = request.form['name']  # Store full name in the 'name' field
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        city = request.form['city']

        # Check if passwords match
        if password != confirm_password:
            return jsonify(message="Passwords do not match"), 400

        # Hash the password
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # Store the name in the 'username' column of the 'users' table
        new_user = User(username=name, email=email, password=hashed_password, city=city)
        
        # Add the new user to the session and commit
        db.session.add(new_user)
        db.session.commit()

        return redirect(url_for('login'))
    
    return render_template('register.html')


# Community route with optional authentication



# User Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Authenticate user
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            access_token = create_access_token(identity=str(user.id))
            response = redirect(url_for('home'))
            set_access_cookies(response, access_token)
            return response

        return render_template('login.html')

    return render_template('login.html')

@app.route('/ctlogin', methods=['GET', 'POST'])
def ctlogin():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Authenticate user
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            access_token = create_access_token(identity=str(user.id))
            response = redirect(url_for('carbon_tracking'))
            set_access_cookies(response, access_token)
            return response

        return render_template('ctlogin.html')

    return render_template('ctlogin.html')

@app.route('/clogin', methods=['GET', 'POST'])
def clogin():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        # Authenticate user
        user = User.query.filter_by(email=email).first()
        if user and bcrypt.check_password_hash(user.password, password):
            access_token = create_access_token(identity=str(user.id))
            response = redirect(url_for('community'))
            set_access_cookies(response, access_token)
            return response
        return render_template('clogin.html')

    return render_template('clogin.html')

@app.route('/community')
def community():
    posts = Post.query.all()
    return render_template('community.html', posts=posts)

# Route to like a post
@app.route('/like_post/<int:post_id>', methods=['POST','GET'])

def like_post(post_id):
    post = Post.query.get_or_404(post_id)
    post.likes += 1
    db.session.commit()
    return redirect(url_for('community'))

# Route to comment on a post
@app.route('/comment_post/<int:post_id>', methods=['GET', 'POST'])
def comment_post(post_id):
    if request.method == 'POST':
        comment = request.form['comment']
        post = Post.query.get_or_404(post_id)
        post.comments = f"{post.comments}\n{comment}" if post.comments else comment
        db.session.commit()
        return redirect(url_for('community'))

    return render_template('comment_post.html', post_id=post_id)


@app.route('/create_post', methods=['GET', 'POST'])
@jwt_required()
def create_post():
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        current_user_id = int(get_jwt_identity())
        new_post = Post(user_id=current_user_id, title=title, description=description)
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for('community'))
    
    return render_template('create_post.html')

# Google Login Callback
@app.route('/google/authorized')
def google_login():
    if not google.authorized:
        return redirect(url_for('google.login'))

    # Fetch user info from Google
    google_info = google.get('/plus/v1/people/me')
    user_info = google_info.json()

    # Handle user authentication or registration here...
    return jsonify(message="Google login successful", user_info=user_info)

@app.route('/track_carbon', methods=['POST'])
@jwt_required()

def track_carbon():
    current_user_id = int(get_jwt_identity())
    user = User.query.get(current_user_id)  # Fetch user details
    transportation_km = request.form['transportation_km']
    transportation_mode = request.form['transportation_mode']
    electricity_prev_month = request.form['electricity_prev_month']
    electricity_today = request.form['electricity_today']
    dry_waste = request.form['dry_waste']
    wet_waste = request.form['wet_waste']

    # Calculate carbon footprint for transportation
    transport_modes = {
        'car': 0.120,  # kg CO2 per km
        'bus': 0.060,
        'bike': 0.020
    }
    
    carbon_transport = float(transportation_km) * transport_modes.get(transportation_mode.lower(), 0.120)

    # Calculate carbon footprint for electricity usage
    carbon_electricity = (float(electricity_today) + float(electricity_prev_month)) * 0.8  # Example conversion factor

    # Calculate carbon footprint for waste
    carbon_waste = (float(dry_waste) + float(wet_waste)) * 0.1  # Example conversion factor

    # Total carbon footprint
    total_carbon_footprint = carbon_transport + carbon_electricity + carbon_waste

    # Store the data in the UserCarbonTracking model
    today_date = datetime.utcnow().date()
    user_carbon_tracking = UserCarbonTracking(
        user_id=current_user_id,
        today_date=today_date,
        transportation=carbon_transport,
        electricity=carbon_electricity,
        water=0.0,  # Adjust this if needed
        totalCarbonFootprint=total_carbon_footprint
    )

    db.session.add(user_carbon_tracking)

    # Update the Leaderboard model
    leaderboard_entry = Leaderboard.query.filter_by(user_id=current_user_id , today_date=today_date).first()
    if not leaderboard_entry:
        leaderboard_entry = Leaderboard(
            user_id=current_user_id,
            today_date=today_date,
            totalCarbonFootprint=total_carbon_footprint,
            city=user.city,
            username=user.username
        )
        db.session.add(leaderboard_entry)
    else:
        leaderboard_entry.totalCarbonFootprint = total_carbon_footprint

    db.session.commit()

    return redirect(url_for('carbon_tracking'))

# Ensure this route is added in your app initialization
@app.route('/carbon_tracking')
@jwt_required()

def carbon_tracking():
    current_user_id = int(get_jwt_identity())
    user = User.query.get(current_user_id)

    # Retrieve historical data for the user
    carbon_data = UserCarbonTracking.query.filter_by(user_id=current_user_id).all()
    dates = [data.today_date.strftime('%Y-%m-%d') for data in carbon_data]
    transportation = [data.transportation for data in carbon_data]
    electricity = [data.electricity for data in carbon_data]
    water = [data.water for data in carbon_data]

    carbon_data_dict = {
        "dates": dates,
        "transportation": transportation,
        "electricity": electricity,
        "water": water
    }

    # Assuming a utility function exists to calculate totals
    carbon_footprint = calculate_total_carbon_footprint(current_user_id)

    # Retrieve leaderboard data
    leaderboard_data = Leaderboard.query.order_by(Leaderboard.totalCarbonFootprint.asc()).all()

    return render_template('carbon_tracking.html', carbon_data=carbon_data_dict, carbon_footprint=carbon_footprint, leaderboard_data=leaderboard_data)

def calculate_total_carbon_footprint(user_id):
    # Aggregate carbon footprint data for the user
    total_transport = db.session.query(db.func.sum(UserCarbonTracking.transportation)).filter_by(user_id=user_id).scalar() or 0.0
    total_electricity = db.session.query(db.func.sum(UserCarbonTracking.electricity)).filter_by(user_id=user_id).scalar() or 0.0
    total_water = db.session.query(db.func.sum(UserCarbonTracking.water)).filter_by(user_id=user_id).scalar() or 0.0

    total_carbon_footprint = total_transport + total_electricity + total_water
    return {
        "transportation": total_transport,
        "electricity": total_electricity,
        "water": total_water,
        "total": total_carbon_footprint
    }




if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Ensure tables are created
    app.run(debug=True)