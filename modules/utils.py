import numpy as np
import math 
import cv2
from pydantic import BaseModel

class Landmark(BaseModel):
    x: float
    y: float
    visibility: float = 1.0
    
    class Config:
        arbitrary_types_allowed = True


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
        left_elbow = Landmark(x=pose_landmarks[13].x, y=pose_landmarks[13].y, visibility=pose_landmarks[13].visibility)
        right_elbow = Landmark(x=pose_landmarks[14].x, y=pose_landmarks[14].y, visibility=pose_landmarks[14].visibility)
        if left_elbow.visibility > right_elbow.visibility:
            print("left", left_elbow)
            print("right", right_elbow)
            return True
        else:
            print("left", left_elbow)
            print("right", right_elbow)
            return False
    return False


def draw_angle_arc(image, point1:list, point2:list, point3:list, angle_degrees:float, color:tuple, thickness:int=2, radius_factor:float=0.15)-> None:
    """
    Draws an arc representing the angle between three points on the image.

    Args:
        image: The image to draw on.
        pt1: Coordinates (x, y) of the first point (e.g., wrist).
        pt2: Coordinates (x, y) of the joint/vertex point (e.g., elbow).
        pt3: Coordinates (x, y) of the third point (e.g., shoulder).
        angle_degrees: The angle value in degrees (used for display, not arc calculation).
        color: The color of the arc (B, G, R).
        thickness: The thickness of the arc line.
        radius_factor: Determines the arc radius relative to the shorter limb length.
    """
    # Convert points to numpy arrays for vector operations
    pt1:np.ndarray = np.array(point1)
    pt2:np.ndarray = np.array(point2) # Joint
    pt3:np.ndarray = np.array(point3)

    # Calculate vectors from the joint
    v21 = pt1 - pt2
    v23 = pt3 - pt2

    # Calculate lengths of the limbs connected to the joint
    len21 = np.linalg.norm(v21)
    len23 = np.linalg.norm(v23)

    # Prevent division by zero or tiny radius
    if len21 < 1 or len23 < 1:
        # print("Warning: Limb length too small for arc drawing.")
        return

    # Determine arc radius based on the shorter limb
    radius = int(min(len21, len23) * radius_factor)
    if radius < 5: # Minimum radius for visibility
        radius = 5
    elif radius > 50: # Maximum radius to avoid being too large
        radius = 50

    # Calculate the angles of the two vectors relative to the positive x-axis
    # atan2 handles quadrants correctly and returns radians [-pi, pi]
    angle21 = math.atan2(v21[1], v21[0])
    angle23 = math.atan2(v23[1], v23[0])

    # Convert radians to degrees for cv2.ellipse [0, 360]
    # OpenCV's angles are measured counter-clockwise from the 3-o'clock position
    start_angle_deg = math.degrees(angle21)
    end_angle_deg = math.degrees(angle23)

  
    # Draw the ellipse (arc)
    # Axes lengths are (radius, radius) for a circular arc
    # Angle is the rotation of the ellipse (0 for a standard arc)
    # startAngle and endAngle define the arc sweep
    axes = (radius, radius)
    cv2.ellipse(image, tuple(pt2.astype(int)), axes, 0, start_angle_deg, end_angle_deg, color, thickness, lineType=cv2.LINE_AA)

    # Draw the angle value near the arc joint
    text_pos = tuple((pt2 + np.array([radius + 5, -radius - 5])).astype(int))
    cv2.putText(image, f"{angle_degrees:.0f}", text_pos, cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
