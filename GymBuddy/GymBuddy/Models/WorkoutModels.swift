//
//  WorkoutModels.swift
//  GymBuddy
//
//  Created by Thibaut Donis on 24/05/2025.
//

import Foundation

// MARK: - Workout Types
enum WorkoutType: String, CaseIterable, Identifiable {
    case pushUps = "push-ups"
    case squats = "squats"
    case abs = "abs"
    
    var id: String { rawValue }
    
    var displayName: String {
        switch self {
        case .pushUps: return "Push-ups"
        case .squats: return "Squats"
        case .abs: return "Abs"
        }
    }
    
    var icon: String {
        switch self {
        case .pushUps: return "figure.strengthtraining.traditional"
        case .squats: return "figure.squat"
        case .abs: return "figure.core.training"
        }
    }
}

// MARK: - Strictness Levels
enum StrictnessLevel: String, CaseIterable, Identifiable {
    case loose = "loose"
    case medium = "medium"
    case strict = "strict"
    
    var id: String { rawValue }
    
    var displayName: String {
        switch self {
        case .loose: return "Beginner"
        case .medium: return "Intermediate"
        case .strict: return "Advanced"
        }
    }
    
    var color: String {
        switch self {
        case .loose: return "green"
        case .medium: return "orange"
        case .strict: return "red"
        }
    }
}

// MARK: - WebSocket Message Types
struct WebSocketMessage: Codable {
    let type: String
    let value: String?
    let message: String?
    let status: String?
    
    init(type: String, value: String? = nil, message: String? = nil, status: String? = nil) {
        self.type = type
        self.value = value
        self.message = message
        self.status = status
    }
}

// MARK: - Workout Status
enum WorkoutStatus: Equatable {
    case idle
    case preparing
    case inProgress
    case completed
    case error(String)
    
    var displayText: String {
        switch self {
        case .idle:
            return "Ready to start"
        case .preparing:
            return "Preparing workout..."
        case .inProgress:
            return "Workout in progress"
        case .completed:
            return "Workout completed!"
        case .error(let message):
            return "Error: \(message)"
        }
    }
    
    var color: String {
        switch self {
        case .idle:
            return "blue"
        case .preparing:
            return "orange"
        case .inProgress:
            return "green"
        case .completed:
            return "purple"
        case .error:
            return "red"
        }
    }
}

// MARK: - Workout Session
struct WorkoutSession: Identifiable {
    let id = UUID()
    let workoutType: WorkoutType
    let reps: Int
    let strictness: StrictnessLevel
    let date: Date
}
