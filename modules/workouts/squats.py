from modules.workouts.workoutParent import Workout
import numpy as np
from numpy import ndarray
from typing import List, Dict, Any


class Squats(Workout):
    """Squats workout class implementing the Workout interface."""
    def update_indices(self) -> None:
        self.shoulder_idx: int = 11 if self.left_side else 12
        self.elbow_idx: int = 13 if self.left_side else 14
        self.wrist_idx: int = 15 if self.left_side else 16
        self.hip_idx: int = 23 if self.left_side else 24
        self.ankle_idx: int = 27 if self.left_side else 28
        self.knee_idx: int = 25 if self.left_side else 26
        self.toes_idx: int = 31 if self.left_side else 32