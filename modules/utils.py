import numpy as np
from pydantic import BaseModel


class Landmark(BaseModel):
    x: float
    y: float
    visibility: float = 0


def compute_angle(point1: Landmark, point2: Landmark, point3: Landmark) -> float:
    """
    description: takes three 2D points with attributes x and y and computes the angle between the vector point1point2 and point2point3
    input: point1, point2, point3
    output: angle in degrees
    """
    if not all(isinstance(p, Landmark) for p in [point1, point2, point3]):
        raise TypeError("Input points must be Landmark objects")
    
    vec1 = np.array([point1.x, point1.y]) - np.array([point2.x, point2.y])
    vec2 = np.array([point3.x, point3.y]) - np.array([point2.x, point2.y])

    # Dot product
    dot_product = np.dot(vec1, vec2)

    # Magnitude of vectors
    mag_vec1 = np.sqrt(np.dot(vec1, vec1))
    mag_vec2 = np.sqrt(np.dot(vec2, vec2))

    # Cosine of angle
    cos_angle = dot_product / (mag_vec1 * mag_vec2)

    # Angle in radians
    angle_rad = np.arccos(cos_angle)

    # Convert to degrees if needed
    angle_deg = np.degrees(angle_rad)

    return angle_deg


def is_left_side(pose_landmarks: list) -> bool:
    """ Determines which shoulder is more visible on the first frame.
        This is used to asses if the user is face right or left.
        input: pose_landmarks: A list of the NormalizedLandmarks
        output: True if the user is facing left, false if right."""
    if not isinstance(pose_landmarks,list):
        raise TypeError("Input must be a list.")
    
    left_elbow = Landmark(
        x=pose_landmarks[13].x,
        y=pose_landmarks[13].y,
        visibility=pose_landmarks[13].visibility,
    )
    right_elbow = Landmark(
        x=pose_landmarks[14].x,
        y=pose_landmarks[14].y,
        visibility=pose_landmarks[14].visibility,
    )
    if left_elbow.visibility > right_elbow.visibility:
        print("left", left_elbow)
        print("right", right_elbow)
        return True

    print("left", left_elbow)
    print("right", right_elbow)
    return False


def extend_row(row: list[dict[str,float]]) -> list:
    """
    Extend a row of landmarks to a flat list.
    Args:
        row (list): A list of landmarks, where each landmark is a list of [x, y, z].
    Returns:
        list: A flat list of landmarks in the format [landmark_0_x, landmark_0_y, ..., landmark_n_x, landmark_n_y].
    """
    if not isinstance(row,list):
        raise TypeError(f"Input should be a list,{type(row)} received instead.")
    extended_row = []
    print(f'row: {row}')
    for landmark in row:
        print(f'landmark: {landmark}')
        extended_row.extend([landmark["x"], landmark["y"]])
    return extended_row
