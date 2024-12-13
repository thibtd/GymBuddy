import numpy as np


def compute_angle(point1:list, point2:list, point3:list) -> np.ndarray:
    '''
    description: takes three 2D points with attributes x and y and computes the angle between the vector point1point2 and point2point3
    input: point1, point2, point3
    output: angle in degrees    
    '''
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
        left_elbow = pose_landmarks[13]
        right_elbow = pose_landmarks[14]
        if left_elbow.visibility > right_elbow.visibility:
            print("left", left_elbow)
            print("right", right_elbow)
            return True
        else:
            print("left", left_elbow)
            print("right", right_elbow)
            return False
