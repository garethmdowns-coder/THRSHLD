from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, session
from flask_login import LoginManager, login_required, current_user
from flask_migrate import Migrate
from flask_mail import Mail
from datetime import datetime, date, timedelta
import os
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create Flask app
app = Flask(__name__)

# Configuration
app.secret_key = os.environ.get("SESSION_SECRET")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Session configuration
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=31)

# Mail configuration
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@thrshld.app')

# Initialize extensions
mail = Mail(app)
from models import db, User
from utils import get_user_stats
db.init_app(app)
migrate = Migrate(app, db)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access THRSHLD.'
login_manager.session_protection = 'strong'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Register blueprints
from blueprints.auth import auth_bp
from blueprints.api import api_bp
from blueprints.strava import strava_bp
from blueprints.password_reset import password_reset_bp

app.register_blueprint(auth_bp)
app.register_blueprint(api_bp)
app.register_blueprint(strava_bp)
app.register_blueprint(password_reset_bp)

# Create database tables
with app.app_context():
    db.create_all()

# Main routes
@app.route("/")
def index():
    logging.debug(f"Index route accessed. User authenticated: {current_user.is_authenticated}")
    
    if current_user.is_authenticated:
        logging.debug(f"Authenticated user: {current_user.email}")
        # Check if user has completed profile setup
        profile = current_user.profile
        logging.debug(f"User profile exists: {profile is not None}")
        
        if not profile or not profile.name:
            # Show profile setup directly for new users
            logging.debug("Index: User needs profile setup, showing profile setup page")
            return render_template("profile_setup.html")
        
        # Get user data from database for returning users
        logging.debug(f"Loading main app for user: {current_user.email}")
        try:
            # Simplified user data loading to avoid errors
            user_data = {
                'profile': {'name': profile.name, 'age': profile.age, 'gender': profile.gender},
                'goals': {},
                'stats': get_user_stats(current_user.id)
            }
            logging.debug(f"User data prepared: {user_data}")
            logging.debug("Rendering index.html template")
            return render_template("index.html", user_data=user_data)
        except Exception as e:
            logging.error(f"Error in index route: {e}")
            import traceback
            logging.error(f"Full traceback: {traceback.format_exc()}")
            return f"Error loading app: {str(e)}", 500
    else:
        logging.debug("User not authenticated, showing auth page")
        return render_template("auth.html")

@app.route("/profile-setup")
@login_required
def profile_setup():
    # Show profile setup page for new users
    logging.debug(f"Profile setup accessed by user: {current_user.email if current_user.is_authenticated else 'Anonymous'}")
    
    # Check if user already has a complete profile
    if current_user.profile and current_user.profile.name:
        logging.debug("User already has profile, redirecting to main app")
        return redirect("/")
    return render_template("profile_setup.html")

@app.route("/goals-setup")
@login_required  
def goals_setup():
    return render_template("goals_setup.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)