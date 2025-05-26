//
//  HistoryView.swift
//  GymBuddy
//
//  Created by Thibaut Donis on 24/05/2025.
//

import SwiftUI

struct HistoryView: View {
    @ObservedObject var webSocketManager: WebSocketManager
    @State private var sessions: [WorkoutSession] = []
    
    var body: some View {
        NavigationView {
            VStack(spacing: 0) {
                if sessions.isEmpty && webSocketManager.workoutHistory.isEmpty {
                    emptyStateView
                } else {
                    historyListView
                }
            }
            .navigationTitle("Workout History")
            .navigationBarTitleDisplayMode(.large)
        }
        .onAppear {
            loadHistory()
        }
    }
    
    private var emptyStateView: some View {
        VStack(spacing: 20) {
            Image(systemName: "clock.badge.questionmark")
                .font(.system(size: 60))
                .foregroundColor(.gray)
            
            Text("No Workouts Yet")
                .font(.title2)
                .fontWeight(.semibold)
                .foregroundColor(.primary)
            
            Text("Start your first workout to see your progress here!")
                .font(.body)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
    
    private var historyListView: some View {
        List {
            if !webSocketManager.workoutHistory.isEmpty {
                Section("Current Session") {
                    ForEach(webSocketManager.workoutHistory, id: \.self) { historyItem in
                        HistoryRowView(historyText: historyItem)
                    }
                }
            }
            
            if !sessions.isEmpty {
                Section("Previous Sessions") {
                    ForEach(sessions) { session in
                        WorkoutSessionRowView(session: session)
                    }
                }
            }
        }
        .listStyle(InsetGroupedListStyle())
    }
    
    private func loadHistory() {
        // In a real app, you would load from persistent storage
        // For now, we'll just use the current session data
    }
}

struct HistoryRowView: View {
    let historyText: String
    
    var body: some View {
        HStack {
            Image(systemName: workoutIcon)
                .foregroundColor(.blue)
                .frame(width: 30)
            
            VStack(alignment: .leading, spacing: 2) {
                Text(workoutName)
                    .font(.headline)
                
                Text("\(reps) reps")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
            
            Spacer()
            
            Text("Today")
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .padding(.vertical, 4)
    }
    
    private var workoutName: String {
        if historyText.contains("push-ups") {
            return "Push-ups"
        } else if historyText.contains("squats") {
            return "Squats"
        } else if historyText.contains("abs") {
            return "Abs"
        }
        return "Workout"
    }
    
    private var workoutIcon: String {
        if historyText.contains("push-ups") {
            return "figure.strengthtraining.traditional"
        } else if historyText.contains("squats") {
            return "figure.squat"
        } else if historyText.contains("abs") {
            return "figure.core.training"
        }
        return "figure.walk"
    }
    
    private var reps: String {
        // Parse reps from strings like "push-ups: 10 reps"
        let components = historyText.components(separatedBy: ": ")
        if components.count > 1 {
            return components[1].replacingOccurrences(of: " reps", with: "")
        }
        return "0"
    }
}

struct WorkoutSessionRowView: View {
    let session: WorkoutSession
    
    var body: some View {
        HStack {
            Image(systemName: session.workoutType.icon)
                .foregroundColor(.blue)
                .frame(width: 30)
            
            VStack(alignment: .leading, spacing: 2) {
                Text(session.workoutType.displayName)
                    .font(.headline)
                
                HStack {
                    Text("\(session.reps) reps")
                    Text("•")
                    Text(session.strictness.displayName)
                }
                .font(.subheadline)
                .foregroundColor(.secondary)
            }
            
            Spacer()
            
            Text(session.date, style: .date)
                .font(.caption)
                .foregroundColor(.secondary)
        }
        .padding(.vertical, 4)
    }
}

#Preview {
    HistoryView(webSocketManager: WebSocketManager())
}
