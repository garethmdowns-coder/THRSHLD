from flask import Flask, render_template, request, jsonify
import os
import requests
import json
import logging

# Configure logging for debugging
logging.basicConfig(level=logging.DEBUG)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key-change-in-production")

USER_DATA_FILE = "user_data.json"

def initialize_user_data():
    if not os.path.exists(USER_DATA_FILE):
        with open(USER_DATA_FILE, "w") as f:
            json.dump({
                "profile": {
                    "name": "",
                    "gender": "",
                    "weight": "",
                    "height": "",
                    "date_of_birth": "",
                    "experience": "",
                    "primary_activity": "",
                    "training_location": "",
                    "profile_photo": ""
                },
                "goal": "", 
                "history": [], 
                "check_ins": [],
                "stats": {
                    "completed_workouts": 0,
                    "current_streak": 0,
                    "best_lifts": {}
                }
            }, f)

def load_user_data():
    try:
        with open(USER_DATA_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        initialize_user_data()
        with open(USER_DATA_FILE, "r") as f:
            return json.load(f)

def save_user_data(data):
    with open(USER_DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

initialize_user_data()

# the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
# do not change this unless explicitly requested by the user
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "your-openai-api-key")

@app.route("/")
def index():
    user_data = load_user_data()
    return render_template("index.html", user_data=user_data)

@app.route("/set-goal", methods=["POST"])
def set_goal():
    try:
        data = load_user_data()
        goal = request.json.get("goal") if request.json else None
        if not isinstance(goal, str) or not goal.strip():
            return jsonify({"error": "Please provide a valid fitness goal."}), 400
        data["goal"] = goal.strip()
        save_user_data(data)
        return jsonify({"message": "Goal updated successfully!", "goal": data["goal"]})
    except Exception as e:
        logging.error(f"Error setting goal: {e}")
        return jsonify({"error": "Failed to save goal. Please try again."}), 500

@app.route("/check-in", methods=["POST"])
def check_in():
    try:
        user_data = load_user_data()
        status = request.json.get("status") if request.json else None
        
        if not isinstance(status, str) or not status.strip():
            return jsonify({"error": "Please provide a valid check-in status."}), 400
        
        status = status.strip()
        user_data["check_ins"].append({
            "status": status,
            "date": json.dumps(None)  # Will be handled by frontend
        })
        
        # Update stats
        user_data["stats"]["completed_workouts"] += 1
        user_data["stats"]["current_streak"] += 1
        
        if not user_data.get("goal"):
            return jsonify({"error": "Please set a fitness goal first before checking in."}), 400

        prompt = f"""User goal: {user_data['goal']}
        
Current check-in: {status}

Recent workout history: {user_data['check_ins'][-3:] if len(user_data['check_ins']) > 1 else 'First workout'}

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

        user_data["history"].append({"check_in": status, "response": reply})
        save_user_data(user_data)

        return jsonify({"reply": reply, "stats": user_data["stats"]})
        
    except requests.exceptions.RequestException as e:
        logging.error(f"Network error calling OpenAI: {e}")
        return jsonify({"error": "Network error. Please check your internet connection and try again."}), 500
    except Exception as e:
        logging.error(f"Error in check-in: {e}")
        return jsonify({"error": "An unexpected error occurred. Please try again."}), 500

@app.route("/get-user-data")
def get_user_data():
    try:
        user_data = load_user_data()
        return jsonify(user_data)
    except Exception as e:
        logging.error(f"Error loading user data: {e}")
        return jsonify({"error": "Failed to load user data"}), 500

@app.route("/set-profile", methods=["POST"])
def set_profile():
    try:
        data = load_user_data()
        profile_data = request.json if request.json else {}
        
        # Validate required fields
        required_fields = ["name", "gender", "weight", "height", "date_of_birth", "experience", "primary_activity", "training_location"]
        for field in required_fields:
            if not profile_data.get(field, "").strip():
                return jsonify({"error": f"Please provide your {field.replace('_', ' ')}."}), 400
        
        # Update profile data
        data["profile"].update(profile_data)
        save_user_data(data)
        
        return jsonify({"message": "Profile created successfully!", "profile": data["profile"]})
    except Exception as e:
        logging.error(f"Error setting profile: {e}")
        return jsonify({"error": "Failed to save profile. Please try again."}), 500

@app.route("/clear-data", methods=["POST"])
def clear_data():
    try:
        initialize_user_data()
        return jsonify({"message": "Data cleared successfully"})
    except Exception as e:
        logging.error(f"Error clearing data: {e}")
        return jsonify({"error": "Failed to clear data"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
