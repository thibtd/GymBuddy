# GymBuddy - Your AI-Powered Workout Companion

**GymBuddy** is an intelligent, real-time personal trainer that uses your webcam to help you achieve perfect form, count your **reps, and provide meaningful feedback on your workouts.**

This project leverages the power of computer vision and large language models to create an accessible and effective fitness experience. Whether you're a beginner learning the basics or an experienced athlete looking to perfect your form, GymBuddy is here to guide and motivate you.

### ✨ Core Features
- **Real-Time Exercise Tracking:** Utilizes Google's MediaPipe to  perform real-time pose estimation directly in your browser, tracking 33 key body landmarks.

- **Automatic Rep Counting:** No more losing count! GymBuddy's algorithms detect full repetitions for supported exercises, currently including:
   - Push-ups
   - Squats

- **AI-Powered Form Correction:** The `feedbackAgent` analyzes your movements and provides instant, actionable advice to help you improve your form and prevent injuries.

- **Scientifically-Grounded Feedback (In Progress):** Our goal is to move beyond generic advice. We are actively developing a **Knowledge Graph (KG)** based on exercise science and biomechanics. By implementing a **GraphRAG pipeline**, the AI's feedback will be grounded in this structured, scientific knowledge, providing you with truly expert-level guidance.

### 🚀 Tech Stack
- Backend: FastAPI, Python 3
- Real-time Communication: WebSockets
- Machine Learning / CV: Google MediaPipe
- Deployment: Docker
- Frontend: Vanilla JavaScript, HTML5, CSS

### 🛠️ Getting Started
**(In Progress) Access the app on our server**

You can get a local instance of GymBuddy up and running in minutes using either Docker (recommended) or by setting up a local Python environment.

#### Option 1: Running with Docker (Recommended)
This is the easiest and most reliable way to run the project.

1. Clone the repository:
```
git clone https://github.com/thibtd/GymBuddy.git
cd GymBuddy
```

2. Run with Docker Compose:
```
docker-compose up --build
```

3. Open your browser and navigate to http://localhost:8080.

#### Option 2: Running Locally with Python

1. Clone the repository:
```
git clone https://github.com/thibtd/GymBuddy.git
cd GymBuddy
```

2. Create and activate a virtual environment:
```
python3 -m venv .venv
source venv/bin/activate
```

3. Install the dependencies:
```
pip install -r requirements.txt
```

4. Run the application using the Makefile:
```
make run
```

Open your browser and navigate to http://localhost:8000.


### 🗺️ Roadmap
GymBuddy is an actively developing project. Here are some of the exciting features on our roadmap:

[ ] Knowledge Graph & GraphRAG Integration: Finalize and implement the KG to provide elite, scientifically-backed feedback.

[ ] Expand Exercise Library: Add more complex exercises like lunges, pull-ups, and planks.

[ ] User Profiles & Progress Tracking: Introduce user accounts to save workout history, track personal bests, and visualize progress over time.

[ ] Advanced Form Analysis: Provide more detailed biomechanical feedback, such as joint-specific angle analysis and stability assessments.

[ ] Customizable Workouts: Allow users to create and save their own workout routines.

### 🤝 Contributing
Contributions are welcome! Whether you're interested in adding new exercises, improving the AI feedback, or enhancing the frontend, we'd love to have your help. Please feel free to open an issue to discuss your ideas or submit a pull request.

### 📄 License
This project is licensed under the MIT License. See the LICENSE file for details.

