from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
from flask_mail import Mail, Message
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
import os
import requests
import json
import logging
from sqlalchemy import func, and_

# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "f8a3b2c1d4e5f6789abc012345def678")

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Session configuration - relaxed for debugging
app.config['SESSION_COOKIE_SECURE'] = False  # Allow HTTP for development
app.config['SESSION_COOKIE_HTTPONLY'] = False  # Allow JS access for debugging
app.config['SESSION_COOKIE_SAMESITE'] = None  # Less restrictive
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)
app.config['SESSION_COOKIE_DOMAIN'] = None  # Default domain

# Mail configuration
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', '587'))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@thrshld.app')

# Initialize extensions
mail = Mail(app)
from models import db, User, UserProfile, UserGoals, Workout, Exercise, CheckIn, BodyMeasurement, PersonalRecord
db.init_app(app)
migrate = Migrate(app, db)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access THRSHLD.'
login_manager.session_protection = None  # Disable session protection for debugging

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create database tables
with app.app_context():
    db.create_all()

# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "your-openai-api-key")

# Authentication routes
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
                'stats': {'total_workouts': 0, 'current_streak': 0, 'personal_records': 0}
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
    from flask import session
    logging.debug(f"Profile setup accessed by user: {current_user.email if current_user.is_authenticated else 'Anonymous'}")
    logging.debug(f"Session in profile setup: {dict(session)}")
    logging.debug(f"User authenticated: {current_user.is_authenticated}")
    
    # Check if user already has a complete profile
    if current_user.profile and current_user.profile.name:
        logging.debug("User already has profile, redirecting to main app")
        return redirect("/")
    return render_template("profile_setup.html")

@app.route("/login", methods=["GET", "POST"])
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
                from flask import session
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

@app.route("/register", methods=["POST"])
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
    user = User(email=email)
    user.set_password(password)
    
    db.session.add(user)
    db.session.commit()
    
    login_user(user)
    
    # New users go to profile setup
    return redirect("/profile-setup")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

# Password Reset Routes
@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
        
    if request.method == "POST":
        email = request.form.get("email")
        
        if not email:
            flash("Email is required")
            return render_template("forgot_password.html")
            
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Generate reset token
            token = user.generate_reset_token()
            db.session.commit()
            
            # Send reset email
            try:
                send_reset_email(user.email, token)
                flash("Password reset instructions have been sent to your email.")
            except Exception as e:
                logging.error(f"Failed to send reset email: {e}")
                flash("Failed to send reset email. Please try again later.")
        else:
            # Don't reveal whether email exists or not for security
            flash("If an account with that email exists, password reset instructions have been sent.")
            
        return render_template("forgot_password.html")
    
    return render_template("forgot_password.html")

@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("index"))
        
    user = User.query.filter_by(reset_token=token).first()
    
    if not user or not user.verify_reset_token(token):
        flash("Invalid or expired reset token")
        return redirect(url_for("forgot_password"))
        
    if request.method == "POST":
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")
        
        if not password or not confirm_password:
            flash("Both password fields are required")
            return render_template("reset_password.html", token=token)
            
        if password != confirm_password:
            flash("Passwords do not match")
            return render_template("reset_password.html", token=token)
            
        if len(password) < 6:
            flash("Password must be at least 6 characters long")
            return render_template("reset_password.html", token=token)
            
        # Update password and clear reset token
        user.set_password(password)
        user.clear_reset_token()
        db.session.commit()
        
        flash("Your password has been updated! You can now log in.")
        return redirect(url_for("login"))
        
    return render_template("reset_password.html", token=token)

def send_reset_email(email, token):
    """Send password reset email"""
    reset_url = url_for('reset_password', token=token, _external=True)
    
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #000000; color: #ffffff; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #111111; border-radius: 10px; padding: 40px;">
            <h1 style="color: #3b82f6; text-align: center; margin-bottom: 30px;">THRSHLD</h1>
            
            <h2 style="color: #ffffff; margin-bottom: 20px;">Password Reset Request</h2>
            
            <p style="color: #9ca3af; margin-bottom: 20px;">
                You have requested to reset your password for your THRSHLD account. 
                Click the button below to reset your password:
            </p>
            
            <div style="text-align: center; margin: 30px 0;">
                <a href="{reset_url}" 
                   style="background-color: #3b82f6; color: white; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;">
                    Reset Password
                </a>
            </div>
            
            <p style="color: #9ca3af; font-size: 14px; margin-top: 30px;">
                This link will expire in 1 hour. If you didn't request this password reset, 
                you can safely ignore this email.
            </p>
            
            <p style="color: #9ca3af; font-size: 12px; margin-top: 20px;">
                If the button doesn't work, copy and paste this URL into your browser:<br>
                <span style="color: #3b82f6;">{reset_url}</span>
            </p>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
    THRSHLD - Password Reset Request
    
    You have requested to reset your password for your THRSHLD account.
    
    Click this link to reset your password: {reset_url}
    
    This link will expire in 1 hour. If you didn't request this password reset, 
    you can safely ignore this email.
    """
    
    msg = Message(
        subject="THRSHLD - Reset Your Password",
        recipients=[email],
        html=html_body,
        body=text_body
    )
    
    mail.send(msg)

def get_user_stats(user_id):
    """Calculate user statistics from database"""
    total_workouts = Workout.query.filter_by(user_id=user_id).count()
    
    # Calculate streak
    recent_workouts = Workout.query.filter_by(user_id=user_id).order_by(Workout.date_completed.desc()).limit(30).all()
    current_streak = 0
    if recent_workouts:
        last_workout_date = recent_workouts[0].date_completed
        current_date = date.today()
        
        while current_date >= last_workout_date:
            day_workouts = [w for w in recent_workouts if w.date_completed == current_date]
            if day_workouts:
                current_streak += 1
                current_date -= timedelta(days=1)
            else:
                break
    
    # Get personal records
    personal_records = PersonalRecord.query.filter_by(user_id=user_id).all()
    
    return {
        'total_workouts': total_workouts,
        'current_streak': current_streak,
        'personal_records': len(personal_records),
        'total_check_ins': CheckIn.query.filter_by(user_id=user_id).count()
    }



@app.route("/set-goal", methods=["POST"])
@login_required
def set_goal():
    try:
        goals_data = request.get_json()
        
        # Get or create user goals
        goals = current_user.goals
        if not goals:
            goals = UserGoals(user_id=current_user.id)
            db.session.add(goals)
        
        # Update goals
        goals.workout_goal = goals_data.get('workout_goal', '')
        goals.compound_lifts = goals_data.get('compound_lifts', [])
        goals.include_running = goals_data.get('include_running', False)
        goals.include_conditioning = goals_data.get('include_conditioning', False)
        goals.target_sessions_per_week = goals_data.get('target_sessions_per_week')
        
        db.session.commit()
        
        return jsonify({"message": "Goals updated successfully!", "goals": goals.to_dict()})
    except Exception as e:
        logging.error(f"Error setting goals: {e}")
        db.session.rollback()
        return jsonify({"error": "Failed to save goals. Please try again."}), 500

@app.route("/check-in", methods=["POST"])
@login_required
def check_in():
    try:
        check_in_data = request.get_json()
        status = check_in_data.get("status") if check_in_data else None
        
        if not isinstance(status, str) or not status.strip():
            return jsonify({"error": "Please provide a valid check-in status."}), 400
        
        status = status.strip()
        
        # Create check-in record
        checkin = CheckIn(
            user_id=current_user.id,
            date=date.today(),
            notes=status
        )
        db.session.add(checkin)
        
        # Get user goals for workout generation
        goals = current_user.goals
        if not goals:
            return jsonify({"error": "Please set your fitness goals first before checking in."}), 400

        # Get recent check-ins for context
        recent_checkins = CheckIn.query.filter_by(user_id=current_user.id).order_by(CheckIn.date.desc()).limit(3).all()
        recent_history = [c.notes for c in recent_checkins if c.notes]

        prompt = f"""User goals: {goals.to_dict()}
        
Current check-in: {status}

Recent workout history: {recent_history[-3:] if len(recent_history) > 1 else 'First workout'}

Based on this information, create a personalized workout plan for today. Include:
1. 4-6 specific exercises
2. Sets and reps for each exercise
3. Brief instructions or form cues
4. Estimated total workout time

Format the response as a structured workout plan that's easy to follow."""

        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "gpt-4o",
            "messages": [
                {"role": "system", "content": "You are THRSHLD's AI fitness coach. Create personalized, safe, and effective workout plans based on user goals and check-ins. Always prioritize proper form and progressive overload."},
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 800,
            "temperature": 0.7
        }

        response = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)

        if response.status_code != 200:
            logging.error(f"OpenAI API error: {response.status_code} - {response.text}")
            return jsonify({"error": "Unable to generate workout plan. Please try again later."}), 500

        result = response.json()
        reply = result.get("choices", [{}])[0].get("message", {}).get("content", "No workout plan generated.")

        # Create workout record
        workout = Workout(
            user_id=current_user.id,
            workout_name="Daily Workout",
            workout_type="generated",
            date_completed=date.today(),
            notes=reply
        )
        db.session.add(workout)
        db.session.commit()

        # Get updated stats
        stats = get_user_stats(current_user.id)

        return jsonify({"reply": reply, "stats": stats})
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error calling OpenAI: {e}")
        return jsonify({"error": "Network error. Please check your internet connection and try again."}), 500
    except Exception as e:
        logging.error(f"Error in check-in: {e}")
        db.session.rollback()
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500

@app.route("/get-user-data")
@login_required
def get_user_data():
    try:
        profile = current_user.profile
        goals = current_user.goals
        
        user_data = {
            'profile': profile.to_dict() if profile else {},
            'goals': goals.to_dict() if goals else {},
            'stats': get_user_stats(current_user.id)
        }
        
        return jsonify(user_data)
    except Exception as e:
        logging.error(f"Error loading user data: {e}")
        return jsonify({"error": "Failed to load user data"}), 500

@app.route("/set-profile", methods=["POST"])
def set_profile():
    try:
        # Debug session information
        from flask import session
        logging.debug(f"Set profile - Session: {dict(session)}")
        logging.debug(f"Set profile - User authenticated: {current_user.is_authenticated}")
        logging.debug(f"Set profile - Current user: {current_user.email if current_user.is_authenticated else 'Anonymous'}")
        
        # Alternative approach: Use the most recent user without profile if session is lost
        if not current_user.is_authenticated:
            logging.debug("Session lost, attempting to find user without profile")
            # Find the most recent user without a complete profile
            user_without_profile = User.query.join(UserProfile, User.id == UserProfile.user_id, isouter=True)\
                                           .filter((UserProfile.id == None) | (UserProfile.name == None) | (UserProfile.name == ''))\
                                           .order_by(User.created_at.desc()).first()
            
            if user_without_profile:
                logging.debug(f"Found user without profile: {user_without_profile.email}")
                # Temporarily log them in for this request
                login_user(user_without_profile, remember=True)
                logging.debug(f"Temporarily logged in user: {user_without_profile.email}")
            else:
                logging.debug("No user without profile found, returning error")
                return jsonify({"success": False, "error": "Authentication required"}), 401
        
        profile_data = request.get_json()
        logging.debug(f"Profile data received: {profile_data}")
        
        # Basic validation
        if not profile_data or not profile_data.get('name', '').strip():
            return jsonify({'error': 'Name is required'}), 400
        
        # Get or create user profile
        profile = current_user.profile
        if not profile:
            profile = UserProfile(user_id=current_user.id)
            db.session.add(profile)
            logging.debug("Created new profile for user")
        
        # Update profile fields
        profile.name = profile_data.get('name', '').strip()
        profile.age = int(profile_data.get('age', 0)) if profile_data.get('age') else None
        profile.gender = profile_data.get('gender', '')
        profile.height_cm = float(profile_data.get('height', 0)) if profile_data.get('height') else None
        profile.weight_kg = float(profile_data.get('weight', 0)) if profile_data.get('weight') else None
        profile.experience_level = profile_data.get('experience', '')
        profile.primary_activity = profile_data.get('primary_activity', '')
        profile.training_location = profile_data.get('training_location', '')
        profile.training_days_per_week = int(profile_data.get('training_days', 0)) if profile_data.get('training_days') else None
        
        # Parse date of birth if provided
        if profile_data.get('date_of_birth'):
            try:
                profile.date_of_birth = datetime.strptime(profile_data['date_of_birth'], '%Y-%m-%d').date()
            except ValueError:
                pass
        
        db.session.commit()
        logging.debug(f"Profile saved successfully for user {current_user.email}")
        
        return jsonify({'success': True, 'message': 'Profile saved successfully!'})
        
    except Exception as e:
        logging.error(f"Error setting profile: {e}")
        logging.error(f"Profile data was: {profile_data}")
        db.session.rollback()
        return jsonify({'error': f'Failed to save profile: {str(e)}'}), 500

# Progress Analytics Routes
@app.route("/api/progress/overview")
@login_required
def progress_overview():
    """Get overall progress statistics"""
    try:
        user_id = current_user.id
        
        # Get basic stats
        stats = get_user_stats(user_id)
        
        # Get recent workouts (last 30 days)
        thirty_days_ago = date.today() - timedelta(days=30)
        recent_workouts = Workout.query.filter(
            and_(Workout.user_id == user_id, Workout.date_completed >= thirty_days_ago)
        ).order_by(Workout.date_completed.desc()).all()
        
        # Calculate weekly workout frequency
        weekly_data = {}
        for workout in recent_workouts:
            week_start = workout.date_completed - timedelta(days=workout.date_completed.weekday())
            week_key = week_start.strftime('%Y-W%U')
            weekly_data[week_key] = weekly_data.get(week_key, 0) + 1
        
        # Get recent check-ins
        recent_checkins = CheckIn.query.filter(
            and_(CheckIn.user_id == user_id, CheckIn.date >= thirty_days_ago)
        ).order_by(CheckIn.date.desc()).limit(7).all()
        
        # Calculate average metrics from check-ins
        avg_energy = sum(c.energy_level for c in recent_checkins if c.energy_level) / len(recent_checkins) if recent_checkins else 0
        avg_motivation = sum(c.motivation_level for c in recent_checkins if c.motivation_level) / len(recent_checkins) if recent_checkins else 0
        
        return jsonify({
            'stats': stats,
            'weekly_workout_data': weekly_data,
            'avg_energy_level': round(avg_energy, 1),
            'avg_motivation_level': round(avg_motivation, 1),
            'recent_workouts': [w.to_dict() for w in recent_workouts[:5]],
            'workout_consistency': len(recent_workouts) / 30 * 100  # percentage
        })
    except Exception as e:
        logging.error(f"Error getting progress overview: {e}")
        return jsonify({"error": "Failed to load progress data"}), 500

@app.route("/api/progress/strength")
@login_required 
def strength_progress():
    """Get strength progression data"""
    try:
        user_id = current_user.id
        
        # Get personal records
        records = PersonalRecord.query.filter_by(user_id=user_id).order_by(PersonalRecord.date_achieved.desc()).all()
        
        # Group by exercise
        strength_data = {}
        for record in records:
            if record.exercise_name not in strength_data:
                strength_data[record.exercise_name] = []
            strength_data[record.exercise_name].append({
                'date': record.date_achieved.isoformat(),
                'value': record.value,
                'unit': record.unit,
                'type': record.record_type
            })
        
        # Get exercise progression over time
        exercises = Exercise.query.filter(
            Exercise.workout.has(user_id=user_id)
        ).filter(Exercise.weight_per_set.isnot(None)).all()
        
        progression_data = {}
        for exercise in exercises:
            if exercise.exercise_name not in progression_data:
                progression_data[exercise.exercise_name] = []
            
            max_weight = max(exercise.weight_per_set) if exercise.weight_per_set else 0
            progression_data[exercise.exercise_name].append({
                'date': exercise.workout.date_completed.isoformat(),
                'max_weight': max_weight,
                'total_volume': sum(exercise.weight_per_set) * sum(exercise.reps_per_set) if exercise.reps_per_set else 0
            })
        
        return jsonify({
            'personal_records': strength_data,
            'progression_data': progression_data
        })
    except Exception as e:
        logging.error(f"Error getting strength progress: {e}")
        return jsonify({"error": "Failed to load strength data"}), 500

@app.route("/api/progress/body-metrics")
@login_required
def body_metrics():
    """Get body measurement progression"""
    try:
        user_id = current_user.id
        
        measurements = BodyMeasurement.query.filter_by(user_id=user_id).order_by(BodyMeasurement.date.asc()).all()
        
        weight_data = []
        body_fat_data = []
        measurement_data = {}
        
        for measurement in measurements:
            date_str = measurement.date.isoformat()
            
            if measurement.weight_kg:
                weight_data.append({'date': date_str, 'value': measurement.weight_kg})
            
            if measurement.body_fat_percentage:
                body_fat_data.append({'date': date_str, 'value': measurement.body_fat_percentage})
            
            if measurement.measurements:
                for key, value in measurement.measurements.items():
                    if key not in measurement_data:
                        measurement_data[key] = []
                    measurement_data[key].append({'date': date_str, 'value': value})
        
        return jsonify({
            'weight_progression': weight_data,
            'body_fat_progression': body_fat_data,
            'measurements': measurement_data,
            'latest_measurement': measurements[-1].to_dict() if measurements else None
        })
    except Exception as e:
        logging.error(f"Error getting body metrics: {e}")
        return jsonify({"error": "Failed to load body metrics"}), 500

@app.route("/api/progress/wellness")
@login_required
def wellness_trends():
    """Get wellness and check-in trends"""
    try:
        user_id = current_user.id
        
        # Get last 90 days of check-ins
        ninety_days_ago = date.today() - timedelta(days=90)
        checkins = CheckIn.query.filter(
            and_(CheckIn.user_id == user_id, CheckIn.date >= ninety_days_ago)
        ).order_by(CheckIn.date.asc()).all()
        
        wellness_data = {
            'energy_levels': [],
            'motivation_levels': [],
            'sleep_quality': [],
            'stress_levels': [],
            'muscle_soreness': [],
            'mood_distribution': {}
        }
        
        for checkin in checkins:
            date_str = checkin.date.isoformat()
            
            if checkin.energy_level:
                wellness_data['energy_levels'].append({'date': date_str, 'value': checkin.energy_level})
            if checkin.motivation_level:
                wellness_data['motivation_levels'].append({'date': date_str, 'value': checkin.motivation_level})
            if checkin.sleep_quality:
                wellness_data['sleep_quality'].append({'date': date_str, 'value': checkin.sleep_quality})
            if checkin.stress_level:
                wellness_data['stress_levels'].append({'date': date_str, 'value': checkin.stress_level})
            if checkin.muscle_soreness:
                wellness_data['muscle_soreness'].append({'date': date_str, 'value': checkin.muscle_soreness})
            
            if checkin.mood:
                wellness_data['mood_distribution'][checkin.mood] = wellness_data['mood_distribution'].get(checkin.mood, 0) + 1
        
        return jsonify(wellness_data)
    except Exception as e:
        logging.error(f"Error getting wellness trends: {e}")
        return jsonify({"error": "Failed to load wellness data"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
