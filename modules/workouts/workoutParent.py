

class Workout:
    def __init__(self,goal_reps:int,ldmrk_res,left_side:bool):
       # parameters common to all workout child classes
        self.down = False
        self.goal_reps = goal_reps
        self.ldmrk_res = ldmrk_res
        self.left_side = left_side
        self.form = None
        self.fix_form = None

    def set_res(self,ldmrk_res):
        '''
        description: set the pose landmarks result from the mediapipe model
        input: ldmrk_res: list of pose landmarks
        output: None
        '''
        self.ldmrk_res = ldmrk_res