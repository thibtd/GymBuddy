//
//  WorkoutSessionView.swift
//  GymBuddy
//
//  Created by Thibaut Donis on 24/05/2025.
//

import SwiftUI

struct WorkoutSessionView: View {
    @ObservedObject var webSocketManager: WebSocketManager
    @Environment(\.dismiss) private var dismiss
    @State private var showingFeedback = false
    
    var body: some View {
        GeometryReader { geometry in
            VStack(spacing: 0) {
                headerSection
                
                videoSection(geometry: geometry)
                
                statsSection
                
                if case .completed = webSocketManager.workoutStatus {
                    completedSection
                }
                
                Spacer()
            }
        }
        .navigationBarHidden(true)
        .background(Color.black)
        .foregroundColor(.white)
        .onChange(of: webSocketManager.workoutStatus) { _, status in
            if case .completed = status {
                showingFeedback = !webSocketManager.feedback.isEmpty
            }
        }
        .sheet(isPresented: $showingFeedback) {
            FeedbackView(feedback: webSocketManager.feedback)
        }
    }
    
    private var headerSection: some View {
        HStack {
            Button(action: { dismiss() }) {
                Image(systemName: "xmark.circle.fill")
                    .font(.title2)
                    .foregroundColor(.white.opacity(0.8))
            }
            
            Spacer()
            
            VStack(alignment: .trailing, spacing: 2) {
                Text(statusText)
                    .font(.headline)
                    .fontWeight(.semibold)
                
                Text(webSocketManager.currentMessage)
                    .font(.caption)
                    .foregroundColor(.white.opacity(0.8))
                    .multilineTextAlignment(.trailing)
            }
        }
        .padding()
        .background(Color.black.opacity(0.3))
    }
    
    private func videoSection(geometry: GeometryProxy) -> some View {
        ZStack {
            Rectangle()
                .fill(Color.gray.opacity(0.3))
                .frame(height: geometry.size.height * 0.5)
            
            if let imageData = webSocketManager.receivedImage,
               let uiImage = UIImage(data: imageData) {
                Image(uiImage: uiImage)
                    .resizable()
                    .aspectRatio(contentMode: .fit)
                    .frame(maxHeight: geometry.size.height * 0.5)
            } else {
                VStack(spacing: 20) {
                    Image(systemName: "video.slash")
                        .font(.system(size: 50))
                        .foregroundColor(.white.opacity(0.6))
                    
                    Text("Waiting for video feed...")
                        .font(.headline)
                        .foregroundColor(.white.opacity(0.8))
                    
                    if !webSocketManager.isConnected {
                        Text("Check your connection")
                            .font(.caption)
                            .foregroundColor(.red.opacity(0.8))
                    }
                }
            }
        }
    }
    
    private var statsSection: some View {
        HStack(spacing: 30) {
            StatCardView(
                title: "Current Reps",
                value: "\(webSocketManager.currentReps)",
                color: .blue
            )
            
            StatCardView(
                title: "Goal",
                value: "\(webSocketManager.goalReps)",
                color: .green
            )
            
            StatCardView(
                title: "Remaining",
                value: "\(max(0, webSocketManager.goalReps - webSocketManager.currentReps))",
                color: .orange
            )
        }
        .padding()
        .background(Color.black.opacity(0.3))
    }
    
    private var completedSection: some View {
        VStack(spacing: 15) {
            Image(systemName: "checkmark.circle.fill")
                .font(.system(size: 50))
                .foregroundColor(.green)
            
            Text("Workout Completed!")
                .font(.title2)
                .fontWeight(.bold)
            
            if !webSocketManager.feedback.isEmpty {
                Button(action: { showingFeedback = true }) {
                    HStack {
                        Image(systemName: "lightbulb.fill")
                        Text("View Feedback")
                    }
                    .padding()
                    .background(Color.blue)
                    .foregroundColor(.white)
                    .cornerRadius(10)
                }
            }
            
            Button(action: { dismiss() }) {
                Text("Done")
                    .font(.headline)
                    .padding()
                    .frame(maxWidth: .infinity)
                    .background(Color.white)
                    .foregroundColor(.black)
                    .cornerRadius(10)
            }
            .padding(.horizontal)
        }
        .padding()
        .background(Color.black.opacity(0.8))
        .cornerRadius(15)
        .padding()
    }
    
    private var statusText: String {
        switch webSocketManager.workoutStatus {
        case .idle:
            return "Ready"
        case .preparing:
            return "Preparing..."
        case .inProgress:
            return "Working Out"
        case .completed:
            return "Completed!"
        case .error:
            return "Error"
        }
    }
}

struct StatCardView: View {
    let title: String
    let value: String
    let color: Color
    
    var body: some View {
        VStack(spacing: 5) {
            Text(value)
                .font(.system(.title, design: .rounded))
                .fontWeight(.bold)
                .foregroundColor(color)
            
            Text(title)
                .font(.caption)
                .foregroundColor(.white.opacity(0.8))
        }
        .frame(maxWidth: .infinity)
        .padding()
        .background(Color.white.opacity(0.1))
        .cornerRadius(10)
    }
}

struct FeedbackView: View {
    let feedback: String
    @Environment(\.dismiss) private var dismiss
    
    var body: some View {
        NavigationView {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    Text("Workout Feedback")
                        .font(.largeTitle)
                        .fontWeight(.bold)
                    
                    Text("Here's how you did:")
                        .font(.headline)
                        .foregroundColor(.secondary)
                    
                    if feedback.contains("<") {
                        // HTML content
                        Text(feedback.replacingOccurrences(of: "<[^>]+>", with: "", options: .regularExpression))
                            .font(.body)
                            .padding()
                            .background(Color.gray.opacity(0.2))
                            .cornerRadius(10)
                    } else {
                        Text(feedback)
                            .font(.body)
                            .padding()
                            .background(Color.gray.opacity(0.2))
                            .cornerRadius(10)
                    }
                    
                    Spacer()
                }
                .padding()
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .navigationBarTrailing) {
                    Button("Done") {
                        dismiss()
                    }
                }
            }
        }
    }
}

#Preview {
    WorkoutSessionView(webSocketManager: WebSocketManager())
}
