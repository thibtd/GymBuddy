from abc import ABC, abstractmethod
from typing import List, Dict, Tuple, Any
from modules.utils import Landmark
class Workout:
    """ Base class for all workout types."""
    def __init__(self, goal_reps: int, ldmrk_res, left_side: bool,strictness_crit:str = "loose"):
        # parameters common to all workout child classes
        self.down:bool = False
        self.goal_reps:int = goal_reps
        self.ldmrk_res = ldmrk_res
        self.left_side:bool = left_side
        self.strictness_crit:str =  strictness_crit
        self.down:bool = False
        self.form:bool = False
        self.fix_form:str = "Checking form..."
        self.angles:Dict[str, float]={}

        self.update_indices()

    def set_res(self, ldmrk_res):
        """
        description: set the pose landmarks result from the mediapipe model
        input: ldmrk_res: list of pose landmarks
        output: None
        """
        self.ldmrk_res = ldmrk_res

    def get_strictness_deviation(self)->float:
        deviation_all_body:dict = {'strict': 5, 'moderate':10, 'loose': 15}
        return deviation_all_body[self.strictness_crit]
    
    @abstractmethod
    def update_indices(self):
        """Abstract method to set the correct landmark indices based on self.left_side."""
        pass

    @abstractmethod
    def count_reps(self) -> int:
        """Abstract method to calculate and return rep increment for the current frame."""
        pass

    @abstractmethod
    def get_form(self) -> bool:
        """Abstract method to check form, update self.form and self.fix_form, and return form status."""
        pass
    
    @abstractmethod
    def get_display_angles(self) -> List[Dict[str, Any]]:
        """
        Abstract method to return data needed for displaying angles.
        Each dict should contain: 'name', 'value', 'joint_indices'.
        """
        pass

    def _get_landmark(self, index: int)->Landmark:
        """Helper to safely get a landmark from the results."""
        if self.ldmrk_res and len(self.ldmrk_res) > 0 and len(self.ldmrk_res[0]) > index:
            return Landmark(x=self.ldmrk_res[0][index].x,
                            y=self.ldmrk_res[0][index].y,
                            visibility=self.ldmrk_res[0][index].visibility)
        raise ValueError(f"Landmark index {index} out of range for the current results.")

    def _compute_and_store_angle(self, name: str, idx1: int, idx2: int, idx3: int) -> float:
        """Helper to compute angle between three landmarks and store it."""
        pt1:Landmark = self._get_landmark(idx1)
        pt2:Landmark = self._get_landmark(idx2)
        pt3:Landmark = self._get_landmark(idx3)

        if pt1 and pt2 and pt3:
            from modules.utils import compute_angle
            angle_value = compute_angle(pt1, pt2, pt3)
            self.angles[name] = angle_value
            return angle_value
        else:
            self.angles[name] = 0.0 # Default if landmarks missing
            return 0.0
    
    @abstractmethod
    def _get_indices(self) -> Dict[str, int]:
        """
        Returns the indices of the landmarks used for the workout.
        This is a placeholder and should be overridden in child classes.
        """
        pass