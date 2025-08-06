// THRSHLD App JavaScript

// Global state
let currentTab = 'today';
let isLoading = false;

// DOM Elements
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
    showTab('today');
    
    // Check if we have a goal and show appropriate UI
    const hasGoal = currentGoal && currentGoal.textContent.trim();
    if (!hasGoal) {
        showGoalSetup();
    }
});

function initializeEventListeners() {
    // Goal form submission
    if (goalForm) {
        goalForm.addEventListener('submit', handleGoalSubmission);
    }
    
    // Check-in form submission
    if (checkinForm) {
        checkinForm.addEventListener('submit', handleCheckinSubmission);
    }
    
    // Start workout button
    if (startWorkoutBtn) {
        startWorkoutBtn.addEventListener('click', handleStartWorkout);
    }
    
    // Auto-resize textareas
    document.querySelectorAll('textarea').forEach(textarea => {
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = this.scrollHeight + 'px';
        });
    });
}

// Tab Management
function showTab(tabName) {
    // Hide all tab content
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.add('hidden');
    });
    
    // Remove active class from all nav tabs
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.remove('active');
        tab.classList.add('text-thrshld-gray-medium');
        tab.classList.remove('text-thrshld-primary');
    });
    
    // Show selected tab content
    const selectedContent = document.getElementById(tabName + '-content');
    if (selectedContent) {
        selectedContent.classList.remove('hidden');
    }
    
    // Activate selected nav tab
    const selectedTab = document.getElementById('tab-' + tabName);
    if (selectedTab) {
        selectedTab.classList.add('active');
        selectedTab.classList.remove('text-thrshld-gray-medium');
        selectedTab.classList.add('text-thrshld-primary');
    }
    
    currentTab = tabName;
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
