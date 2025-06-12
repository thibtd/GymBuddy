const workoutSelect = document.getElementById('workout-select');
const repsSelect = document.getElementById('reps-select');
const strictnessSelect = document.getElementById('strictness-select');
const goButton = document.getElementById('go-button');
const canvas = document.getElementById('videoCanvas');
const ctx = canvas.getContext('2d');
const historyDiv = document.getElementById('history');
const statusEl = document.getElementById('status');

// --- Sound Effects ---
const repCompleteSound = new Audio('/static/sounds/rep-complete.mp3');
const victorySound = new Audio('/static/sounds/victory.mp3');
// Preload sounds for better performance, though browsers might restrict this
// repCompleteSound.preload = 'auto';
// victorySound.preload = 'auto';


let videoElement = null;
let mediaStream = null;
let isCapturing = false;
let lastAnalysisData = null;
let previousRepCount = 0; // To track rep increases
let workoutCompletedSoundPlayed = false; // Flag to ensure victory sound plays only once
let completedSeries = false;

// Update WebSocket connection to use secure protocol when on HTTPS
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
ws.binaryType = "arraybuffer";

// --- Drawing Helpers ---

// MediaPipe standard connections for drawing the skeleton
const POSE_CONNECTIONS = [[0, 1], [1, 2], [2, 3], [3, 7], [0, 4], [4, 5],
[5, 6], [6, 8], [9, 10], [11, 12], [11, 13],
[13, 15], [15, 17], [15, 19], [15, 21], [17, 19],
[12, 14], [14, 16], [16, 18], [16, 20], [16, 22],
[18, 20], [11, 23], [12, 24], [23, 24], [23, 25],
[24, 26], [25, 27], [26, 28], [27, 29], [28, 30],
[29, 31], [30, 32], [27, 31], [28, 32]];

function drawSkeleton(landmarks) {
    if (!landmarks || landmarks.length === 0) return;
    ctx.lineWidth = 3;
    ctx.strokeStyle = 'cyan';

    POSE_CONNECTIONS.forEach(conn => {
        const p1 = landmarks[conn[0]];
        const p2 = landmarks[conn[1]];
        if (p1 && p2) {
            ctx.beginPath();
            ctx.moveTo(p1.x * canvas.width, p1.y * canvas.height);
            ctx.lineTo(p2.x * canvas.width, p2.y * canvas.height);
            ctx.stroke();
        }
    });
}

function drawLandmarks(landmarks) {
    if (!landmarks || landmarks.length === 0) return;
    ctx.fillStyle = 'red';
    landmarks.forEach(lm => {
        ctx.beginPath();
        ctx.arc(lm.x * canvas.width, lm.y * canvas.height, 5, 0, 2 * Math.PI);
        ctx.fill();
    });
}

function drawInfoText(data) {
    ctx.font = 'bold 24px Arial';
    ctx.fillStyle = data.form_ok ? '#38b000' : '#d00000'; // Success or Danger color
    ctx.textAlign = 'left';
    ctx.fillText(data.form_message, 20, 40);
    
    ctx.font = 'bold 36px Arial';
    ctx.fillStyle = 'white';
    ctx.fillText(`Reps: ${data.rep_count} / ${data.goal_reps}`, 20, 80);
}

function drawAngles(data) {
    if (!data.landmarks || !data.display_angles) return;
    
    ctx.font = 'bold 18px Arial';
    ctx.fillStyle = 'yellow';
    
    data.display_angles.forEach((angleInfo, index) => {
        const [idx1, idx2, idx3] = angleInfo.joint_indices;
        const p1 = data.landmarks[idx1];
        const p2 = data.landmarks[idx2]; // The joint
        const p3 = data.landmarks[idx3];

        if (!p1 || !p2 || !p3) return;
    

        // Draw the angle arc
        const p1_coords = { x: p1.x * canvas.width, y: p1.y * canvas.height };
        const p2_coords = { x: p2.x * canvas.width, y: p2.y * canvas.height };
        const p3_coords = { x: p3.x * canvas.width, y: p3.y * canvas.height };

        const angleRad1 = Math.atan2(p1_coords.y - p2_coords.y, p1_coords.x - p2_coords.x);
        const angleRad2 = Math.atan2(p3_coords.y - p2_coords.y, p3_coords.x - p2_coords.x);

        ctx.strokeStyle = 'yellow';
        ctx.lineWidth = 4;
        ctx.beginPath();
        ctx.arc(p2_coords.x, p2_coords.y, 30, angleRad1, angleRad2);
        ctx.stroke();
        ctx.fillText(`${angleInfo.name}: ${angleInfo.value.toFixed(0)}°`,p2_coords.x, p2_coords.y-2);
    });
}

// Initialize camera with better error handling
async function initCamera() {
    try {
        console.log('Requesting camera access...');
        
        // For Docker/localhost, we can be more permissive
        const isLocalhost = location.hostname === 'localhost' || location.hostname === '127.0.0.1';
        const isSecure = location.protocol === 'https:';
        
        if (!isLocalhost && !isSecure) {
            console.warn('Camera may not work without HTTPS on non-localhost domains');
        }

        const constraints = {
            video: {
                width: { ideal: 640 },
                height: { ideal: 480 },
                facingMode: "user"
            }
        };
        
        // Show permission request status
        updateStatus("Requesting camera permission...", "ready");
        
        mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
        
        if (!videoElement) {
            videoElement = document.createElement('video');
            videoElement.autoplay = true;
            videoElement.playsInline = true;
            videoElement.muted = true;
            videoElement.style.display = 'none';
            document.body.appendChild(videoElement);
        }
        
        videoElement.srcObject = mediaStream;
        await videoElement.play();

        canvas.width = videoElement.videoWidth;
        canvas.height = videoElement.videoHeight;
        
        updateStatus("Camera ready! Configure your workout settings.", "ready");
        
        //startFrameCapture();
        renderLoop(); // Start the rendering loop

        // Start capturing frames immediately
        startFrameCapture();
        return true;
    } catch (error) {
        console.error('Camera error:', error);
        
        if (error.name === 'NotAllowedError') {
            updateStatus('Camera permission denied. Please allow camera access in your browser and refresh the page.', 'error');
        } else if (error.name === 'NotFoundError') {
            updateStatus('No camera found. Please connect a camera and refresh the page.', 'error');
        } else if (error.name === 'NotReadableError') {
            updateStatus('Camera is already in use by another application.', 'error');
        } else if (error.name === 'OverconstrainedError') {
            updateStatus('Camera does not support the requested video constraints.', 'error');
        } else if (error.name === 'SecurityError') {
            updateStatus('Camera access blocked due to security restrictions. Try using HTTPS.', 'error');
        } else {
            updateStatus(`Camera error: ${error.message}. Try refreshing the page.`, 'error');
        }
        return false;
    }
}

function captureAndSendFrame() {
    if (!videoElement || !isCapturing || ws.readyState !== WebSocket.OPEN) return;

    const tempCanvas = document.createElement('canvas');
    tempCanvas.width = videoElement.videoWidth;
    tempCanvas.height = videoElement.videoHeight;
    const tempCtx = tempCanvas.getContext('2d');
    tempCtx.drawImage(videoElement, 0, 0);

    tempCanvas.toBlob((blob) => {
        if (blob) {
            blob.arrayBuffer().then(buffer => ws.send(buffer));
        }
    }, 'image/jpeg', 0.8);
}


function startFrameCapture() {
    isCapturing = true;
    const captureInterval = setInterval(() => {
        if (!isCapturing) {
            clearInterval(captureInterval);
            return;
        }
        captureAndSendFrame();
    }, 100); // Send frames at 10 FPS
}

function renderLoop() {
    if (!videoElement || !ctx) return;
    
    // Draw the local video feed to the canvas
    ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height);

    // If we have analysis data, draw overlays
    if (lastAnalysisData) {
        drawSkeleton(lastAnalysisData.landmarks);
        drawLandmarks(lastAnalysisData.landmarks);
        drawInfoText(lastAnalysisData);
        drawAngles(lastAnalysisData);
    }
    if(completedSeries){
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        if (videoElement) {
            ctx.drawImage(videoElement, 0, 0, canvas.width, canvas.height);
        }
    }


    // Continue the loop
    requestAnimationFrame(renderLoop);
}

// WebSocket message handler
ws.onmessage = (event) => {
    if (typeof event.data === "string") {
        const data = JSON.parse(event.data);
        console.log('Received:', data);

        if (data.landmarks) {
            lastAnalysisData = data;
            const currentReps = lastAnalysisData.rep_count;
            const goalReps = lastAnalysisData.goal_reps;

            if (currentReps > previousRepCount && currentReps != goalReps && goalReps>0) { // A rep was made
                    repCompleteSound.play().catch(e => console.error("Error playing rep sound:", e));
                }
                previousRepCount = currentReps;

            // Reset flags and counts if workout is reset (e.g., goal_reps becomes 0, or rep_count is reset by server)
            if (goalReps === 0 || currentReps === 0) {
                previousRepCount = 0;
                workoutCompletedSoundPlayed = false; // Reset flag
            }
        } else if (data.type === 'data') {
            updateStatus(data.message, data.status);
            if (data.status === 'completed') {
                if (!workoutCompletedSoundPlayed) { // Only play if not already played by landmark update
                    victorySound.play().catch(e => console.error("Error playing victory sound:", e));
                }
                previousRepCount = 0; // Reset for next workout
                workoutCompletedSoundPlayed = false; // Reset flag for the next workout session
                completedSeries = true; // Mark series as completed
            }
        } else if (data.type === 'history') {
            updateHistory(data.message);
        } else if (data.type === 'feedback') {
            addFeedbackToHistory(data.message);
        }
        console.log("Updated status:", data.message, "Status:", data.status);
    }
};

function updateStatus(message, status) {
    if (!statusEl) return;
    statusEl.style.display = 'block';
    statusEl.textContent = message;
    statusEl.className = `status-${status}`;
}

function updateHistory(htmlContent) {
    if (!historyDiv) return;
    if (htmlContent.trim() === '') {
        historyDiv.innerHTML = '<p>No workout history yet.</p>';
    } else {
        historyDiv.innerHTML = htmlContent;
    }
}

function addFeedbackToHistory(feedback) {
    console.log('Feedback received:', feedback);
    
    if (!feedback || feedback.trim() === '') {
        return;
    }
    
    // Create or find feedback section
    let feedbackSection = document.querySelector('.feedback-section');
    
    if (!feedbackSection) {
        feedbackSection = document.createElement('div');
        feedbackSection.className = 'feedback-section';
        feedbackSection.innerHTML = '<h3>Latest Feedback</h3><div class="feedback-content"></div>';
        
        // Add it after the history div
        const historyDiv = document.getElementById('history');
        if (historyDiv && historyDiv.parentNode) {
            historyDiv.parentNode.insertBefore(feedbackSection, historyDiv.nextSibling);
        }
    }
    
    const feedbackContent = feedbackSection.querySelector('.feedback-content');
    if (feedbackContent) {
        feedbackContent.innerHTML = `<div class="feedback-item">${feedback}</div>`;
        
        // Add some styling
        const feedbackItem = feedbackContent.querySelector('.feedback-item');
        if (feedbackItem) {
            feedbackItem.style.padding = '10px';
            feedbackItem.style.backgroundColor = '#e8f5e8';
            feedbackItem.style.border = '1px solid #4caf50';
            feedbackItem.style.borderRadius = '5px';
            feedbackItem.style.marginTop = '10px';
            feedbackItem.style.animation = 'fadeIn 0.5s ease-in-out';
        }
    }
}

// Add CSS animation
const style = document.createElement('style');
style.textContent = `
    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(-10px); }
        to { opacity: 1; transform: translateY(0); }
    }
`;
document.head.appendChild(style);

// Event listeners
workoutSelect?.addEventListener('change', () => {
    const selectedWorkout = workoutSelect.value;
    ws.send(JSON.stringify({ type: 'workout', value: selectedWorkout }));
    console.log("Selected workout:", selectedWorkout);
});


strictnessSelect?.addEventListener('change', () => {
    const selectedStrictness = strictnessSelect.value;
    ws.send(JSON.stringify({ type: 'strictness', value: selectedStrictness }));
    console.log("Selected strictness:", selectedStrictness);
});

goButton?.addEventListener('click', () => {
    console.log("Starting workout...");
    ws.send(JSON.stringify({type: 'start', value: true}));
    ws.send(JSON.stringify({type:'workout',value: workoutSelect.value}));
    ws.send(JSON.stringify({type:'reps', value:repsSelect.value}));
    ws.send(JSON.stringify({type:'strictness',value: strictnessSelect.value}));
    //ws.send(JSON.stringify({ type: 'start' }));
    updateStatus("Workout started! Get into position...", "in_progress");
    previousRepCount = 0; // Reset rep count when starting a new workout
    workoutCompletedSoundPlayed = false; // Reset flag for new workout
    completedSeries = false; // Reset completed series flag
});


// WebSocket event handlers
ws.onopen = () => {
    console.log("WebSocket connected");
    initCamera();
};

ws.onclose = () => {
    console.log("WebSocket disconnected");
    updateStatus("Connection lost. Please refresh the page.", "error");
    isCapturing = false;
};

ws.onerror = (error) => {
    console.error("WebSocket error:", error);
    updateStatus("Connection error. Please refresh the page.", "error");
};

// Initialize when page loads
document.addEventListener('DOMContentLoaded', () => {
    updateStatus("Connecting...", "ready");
});