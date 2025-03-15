# GymBuddy - Your AI-Powered Personal Trainer

Welcome to **GymBuddy**, the revolutionary AI-powered fitness app that brings the expertise of a personal trainer right to your home! GymBuddy uses advanced computer vision technology to track your workouts in real-time, provide instant feedback on your form, and help you achieve your fitness goals faster and safer.

## 🚀 Features

- **Real-Time Pose Estimation**: Utilizing the power of MediaPipe, GymBuddy detects and analyzes your movements to ensure you're performing exercises correctly.
- **Instant Form Feedback**: Receive immediate suggestions on how to correct your posture and technique to prevent injuries and maximize effectiveness.
- **Automatic Rep Counting**: Focus on your workout while GymBuddy counts your reps for you.
- **Interactive Web Interface**: A sleek and user-friendly interface to track your progress and view your workout history.
- **Customizable Workouts**: Choose from different exercises like push-ups, abs, and squats, and set your desired number of reps.

## 🛠 Tech Stack

- **Python**: The core programming language driving the application.
- **FastAPI**: A modern, fast web framework for building APIs with Python.
- **OpenCV**: Open Source Computer Vision Library for real-time computer vision.
- **MediaPipe**: A cross-platform framework for building multimodal applied machine learning pipelines.
- **NumPy**: Essential package for scientific computing with Python.
- **WebSockets**: For real-time communication between the server and client.
- **HTML/CSS/JavaScript**: Front-end technologies for the interactive web interface.

## 📖 How It Works

GymBuddy captures video input, analyzes your movements using MediaPipe's pose estimation, and processes the data to provide feedback and count repetitions. The application runs a FastAPI server that handles WebSocket connections to stream video data and interact with the client-side web interface.

## 💡 Why GymBuddy?

- **Innovative Technology**: Combines state-of-the-art computer vision and machine learning technologies.
- **Enhances Workouts**: Helps you maintain proper form, which is crucial for effectiveness and injury prevention.
- **Convenient and Accessible**: No need for expensive equipment or personal trainers; GymBuddy is accessible from your own device.
- **Motivational**: Keep track of your progress and stay motivated by seeing your improvements over time.

## 🔧 Getting Started

### Prerequisites

- Python 3.7 or higher installed on your system.
- `pip` for managing Python packages.
- A webcam or video source for capturing your workout.

### Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/yourusername/gymbuddy.git
   cd gymbuddy
   ```

2. **Install Dependencies**

   Use the provided 

makefile

 to install the required packages:

   ```bash
   make install
   ```

   Alternatively, install manually:

   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

### Usage

1. **Run the Application**

   ```bash
   uvicorn main:app --reload
   ```

2. **Access the Web Interface**

   Open your web browser and navigate to `http://127.0.0.1:8000`.

3. **Start Your Workout**

   - Select your desired workout (e.g., push-ups, abs, squats).
   - Enter the number of reps.
   - Click the "Go" button to start.

4. **View Feedback**

   - Watch your live video stream with real-time annotations.
   - Receive feedback on your form and keep track of your reps.
