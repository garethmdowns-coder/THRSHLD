from flask import Blueprint, request, redirect, url_for, flash, session, render_template
from flask_login import login_required, current_user, login_user
import logging
from models import User
from strava_integration import strava_api

strava_bp = Blueprint('strava', __name__, url_prefix='/strava')

@strava_bp.route("/connect")
@login_required
def connect_strava():
    # Store user ID in session before redirecting
    session['user_id_for_strava'] = current_user.id
    redirect_uri = url_for('strava.strava_callback', _external=True)
    auth_url = strava_api.get_authorization_url(redirect_uri)
    
    # Return a page that closes the popup window after auth
    return f"""
    <html>
    <head><title>Connecting to Strava...</title></head>
    <body>
        <script>
            window.location.href = '{auth_url}';
        </script>
        <p>Redirecting to Strava...</p>
    </body>
    </html>
    """

@strava_bp.route("/callback")
def strava_callback():
    code = request.args.get('code')
    if not code:
        return redirect(url_for('index') + '?error=strava_auth_failed')
    
    # If user is not authenticated, try to log them back in if we have their user ID
    if not current_user.is_authenticated:
        user_id = session.get('user_id_for_strava')
        if user_id:
            user = User.query.get(user_id)
            if user:
                login_user(user, remember=True)
                session.permanent = True
    
    # Now process the Strava token
    if current_user.is_authenticated:
        token_data = strava_api.exchange_code_for_token(code)
        if token_data:
            # Return a page that closes the popup and notifies parent
            return """
            <html>
            <head><title>Strava Connected</title></head>
            <body>
                <script>
                    if (window.opener) {
                        window.opener.postMessage('strava_connected', '*');
                        window.close();
                    } else {
                        window.location.href = '/';
                    }
                </script>
                <p>Strava connected successfully! This window will close automatically.</p>
            </body>
            </html>
            """
        else:
            return """
            <html>
            <head><title>Strava Connection Failed</title></head>
            <body>
                <script>
                    if (window.opener) {
                        window.opener.postMessage('strava_error', '*');
                        window.close();
                    } else {
                        window.location.href = '/?error=strava_token_failed';
                    }
                </script>
                <p>Strava connection failed. This window will close automatically.</p>
            </body>
            </html>
            """
    else:
        return redirect(url_for('index') + '?error=auth_required')
    
    return redirect(url_for('index'))

@strava_bp.route("/disconnect")
@login_required
def disconnect_strava():
    # Clear Strava session data
    session.pop('strava_access_token', None)
    session.pop('strava_refresh_token', None)
    session.pop('strava_expires_at', None)
    session.pop('strava_athlete_id', None)
    
    flash("Strava disconnected successfully.", "success")
    return redirect(url_for('index'))