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
    console.log('THRSHLD app loaded successfully');
    
    initializeEventListeners();
    
    // Load saved goals if they exist
    const savedGoals = localStorage.getItem('userGoals');
    if (savedGoals) {
        try {
            const goalsData = JSON.parse(savedGoals);
            updateGoalsDisplay(goalsData);
        } catch (e) {
            console.error('Error loading saved goals:', e);
        }
    }
    
    // Try to load progress data, but don't fail if it's not available
    try {
        loadProgressData();
    } catch (error) {
        console.log('Progress data not available:', error);
    }
    
    // Check if profile setup is visible (indicates new user)
    const profileSetup = document.getElementById('profile-setup');
    if (profileSetup && profileSetup.style.display !== 'none') {
        // Profile setup is visible, stay in onboarding mode
        hideMainApp();
    } else {
        // Profile setup is hidden, user has profile - show main app
        showMainApp();
        showTab('today');
        
        // Try to load user data, but don't block if it fails
        fetch('/get-user-data', {
            credentials: 'same-origin'
        })
        .then(response => {
            if (response.ok) {
                return response.json();
            }
            throw new Error('Failed to load user data');
        })
        .then(data => {
            console.log('User data loaded:', data);
            // Update UI with loaded data if available
            if (data.profile) {
                updateProfileDisplay(data.profile);
            }
        })
        .catch(error => {
            console.log('User data not available, using defaults:', error);
            // Continue with default UI - don't hide the app
        });
    }
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
    
    // Edit goals button
    const editGoalsBtn = document.getElementById('edit-goals-btn');
    if (editGoalsBtn) {
        editGoalsBtn.addEventListener('click', showEditGoals);
    }
    
    // Profile photo upload
    const profilePhoto = document.getElementById('profile-photo');
    if (profilePhoto) {
        profilePhoto.addEventListener('change', handleProfilePhotoUpload);
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
                // Update profile display with new data
                updateProfileDisplay(profileData);
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
    
    // Store goals locally and update display
    localStorage.setItem('userGoals', JSON.stringify(goalsData));
    updateGoalsDisplay(goalsData);
    
    // Check if we're editing or creating
    const title = document.querySelector('#goals-content h1');
    if (title && title.textContent === 'Update Your Goals') {
        // Return to profile tab after editing
        showTab('profile');
        showSuccess('Goals updated! Your new programme is being prepared.');
    } else {
        // Show holding page, then redirect to Today
        showHoldingPage();
        setTimeout(() => {
            showMainApp();
            showTab('today');
            showSuccess('Your programme is ready!');
        }, 3000);
    }
}

function updateGoalsDisplay(goalsData) {
    const goalsDisplay = document.getElementById('current-goals-display');
    if (goalsDisplay) {
        goalsDisplay.innerHTML = '';
        
        // Add primary goal
        if (goalsData.workout_goal) {
            const goalText = goalsData.workout_goal.replace('-', ' ').replace(/\b\w/g, l => l.toUpperCase());
            const goalSpan = document.createElement('span');
            goalSpan.className = 'px-3 py-1 bg-thrshld-accent text-white text-sm rounded-full';
            goalSpan.textContent = goalText;
            goalsDisplay.appendChild(goalSpan);
        }
        
        // Add compound lifts
        goalsData.compound_lifts.forEach(lift => {
            const liftText = lift.replace('-', ' ').replace(/\b\w/g, l => l.toUpperCase());
            const liftSpan = document.createElement('span');
            liftSpan.className = 'px-3 py-1 bg-thrshld-gray-dark text-thrshld-primary text-sm rounded-full';
            liftSpan.textContent = liftText;
            goalsDisplay.appendChild(liftSpan);
        });
        
        // Add training preferences
        if (goalsData.include_running) {
            const runningSpan = document.createElement('span');
            runningSpan.className = 'px-3 py-1 bg-thrshld-gray-dark text-thrshld-primary text-sm rounded-full';
            runningSpan.textContent = 'Running';
            goalsDisplay.appendChild(runningSpan);
        }
        
        if (goalsData.include_conditioning) {
            const conditioningSpan = document.createElement('span');
            conditioningSpan.className = 'px-3 py-1 bg-thrshld-gray-dark text-thrshld-primary text-sm rounded-full';
            conditioningSpan.textContent = 'Conditioning';
            goalsDisplay.appendChild(conditioningSpan);
        }
    }
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
    const profileDetails = document.getElementById('profile-details');
    
    // Populate form fields
    const nameInput = document.getElementById('name-input');
    const ageInput = document.getElementById('age-input');
    const genderInput = document.getElementById('gender-input');
    const experienceInput = document.getElementById('experience-input');
    const trainingDaysInput = document.getElementById('training-days-input');
    
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
    
    // Parse experience and training days from profile details
    if (profileDetails && experienceInput && trainingDaysInput) {
        const details = profileDetails.textContent.trim();
        const parts = details.split(' • ');
        if (parts.length >= 2) {
            const experience = parts[0].toLowerCase();
            const trainingDays = parts[1].replace(' days/week', '');
            
            experienceInput.value = experience;
            if (trainingDays !== '0') trainingDaysInput.value = trainingDays;
        }
    }
}

function updateProfileDisplay(profileData) {
    // Update profile display elements
    const profileName = document.getElementById('profile-name');
    const profileAge = document.getElementById('profile-age');
    const profileGender = document.getElementById('profile-gender');
    const profileDetails = document.getElementById('profile-details');
    
    if (profileName) profileName.textContent = profileData.name || 'User';
    if (profileAge) profileAge.textContent = profileData.age || '--';
    if (profileGender) profileGender.textContent = profileData.gender ? profileData.gender.charAt(0).toUpperCase() + profileData.gender.slice(1) : '--';
    if (profileDetails) {
        const experience = profileData.experience ? profileData.experience.charAt(0).toUpperCase() + profileData.experience.slice(1) : 'New User';
        const trainingDays = profileData.training_days || '0';
        profileDetails.textContent = `${experience} • ${trainingDays} days/week`;
    }
}

function showEditGoals() {
    // Show confirmation dialog
    if (confirm('Consistency is key to progress and this will start a brand new programme - are you sure you want to proceed?')) {
        hideAllPages();
        const goalsContent = document.getElementById('goals-content');
        if (goalsContent) {
            goalsContent.style.display = 'block';
            
            // Hide app navigation for full-screen editing
            const navigation = document.getElementById('app-navigation');
            const header = document.getElementById('app-header');
            if (navigation) navigation.style.display = 'none';
            if (header) header.style.display = 'none';
            
            // Update form title for editing
            const title = goalsContent.querySelector('h1');
            if (title) title.textContent = 'Update Your Goals';
            
            // Update button text
            const submitBtn = goalsContent.querySelector('button[type="submit"]');
            if (submitBtn) submitBtn.textContent = 'Update Programme';
        }
    }
}

function handleProfilePhotoUpload(event) {
    const file = event.target.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = function(e) {
            // Update the profile photo display
            const photoBtn = document.querySelector('#profile-photo').parentNode.querySelector('button');
            if (photoBtn) {
                photoBtn.innerHTML = `<img src="${e.target.result}" alt="Profile" class="w-full h-full object-cover rounded-full">`;
            }
            
            // Also update profile tab photo if it exists
            const profileTabPhoto = document.querySelector('#profile-content .w-24.h-24');
            if (profileTabPhoto) {
                profileTabPhoto.innerHTML = `<img src="${e.target.result}" alt="Profile" class="w-full h-full object-cover rounded-full">`;
            }
        };
        reader.readAsDataURL(file);
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

// Progress Analytics Functions
function showProgressTab(tabName) {
    // Update tab buttons
    document.querySelectorAll('[id^="progress-tab-"]').forEach(btn => {
        btn.classList.remove('bg-thrshld-accent', 'text-thrshld-primary');
        btn.classList.add('text-thrshld-gray-medium');
    });
    document.getElementById(`progress-tab-${tabName}`).classList.add('bg-thrshld-accent', 'text-thrshld-primary');
    document.getElementById(`progress-tab-${tabName}`).classList.remove('text-thrshld-gray-medium');
    
    // Show/hide content
    document.querySelectorAll('.progress-tab-content').forEach(content => {
        content.classList.add('hidden');
    });
    document.getElementById(`progress-${tabName}`).classList.remove('hidden');
    
    // Load data for specific tab
    loadProgressTabData(tabName);
}

function loadProgressData() {
    // Load overview stats with fallback
    fetch('/api/progress/overview', {
        credentials: 'same-origin'
    })
        .then(response => {
            if (response.ok) {
                return response.json();
            }
            throw new Error('Progress data not available');
        })
        .then(data => {
            if (data.stats) {
                document.getElementById('total-workouts').textContent = data.stats.total_workouts || 0;
                document.getElementById('current-streak').textContent = data.stats.current_streak || 0;
                document.getElementById('personal-records').textContent = data.stats.personal_records || 0;
                document.getElementById('consistency').textContent = Math.round(data.workout_consistency || 0) + '%';
            }
        })
        .catch(error => {
            console.log('Progress data not available, using defaults:', error);
            // Set default values
            const totalWorkouts = document.getElementById('total-workouts');
            const currentStreak = document.getElementById('current-streak');
            const personalRecords = document.getElementById('personal-records');
            const consistency = document.getElementById('consistency');
            
            if (totalWorkouts) totalWorkouts.textContent = '0';
            if (currentStreak) currentStreak.textContent = '0';
            if (personalRecords) personalRecords.textContent = '0';
            if (consistency) consistency.textContent = '0%';
        });
}

function updateProfileDisplay(profile) {
    // Update profile display elements if they exist
    const profileName = document.getElementById('profile-name');
    const profileAge = document.getElementById('profile-age');
    const profileGender = document.getElementById('profile-gender');
    
    if (profileName && profile.name) {
        profileName.textContent = profile.name;
    }
    if (profileAge && profile.age) {
        profileAge.textContent = profile.age;
    }
    if (profileGender && profile.gender) {
        profileGender.textContent = profile.gender.charAt(0).toUpperCase() + profile.gender.slice(1);
    }
}

function loadProgressTabData(tabName) {
    switch(tabName) {
        case 'overview':
            loadOverviewData();
            break;
        case 'strength':
            loadStrengthData();
            break;
        case 'body':
            loadBodyMetricsData();
            break;
        case 'wellness':
            loadWellnessData();
            break;
    }
}

function loadOverviewData() {
    fetch('/api/progress/overview')
        .then(response => response.json())
        .then(data => {
            if (data.weekly_workout_data) {
                createWeeklyChart(data.weekly_workout_data);
            }
            if (data.recent_workouts) {
                populateRecentWorkouts(data.recent_workouts);
            }
        })
        .catch(error => console.error('Error loading overview data:', error));
}

function createWeeklyChart(weeklyData) {
    const ctx = document.getElementById('weekly-chart');
    if (!ctx) return;
    
    const weeks = Object.keys(weeklyData).sort();
    const workoutCounts = weeks.map(week => weeklyData[week]);
    
    new Chart(ctx, {
        type: 'bar',
        data: {
            labels: weeks.map(week => `Week ${week.split('-W')[1]}`),
            datasets: [{
                label: 'Workouts',
                data: workoutCounts,
                backgroundColor: '#3b82f6',
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: { display: false }
            },
            scales: {
                y: { beginAtZero: true }
            }
        }
    });
}

function populateRecentWorkouts(workouts) {
    const container = document.getElementById('recent-workouts-list');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (workouts.length === 0) {
        container.innerHTML = '<div class="text-center py-8 text-thrshld-gray-medium">No recent workouts found</div>';
        return;
    }
    
    workouts.forEach(workout => {
        const workoutElement = document.createElement('div');
        workoutElement.className = 'p-3 bg-gray-800 rounded-lg';
        workoutElement.innerHTML = `
            <div class="flex justify-between items-center">
                <div>
                    <div class="text-white font-medium">${workout.workout_name}</div>
                    <div class="text-gray-400 text-sm">${workout.date_completed}</div>
                </div>
                <div class="text-right">
                    <div class="text-white">${workout.duration_minutes || '--'} min</div>
                    <div class="text-gray-400 text-sm">${workout.workout_type || 'Workout'}</div>
                </div>
            </div>
        `;
        container.appendChild(workoutElement);
    });
}

// Add progress data loading to main initialization
document.addEventListener('DOMContentLoaded', function() {
    loadProgressData();
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
