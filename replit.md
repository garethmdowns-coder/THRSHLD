# THRSHLD - Strength & Conditioning App

## Overview

THRSHLD is a personalized fitness coaching web application that helps users set fitness goals, track daily check-ins, and receive AI-powered workout recommendations. The app uses OpenAI's GPT-4 to generate customized workout plans based on user goals and daily status updates. Built as a mobile-first progressive web app with a clean, minimalist interface focused on simplicity and user engagement.

## User Preferences

Preferred communication style: Simple, everyday language.
Design preference: Dark mode interface with professional styling.
User onboarding preference: Comprehensive profile setup before goal setting.

## System Architecture

### Frontend Architecture
- **Mobile-First Design**: Single-page application optimized for mobile devices with responsive design
- **Dark Mode Interface**: Professional dark theme with high contrast and accessibility support
- **Template Engine**: Flask's Jinja2 templating system for server-side rendering
- **UI Framework**: Tailwind CSS for utility-first styling with custom dark color scheme
- **JavaScript**: Vanilla JavaScript for client-side interactions and API communication
- **Component Structure**: Modular tab-based interface (Today, Progress, Recovery, Library) with dynamic content loading
- **User Onboarding**: Comprehensive profile setup flow before goal setting and workout generation

### Backend Architecture
- **Web Framework**: Flask (Python) for lightweight web server and API endpoints
- **Session Management**: Flask sessions with configurable secret key for user state
- **API Design**: RESTful endpoints for profile setup (`/set-profile`), goal setting (`/set-goal`) and check-ins (`/check-in`)
- **Error Handling**: Comprehensive input validation and error responses with proper HTTP status codes
- **Logging**: Debug-level logging for development and troubleshooting

### Data Storage
- **File-Based Storage**: JSON file (`user_data.json`) for persisting user data
- **Data Structure**: Comprehensive user data including profile information, goals, check-in history, workout history, and statistics
- **Profile Data**: Name, gender, weight, height, date of birth, experience level, primary activity, training location
- **Data Management**: Automatic initialization and graceful handling of missing/corrupted data files
- **Statistics Tracking**: Workout completion counts, streaks, and personal records

### Authentication & Authorization
- **Current State**: No authentication system implemented (single-user application)
- **Session Security**: Basic session management with secret key configuration
- **Future Consideration**: Ready for multi-user authentication implementation

## External Dependencies

### AI Integration
- **OpenAI API**: GPT-4o model integration for generating personalized workout recommendations
- **API Configuration**: Environment variable configuration for API key management
- **Prompt Engineering**: Contextual prompts using user goals and check-in data

### Frontend Libraries
- **Tailwind CSS**: CDN-based utility-first CSS framework
- **Heroicons**: Icon library for consistent UI elements
- **Custom Styling**: Additional CSS for animations and theme customization

### Development Tools
- **Python Libraries**: 
  - Flask for web framework
  - Requests for HTTP client functionality
  - Standard library modules (os, json, logging)
- **Environment Configuration**: Environment variables for API keys and configuration

### Deployment Considerations
- **Static Assets**: CSS and JavaScript files served through Flask's static file handling
- **Template System**: HTML templates with server-side rendering
- **Configuration**: Environment-based configuration for production deployment