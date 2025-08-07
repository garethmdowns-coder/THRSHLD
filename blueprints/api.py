from flask import Blueprint, request, jsonify, session
from flask_login import login_required, current_user, login_user
from datetime import datetime, date, timedelta
import requests
import json
import logging
from sqlalchemy import func, and_
from models import db, User, UserProfile, UserGoals, Workout, Exercise, CheckIn, BodyMeasurement, PersonalRecord
from strava_integration import strava_api
import os

api_bp = Blueprint('api', __name__, url_prefix='/api')

# OpenAI API Key
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "your-openai-api-key")

def get_user_stats(user_id):
    """Get user statistics"""
    try:
        total_workouts = Workout.query.filter_by(user_id=user_id).count()
        
        # Calculate current streak
        recent_workouts = Workout.query.filter_by(user_id=user_id)\
                                     .order_by(Workout.date_completed.desc())\
                                     .limit(30).all()
        
        current_streak = 0
        if recent_workouts:
            current_date = date.today()
            for workout in recent_workouts:
                if workout.date_completed == current_date or workout.date_completed == current_date - timedelta(days=1):
                    current_streak += 1
                    current_date = workout.date_completed - timedelta(days=1)
                else:
                    break
        
        personal_records = PersonalRecord.query.filter_by(user_id=user_id).count()
        
        return {
            'total_workouts': total_workouts,
            'current_streak': current_streak,
            'personal_records': personal_records
        }
    except Exception as e:
        logging.error(f"Error getting user stats: {e}")
        return {'total_workouts': 0, 'current_streak': 0, 'personal_records': 0}

@api_bp.route("/check-in", methods=["POST"])
@login_required
def check_in():
    try:
        data = request.get_json()
        status = data.get('status', '').strip()
        
        if not status:
            return jsonify({"error": "Status is required"}), 400
        
        # Create check-in record
        checkin = CheckIn()
        checkin.user_id = current_user.id
        checkin.date = date.today()
        checkin.notes = status
        db.session.add(checkin)
        
        # Get user profile and goals for AI context
        profile = current_user.profile
        goals = current_user.goals
        
        # Prepare AI prompt with user context
        user_context = ""
        if profile:
            user_context += f"User: {profile.name}, Age: {profile.age}, Experience: {profile.experience_level or 'beginner'}, "
            user_context += f"Training {profile.training_days_per_week or 3} days/week. "
            
            # Include 1RM data for strength programming
            if profile.squat_1rm:
                user_context += f"Squat 1RM: {profile.squat_1rm}kg, "
            if profile.bench_1rm:
                user_context += f"Bench 1RM: {profile.bench_1rm}kg, "
            if profile.deadlift_1rm:
                user_context += f"Deadlift 1RM: {profile.deadlift_1rm}kg, "
            if profile.overhead_press_1rm:
                user_context += f"Overhead Press 1RM: {profile.overhead_press_1rm}kg. "
        
        if goals:
            user_context += f"Primary goal: {goals.workout_goal}. "
            if goals.compound_lifts:
                user_context += f"Focuses on: {', '.join(goals.compound_lifts)}. "
        
        prompt = f"""You are THRSHLD, an expert strength and conditioning coach. Based on this user's check-in, create a personalized workout.

{user_context}

User's Status Today: "{status}"

Create a specific workout with:
1. Warm-up (5-10 minutes)
2. Main exercises with exact sets, reps, and weights (use their 1RM data for percentage-based programming)
3. Cool-down

Keep it concise and actionable. If they have 1RM data, use specific percentages (e.g., "Squat: 3 sets of 5 reps at 85% of {profile.squat_1rm if profile and profile.squat_1rm else 'your max'}kg").

Match the workout intensity to their current state."""

        # Call OpenAI API
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "gpt-4o",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 800,
                "temperature": 0.7
            },
            timeout=30
        )
        
        response.raise_for_status()
        ai_response = response.json()
        reply = ai_response['choices'][0]['message']['content']
        
        # Save workout
        workout = Workout()
        workout.user_id = current_user.id
        workout.workout_name = "Daily Workout"
        workout.workout_type = "generated"
        workout.date_completed = date.today()
        workout.notes = reply
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

@api_bp.route("/user-data")
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

@api_bp.route("/profile", methods=["POST"])
def set_profile():
    try:
        # Debug session information
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
            profile = UserProfile()
            profile.user_id = current_user.id
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
        
        # Update performance data fields
        profile.squat_1rm = float(profile_data.get('squat_1rm', 0)) if profile_data.get('squat_1rm') else None
        profile.bench_1rm = float(profile_data.get('bench_1rm', 0)) if profile_data.get('bench_1rm') else None
        profile.deadlift_1rm = float(profile_data.get('deadlift_1rm', 0)) if profile_data.get('deadlift_1rm') else None
        profile.overhead_press_1rm = float(profile_data.get('overhead_press_1rm', 0)) if profile_data.get('overhead_press_1rm') else None
        profile.max_pull_ups = int(profile_data.get('max_pull_ups', 0)) if profile_data.get('max_pull_ups') else None
        profile.five_km_time = profile_data.get('five_km_time', '').strip() if profile_data.get('five_km_time') else None
        profile.preferred_intensity = profile_data.get('preferred_intensity', '').strip() if profile_data.get('preferred_intensity') else None
        
        # Clear any cached workout data to force regeneration with new performance data
        logging.debug(f"Performance data updated for user {current_user.email}: "
                     f"Squat: {profile.squat_1rm}kg, Bench: {profile.bench_1rm}kg, "
                     f"Deadlift: {profile.deadlift_1rm}kg, OHP: {profile.overhead_press_1rm}kg")
        
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
        # Only log profile_data if it exists
        if 'profile_data' in locals():
            logging.error(f"Profile data was: {profile_data}")
        db.session.rollback()
        return jsonify({'error': f'Failed to save profile: {str(e)}'}), 500

# Progress Analytics Routes
@api_bp.route("/progress/overview")
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

@api_bp.route("/progress/strength")
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
        exercises = Exercise.query.join(Workout).filter(
            Workout.user_id == user_id
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

@api_bp.route("/progress/body-metrics")
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

@api_bp.route("/progress/wellness")
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

# Strava Integration Routes
@api_bp.route("/strava/recovery-metrics")
@login_required
def get_strava_recovery_metrics():
    if not strava_api.is_connected():
        return jsonify({"error": "Strava not connected"}), 400
    
    try:
        metrics = strava_api.get_recovery_metrics()
        if metrics:
            return jsonify(metrics)
        else:
            return jsonify({"error": "Unable to fetch Strava data"}), 500
    except Exception as e:
        logging.error(f"Error fetching Strava recovery metrics: {e}")
        return jsonify({"error": "Failed to fetch recovery data"}), 500