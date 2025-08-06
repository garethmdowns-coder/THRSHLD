// THRSHLD App JavaScript

// Global state
let currentTab = 'today';
let isLoading = false;

// DOM Elements
const profileSetup = document.getElementById('profile-setup');
const profileForm = document.getElementById('profile-form');
const goalForm = document.getElementById('goal-form');
const goalInput = document.getElementById('goal-input');
const goalSetup = document.getElementById('goal-setup');
const goalDisplay = document.getElementById('goal-display');
const currentGoal = document.getElementById('current-goal');
const checkinCard = document.getElementById('checkin-card');
const checkinForm = document.getElementById('checkin-form');
const statusInput = document.getElementById('status-input');
const checkinBtn = document.getElementById('checkin-btn');
const workoutCard = document.getElementById('workout-card');
const workoutContent = document.getElementById('workout-content');
const startWorkoutBtn = document.getElementById('start-workout-btn');
const loadingModal = document.getElementById('loading-modal');
const errorToast = document.getElementById('error-toast');
const successToast = document.getElementById('success-toast');

// Initialize app
document.addEventListener('DOMContentLoaded', function() {
    initializeEventListeners();
    
    // Check if profile exists to determine app state
    fetch('/get-user-data')
        .then(response => response.json())
        .then(data => {
            if (data.profile && data.profile.name) {
                // Profile exists, show main app
                showMainApp();
                showTab('today');
                
                // Check if we have a goal and show appropriate UI
                const hasGoal = data.goal && data.goal.trim();
                if (!hasGoal) {
                    showGoalSetup();
                }
            } else {
                // No profile, stay in onboarding
                hideMainApp();
            }
        })
        .catch(error => {
            console.error('Error checking profile:', error);
            hideMainApp();
        });
});

function initializeEventListeners() {
    // Profile form submission
    if (profileForm) {
        profileForm.addEventListener('submit', handleProfileSubmission);
    }
    
    // Goals form submission
    const goalsForm = document.getElementById('goals-form');
    if (goalsForm) {
        goalsForm.addEventListener('submit', handleGoalsSubmission);
    }
    
    // Log workout button
    const logWorkoutBtn = document.getElementById('log-workout-btn');
    if (logWorkoutBtn) {
        logWorkoutBtn.addEventListener('click', showWorkoutDiary);
    }
    
    // Complete workout button
    const completeWorkoutBtn = document.getElementById('complete-workout-btn');
    if (completeWorkoutBtn) {
        completeWorkoutBtn.addEventListener('click', handleCompleteWorkout);
    }
    
    // Profile button in header
    const profileBtn = document.getElementById('profile-btn');
    if (profileBtn) {
        profileBtn.addEventListener('click', () => showTab('profile'));
    }
    
    // Edit profile button
    const editProfileBtn = document.getElementById('edit-profile-btn');
    if (editProfileBtn) {
        editProfileBtn.addEventListener('click', showEditProfile);
    }
    
    // Auto-resize textareas
    document.querySelectorAll('textarea').forEach(textarea => {
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = this.scrollHeight + 'px';
        });
    });
}

function handleCompleteWorkout() {
    // Update workout status
    const workoutStatus = document.getElementById('workout-status');
    if (workoutStatus) workoutStatus.textContent = 'Completed';
    
    // Return to Today tab
    showTab('today');
    showSuccess('Workout completed successfully!');
}



// Tab Management
function showTab(tabName) {
    // Make sure app UI is visible
    showMainApp();
    
    // Hide all tab contents
    hideAllPages();
    
    // Remove active class from all nav tabs
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.remove('active');
        tab.classList.add('text-thrshld-gray-medium');
        tab.classList.remove('text-thrshld-primary');
    });
    
    // Show selected tab content
    const selectedContent = document.getElementById(`${tabName}-content`);
    if (selectedContent) {
        selectedContent.style.display = 'block';
    }
    
    // Activate selected tab
    const selectedTab = document.getElementById(`tab-${tabName}`);
    if (selectedTab) {
        selectedTab.classList.add('active');
        selectedTab.classList.remove('text-thrshld-gray-medium');
        selectedTab.classList.add('text-thrshld-primary');
    }
    
    currentTab = tabName;
}

// Profile Management
async function handleProfileSubmission(event) {
    event.preventDefault();
    
    const profileData = {
        name: document.getElementById('name-input').value.trim(),
        age: document.getElementById('age-input').value,
        gender: document.getElementById('gender-input').value,
        experience: document.getElementById('experience-input').value,
        training_days: document.getElementById('training-days-input').value
    };
    
    // Basic validation
    if (!profileData.name) {
        showError('Please enter your name');
        return;
    }
    
    if (isLoading) return;
    
    try {
        setLoading(true);
        
        const response = await fetch('/set-profile', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(profileData)
        });
        
        const data = await response.json();
        
        if (response.ok) {
            // Check if we're editing or creating
            const title = document.querySelector('#profile-setup h1');
            if (title && title.textContent === 'Edit Profile') {
                // Return to profile tab after editing
                showTab('profile');
                showSuccess('Profile updated successfully!');
            } else {
                // New profile - continue to goals
                showGoalsPage();
                showSuccess('Profile created successfully!');
            }
        } else {
            showError(data.error || 'Failed to save profile');
        }
    } catch (error) {
        console.error('Profile submission error:', error);
        showError('Network error. Please check your connection and try again.');
    } finally {
        setLoading(false);
    }
}

// Goals Management
function handleGoalsSubmission(event) {
    event.preventDefault();
    
    const formData = new FormData(event.target);
    const goalsData = {
        workout_goal: formData.get('workout-goal'),
        compound_lifts: formData.getAll('compound-lifts'),
        include_running: formData.get('include-running') === 'on',
        include_conditioning: formData.get('include-conditioning') === 'on'
    };
    
    // Basic validation
    if (!goalsData.workout_goal) {
        showError('Please select a workout goal');
        return;
    }
    
    // Store goals locally for now
    localStorage.setItem('userGoals', JSON.stringify(goalsData));
    
    // Show holding page, then redirect to Today
    showHoldingPage();
    setTimeout(() => {
        showMainApp();
        showTab('today');
        showSuccess('Your programme is ready!');
    }, 3000);
}

function showGoalsPage() {
    if (profileSetup) profileSetup.style.display = 'none';
    const goalsContent = document.getElementById('goals-content');
    if (goalsContent) goalsContent.style.display = 'block';
}

function showHoldingPage() {
    const goalsContent = document.getElementById('goals-content');
    const holdingContent = document.getElementById('holding-content');
    if (goalsContent) goalsContent.style.display = 'none';
    if (holdingContent) holdingContent.style.display = 'block';
}

function showWorkoutDiary() {
    hideAllPages();
    const workoutDiary = document.getElementById('workout-diary-content');
    if (workoutDiary) workoutDiary.style.display = 'block';
    
    // Hide app navigation for full-screen experience
    const navigation = document.getElementById('app-navigation');
    const header = document.getElementById('app-header');
    if (navigation) navigation.style.display = 'none';
    if (header) header.style.display = 'none';
}

function hideAllPages() {
    const pages = ['profile-setup', 'goals-content', 'holding-content', 'today-content', 'progress-content', 'profile-content', 'workout-diary-content'];
    pages.forEach(pageId => {
        const page = document.getElementById(pageId);
        if (page) page.style.display = 'none';
    });
}

function showEditProfile() {
    // Show the profile setup form but with editing functionality
    hideAllPages();
    const profileSetup = document.getElementById('profile-setup');
    if (profileSetup) {
        profileSetup.style.display = 'block';
        
        // Show back button for editing
        const backBtn = document.getElementById('profile-back-btn');
        if (backBtn) backBtn.style.display = 'flex';
        
        // Change form title for editing
        const title = profileSetup.querySelector('h1');
        if (title) title.textContent = 'Edit Profile';
        
        // Change description
        const description = profileSetup.querySelector('p');
        if (description) description.textContent = 'Update your profile information';
        
        // Change button text
        const submitBtn = profileSetup.querySelector('button[type="submit"]');
        if (submitBtn) submitBtn.textContent = 'Save Changes';
        
        // Populate form with current data
        populateProfileForm();
        
        // Hide app navigation for full-screen editing
        const navigation = document.getElementById('app-navigation');
        const header = document.getElementById('app-header');
        if (navigation) navigation.style.display = 'none';
        if (header) header.style.display = 'none';
    }
}

function populateProfileForm() {
    // Get current profile data from the profile tab
    const profileName = document.getElementById('profile-name');
    const profileAge = document.getElementById('profile-age');
    const profileGender = document.getElementById('profile-gender');
    
    // Populate form fields
    const nameInput = document.getElementById('name-input');
    const ageInput = document.getElementById('age-input');
    const genderInput = document.getElementById('gender-input');
    
    if (profileName && nameInput) {
        nameInput.value = profileName.textContent.trim();
    }
    if (profileAge && ageInput) {
        const age = profileAge.textContent.trim();
        if (age !== '--') ageInput.value = age;
    }
    if (profileGender && genderInput) {
        const gender = profileGender.textContent.trim().toLowerCase();
        if (gender !== '--') genderInput.value = gender;
    }
}

function showMainApp() {
    const header = document.getElementById('app-header');
    const navigation = document.getElementById('app-navigation');
    const todayContent = document.getElementById('today-content');
    
    if (header) header.style.display = 'block';
    if (navigation) navigation.style.display = 'block';
    if (todayContent) todayContent.style.display = 'block';
    
    // Adjust main content padding when app UI is visible
    const main = document.querySelector('main');
    if (main) {
        main.classList.add('pb-24');
    }
}

function hideMainApp() {
    const header = document.getElementById('app-header');
    const navigation = document.getElementById('app-navigation');
    const todayContent = document.getElementById('today-content');
    
    if (header) header.style.display = 'none';
    if (navigation) navigation.style.display = 'none';
    if (todayContent) todayContent.style.display = 'none';
    
    // Remove padding when in onboarding
    const main = document.querySelector('main');
    if (main) {
        main.classList.remove('pb-24');
    }
}

// Goal Management
function showGoalSetup() {
    if (goalSetup) goalSetup.style.display = 'block';
    if (goalDisplay) goalDisplay.style.display = 'none';
    if (checkinCard) checkinCard.style.display = 'none';
}

function showGoalDisplay(goal) {
    if (currentGoal) currentGoal.textContent = goal;
    if (goalSetup) goalSetup.style.display = 'none';
    if (goalDisplay) goalDisplay.style.display = 'block';
    if (checkinCard) checkinCard.style.display = 'block';
}

function editGoal() {
    const currentGoalText = currentGoal ? currentGoal.textContent : '';
    if (goalInput) goalInput.value = currentGoalText;
    showGoalSetup();
}

async function handleGoalSubmission(event) {
    event.preventDefault();
    
    const goal = goalInput.value.trim();
    if (!goal) {
        showError('Please enter a fitness goal');
        return;
    }
    
    if (isLoading) return;
    
    try {
        setLoading(true);
        
        const response = await fetch('/set-goal', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ goal: goal })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            showGoalDisplay(data.goal);
            showSuccess('Goal updated successfully!');
            goalInput.value = '';
        } else {
            showError(data.error || 'Failed to save goal');
        }
    } catch (error) {
        console.error('Goal submission error:', error);
        showError('Network error. Please check your connection and try again.');
    } finally {
        setLoading(false);
    }
}

// Check-in Management
async function handleCheckinSubmission(event) {
    event.preventDefault();
    
    const status = statusInput.value.trim();
    if (!status) {
        showError('Please share how you\'re feeling today');
        return;
    }
    
    if (isLoading) return;
    
    try {
        setLoading(true);
        checkinBtn.textContent = 'Creating Workout...';
        
        const response = await fetch('/check-in', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ status: status })
        });
        
        const data = await response.json();
        
        if (response.ok) {
            displayWorkout(data.reply);
            updateStats(data.stats);
            statusInput.value = '';
            showSuccess('Your personalized workout is ready!');
        } else {
            showError(data.error || 'Failed to generate workout');
        }
    } catch (error) {
        console.error('Check-in error:', error);
        showError('Network error. Please check your connection and try again.');
    } finally {
        setLoading(false);
        checkinBtn.textContent = 'Get My Workout';
    }
}

function displayWorkout(workoutText) {
    if (workoutContent) {
        // Format the workout text for better display
        let formattedWorkout = workoutText
            .replace(/\n\n/g, '</p><p>')
            .replace(/\n/g, '<br>')
            .replace(/^\d+\.\s*/gm, '<strong>$&</strong>')
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>');
        
        // Wrap in paragraphs if not already
        if (!formattedWorkout.includes('<p>')) {
            formattedWorkout = '<p>' + formattedWorkout + '</p>';
        }
        
        workoutContent.innerHTML = formattedWorkout;
    }
    
    if (workoutCard) {
        workoutCard.style.display = 'block';
        workoutCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}

function updateStats(stats) {
    const completedWorkouts = document.getElementById('completed-workouts');
    const currentStreak = document.getElementById('current-streak');
    
    if (completedWorkouts && stats.completed_workouts !== undefined) {
        completedWorkouts.textContent = stats.completed_workouts;
    }
    
    if (currentStreak && stats.current_streak !== undefined) {
        currentStreak.textContent = stats.current_streak;
    }
}

function handleStartWorkout() {
    // For MVP, this could expand workout details or start a timer
    showSuccess('Workout started! Track your progress and stay focused.');
    
    // Could implement workout timer, exercise tracking, etc.
    startWorkoutBtn.textContent = 'Workout in Progress...';
    startWorkoutBtn.style.backgroundColor = '#22c55e';
    
    // Reset button after 3 seconds (for demo purposes)
    setTimeout(() => {
        startWorkoutBtn.textContent = 'Start Workout';
        startWorkoutBtn.style.backgroundColor = '';
    }, 3000);
}

// UI Helpers
function setLoading(loading) {
    isLoading = loading;
    if (loadingModal) {
        loadingModal.style.display = loading ? 'flex' : 'none';
    }
}

function showError(message) {
    const errorMessage = document.getElementById('error-message');
    if (errorMessage) errorMessage.textContent = message;
    
    if (errorToast) {
        errorToast.classList.add('toast-show');
        setTimeout(() => {
            errorToast.classList.remove('toast-show');
        }, 4000);
    }
}

function showSuccess(message) {
    const successMessage = document.getElementById('success-message');
    if (successMessage) successMessage.textContent = message;
    
    if (successToast) {
        successToast.classList.add('toast-show');
        setTimeout(() => {
            successToast.classList.remove('toast-show');
        }, 3000);
    }
}

// Utility Functions
function formatWorkoutHistory() {
    // This could be used to format and display workout history
    fetch('/get-user-data')
        .then(response => response.json())
        .then(data => {
            const historyContainer = document.getElementById('workout-history');
            if (historyContainer && data.history) {
                // Update history display
                console.log('History loaded:', data.history);
            }
        })
        .catch(error => {
            console.error('Error loading user data:', error);
        });
}

// Keyboard shortcuts
document.addEventListener('keydown', function(event) {
    // Quick navigation with keyboard
    if (event.altKey) {
        switch(event.key) {
            case '1':
                event.preventDefault();
                showTab('today');
                break;
            case '2':
                event.preventDefault();
                showTab('progress');
                break;
            case '3':
                event.preventDefault();
                showTab('recovery');
                break;
            case '4':
                event.preventDefault();
                showTab('library');
                break;
        }
    }
});

// Handle offline/online status
window.addEventListener('online', function() {
    showSuccess('Connection restored');
});

window.addEventListener('offline', function() {
    showError('You are offline. Some features may not work.');
});

// Progressive Web App support (basic)
if ('serviceWorker' in navigator) {
    window.addEventListener('load', function() {
        // Service worker could be added for offline functionality
        console.log('THRSHLD app loaded successfully');
    });
}

// Export functions for testing or external use
window.THRSHLD = {
    showTab,
    editGoal,
    setLoading,
    showError,
    showSuccess
};
