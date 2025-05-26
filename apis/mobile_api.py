from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

mobile_router = APIRouter(prefix="/api/mobile", tags=["mobile"])

# Data models for mobile API
class WorkoutRequest(BaseModel):
    workout_type: str
    reps: int
    strictness: str = "medium"

class WorkoutResult(BaseModel):
    id: str
    workout_type: str
    reps_completed: int
    target_reps: int
    duration: float
    feedback: Optional[str] = None
    created_at: datetime

class WorkoutHistory(BaseModel):
    workouts: List[WorkoutResult]
    total_workouts: int

@mobile_router.get("/health")
async def health_check():
    """Health check endpoint for mobile app"""
    return {"status": "healthy", "service": "GymBuddy Mobile API"}

@mobile_router.get("/workouts/types")
async def get_workout_types():
    """Get available workout types"""
    return {
        "workout_types": [
            {"id": "push-ups", "name": "Push-ups", "icon": "figure.strengthtraining.traditional"},
            {"id": "squats", "name": "Squats", "icon": "figure.squat"},
            {"id": "abs", "name": "Abs", "icon": "figure.core.training"}
        ]
    }

@mobile_router.get("/strictness/levels")
async def get_strictness_levels():
    """Get available strictness levels"""
    return {
        "strictness_levels": [
            {"id": "loose", "name": "Beginner", "description": "More forgiving form detection"},
            {"id": "medium", "name": "Intermediate", "description": "Balanced form requirements"},
            {"id": "strict", "name": "Advanced", "description": "Perfect form required"}
        ]
    }

@mobile_router.post("/workouts/validate")
async def validate_workout_request(workout: WorkoutRequest):
    """Validate workout request parameters"""
    valid_workouts = ["push-ups", "squats", "abs"]
    valid_strictness = ["loose", "medium", "strict"]
    
    if workout.workout_type not in valid_workouts:
        raise HTTPException(status_code=400, detail="Invalid workout type")
    
    if workout.strictness not in valid_strictness:
        raise HTTPException(status_code=400, detail="Invalid strictness level")
    
    if workout.reps < 1 or workout.reps > 100:
        raise HTTPException(status_code=400, detail="Reps must be between 1 and 100")
    
    return {"valid": True, "message": "Workout request is valid"}

@mobile_router.get("/server/info")
async def get_server_info():
    """Get server information for mobile app"""
    return {
        "server_name": "GymBuddy Backend",
        "version": "1.0.0",
        "websocket_endpoint": "/ws",
        "capabilities": ["real_time_pose_detection", "rep_counting", "form_feedback"]
    }
