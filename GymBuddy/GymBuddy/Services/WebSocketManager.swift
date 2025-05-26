//
//  WebSocketManager.swift
//  GymBuddy
//
//  Created by Thibaut Donis on 24/05/2025.
//

import Foundation
import Combine

class WebSocketManager: NSObject, ObservableObject {
    @Published var isConnected = false
    @Published var currentMessage = ""
    @Published var workoutStatus: WorkoutStatus = .idle
    @Published var currentReps = 0
    @Published var goalReps = 0
    @Published var workoutHistory: [String] = []
    @Published var feedback = ""
    @Published var receivedImage: Data?
    
    private var webSocket: URLSessionWebSocketTask?
    private var urlSession: URLSession?
    
    // Server configuration
    @Published var serverHost = "127.0.0.1"
    @Published var serverPort = "8000"
    
    private var serverURL: String {
        "ws://\(serverHost):\(serverPort)/ws"
    }
    
    override init() {
        super.init()
        urlSession = URLSession(configuration: .default, delegate: self, delegateQueue: nil)
    }
    
    func connect() {
        guard let url = URL(string: serverURL) else {
            workoutStatus = .error("Invalid server URL")
            return
        }
        
        webSocket = urlSession?.webSocketTask(with: url)
        webSocket?.resume()
        receiveMessage()
    }
    
    func disconnect() {
        webSocket?.cancel(with: .goingAway, reason: nil)
        webSocket = nil
        isConnected = false
    }
    
    private func receiveMessage() {
        webSocket?.receive { [weak self] result in
            switch result {
            case .success(let message):
                DispatchQueue.main.async {
                    self?.handleMessage(message)
                }
                self?.receiveMessage() // Continue listening
            case .failure(let error):
                DispatchQueue.main.async {
                    self?.workoutStatus = .error("Connection error: \(error.localizedDescription)")
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
            handleBinaryMessage(data)
        @unknown default:
            break
        }
    }
    
    private func handleTextMessage(_ text: String) {
        guard let data = text.data(using: .utf8),
              let message = try? JSONDecoder().decode(WebSocketMessage.self, from: data) else {
            return
        }
        
        switch message.type {
        case "data":
            if let messageText = message.message {
                currentMessage = messageText
                // Parse rep count from message
                parseRepCount(from: messageText)
            }
            if let status = message.status {
                updateWorkoutStatus(status)
            }
        case "history":
            if let historyText = message.message {
                workoutHistory = historyText.components(separatedBy: "<br>").filter { !$0.isEmpty }
            }
        case "feedback":
            if let feedbackText = message.message {
                feedback = feedbackText
            }
        default:
            break
        }
    }
    
    private func handleBinaryMessage(_ data: Data) {
        // This is the video frame data
        receivedImage = data
    }
    
    private func parseRepCount(from message: String) {
        // Extract current reps from messages like "Completed 5 out of 10 push-ups, 5 to go!"
        let components = message.components(separatedBy: " ")
        if let completedIndex = components.firstIndex(of: "Completed"),
           completedIndex + 1 < components.count,
           let reps = Int(components[completedIndex + 1]) {
            currentReps = reps
        }
        
        // Extract goal reps
        if let outIndex = components.firstIndex(of: "out"),
           outIndex + 2 < components.count,
           let goal = Int(components[outIndex + 2]) {
            goalReps = goal
        }
    }
    
    private func updateWorkoutStatus(_ status: String) {
        switch status {
        case "in_progress":
            workoutStatus = .inProgress
        case "completed":
            workoutStatus = .completed
        default:
            workoutStatus = .idle
        }
    }
    
    // MARK: - Message Sending
    func sendWorkoutSelection(_ workout: WorkoutType) {
        sendMessage(WebSocketMessage(type: "workout", value: workout.rawValue))
    }
    
    func sendRepsSelection(_ reps: Int) {
        sendMessage(WebSocketMessage(type: "reps", value: String(reps)))
    }
    
    func sendStrictnessSelection(_ strictness: StrictnessLevel) {
        sendMessage(WebSocketMessage(type: "strictness", value: strictness.rawValue))
    }
    
    func startWorkout() {
        sendMessage(WebSocketMessage(type: "start"))
        workoutStatus = .preparing
    }
    
    private func sendMessage(_ message: WebSocketMessage) {
        guard let data = try? JSONEncoder().encode(message),
              let string = String(data: data, encoding: .utf8) else {
            return
        }
        
        webSocket?.send(.string(string)) { error in
            if let error = error {
                DispatchQueue.main.async {
                    self.workoutStatus = .error("Failed to send message: \(error.localizedDescription)")
                }
            }
        }
    }
}

// MARK: - URLSessionWebSocketDelegate
extension WebSocketManager: URLSessionWebSocketDelegate {
    func urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask, didOpenWithProtocol protocol: String?) {
        DispatchQueue.main.async {
            self.isConnected = true
            self.workoutStatus = .idle
        }
    }
    
    func urlSession(_ session: URLSession, webSocketTask: URLSessionWebSocketTask, didCloseWith closeCode: URLSessionWebSocketTask.CloseCode, reason: Data?) {
        DispatchQueue.main.async {
            self.isConnected = false
            self.workoutStatus = .idle
        }
    }
}
