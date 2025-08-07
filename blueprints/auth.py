from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.security import check_password_hash
from datetime import timedelta
import logging
from models import db, User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        logging.debug("User already authenticated, redirecting to index")
        return redirect("/")
        
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        logging.debug(f"Login attempt for email: {email}")
        
        if not email or not password:
            flash("Email and password are required")
            return render_template("auth.html")
        
        user = User.query.filter_by(email=email).first()
        logging.debug(f"User found: {user is not None}")
        
        if user:
            password_valid = user.check_password(password)
            logging.debug(f"Password valid: {password_valid}")
            
            if password_valid:
                session.permanent = True
                login_user(user, remember=True)
                logging.debug(f"User logged in successfully: {user.email}")
                logging.debug(f"Session after login: {dict(session)}")
                
                # Check if user needs to complete profile setup
                has_profile = user.profile is not None
                has_name = has_profile and user.profile.name
                logging.debug(f"Has profile: {has_profile}, Has name: {has_name}")
                
                if not has_profile or not has_name:
                    logging.debug("User needs profile setup, rendering profile setup template directly")
                    return render_template("profile_setup.html")
                else:
                    logging.debug("User has complete profile, loading main app directly")
                    # Load main app directly instead of redirecting
                    try:
                        user_data = {
                            'profile': {'name': user.profile.name, 'age': user.profile.age, 'gender': user.profile.gender},
                            'goals': {},
                            'stats': {'total_workouts': 0, 'current_streak': 0, 'personal_records': 0}
                        }
                        logging.debug(f"Rendering index.html with user data: {user_data}")
                        return render_template("index.html", user_data=user_data)
                    except Exception as e:
                        logging.error(f"Error loading user data in login: {e}")
                        return render_template("index.html", user_data={'profile': {'name': user.profile.name}, 'goals': {}, 'stats': {}})
            else:
                flash("Invalid email or password")
                return render_template("auth.html")
        else:
            flash("Invalid email or password")
            return render_template("auth.html")
    
    return render_template("auth.html")

@auth_bp.route("/register", methods=["POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
        
    email = request.form.get("email")
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")
    
    if not email or not password:
        flash("Email and password are required")
        return render_template("auth.html")
    
    if password != confirm_password:
        flash("Passwords do not match")
        return render_template("auth.html")
    
    if User.query.filter_by(email=email).first():
        flash("Email already registered")
        return render_template("auth.html")
    
    # Create new user
    user = User()
    user.email = email
    user.set_password(password)
    
    db.session.add(user)
    db.session.commit()
    
    login_user(user)
    
    # New users go to profile setup
    return redirect("/profile-setup")

@auth_bp.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")