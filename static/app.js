const workoutSelect = document.getElementById('workout-select');
const repsSelect = document.getElementById('reps-select');
const strictnessSelect = document.getElementById('strictness-select');
const goButton = document.getElementById('go-button');
const canvas = document.getElementById('videoCanvas');
const ctx = canvas.getContext('2d');
const historyDiv = document.getElementById('history');
const statusEl = document.getElementById('status');

let videoElement = null;
let mediaStream = null;
let isCapturing = false;

// Update WebSocket connection to use secure protocol when on HTTPS
const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
const ws = new WebSocket(`${protocol}//${window.location.host}/ws`);
ws.binaryType = "arraybuffer";

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
        
        console.log('Camera initialized successfully');
        updateStatus("Camera ready! Configure your workout settings.", "ready");
        
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

// Capture and send frames
function captureAndSendFrame() {
    if (!videoElement || !isCapturing) return;
    
    const tempCanvas = document.createElement('canvas');
    const tempCtx = tempCanvas.getContext('2d');
    
    tempCanvas.width = videoElement.videoWidth;
    tempCanvas.height = videoElement.videoHeight;
    
    tempCtx.drawImage(videoElement, 0, 0);
    
    tempCanvas.toBlob((blob) => {
        if (blob && ws.readyState === WebSocket.OPEN) {
            blob.arrayBuffer().then(buffer => {
                ws.send(buffer);
            });
        }
    }, 'image/jpeg', 0.8);
}

// Start frame capture loop
function startFrameCapture() {
    isCapturing = true;
    
    function capture() {
        if (isCapturing) {
            captureAndSendFrame();
            setTimeout(capture, 100); // 10 FPS for testing
        }
    }
    
    capture();
}

// WebSocket message handler
ws.onmessage = (event) => {
    if (typeof event.data === "string") {
        const data = JSON.parse(event.data);
        console.log('Received:', data);
        
        if (data.type === 'data') {
            updateStatus(data.message, data.status);
        } else if (data.type === 'history') {
            updateHistory(data.message);
        } else if (data.type === 'feedback') {
            addFeedbackToHistory(data.message);
        }
    } else {
        // Display received frame
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

repsSelect?.addEventListener('change', () => {
    const selectedReps = repsSelect.value;
    ws.send(JSON.stringify({ type: 'reps', value: selectedReps }));
    console.log("Selected reps:", selectedReps);
});

strictnessSelect?.addEventListener('change', () => {
    const selectedStrictness = strictnessSelect.value;
    ws.send(JSON.stringify({ type: 'strictness', value: selectedStrictness }));
    console.log("Selected strictness:", selectedStrictness);
});

goButton?.addEventListener('click', () => {
    console.log("Starting workout...");
    ws.send(JSON.stringify({ type: 'start' }));
    updateStatus("Workout started! Get into position...", "in_progress");
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