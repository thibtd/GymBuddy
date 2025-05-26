//
//  SettingsView.swift
//  GymBuddy
//
//  Created by Thibaut Donis on 24/05/2025.
//

import SwiftUI

struct SettingsView: View {
    @ObservedObject var webSocketManager: WebSocketManager
    @State private var serverURL = "127.0.0.1:8000"
    @State private var showingInfo = false
    
    var body: some View {
        NavigationView {
            Form {
                Section(header: Text("Connection")) {
                    HStack {
                        Text("Server URL")
                        Spacer()
                        TextField("Enter server URL", text: $serverURL)
                            .textFieldStyle(RoundedBorderTextFieldStyle())
                            .frame(width: 150)
                    }
                    
                    HStack {
                        Text("Status")
                        Spacer()
                        HStack {
                            Circle()
                                .fill(webSocketManager.isConnected ? .green : .red)
                                .frame(width: 8, height: 8)
                            Text(webSocketManager.isConnected ? "Connected" : "Disconnected")
                                .foregroundColor(.secondary)
                        }
                    }
                    
                    Button(webSocketManager.isConnected ? "Disconnect" : "Connect") {
                        if webSocketManager.isConnected {
                            webSocketManager.disconnect()
                        } else {
                            webSocketManager.connect()
                        }
                    }
                }
                
                Section(header: Text("About")) {
                    Button("App Information") {
                        showingInfo = true
                    }
                    
                    HStack {
                        Text("Version")
                        Spacer()
                        Text("1.0.0")
                            .foregroundColor(.secondary)
                    }
                }
                
                Section(header: Text("Support")) {
                    Link("GitHub Repository", destination: URL(string: "https://github.com")!)
                    
                    Button("Reset App Data") {
                        // Reset functionality would go here
                    }
                    .foregroundColor(.red)
                }
            }
            .navigationTitle("Settings")
            .navigationBarTitleDisplayMode(.large)
        }
        .sheet(isPresented: $showingInfo) {
            AppInfoView()
        }
    }
}

struct AppInfoView: View {
    @Environment(\.dismiss) private var dismiss
    
    var body: some View {
        NavigationView {
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    VStack(spacing: 10) {
                        Image(systemName: "figure.strengthtraining.traditional")
                            .font(.system(size: 60))
                            .foregroundColor(.blue)
                        
                        Text("GymBuddy")
                            .font(.largeTitle)
                            .fontWeight(.bold)
                        
                        Text("Your AI-Powered Personal Trainer")
                            .font(.headline)
                            .foregroundColor(.secondary)
                            .multilineTextAlignment(.center)
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.bottom)
                    
                    VStack(alignment: .leading, spacing: 15) {
                        Text("Features")
                            .font(.headline)
                            .fontWeight(.semibold)
                        
                        FeatureRowView(
                            icon: "eye.fill",
                            title: "Real-Time Pose Estimation",
                            description: "Advanced computer vision tracks your movements"
                        )
                        
                        FeatureRowView(
                            icon: "checkmark.circle.fill",
                            title: "Form Feedback",
                            description: "Get instant corrections to improve your technique"
                        )
                        
                        FeatureRowView(
                            icon: "number.circle.fill",
                            title: "Automatic Rep Counting",
                            description: "Focus on your workout while we count for you"
                        )
                        
                        FeatureRowView(
                            icon: "chart.line.uptrend.xyaxis",
                            title: "Progress Tracking",
                            description: "Monitor your fitness journey over time"
                        )
                    }
                    
                    Spacer()
                }
                .padding()
            }
            .navigationTitle("About GymBuddy")
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

struct FeatureRowView: View {
    let icon: String
    let title: String
    let description: String
    
    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Image(systemName: icon)
                .font(.title2)
                .foregroundColor(.blue)
                .frame(width: 24)
            
            VStack(alignment: .leading, spacing: 2) {
                Text(title)
                    .font(.headline)
                    .fontWeight(.medium)
                
                Text(description)
                    .font(.body)
                    .foregroundColor(.secondary)
            }
            
            Spacer()
        }
    }
}

struct SettingsView_Previews: PreviewProvider {
    static var previews: some View {
        SettingsView(webSocketManager: WebSocketManager())
    }
}
