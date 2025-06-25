from modules.workouts.workoutParent import Workout
import numpy as np
from typing import List, Dict, Any
from modules.utils import Landmark


class Squats(Workout):
    """Squats workout class implementing the Workout interface."""

    def update_indices(self) -> None:
        self.shoulder_idx: int = 11 if self.left_side else 12
        self.wrist_idx: int = 15 if self.left_side else 16
        self.hip_idx: int = 23 if self.left_side else 24
        self.ankle_idx: int = 27 if self.left_side else 28
        self.knee_idx: int = 25 if self.left_side else 26
        self.toes_idx: int = 31 if self.left_side else 32

    def count_reps(self) -> int:
        # handles the logic of when to determine if squat is counted
        angle = self._compute_and_store_angle(
            "knee", self.ankle_idx, self.knee_idx, self.hip_idx
        )
        count: int = self.incr_count(angle, down_threshold=90, up_threshold=150)
        print("down", self.down)
        return count

    def get_form(self) -> bool:
        """starting form for squats:
        1) knees to feet:
            if up: knees aligned with ankles
            if down: knees aligned with toes
        2) hips angles:
            if up: hips angle (ankle, knee, hip) == 180
            if down: hips angle (ankle, knee, hip) < 90 > 45
        3) shoulders over ankles
        """
        # get the landmarks
        ankle: Landmark = self._get_landmark(self.ankle_idx)
        knee: Landmark = self._get_landmark(self.knee_idx)
        shoulder: Landmark = self._get_landmark(self.shoulder_idx)
        toes: Landmark = self._get_landmark(self.toes_idx)

        # get the parameters
        variation: int = 5
        deviation: float = self.get_strictness_deviation()
        up_threshold: int = 150
        down_threshold: int = 90

        # Get the angles
        hips_angle: float = self._compute_and_store_angle(
            "hips", self.shoulder_idx, self.hip_idx, self.knee_idx
        )

        # conditions
        knee_to_foot: bool = False
        hips_angles_bool: bool = False
        shoulders_over_ankles: bool = (
            np.round(shoulder.x, 1) - np.round(ankle.x, 1) < variation
        )

        if not self.down:
            knee_to_foot = np.round(knee.x, 1) - np.round(ankle.x, 1) < variation
            if self.angles["knee"] > up_threshold:
                print(f'moving state: {self.angles["knee"]> up_threshold}')
                hips_angles_bool = (180 - hips_angle) < deviation
            else:
                hips_angles_bool = True
        else:
            knee_to_foot = np.round(knee.x, 1) - np.round(toes.x, 1) < variation
            if (
                self.angles["knee"] < up_threshold
                and self.angles["knee"] > down_threshold
            ):
                print(
                    f'moving state: {self.angles["knee"]< up_threshold and self.angles["knee"] > down_threshold}'
                )
                hips_angles_bool = True
            else:
                hips_angles_bool = 45 - deviation < hips_angle < (90 + deviation)

        # Determine form and fixes
        form_issues: list = []
        if not knee_to_foot:
            if self.down:
                form_issues.append("knees not aligned with toes")
            else:
                form_issues.append("knees not aligned with ankles")

        if not hips_angles_bool:
            if self.down:
                form_issues.append(
                    f"hips angle not between 45 and 90 degrees (angle: {hips_angle:.1f} degrees)"
                )
            else:
                form_issues.append(
                    f"You are not standing straight (angle: {hips_angle:.1f} degrees)"
                )

        if not shoulders_over_ankles:
            form_issues.append("your shoulders are not over your ankles")

        # Set form feedback
        if form_issues:
            self.fix_form = ", ".join(form_issues)
            return False
        self.fix_form = "Good form! Keep Going!"
        return True

    def get_display_angles(self) -> List[Dict[str, Any]]:
        """Return data needed for displaying angles."""
        display_list = []
        if "knee" in self.angles:
            display_list.append(
                {
                    "name": "knee",
                    "value": self.angles["knee"],
                    "joint_indices": (self.ankle_idx, self.knee_idx, self.hip_idx),
                }
            )
        if "hips" in self.angles:
            display_list.append(
                {
                    "name": "hip",
                    "value": self.angles["hips"],
                    "joint_indices": (self.shoulder_idx, self.hip_idx, self.knee_idx),
                }
            )

        return display_list

    def get_indices(self) -> Dict[str, int]:
        """Returns the indices of the landmarks used for squats."""
        return {
            "shoulder": self.shoulder_idx,
            "wrist": self.wrist_idx,
            "hip": self.hip_idx,
            "ankle": self.ankle_idx,
            "knee": self.knee_idx,
            "toes": self.toes_idx,
        }
