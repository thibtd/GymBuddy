from modules.utils import compute_angle
from modules.workouts.wourkoutParent import Workout
import numpy as np 
from numpy import ndarray

class PushUps(Workout):
    def __init__(self,goal_reps:int,ldmrk_res,left_side:bool):
        super().__init__(goal_reps,ldmrk_res,left_side)
        self.shoulder_idx = 11 if self.left_side else 12
        self.elbow_idx = 13 if self.left_side else 14
        self.wrist_idx = 15 if self.left_side else 16 
        self.hip_idx = 23 if self.left_side else 24 
        self.knee_idx = 25 if self.left_side else 26
        self.form = None
        self.fix_form = None

    def count_reps(self)->int:
        # handles the logic of when to determine if pu is counted 
        angle: ndarray = np.zeros((0, 1))
        count:int = 0   
        for idx in range(len(self.ldmrk_res)):
            pose_landmarks = self.ldmrk_res[idx]
            wrist, elbow, shoulder,knee, hip = (
                pose_landmarks[self.wrist_idx],
                pose_landmarks[self.elbow_idx],
                pose_landmarks[self.shoulder_idx],
                pose_landmarks[self.knee_idx],
                pose_landmarks[self.hip_idx]
            )
            angle = compute_angle(wrist,elbow,shoulder)
        if self.form:
            if angle.size > 0:
                if angle <= 90:
                    if self.down:
                        pass
                    else:
                        self.down = True
                elif angle >= 120:
                    if not self.down:
                        pass
                    else:
                        self.down = False
                        count = 1
        print('down',self.down)
        return count
    
    def get_form(self)->bool:
        ''' starting form for pu: 
            1) shoulders above wrists 
            2) knees not on floor (y knees > y wrist)
            3) hips wide open 
            '''
        # TODO: add fixes to the position i.e. why is form not correct and display it to the user.
        #(0,0) is top left of image and (1,1) is bottom right
        #if form was true in the previous frame, return true
    
        pose_landmarks = self.ldmrk_res[0]
        wrist, elbow, shoulder,knee, hip = (
            pose_landmarks[self.wrist_idx],
            pose_landmarks[self.elbow_idx],
            pose_landmarks[self.shoulder_idx],
            pose_landmarks[self.knee_idx],
            pose_landmarks[self.hip_idx]
        )
        out = False
        print(f'wrist ({np.round(wrist.x,2),np.round(wrist.y,2)}),shoulder({np.round(shoulder.x,2),np.round(shoulder.y,2)}) \
              knee({np.round(knee.x,2),np.round(knee.y,2)}),hip({np.round(hip.x,2),np.round(hip.y,2)})')
        if np.round(wrist.x,1) == np.round(shoulder.x,1):
            if np.round(knee.y,2)< np.round(wrist.y,2):
                if compute_angle(shoulder,hip,knee) > 110:
                    self.fix_form = None
                    out=  True
                else:
                    self.fix_form = "hips not wide open"
            else:
                self.fix_form = "knees on floor"
        else:
            self.fix_form = "shoulders not above wrists" 
        return out