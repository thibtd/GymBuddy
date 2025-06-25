import numpy as np
from pydantic import BaseModel


class Landmark(BaseModel):
    x: float
    y: float
    visibility: float = 1.0


def compute_angle(point1: Landmark, point2: Landmark, point3: Landmark) -> float:
    """
    description: takes three 2D points with attributes x and y and computes the angle between the vector point1point2 and point2point3
    input: point1, point2, point3
    output: angle in degrees
    """
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


def is_left_side(res: list) -> bool:
    for idx in range(len(res)):
        pose_landmarks = res[idx]
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


def extend_row(row: dict) -> list:
    """
    Extend a row of landmarks to a flat list.
    Args:
        row (list): A list of landmarks, where each landmark is a list of [x, y, z].
    Returns:
        list: A flat list of landmarks in the format [landmark_0_x, landmark_0_y, ..., landmark_n_x, landmark_n_y].
    """
    extended_row = []
    for landmark in row:
        extended_row.extend([landmark["x"], landmark["y"]])
    return extended_row
