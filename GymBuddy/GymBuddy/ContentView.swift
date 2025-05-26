//
//  ContentView.swift
//  GymBuddy
//
//  Created by Thibaut Donis on 24/05/2025.
//

import SwiftUI
import Foundation
import Combine

// MARK: - Simple WebSocket Manager
class SimpleWebSocketManager: ObservableObject {
    @Published var isConnected = false
    @Published var currentMessage = "Ready to start your workout!"
    @Published var currentReps = 0
    @Published var goalReps = 0
    @Published var receivedImage: Data?
    
    private var webSocket: URLSessionWebSocketTask?
    private let serverURL = "ws://127.0.0.1:8000/ws"
    
    func connect() {
        guard let url = URL(string: serverURL) else { return }
        webSocket = URLSession.shared.webSocketTask(with: url)
        webSocket?.resume()
        isConnected = true
        receiveMessage()
    }
    
    func disconnect() {
        webSocket?.cancel()
        isConnected = false
    }
    
    private func receiveMessage() {
        webSocket?.receive { [weak self] result in
            switch result {
            case .success(let message):
                // Handle messages
                DispatchQueue.main.async {
                    self?.handleMessage(message)
                }
                self?.receiveMessage()
            case .failure:
                DispatchQueue.main.async {
                    self?.isConnected = false
                }
            }
        }
    }
    
    private func handleMessage(_ message: URLSessionWebSocketTask.Message) {
        switch message {
        case .string(let text):
            handleTextMessage(text)
        case .data(let data):
            // Handle binary data (video frames)
            receivedImage = data
        @unknown default:
            break
        }
    }
    
    private func handleTextMessage(_ text: String) {
        // Parse any text messages from the backend
        // This could be improved to parse JSON messages properly
        if text.contains("reps") {
            // Simple parsing for demonstration
            let components = text.components(separatedBy: " ")
            // Find first component that can be converted to an integer
            for component in components {
                if let reps = Int(component) {
                    currentReps = reps
                    break
                }
            }
        }
    }
    
    func sendWorkout(_ workout: WorkoutType, reps: Int, strictness: StrictnessLevel) {
        goalReps = reps
        // Send messages to backend
        let workoutMessage = """
        {"type": "workout", "value": "\(workout.rawValue)"}
        """
        webSocket?.send(.string(workoutMessage)) { _ in }
        
        let repsMessage = """
        {"type": "reps", "value": "\(reps)"}
        """
        webSocket?.send(.string(repsMessage)) { _ in }
        
        let strictnessMessage = """
        {"type": "strictness", "value": "\(strictness.rawValue)"}
        """
        webSocket?.send(.string(strictnessMessage)) { _ in }
    }
    
    func startWorkout() {
        let startMessage = """
        {"type": "start"}
        """
        webSocket?.send(.string(startMessage)) { _ in }
    }
}

struct ContentView: View {
    @StateObject private var webSocketManager = SimpleWebSocketManager()
    @State private var selectedWorkout: WorkoutType = .pushUps
    @State private var selectedReps = 10
    @State private var selectedStrictness: StrictnessLevel = .medium
    @State private var showingWorkout = false
    
    var body: some View {
        NavigationView {
            VStack(spacing: 30) {
                // Header
                VStack(spacing: 10) {
                    Image(systemName: "figure.strengthtraining.traditional")
                        .font(.system(size: 60))
                        .foregroundColor(.blue)
                    
                    Text("GymBuddy")
                        .font(.largeTitle)
                        .fontWeight(.bold)
                    
                    Text("Your AI-Powered Personal Trainer")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                    
                    // Connection Status
                    HStack {
                        Circle()
                            .fill(webSocketManager.isConnected ? .green : .red)
                            .frame(width: 8, height: 8)
                        Text(webSocketManager.isConnected ? "Connected" : "Disconnected")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
                
                ScrollView {
                    VStack(spacing: 25) {
                        // Workout Selection
                        VStack(alignment: .leading, spacing: 15) {
                            Text("Choose Your Workout")
                                .font(.headline)
                                .fontWeight(.semibold)
                            
                            HStack(spacing: 15) {
                                ForEach(WorkoutType.allCases) { workout in
                                    Button(action: { selectedWorkout = workout }) {
                                        VStack(spacing: 8) {
                                            Image(systemName: workout.icon)
                                                .font(.system(size: 30))
                                                .foregroundColor(selectedWorkout == workout ? .white : .blue)
                                            
                                            Text(workout.displayName)
                                                .font(.caption)
                                                .fontWeight(.medium)
                                                .foregroundColor(selectedWorkout == workout ? .white : .primary)
                                        }
                                        .frame(height: 80)
                                        .frame(maxWidth: .infinity)
                                        .background(
                                            RoundedRectangle(cornerRadius: 12)
                                                .fill(selectedWorkout == workout ? .blue : Color.gray.opacity(0.2))
                                        )
                                    }
                                }
                            }
                        }
                        
                        // Reps Selection
                        VStack(alignment: .leading, spacing: 15) {
                            Text("Number of Reps")
                                .font(.headline)
                                .fontWeight(.semibold)
                            
                            let repOptions = [1, 5, 15, 20, 25, 30]
                            LazyVGrid(columns: Array(repeating: GridItem(.flexible()), count: 3), spacing: 10) {
                                ForEach(repOptions, id: \.self) { reps in
                                    Button(action: { selectedReps = reps }) {
                                        Text("\(reps)")
                                            .font(.system(.title2, design: .rounded))
                                            .fontWeight(.medium)
                                            .frame(height: 50)
                                            .frame(maxWidth: .infinity)
                                            .background(
                                                RoundedRectangle(cornerRadius: 12)
                                                    .fill(selectedReps == reps ? .blue : Color.gray.opacity(0.2))
                                            )
                                            .foregroundColor(selectedReps == reps ? .white : .primary)
                                    }
                                }
                            }
                        }
                        
                        // Strictness Selection
                        VStack(alignment: .leading, spacing: 15) {
                            Text("Difficulty Level")
                                .font(.headline)
                                .fontWeight(.semibold)
                            
                            VStack(spacing: 10) {
                                ForEach(StrictnessLevel.allCases) { strictness in
                                    Button(action: { selectedStrictness = strictness }) {
                                        HStack {
                                            Text(strictness.displayName)
                                                .font(.headline)
                                                .fontWeight(.medium)
                                            
                                            Spacer()
                                            
                                            if selectedStrictness == strictness {
                                                Image(systemName: "checkmark.circle.fill")
                                                    .foregroundColor(.blue)
                                            }
                                        }
                                        .padding()
                                        .background(
                                            RoundedRectangle(cornerRadius: 12)
                                                .fill(selectedStrictness == strictness ? Color.blue.opacity(0.1) : Color.gray.opacity(0.2))
                                        )
                                        .foregroundColor(.primary)
                                    }
                                }
                            }
                        }
                        
                        // Start Button
                        Button(action: startWorkout) {
                            HStack {
                                Image(systemName: "play.fill")
                                Text("Start Workout")
                                    .fontWeight(.semibold)
                            }
                            .font(.headline)
                            .foregroundColor(.white)
                            .frame(height: 55)
                            .frame(maxWidth: .infinity)
                            .background(
                                RoundedRectangle(cornerRadius: 16)
                                    .fill(webSocketManager.isConnected ? .blue : .gray)
                            )
                        }
                        .disabled(!webSocketManager.isConnected)
                    }
                    .padding(.horizontal)
                }
                
                Spacer()
            }
            .navigationTitle("GymBuddy")
            .onAppear {
                if !webSocketManager.isConnected {
                    webSocketManager.connect()
                }
            }
        }
        .sheet(isPresented: $showingWorkout) {
            WorkoutView(webSocketManager: webSocketManager)
        }
    }
    
    private func startWorkout() {
        webSocketManager.sendWorkout(selectedWorkout, reps: selectedReps, strictness: selectedStrictness)
        webSocketManager.startWorkout()
        showingWorkout = true
    }
}

struct WorkoutView: View {
    @ObservedObject var webSocketManager: SimpleWebSocketManager
    @Environment(\.dismiss) private var dismiss
    
    var body: some View {
        VStack(spacing: 20) {
            // Header
            HStack {
                Button(action: { dismiss() }) {
                    Image(systemName: "xmark.circle.fill")
                        .font(.title)
                        .foregroundColor(.white)
                }
                Spacer()
                Text("Workout in Progress")
                    .font(.headline)
                    .foregroundColor(.white)
                Spacer()
            }
            .padding()
            
            // Video feed
            ZStack {
                Rectangle()
                    .fill(Color.gray.opacity(0.3))
                    .frame(height: 300)
                    .cornerRadius(15)
                
                if let imageData = webSocketManager.receivedImage,
                   let uiImage = UIImage(data: imageData) {
                    Image(uiImage: uiImage)
                        .resizable()
                        .aspectRatio(contentMode: .fit)
                        .frame(maxHeight: 300)
                        .cornerRadius(15)
                } else {
                    VStack {
                        Image(systemName: "video.slash")
                            .font(.system(size: 50))
                            .foregroundColor(.white.opacity(0.6))
                        Text("Waiting for video feed...")
                            .foregroundColor(.white.opacity(0.8))
                    }
                }
            }
            .padding()
            
            // Stats
            HStack(spacing: 30) {
                VStack {
                    Text("\(webSocketManager.currentReps)")
                        .font(.system(.largeTitle, design: .rounded))
                        .fontWeight(.bold)
                        .foregroundColor(.blue)
                    Text("Current")
                        .font(.caption)
                        .foregroundColor(.white.opacity(0.8))
                }
                
                VStack {
                    Text("\(webSocketManager.goalReps)")
                        .font(.system(.largeTitle, design: .rounded))
                        .fontWeight(.bold)
                        .foregroundColor(.green)
                    Text("Goal")
                        .font(.caption)
                        .foregroundColor(.white.opacity(0.8))
                }
                
                VStack {
                    Text("\(max(0, webSocketManager.goalReps - webSocketManager.currentReps))")
                        .font(.system(.largeTitle, design: .rounded))
                        .fontWeight(.bold)
                        .foregroundColor(.orange)
                    Text("Remaining")
                        .font(.caption)
                        .foregroundColor(.white.opacity(0.8))
                }
            }
            .padding()
            .background(Color.white.opacity(0.1))
            .cornerRadius(15)
            .padding()
            
            // Status message
            Text(webSocketManager.currentMessage)
                .font(.headline)
                .foregroundColor(.white)
                .multilineTextAlignment(.center)
                .padding()
            
            Spacer()
            
            // Done button
            Button(action: { dismiss() }) {
                Text("End Workout")
                    .font(.headline)
                    .foregroundColor(.black)
                    .frame(height: 50)
                    .frame(maxWidth: .infinity)
                    .background(Color.white)
                    .cornerRadius(15)
            }
            .padding()
        }
        .background(Color.black)
    }
}

struct ContentView_Previews: PreviewProvider {
    static var previews: some View {
        ContentView()
    }
}
