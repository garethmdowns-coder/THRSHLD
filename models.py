from datetime import datetime, date, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
import json
import secrets

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    active = db.Column(db.Boolean, default=True)
    
    # Relationships
    profile = db.relationship('UserProfile', backref='user', uselist=False, cascade='all, delete-orphan')
    goals = db.relationship('UserGoals', backref='user', uselist=False, cascade='all, delete-orphan')
    workouts = db.relationship('Workout', backref='user', cascade='all, delete-orphan')
    check_ins = db.relationship('CheckIn', backref='user', cascade='all, delete-orphan')
    measurements = db.relationship('BodyMeasurement', backref='user', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_reset_token(self):
        """Generate a password reset token"""
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expires = datetime.utcnow() + timedelta(hours=1)  # Token expires in 1 hour
        return self.reset_token

    def verify_reset_token(self, token):
        """Verify if the reset token is valid and not expired"""
        if not self.reset_token or not self.reset_token_expires:
            return False
        if datetime.utcnow() > self.reset_token_expires:
            return False
        return self.reset_token == token

    def clear_reset_token(self):
        """Clear the reset token after use"""
        self.reset_token = None
        self.reset_token_expires = None

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'active': self.active
        }

class UserProfile(db.Model):
    __tablename__ = 'user_profiles'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    age = db.Column(db.Integer)
    gender = db.Column(db.String(20))
    height_cm = db.Column(db.Float)
    weight_kg = db.Column(db.Float)
    date_of_birth = db.Column(db.Date)
    experience_level = db.Column(db.String(20))  # beginner, intermediate, advanced
    primary_activity = db.Column(db.String(50))
    training_location = db.Column(db.String(20))  # gym, home, outdoor
    training_days_per_week = db.Column(db.Integer)
    profile_photo_url = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'name': self.name,
            'age': self.age,
            'gender': self.gender,
            'height_cm': self.height_cm,
            'weight_kg': self.weight_kg,
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'experience_level': self.experience_level,
            'primary_activity': self.primary_activity,
            'training_location': self.training_location,
            'training_days_per_week': self.training_days_per_week,
            'profile_photo_url': self.profile_photo_url
        }

class UserGoals(db.Model):
    __tablename__ = 'user_goals'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    workout_goal = db.Column(db.String(50), nullable=False)  # build-muscle, lose-weight, strength, endurance
    compound_lifts = db.Column(db.JSON)  # Array of selected lifts
    include_running = db.Column(db.Boolean, default=False)
    include_conditioning = db.Column(db.Boolean, default=False)
    target_sessions_per_week = db.Column(db.Integer)
    specific_targets = db.Column(db.JSON)  # Custom goals like "Bench 100kg", "Run 5K in 25min"
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'workout_goal': self.workout_goal,
            'compound_lifts': self.compound_lifts or [],
            'include_running': self.include_running,
            'include_conditioning': self.include_conditioning,
            'target_sessions_per_week': self.target_sessions_per_week,
            'specific_targets': self.specific_targets or []
        }

class Workout(db.Model):
    __tablename__ = 'workouts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    workout_name = db.Column(db.String(100), nullable=False)
    workout_type = db.Column(db.String(50))  # strength, cardio, conditioning, hybrid
    date_completed = db.Column(db.Date, nullable=False)
    duration_minutes = db.Column(db.Integer)
    exercises = db.Column(db.JSON)  # Array of exercise objects with sets, reps, weight
    notes = db.Column(db.Text)
    difficulty_rating = db.Column(db.Integer)  # 1-10 scale
    energy_level_before = db.Column(db.Integer)  # 1-10 scale
    energy_level_after = db.Column(db.Integer)  # 1-10 scale
    calories_burned = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    exercises_detailed = db.relationship('Exercise', backref='workout', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'workout_name': self.workout_name,
            'workout_type': self.workout_type,
            'date_completed': self.date_completed.isoformat() if self.date_completed else None,
            'duration_minutes': self.duration_minutes,
            'exercises': self.exercises or [],
            'notes': self.notes,
            'difficulty_rating': self.difficulty_rating,
            'energy_level_before': self.energy_level_before,
            'energy_level_after': self.energy_level_after,
            'calories_burned': self.calories_burned
        }

class Exercise(db.Model):
    __tablename__ = 'exercises'
    
    id = db.Column(db.Integer, primary_key=True)
    workout_id = db.Column(db.Integer, db.ForeignKey('workouts.id'), nullable=False)
    exercise_name = db.Column(db.String(100), nullable=False)
    exercise_type = db.Column(db.String(50))  # compound, isolation, cardio
    muscle_groups = db.Column(db.JSON)  # Array of muscle groups targeted
    sets_completed = db.Column(db.Integer)
    reps_per_set = db.Column(db.JSON)  # Array of reps for each set
    weight_per_set = db.Column(db.JSON)  # Array of weights for each set
    distance_km = db.Column(db.Float)  # For cardio exercises
    time_seconds = db.Column(db.Integer)  # Duration of exercise
    rest_between_sets = db.Column(db.Integer)  # Rest time in seconds
    personal_record = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)

    def to_dict(self):
        return {
            'id': self.id,
            'exercise_name': self.exercise_name,
            'exercise_type': self.exercise_type,
            'muscle_groups': self.muscle_groups or [],
            'sets_completed': self.sets_completed,
            'reps_per_set': self.reps_per_set or [],
            'weight_per_set': self.weight_per_set or [],
            'distance_km': self.distance_km,
            'time_seconds': self.time_seconds,
            'rest_between_sets': self.rest_between_sets,
            'personal_record': self.personal_record,
            'notes': self.notes
        }

class CheckIn(db.Model):
    __tablename__ = 'check_ins'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    energy_level = db.Column(db.Integer)  # 1-10 scale
    motivation_level = db.Column(db.Integer)  # 1-10 scale
    sleep_quality = db.Column(db.Integer)  # 1-10 scale
    stress_level = db.Column(db.Integer)  # 1-10 scale
    muscle_soreness = db.Column(db.Integer)  # 1-10 scale
    mood = db.Column(db.String(20))  # great, good, okay, tired, stressed
    notes = db.Column(db.Text)
    planned_workout = db.Column(db.Boolean, default=False)
    workout_completed = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'energy_level': self.energy_level,
            'motivation_level': self.motivation_level,
            'sleep_quality': self.sleep_quality,
            'stress_level': self.stress_level,
            'muscle_soreness': self.muscle_soreness,
            'mood': self.mood,
            'notes': self.notes,
            'planned_workout': self.planned_workout,
            'workout_completed': self.workout_completed
        }

class BodyMeasurement(db.Model):
    __tablename__ = 'body_measurements'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    weight_kg = db.Column(db.Float)
    body_fat_percentage = db.Column(db.Float)
    muscle_mass_kg = db.Column(db.Float)
    measurements = db.Column(db.JSON)  # Chest, waist, arms, etc.
    progress_photos = db.Column(db.JSON)  # URLs to progress photos
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'weight_kg': self.weight_kg,
            'body_fat_percentage': self.body_fat_percentage,
            'muscle_mass_kg': self.muscle_mass_kg,
            'measurements': self.measurements or {},
            'progress_photos': self.progress_photos or [],
            'notes': self.notes
        }

class PersonalRecord(db.Model):
    __tablename__ = 'personal_records'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    exercise_name = db.Column(db.String(100), nullable=False)
    record_type = db.Column(db.String(20), nullable=False)  # max_weight, max_reps, fastest_time, longest_distance
    value = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(10))  # kg, lbs, seconds, km, miles
    date_achieved = db.Column(db.Date, nullable=False)
    workout_id = db.Column(db.Integer, db.ForeignKey('workouts.id'))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'exercise_name': self.exercise_name,
            'record_type': self.record_type,
            'value': self.value,
            'unit': self.unit,
            'date_achieved': self.date_achieved.isoformat() if self.date_achieved else None,
            'notes': self.notes
        }