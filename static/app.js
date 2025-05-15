const workoutSelect = document.getElementById('workout-select');
const repsSelect = document.getElementById('reps-select');
const strictnessSelect = document.getElementById('strictness-select');
const goButton = document.getElementById('go-button');
const canvas = document.getElementById('videoCanvas');
const ctx = canvas.getContext('2d');
const historyDiv = document.getElementById('history');
const statusEl = document.getElementById('status');


// Audio objects for sound effects
const repSound = new Audio();
const victorySound = new Audio();

// Debug flag to monitor audio playback
const debugAudio = true;

// Track the previous status to avoid repeating animations
let previousStatus = null;

// Track the previous rep count to detect when a new rep is completed
let previousRepCount = 0;


// Connect to WebSocket
const ws = new WebSocket(`ws://${window.location.host}/ws`);
ws.binaryType = "arraybuffer";

// Handle WebSocket events
ws.onmessage = (event) => {
    if (typeof event.data === "string") {
        const data = JSON.parse(event.data);
        if (data.type === 'data') {
            console.log('Data received:');
            updateStatus(data.message, data.status);
        } else if (data.type === 'history') {
            console.log('History update received:');
            updateHistory(data.message);
        } else if (data.type === 'feedback') {
            console.log('Feedback received:');
            addFeedbackToHistory(data.message);
        }
    } else {
        const imageBlob = new Blob([event.data], { type: "image/jpeg" });
        const imageURL = URL.createObjectURL(imageBlob);
        const img = new Image();
        img.onload = () => {
            canvas.width = img.width;
            canvas.height = img.height;
            ctx.drawImage(img, 0, 0);
            URL.revokeObjectURL(imageURL);
        };
        img.src = imageURL;
    }
};

function updateStatus(message, status) {
    statusEl.style.display = 'block';
    
    // Remove any existing animation if status is changing
    if (previousStatus !== status) {
        statusEl.style.animation = '';
    }
    
    // Determine message type and set appropriate styling
    if (status === 'completed') {
        statusEl.style.backgroundColor = 'var(--success)';
        statusEl.style.color = 'white';
        statusEl.innerHTML = `<i class="fas fa-check-circle"></i> ${message}`;
        
        // Add celebratory animation only when transitioning to completed state
        if (previousStatus !== 'completed') {
            statusEl.style.animation = 'pulse 2s';
            
            // Play victory sound when the workout is completed
            console.log('Trying to play victory sound...');
            victorySound.play().catch(error => {
                console.error('Error playing victory sound:', error);
            });
            
            // Reset the start button to its original state
            goButton.innerHTML = '<i class="fas fa-play"></i> Start New Workout';
            goButton.style.backgroundColor = 'var(--success)';
            
            // Reset button style after a brief delay
            setTimeout(() => {
                goButton.style.backgroundColor = 'var(--primary)';
            }, 3000);
        }
    } else if (message.includes('Error') || message.includes('failed')) {
        statusEl.style.backgroundColor = 'var(--danger)';
        statusEl.style.color = 'white';
        statusEl.innerHTML = `<i class="fas fa-exclamation-circle"></i> ${message}`;
    } else if (message.includes('Ready') || message.includes('starting')) {
        statusEl.style.backgroundColor = 'var(--primary)';
        statusEl.style.color = 'white';
        statusEl.innerHTML = `<i class="fas fa-play-circle"></i> ${message}`;
    } else if (status === 'in_progress') {
        statusEl.style.backgroundColor = 'var(--warning)';
        statusEl.style.color = 'white';
        statusEl.innerHTML = `<i class="fas fa-sync"></i> ${message}`;
    } else {
        statusEl.style.backgroundColor = 'var(--light)';
        statusEl.style.color = 'var(--dark)';
        statusEl.textContent = message;
    }
    
    // Update the counter display and play sound when rep is completed
    const counterEl = document.querySelector('.workout-counter');
    if (counterEl) {
        // Extract numbers from the message if available
        const match = message.match(/(\d+) out of (\d+)/);
        if (match) {
            const [_, current, total] = match;
            const currentRepCount = parseInt(current, 10);
            
            // Check if the rep count has changed by testing the displayed text
            const oldRepDisplayed = counterEl.textContent.trim().split('/')[0].trim();
            const oldRepCount = parseInt(oldRepDisplayed, 10) || 0;
            
            console.log(`Rep tracking: old=${oldRepCount}, new=${currentRepCount}, previous=${previousRepCount}`);
            
            // Update the display with the new rep count
            counterEl.innerHTML = `${currentRepCount} / ${total}`;
            
            // Play sound if the rep count has increased (more reliable than comparing with previousRepCount)
            if (currentRepCount > oldRepCount && currentRepCount > 0) {
                console.log(`Rep completed! ${currentRepCount}/${total}. Playing sound...`);
                // Play rep completion sound
                repSound.currentTime = 0; // Reset sound to start
                repSound.play().catch(error => {
                    console.error('Error playing rep completion sound:', error);
                });
            }
            
            // Update previous rep count
            previousRepCount = currentRepCount;
            
            // Set green background when workout is finished (using status flag)
            if (status === 'completed') { 
                counterEl.style.backgroundColor = 'var(--success)';
            } else {
                counterEl.style.backgroundColor = 'rgba(0, 0, 0, 0.7)';
            }
        } else if (status === 'completed') {
            // Set success style when workout is completed
            counterEl.style.backgroundColor = 'var(--success)';
        }
    }
    
    // Update the pose indicator
    const poseEl = document.querySelector('.workout-pose-indicator');
    if (poseEl) {
        if (message.includes('form:')) {
            // Extract form tips from message
            const formTip = message.split('form:')[1].trim();
            poseEl.innerHTML = formTip;
            poseEl.style.display = 'block';
        } else {
            poseEl.style.display = 'none';
        }
    }
    
    // Store the current status for the next update
    previousStatus = status;
}

// Track the workout history internally
let workoutHistoryList = [];

function updateHistory(rawHistoryHtml) {
    // The server sends the history as text with <br> tags
    const historyEntries = rawHistoryHtml.split('<br>').filter(entry => entry.trim() !== "");
    
    // Check if we have new entries to add
    let newEntriesAdded = false;
    
    // If the number of entries has changed, we need to update our display
    if (historyEntries.length !== workoutHistoryList.length) {
        // Find new entries by looking for entries not in our current list
        for (let i = 0; i < historyEntries.length; i++) {
            if (i >= workoutHistoryList.length || historyEntries[i] !== workoutHistoryList[i]) {
                // Add new entry to our history list
                if (i >= workoutHistoryList.length) {
                    workoutHistoryList.push(historyEntries[i]);
                } else {
                    workoutHistoryList[i] = historyEntries[i];
                }
                newEntriesAdded = true;
            }
        }
        
        // If list was shortened (shouldn't happen but just in case)
        if (historyEntries.length < workoutHistoryList.length) {
            workoutHistoryList = historyEntries.slice();
            newEntriesAdded = true;
        }
    }
    
    // Only rebuild the display if we have changes
    if (newEntriesAdded || historyDiv.children.length === 0) {
        // Clear current history display
        historyDiv.innerHTML = '';
        
        // If we have no entries, show the empty state
        if (workoutHistoryList.length === 0) {
            historyDiv.innerHTML = `
                <div style="text-align: center; padding: 2rem; color: var(--gray);">
                    <i class="fas fa-history" style="font-size: 2rem; margin-bottom: 1rem;"></i>
                    <p>No workout history yet</p>
                </div>
            `;
            return;
        }
        
        // Create and append each history entry
        workoutHistoryList.forEach((entryText, index) => {
            // Create enhanced history entry
            const entryDiv = document.createElement('div');
            entryDiv.className = 'workout-entry';
            entryDiv.style.marginBottom = '10px';
            entryDiv.style.padding = '10px';
            entryDiv.style.backgroundColor = '#f5f5f5';
            entryDiv.style.borderRadius = '8px';
            entryDiv.style.boxShadow = '0 2px 4px rgba(0,0,0,0.05)';
            entryDiv.style.transition = 'transform 0.2s';
            
            // Extract workout type and reps
            let workoutType = 'Workout';
            let workoutReps = '0';
            
            if (entryText.includes('push-ups')) workoutType = 'Push-ups';
            else if (entryText.includes('abs')) workoutType = 'Abs';
            else if (entryText.includes('squats')) workoutType = 'Squats';
            
            // Extract rep count if available
            const repsMatch = entryText.match(/(\d+)\s*reps/i);
            if (repsMatch) {
                workoutReps = repsMatch[1];
            }
            
            // Create formatted entry with rep count in a bubble
            entryDiv.innerHTML = `
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h3 style="margin: 0; color: var(--primary); font-size: 1rem;">${workoutType}</h3>
                    <span class="workout-badge" style="background-color: var(--primary); color: white; padding: 2px 8px; border-radius: 12px; font-size: 0.8rem; font-weight: bold;">${workoutReps} reps</span>
                </div>
            `;
            
            // Add a subtle hover effect
            entryDiv.addEventListener('mouseenter', () => {
                entryDiv.style.transform = 'translateY(-2px)';
                entryDiv.style.boxShadow = '0 4px 8px rgba(0,0,0,0.1)';
            });
            
            entryDiv.addEventListener('mouseleave', () => {
                entryDiv.style.transform = 'translateY(0)';
                entryDiv.style.boxShadow = '0 2px 4px rgba(0,0,0,0.05)';
            });
            
            // Apply animation for new entries (only the most recent one)
            if (index === workoutHistoryList.length - 1 && newEntriesAdded) {
                entryDiv.style.opacity = '0';
                entryDiv.style.transform = 'translateY(10px)';
                entryDiv.style.transition = 'opacity 0.3s ease, transform 0.3s ease, box-shadow 0.2s';
                
                // Add to DOM
                historyDiv.insertBefore(entryDiv, historyDiv.firstChild);
                
                // Trigger animation
                setTimeout(() => {
                    entryDiv.style.opacity = '1';
                    entryDiv.style.transform = 'translateY(0)';
                    
                    // Remove transition after animation completes to prevent further bouncing
                    // but keep the hover transitions
                    setTimeout(() => {
                        entryDiv.style.transition = 'transform 0.2s, box-shadow 0.2s';
                    }, 300);
                }, 10);
            } else {
                // Add older entries without animation
                historyDiv.appendChild(entryDiv);
            }
        });
    }
}

// --- FEEDBACK SECTION CREATION ---
// Ensure feedback section exists under history section
function ensureFeedbackSection() {
    let feedbackSection = document.getElementById('feedback-section');
    if (!feedbackSection) {
        feedbackSection = document.createElement('div');
        feedbackSection.id = 'feedback-section';
        feedbackSection.innerHTML = `
            <h2 style="font-size: 1.5rem; margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 2px solid var(--light);">Feedback</h2>
            <div id="feedback-list">
                <div id="feedback-empty" style="text-align: center; color: var(--gray); padding: 2rem 0;">
                    <i class="fas fa-comment-dots" style="font-size: 2rem; margin-bottom: 1rem;"></i>
                    <p>No feedback yet. Complete a workout to receive feedback!</p>
                </div>
            </div>
        `;
        // Insert after historyDiv
        if (historyDiv && historyDiv.parentNode) {
            historyDiv.parentNode.insertBefore(feedbackSection, historyDiv.nextSibling);
        }
    }
}

function addFeedbackToHistory(feedbackHtml) {
    ensureFeedbackSection();
    const feedbackList = document.getElementById('feedback-list');
    const feedbackEmpty = document.getElementById('feedback-empty');
    if (!feedbackList) return;
    // If feedbackHtml is empty, show the empty state and return
    if (!feedbackHtml || feedbackHtml.trim() === "") {
        if (feedbackEmpty) feedbackEmpty.style.display = 'block';
        // Remove any previous feedback
        const prev = document.getElementById('feedback-static');
        if (prev) prev.remove();
        return;
    }
    // Hide the empty state if present
    if (feedbackEmpty) feedbackEmpty.style.display = 'none';
    // Check if feedback is already displayed and unchanged (compare raw HTML, not innerHTML)
    let prev = document.getElementById('feedback-static');
    if (prev) {
        // Store the last feedbackHtml as a property for static comparison
        if (prev._lastFeedbackHtml === feedbackHtml) {
            // No change, do nothing
            return;
        } else {
            // Update HTML and animate bounce
            const prevText = prev.querySelector('.feedback-text');
            if (prevText) prevText.innerHTML = feedbackHtml;
            prev._lastFeedbackHtml = feedbackHtml;
            prev.style.animation = 'feedbackBounce 0.4s';
            prev.addEventListener('animationend', () => {
                prev.style.animation = '';
            }, { once: true });
            return;
        }
    }
    // Remove any previous feedback (shouldn't be needed, but for safety)
    if (prev) prev.remove();
    // Create static feedback entry
    const entryDiv = document.createElement('div');
    entryDiv.id = 'feedback-static';
    entryDiv.className = 'workout-entry';
    entryDiv.style.backgroundColor = 'var(--light)';
    entryDiv.style.color = 'var(--dark)';
    entryDiv.style.marginBottom = '10px';
    entryDiv.style.padding = '10px';
    entryDiv.style.borderRadius = '8px';
    entryDiv.style.boxShadow = '0 2px 4px rgba(0,0,0,0.08)';
    entryDiv.style.transition = 'transform 0.2s';
    entryDiv._lastFeedbackHtml = feedbackHtml;
    // Insert HTML directly (already sanitized/converted on backend)
    entryDiv.innerHTML = `
        <div class="feedback-text" style="padding:0 font-size=0.875em;">
            ${feedbackHtml}
        </div>
    `;

    feedbackList.appendChild(entryDiv);
    entryDiv.style.opacity = '0';
    entryDiv.style.transform = 'translateY(10px)';
    setTimeout(function() {
        entryDiv.style.opacity = '1';
        entryDiv.style.transform = 'translateY(0)';
    }, 10);
}

// Add feedback bounce animation to the page
(function addFeedbackBounceStyle() {
    const style = document.createElement('style');
    style.textContent = `
        @keyframes feedbackBounce {
            0% { transform: scale(1); }
            30% { transform: scale(1.08); }
            60% { transform: scale(0.97); }
            100% { transform: scale(1); }
        }
    `;
    document.head.appendChild(style);
})();

ws.onclose = () => {
    console.log("WebSocket disconnected");
    updateStatus("Connection lost. Please refresh the page.");
};

ws.onerror = (error) => {
    console.error("WebSocket error:", error);
    updateStatus("Connection error. Please refresh the page.");
};

// Initialize UI components
function initUI() {
    // Add keyframe animations
    const style = document.createElement('style');
    style.textContent = `
        @keyframes pulse {
            0% { transform: scale(1); }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); }
        }
        
        .video-container {
            position: relative;
        }
        
        .workout-counter {
            display: none !important; /* Force hiding the workout counter */
            position: absolute;
            top: 20px;
            right: 20px;
            background-color: rgba(0, 0, 0, 0.7);
            color: white;
            padding: 10px 15px;
            border-radius: 30px;
            font-size: 1.2rem;
            font-weight: bold;
            z-index: 10;
        }
        
        .workout-pose-indicator {
            position: absolute;
            bottom: 20px;
            left: 50%;
            transform: translateX(-50%);
            background-color: rgba(0, 0, 0, 0.7);
            color: white;
            padding: 10px 20px;
            border-radius: 30px;
            font-size: 1rem;
            z-index: 10;
            display: none;
        }
    `;
    document.head.appendChild(style);
    
    
    // Create workout counter (hidden) and pose indicator elements if they don't exist
    const videoContainer = document.querySelector('.video-container');
    if (videoContainer) {
        // Create hidden workout counter for tracking reps and playing sounds
        if (!document.querySelector('.workout-counter')) {
            const counterElement = document.createElement('div');
            counterElement.className = 'workout-counter';
            counterElement.textContent = '0 / 0';
            counterElement.style.display = 'none';
            videoContainer.appendChild(counterElement);
            console.log('Created hidden workout counter element for tracking reps');
        }
        
        // Create pose indicator
        if (!document.querySelector('.workout-pose-indicator')) {
            const poseElement = document.createElement('div');
            poseElement.className = 'workout-pose-indicator';
            poseElement.textContent = 'Checking form...';
            videoContainer.appendChild(poseElement);
            console.log('Created pose indicator element');
        }
    } else {
        console.error('Video container not found, cannot create workout UI elements');
    }
    
    // Initialize sound effects
    repSound.src = 'static/sounds/rep-complete.mp3';
    victorySound.src = 'static/sounds/victory.mp3'; // Updated to a "TEEEEEET" buzzer sound
    
    // Add audio loading event listeners for debugging
    repSound.addEventListener('canplaythrough', () => {
        console.log('Rep sound loaded successfully');
    });
    
    victorySound.addEventListener('canplaythrough', () => {
        console.log('Victory sound loaded successfully');
    });
    
    repSound.addEventListener('error', (e) => {
        console.error('Error loading rep sound:', e);
    });
    
    victorySound.addEventListener('error', (e) => {
        console.error('Error loading victory sound:', e);
    });
    
    // Test sound playback (uncomment to test)
    // setTimeout(() => {
    //     console.log('Testing rep sound...');
    //     repSound.play().catch(e => console.error('Error playing rep sound:', e));
    // }, 2000);
    
    // Setup UI event listeners for visual effects
    goButton.addEventListener('mouseenter', () => {
        goButton.style.transform = 'translateY(-3px)';
    });
    
    goButton.addEventListener('mouseleave', () => {
        goButton.style.transform = 'translateY(0)';
    });
}

// Send workout selection when changed
workoutSelect.addEventListener('change', () => {
    const selectedWorkout = workoutSelect.value;
    ws.send(JSON.stringify({ type: 'workout', value: selectedWorkout }));
    console.log("Selected workout:", selectedWorkout);
});

// Send strictness selection when changed
strictnessSelect.addEventListener('change', () => {
    const selectedStrictness = strictnessSelect.value;
    ws.send(JSON.stringify({ type: 'strictness', value: selectedStrictness }));
    console.log("Selected strictness:", selectedStrictness);
});

// Send reps value and start detection when "Go" button is clicked
goButton.addEventListener('click', () => {
    const selectedReps = parseInt(repsSelect.value, 10);
    if (isNaN(selectedReps) || selectedReps < 1) {
        updateStatus("Please enter a valid number of reps.");
        return;
    }
    
    // Visual feedback
    goButton.innerHTML = '<i class="fas fa-spinner"></i> Starting...';
    
    // Update status
    updateStatus("Initializing workout session...");
    
    
    // Send reps value
    ws.send(JSON.stringify({ type: 'reps', value: selectedReps }));
    console.log("Selected reps:", selectedReps);

    // Send start message
    ws.send(JSON.stringify({ type: 'start' }));
    console.log("Detection started");
    
    // Initialize hidden workout counter for sound tracking
    const workoutCounter = document.querySelector('.workout-counter');
    if (workoutCounter) {
        workoutCounter.innerHTML = `0 / ${selectedReps}`;
        console.log(`Initialized hidden rep counter: 0/${selectedReps}`);
    }
    
    // Show only pose indicator (not workout counter)
    const poseIndicator = document.querySelector('.workout-pose-indicator');
    
    if (poseIndicator) {
        poseIndicator.style.display = 'block';
    } else {
        console.error('Pose indicator element not found');
    }
    
    // Reset button after a delay
    setTimeout(() => {
        goButton.innerHTML = '<i class="fas fa-play"></i> Start Workout';
    }, 2000);
});

// Add a test sound button
const testSoundButton = document.createElement('button');
testSoundButton.className = 'btn btn-secondary btn-sm';
testSoundButton.innerHTML = '<i class="fas fa-volume-up"></i> Test Sound';
testSoundButton.style.marginTop = '10px';
testSoundButton.addEventListener('click', () => {
    // Test sounds when explicitly clicked by user (should bypass autoplay restrictions)
    console.log('Testing sounds via button click...');
    repSound.currentTime = 0;
    repSound.play().then(() => {
        console.log('Rep sound played successfully via button');
    }).catch(error => {
        console.error('Failed to play rep sound via button:', error);
    });
    
    setTimeout(() => {
        victorySound.currentTime = 0;
        victorySound.play().then(() => {
            console.log('Victory sound played successfully via button');
        }).catch(error => {
            console.error('Failed to play victory sound via button:', error);
        });
    }, 1000);
});

// Add the test button to the page
document.addEventListener('DOMContentLoaded', () => {
    // Wait for DOM to be ready
    initUI();
    
    // Add the test button to the control panel
    const controlPanel = document.querySelector('.control-panel');
    if (controlPanel) {
        controlPanel.appendChild(testSoundButton);
    }
});