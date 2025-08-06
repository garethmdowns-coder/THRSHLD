# THRSHLD - Strength & Conditioning App

## Overview

THRSHLD is a personalized fitness coaching web application that helps users set fitness goals, track daily check-ins, and receive AI-powered workout recommendations. The app uses OpenAI's GPT-4 to generate customized workout plans based on user goals and daily status updates. Built as a mobile-first progressive web app with a clean, minimalist interface focused on simplicity and user engagement.

## User Preferences

Preferred communication style: Simple, everyday language.
Design preference: Pure black background with white text for maximum contrast.
User onboarding preference: Profile setup must be completed before accessing any other app features.

## System Architecture

### Frontend Architecture
- **Mobile-First Design**: Single-page application optimized for mobile devices with responsive design
- **Pure Black Interface**: High contrast design with pure black background and white text for maximum readability
- **Template Engine**: Flask's Jinja2 templating system for server-side rendering
- **UI Framework**: Tailwind CSS for utility-first styling with custom dark color scheme
- **JavaScript**: Vanilla JavaScript for client-side interactions and API communication
- **Component Structure**: Modular tab-based interface (Today, Progress, Recovery, Library) with dynamic content loading
- **Authentication Flow**: Login/registration screens with automatic redirection to main app
- **Gated Onboarding**: Full-screen profile setup that blocks access to all other features until completed
- **Progress Analytics**: Multi-tab progress interface with Chart.js integration for interactive data visualization

### Backend Architecture
- **Web Framework**: Flask (Python) with SQLAlchemy ORM for database operations
- **Database Layer**: PostgreSQL with Flask-SQLAlchemy for data modeling and relationships
- **Authentication**: Flask-Login for user session management and route protection
- **API Design**: RESTful endpoints for profile (`/set-profile`), goals (`/set-goal`), check-ins (`/check-in`), and progress analytics
- **Progress Analytics**: Multiple API endpoints (`/api/progress/*`) providing detailed charts and statistics
- **Error Handling**: Comprehensive input validation, database transaction rollbacks, and proper HTTP status codes
- **Logging**: Debug-level logging for development, authentication events, and database operations

### Data Storage
- **PostgreSQL Database**: Full database integration with SQLAlchemy ORM for robust data persistence
- **Database Models**: User, UserProfile, UserGoals, Workout, Exercise, CheckIn, BodyMeasurement, PersonalRecord
- **Data Relationships**: Proper foreign key relationships between users and their data
- **Profile Data**: Name, age, gender, weight, height, date of birth, experience level, primary activity, training location
- **Data Management**: Automatic table creation, transaction management, and data integrity
- **Statistics Tracking**: Real-time calculation of workout counts, streaks, personal records, and progress metrics

### Authentication & Authorization
- **Flask-Login Integration**: Complete user authentication system with login/logout functionality
- **User Registration**: Email-based account creation with password hashing (Werkzeug)
- **Session Management**: Secure session handling with Flask-Login user loading
- **Route Protection**: Login-required decorators protecting all user data endpoints
- **Database Security**: User data isolation - users only access their own records

## External Dependencies

### AI Integration
- **OpenAI API**: GPT-4o model integration for generating personalized workout recommendations
- **API Configuration**: Environment variable configuration for API key management
- **Prompt Engineering**: Contextual prompts using user goals and check-in data

### Frontend Libraries
- **Tailwind CSS**: CDN-based utility-first CSS framework
- **Chart.js**: Interactive charts for progress analytics and data visualization
- **Heroicons**: Icon library for consistent UI elements
- **Custom Styling**: Additional CSS for animations and theme customization

### Development Tools
- **Python Libraries**: 
  - Flask for web framework
  - Flask-SQLAlchemy for database ORM
  - Flask-Login for authentication
  - Flask-Migrate for database migrations
  - Werkzeug for password hashing
  - Requests for HTTP client functionality
  - SQLAlchemy for advanced database queries
- **Database**: PostgreSQL with environment-based connection configuration
- **Environment Configuration**: Environment variables for API keys, database connection, and session secrets

### Deployment Considerations
- **Static Assets**: CSS and JavaScript files served through Flask's static file handling
- **Template System**: HTML templates with server-side rendering
- **Configuration**: Environment-based configuration for production deployment