import os
import requests
import logging
from datetime import datetime, timedelta
from flask import session, url_for, request, redirect
import json

class StravaAPI:
    def __init__(self):
        self.client_id = os.environ.get('STRAVA_CLIENT_ID')
        self.client_secret = os.environ.get('STRAVA_CLIENT_SECRET')
        self.base_url = 'https://www.strava.com/api/v3'
        self.auth_url = 'https://www.strava.com/oauth/authorize'
        self.token_url = 'https://www.strava.com/oauth/token'
        
    def get_authorization_url(self, redirect_uri):
        """Generate Strava OAuth authorization URL"""
        params = {
            'client_id': self.client_id,
            'redirect_uri': redirect_uri,
            'response_type': 'code',
            'scope': 'read,activity:read_all',
            'approval_prompt': 'auto'
        }
        
        auth_url = f"{self.auth_url}?" + "&".join([f"{k}={v}" for k, v in params.items()])
        return auth_url
    
    def exchange_code_for_token(self, code):
        """Exchange authorization code for access token"""
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'grant_type': 'authorization_code'
        }
        
        try:
            response = requests.post(self.token_url, data=data)
            response.raise_for_status()
            token_data = response.json()
            
            # Store token data in session
            session['strava_access_token'] = token_data.get('access_token')
            session['strava_refresh_token'] = token_data.get('refresh_token')
            session['strava_expires_at'] = token_data.get('expires_at')
            session['strava_athlete_id'] = token_data.get('athlete', {}).get('id')
            
            logging.info(f"Strava token exchanged successfully for athlete {session.get('strava_athlete_id')}")
            return token_data
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error exchanging Strava code for token: {e}")
            return None
    
    def refresh_access_token(self):
        """Refresh expired access token"""
        if not session.get('strava_refresh_token'):
            return None
            
        data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': session.get('strava_refresh_token'),
            'grant_type': 'refresh_token'
        }
        
        try:
            response = requests.post(self.token_url, data=data)
            response.raise_for_status()
            token_data = response.json()
            
            # Update session with new tokens
            session['strava_access_token'] = token_data.get('access_token')
            session['strava_refresh_token'] = token_data.get('refresh_token')
            session['strava_expires_at'] = token_data.get('expires_at')
            
            logging.info("Strava access token refreshed successfully")
            return token_data.get('access_token')
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error refreshing Strava token: {e}")
            return None
    
    def get_valid_access_token(self):
        """Get valid access token, refreshing if necessary"""
        access_token = session.get('strava_access_token')
        expires_at = session.get('strava_expires_at')
        
        if not access_token:
            return None
            
        # Check if token is expired (with 5 minute buffer)
        if expires_at and datetime.now().timestamp() >= (expires_at - 300):
            access_token = self.refresh_access_token()
            
        return access_token
    
    def make_api_request(self, endpoint):
        """Make authenticated request to Strava API"""
        access_token = self.get_valid_access_token()
        if not access_token:
            return None
            
        headers = {'Authorization': f'Bearer {access_token}'}
        url = f"{self.base_url}/{endpoint}"
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logging.error(f"Error making Strava API request to {endpoint}: {e}")
            return None
    
    def get_athlete_stats(self):
        """Get athlete statistics"""
        athlete_id = session.get('strava_athlete_id')
        if not athlete_id:
            return None
            
        return self.make_api_request(f'athletes/{athlete_id}/stats')
    
    def get_recent_activities(self, limit=10):
        """Get recent activities"""
        return self.make_api_request(f'athlete/activities?per_page={limit}')
    
    def get_activity_details(self, activity_id):
        """Get detailed activity information"""
        return self.make_api_request(f'activities/{activity_id}')
    
    def get_recovery_metrics(self):
        """Extract recovery-relevant metrics from Strava data"""
        try:
            activities = self.get_recent_activities(limit=7)  # Last 7 activities
            athlete_stats = self.get_athlete_stats()
            
            if not activities:
                return None
                
            # Calculate training load metrics
            recent_training_load = 0
            recent_distance = 0
            recent_time = 0
            activity_count = len(activities)
            
            for activity in activities:
                # Training stress score approximation
                if activity.get('suffer_score'):
                    recent_training_load += activity.get('suffer_score', 0)
                    
                # Distance and time
                recent_distance += activity.get('distance', 0) / 1000  # Convert to km
                recent_time += activity.get('moving_time', 0) / 3600  # Convert to hours
            
            # Calculate weekly averages and fatigue indicators
            avg_training_load = recent_training_load / max(activity_count, 1)
            avg_distance_per_activity = recent_distance / max(activity_count, 1)
            
            # Recovery recommendations based on training load
            if avg_training_load > 150:
                readiness = "Moderate"
                readiness_score = 65
                recovery_tip = "Consider an active recovery day - high training load detected"
            elif avg_training_load > 100:
                readiness = "Good"
                readiness_score = 80
                recovery_tip = "You're training consistently - maintain current intensity"
            else:
                readiness = "Excellent"
                readiness_score = 95
                recovery_tip = "Low training stress - great time for a challenging workout"
            
            return {
                'training_load': {
                    'weekly_total': recent_training_load,
                    'average_per_session': round(avg_training_load, 1),
                    'status': 'High' if avg_training_load > 150 else 'Moderate' if avg_training_load > 100 else 'Light'
                },
                'volume': {
                    'weekly_distance': round(recent_distance, 1),
                    'weekly_time': round(recent_time, 1),
                    'activities_count': activity_count
                },
                'readiness': {
                    'score': readiness_score,
                    'status': readiness,
                    'recommendation': recovery_tip
                },
                'last_activity': activities[0] if activities else None
            }
            
        except Exception as e:
            logging.error(f"Error calculating recovery metrics: {e}")
            return None
    
    def is_connected(self):
        """Check if user has connected Strava account"""
        return bool(session.get('strava_access_token') and session.get('strava_athlete_id'))

# Global instance
strava_api = StravaAPI()