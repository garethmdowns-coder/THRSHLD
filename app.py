from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_migrate import Migrate
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
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize extensions
from models import db, User, UserProfile, UserGoals, Workout, Exercise, CheckIn, BodyMeasurement, PersonalRecord
db.init_app(app)
migrate = Migrate(app, db)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access THRSHLD.'

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
    if current_user.is_authenticated:
        # Get user data from database
        profile = current_user.profile
        goals = current_user.goals
        
        user_data = {
            'profile': profile.to_dict() if profile else {},
            'goals': goals.to_dict() if goals else {},
            'stats': get_user_stats(current_user.id)
        }
        return render_template("index.html", user_data=user_data)
    else:
        return render_template("auth.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        
        if not email or not password:
            flash("Email and password are required")
            return render_template("auth.html")
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for("index"))
        else:
            flash("Invalid email or password")
            return render_template("auth.html")
    
    return render_template("auth.html")

@app.route("/register", methods=["POST"])
def register():
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
    
    user = User(email=email)
    user.set_password(password)
    
    db.session.add(user)
    db.session.commit()
    
    login_user(user)
    return redirect(url_for("index"))

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("index"))

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
@login_required
def set_profile():
    try:
        profile_data = request.get_json()
        
        # Basic validation
        if not profile_data.get('name', '').strip():
            return jsonify({'error': 'Name is required'}), 400
        
        # Get or create user profile
        profile = current_user.profile
        if not profile:
            profile = UserProfile(user_id=current_user.id)
            db.session.add(profile)
        
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
        
        return jsonify({'success': True, 'message': 'Profile saved successfully!'})
        
    except Exception as e:
        logging.error(f"Error setting profile: {e}")
        db.session.rollback()
        return jsonify({'error': 'Failed to save profile'}), 500

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
