from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import current_user
from flask_mail import Message
import logging
from models import db, User
from datetime import datetime

password_reset_bp = Blueprint('password_reset', __name__)

def send_reset_email(email, token):
    """Send password reset email"""
    from app import mail
    reset_url = url_for('password_reset.reset_password', token=token, _external=True)
    
    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif; background-color: #000000; color: #ffffff; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #111111; border-radius: 10px; padding: 40px;">
            <h1 style="color: #3b82f6; text-align: center; margin-bottom: 30px;">THRSHLD</h1>
            <h2 style="color: #ffffff; margin-bottom: 20px;">Reset Your Password</h2>
            <p style="color: #9ca3af; margin-bottom: 20px;">
                We received a request to reset your password. Click the link below to create a new password:
            </p>
            <div style="text-align: center; margin: 30px 0;">
                <a href="{reset_url}" 
                   style="background-color: #3b82f6; color: #ffffff; padding: 15px 30px; text-decoration: none; border-radius: 8px; font-weight: bold; display: inline-block;">
                    Reset Password
                </a>
            </div>
            <p style="color: #9ca3af; font-size: 14px; margin-top: 30px;">
                If you didn't request this password reset, you can safely ignore this email.
                This link will expire in 1 hour for security.
            </p>
            <div style="border-top: 1px solid #374151; margin-top: 30px; padding-top: 20px; text-align: center;">
                <p style="color: #6b7280; font-size: 12px;">
                    THRSHLD - Strength & Conditioning
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    text_body = f"""
    THRSHLD - Password Reset
    
    We received a request to reset your password.
    
    Click this link to reset your password: {reset_url}
    
    If you didn't request this password reset, you can safely ignore this email.
    This link will expire in 1 hour for security.
    
    THRSHLD - Strength & Conditioning
    """
    
    msg = Message(
        subject='THRSHLD - Reset Your Password',
        recipients=[email],
        html=html_body,
        body=text_body
    )
    
    mail.send(msg)

@password_reset_bp.route("/forgot-password", methods=["GET", "POST"])
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

@password_reset_bp.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for("index"))
        
    user = User.query.filter_by(reset_token=token).first()
    
    if not user or not user.verify_reset_token(token):
        flash("Invalid or expired reset token")
        return redirect(url_for("password_reset.forgot_password"))
        
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
        return redirect(url_for("auth.login"))
        
    return render_template("reset_password.html", token=token)