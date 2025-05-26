//
//  WorkoutSetupView.swift
//  GymBuddy
//
//  Created by Thibaut Donis on 24/05/2025.
//

import SwiftUI

struct WorkoutSetupView: View {
    @ObservedObject var webSocketManager: WebSocketManager
    @State private var selectedWorkout: WorkoutType = .pushUps
    @State private var selectedReps: Int = 10
    @State private var selectedStrictness: StrictnessLevel = .medium
    @State private var showingWorkoutView = false
    
    private let repOptions = [1,5, 10, 20, 25, 30]
    
    var body: some View {
        NavigationView {
            VStack(spacing: 30) {
                headerSection
                
                ScrollView {
                    VStack(spacing: 25) {
                        workoutSelectionSection
                        repsSelectionSection
                        strictnessSelectionSection
                        startButtonSection
                    }
                    .padding(.horizontal)
                }
                
                Spacer()
            }
            .navigationTitle("GymBuddy")
            .navigationBarTitleDisplayMode(.large)
        }
        .fullScreenCover(isPresented: $showingWorkoutView) {
            WorkoutSessionView(webSocketManager: webSocketManager)
        }
        .onAppear {
            connectToServer()
        }
    }
    
    private var headerSection: some View {
        VStack(spacing: 10) {
            Image(systemName: "figure.strengthtraining.traditional")
                .font(.system(size: 60))
                .foregroundColor(.blue)
            
            Text("Your AI-Powered Personal Trainer")
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
            
            connectionStatusView
        }
        .padding(.top)
    }
    
    private var connectionStatusView: some View {
        HStack {
            Circle()
                .fill(webSocketManager.isConnected ? .green : .red)
                .frame(width: 8, height: 8)
            
            Text(webSocketManager.isConnected ? "Connected" : "Disconnected")
                .font(.caption)
                .foregroundColor(.secondary)
        }
    }
    
    private var workoutSelectionSection: some View {
        VStack(alignment: .leading, spacing: 15) {
            Text("Choose Your Workout")
                .font(.headline)
                .fontWeight(.semibold)
            
            LazyVGrid(columns: Array(repeating: GridItem(.flexible()), count: 3), spacing: 15) {
                ForEach(WorkoutType.allCases) { workout in
                    WorkoutCardView(
                        workout: workout,
                        isSelected: selectedWorkout == workout
                    ) {
                        selectedWorkout = workout
                        webSocketManager.sendWorkoutSelection(workout)
                    }
                }
            }
        }
    }
    
    private var repsSelectionSection: some View {
        VStack(alignment: .leading, spacing: 15) {
            Text("Number of Reps")
                .font(.headline)
                .fontWeight(.semibold)
            
            LazyVGrid(columns: Array(repeating: GridItem(.flexible()), count: 3), spacing: 10) {
                ForEach(repOptions, id: \.self) { reps in
                    Button(action: {
                        selectedReps = reps
                        webSocketManager.sendRepsSelection(reps)
                    }) {
                        Text("\(reps)")
                            .font(.system(.title2, design: .rounded))
                            .fontWeight(.medium)
                            .frame(height: 50)
                            .frame(maxWidth: .infinity)
                            .background(
                                RoundedRectangle(cornerRadius: 12)
                                    .fill(selectedReps == reps ? .blue : Color(.systemGray6))
                            )
                            .foregroundColor(selectedReps == reps ? .white : .primary)
                    }
                }
            }
        }
    }
    
    private var strictnessSelectionSection: some View {
        VStack(alignment: .leading, spacing: 15) {
            Text("Difficulty Level")
                .font(.headline)
                .fontWeight(.semibold)
            
            VStack(spacing: 10) {
                ForEach(StrictnessLevel.allCases) { strictness in
                    Button(action: {
                        selectedStrictness = strictness
                        webSocketManager.sendStrictnessSelection(strictness)
                    }) {
                        HStack {
                            VStack(alignment: .leading, spacing: 2) {
                                Text(strictness.displayName)
                                    .font(.headline)
                                    .fontWeight(.medium)
                                
                                Text(strictnessDescription(for: strictness))
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                            
                            Spacer()
                            
                            if selectedStrictness == strictness {
                                Image(systemName: "checkmark.circle.fill")
                                    .foregroundColor(.blue)
                            }
                        }
                        .padding()
                        .background(
                            RoundedRectangle(cornerRadius: 12)
                                .fill(selectedStrictness == strictness ? Color.blue.opacity(0.1) : Color(.systemGray6))
                        )
                        .foregroundColor(.primary)
                    }
                }
            }
        }
    }
    
    private var startButtonSection: some View {
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
        .padding(.top)
    }
    
    private func connectToServer() {
        if !webSocketManager.isConnected {
            webSocketManager.connect()
        }
    }
    
    private func startWorkout() {
        webSocketManager.startWorkout()
        showingWorkoutView = true
    }
    
    private func strictnessDescription(for strictness: StrictnessLevel) -> String {
        switch strictness {
        case .loose:
            return "More forgiving form detection"
        case .medium:
            return "Balanced form requirements"
        case .strict:
            return "Perfect form required"
        }
    }
}

struct WorkoutCardView: View {
    let workout: WorkoutType
    let isSelected: Bool
    let action: () -> Void
    
    var body: some View {
        Button(action: action) {
            VStack(spacing: 8) {
                Image(systemName: workout.icon)
                    .font(.system(size: 30))
                    .foregroundColor(isSelected ? .white : .blue)
                
                Text(workout.displayName)
                    .font(.caption)
                    .fontWeight(.medium)
                    .foregroundColor(isSelected ? .white : .primary)
            }
            .frame(height: 80)
            .frame(maxWidth: .infinity)
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(isSelected ? .blue : Color(.systemGray6))
            )
        }
    }
}

#Preview {
    WorkoutSetupView(webSocketManager: WebSocketManager())
}
