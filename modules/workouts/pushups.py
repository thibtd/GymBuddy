from modules.workouts.workoutParent import Workout
import numpy as np
from numpy import ndarray
from typing import List, Dict, Any


class PushUps(Workout):
    """Pushups workout class implementing the Workout interface."""
    def update_indices(self) -> None:
        self.shoulder_idx: int = 11 if self.left_side else 12
        self.elbow_idx: int = 13 if self.left_side else 14
        self.wrist_idx: int = 15 if self.left_side else 16
        self.hip_idx: int = 23 if self.left_side else 24
        self.ankle_idx: int = 27 if self.left_side else 28
        self.knee_idx: int = 25 if self.left_side else 26
        self.toes_idx: int = 31 if self.left_side else 32

    
    def __init__(self, goal_reps: int, ldmrk_res, left_side: bool,strictness_crit:str = "loose") -> None:
        """Pushups workout class."""
        super().__init__(goal_reps, ldmrk_res, left_side,strictness_crit)
        


    def count_reps(self) -> int:
        # handles the logic of when to determine if pu is counted
        count: int = 0
        angle:float = self._compute_and_store_angle('elbow',self.wrist_idx, self.elbow_idx, self.shoulder_idx)
        if self.form:
            down_threshold: int = 90
            up_threshold: int = 150

            if angle <= down_threshold:
                if not self.down:
                    self.down = True
            elif angle >= up_threshold:
                if self.down:
                    self.down = False
                    self.form = False
                    count = 1
        print("down", self.down)
        return count
    
    



    def get_form(self) -> bool:
        """starting form for pu:
        1) shoulders above wrists
        2) knees not on floor (y knees > y wrist)
        3) hips wide open
        """
        # get the landmarks
        wrist= self._get_landmark(self.wrist_idx)
        shoulder= self._get_landmark(self.shoulder_idx)
        ankle= self._get_landmark(self.ankle_idx)
        knee = self._get_landmark(self.knee_idx)
        toes = self._get_landmark(self.toes_idx)


        # compute the angles
        self._compute_and_store_angle('body', self.shoulder_idx, self.hip_idx, self.knee_idx)
        angle_elbow: float = self.angles["elbow"]

        # compute form criteria
        variation:int = 5
        goal_all_body:int = 180 
        deviations:float = self.get_strictness_deviation()
        elbow_threshold:float = 165
       
        #compute the form criterions 
        body_aligned:bool = (self.angles['body'] > goal_all_body - (deviations + variation) and 
                             self.angles['body'] < goal_all_body + deviations + variation)
        shoulders_aligned:bool = ( np.round(wrist.x, 1) == np.round(shoulder.x, 1) or 
                                  angle_elbow <=160)
                                  
        knees_up:bool = np.round(knee.y, 2) < min(np.round(wrist.y, 2),np.round(toes.y, 2))
        print(f'knees:{np.round(knee.y, 2)}, wrist: {np.round(wrist.y, 2)}, toes: {np.round(toes.y, 2)}')

        #Determine form and fixes
        form_issues:list = []
        if not shoulders_aligned:
            form_issues.append("shoulders not aligned with wrists")
        if not knees_up:
            form_issues.append("knees on floor")
        if not body_aligned:
            form_issues.append("body not straight")
        
        # Set form feedback

        if form_issues:
            self.fix_form = ", ".join(form_issues)
            return False
        
        else:
            self.fix_form = "Good form"
            return True
        
    def get_display_angles(self) -> List[Dict[str, Any]]:
        """Returns data for angles to be displayed (Elbow and Body)."""
        display_list = []
        if "elbow" in self.angles:
            display_list.append({
                "name": "elbow",
                "value": self.angles["elbow"],
                "joint_indices": (self.wrist_idx, self.elbow_idx, self.shoulder_idx)
            })
        if "body" in self.angles: 
             display_list.append({
                 "name": "body",
                 "value": self.angles["body"],
                 "joint_indices": (self.shoulder_idx, self.hip_idx, self.ankle_idx)
             })
        return display_list

    def _get_indices(self)-> Dict[str, int]:
        """Returns the indices of the landmarks used for pushups."""
        return {
            "shoulder": self.shoulder_idx,
            "elbow": self.elbow_idx,
            "wrist": self.wrist_idx,
            "hip": self.hip_idx,
            "ankle": self.ankle_idx,
            "knee": self.knee_idx,
            "toes": self.toes_idx
        }