import logging
from datetime import date, timedelta
from typing import Dict, Any
from models import Workout, PersonalRecord

def get_user_stats(user_id: int) -> Dict[str, Any]:
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

def validate_profile_data(profile_data: Dict[str, Any]) -> tuple[bool, str]:
    """Validate profile data and return (is_valid, error_message)"""
    if not profile_data:
        return False, "Profile data is required"
    
    if not profile_data.get('name', '').strip():
        return False, "Name is required"
    
    # Validate age if provided
    age = profile_data.get('age')
    if age and (not isinstance(age, (int, str)) or not str(age).isdigit() or int(age) < 13 or int(age) > 120):
        return False, "Age must be between 13 and 120"
    
    # Validate 1RM values if provided
    for field in ['squat_1rm', 'bench_1rm', 'deadlift_1rm', 'overhead_press_1rm']:
        value = profile_data.get(field)
        if value and (not isinstance(value, (int, float, str)) or float(value) < 0 or float(value) > 1000):
            return False, f"{field.replace('_', ' ').title()} must be between 0 and 1000kg"
    
    return True, ""

def format_workout_response(ai_response: str) -> str:
    """Format AI workout response for better display"""
    # Basic formatting improvements
    formatted = ai_response.strip()
    
    # Ensure proper spacing after numbered lists
    formatted = formatted.replace('\n1.', '\n\n1.')
    formatted = formatted.replace('\n2.', '\n\n2.')
    formatted = formatted.replace('\n3.', '\n\n3.')
    
    # Clean up extra whitespace
    lines = formatted.split('\n')
    cleaned_lines = []
    for line in lines:
        if line.strip():
            cleaned_lines.append(line.strip())
        elif cleaned_lines and cleaned_lines[-1]:  # Only add empty line if previous line wasn't empty
            cleaned_lines.append('')
    
    return '\n'.join(cleaned_lines)

def sanitize_input(text: str, max_length: int = 500) -> str:
    """Sanitize user input for safety"""
    if not text:
        return ""
    
    # Remove potentially harmful characters
    sanitized = text.strip()
    
    # Limit length
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized