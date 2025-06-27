import pytest
from modules.utils import compute_angle, is_left_side, extend_row, Landmark
from pydantic import ValidationError

### tests for the Landmark class
INVALID_INPUT_LANDMARKS = [
    "not a number",
    None,          
    [1, 2],        
    {"x": 1}
]
BASE_LANDMARK = [(Landmark(x=1,y=1),1,1)]
def test_Landmark_all_params():
    landmark1 = Landmark(x=1,y=1,visibility=0.2)
    assert landmark1.x == 1 and landmark1.y ==1, landmark1.visibility==0.2

@pytest.mark.parametrize('ldmk, x,y',[(Landmark(x=1,y=1),1,1)])
def test_landmarks_only_req_params(ldmk,x,y):
    assert ldmk.x ==x, ldmk.y ==y

def test_landmarks__visibility_def_0():
    ldmk = Landmark(x=1,y=1)
    assert ldmk.visibility ==0

@pytest.mark.parametrize("invalid_x_value",INVALID_INPUT_LANDMARKS )
def test_Landmark_invalid_x_input(invalid_x_value):
     with pytest.raises(ValidationError):
        Landmark(x=invalid_x_value,y=1)

@pytest.mark.parametrize("invalid_y_value",INVALID_INPUT_LANDMARKS)
def test_landmark_invalid_y_input(invalid_y_value):
    with pytest.raises(ValidationError):
        Landmark(x=1,y=invalid_y_value)

### tests for compute_angle function
@pytest.mark.parametrize("p1,p2,p3, correct_angle",[
    (Landmark(x=0,y=0),Landmark(x=1,y=1),Landmark(x=1,y=0),45),
    (Landmark(x=0,y=0),Landmark(x=0,y=1),Landmark(x=1,y=1),90),
    (Landmark(x=0,y=0),Landmark(x=0,y=1),Landmark(x=1,y=2),135),
    (Landmark(x=0,y=0),Landmark(x=0,y=1),Landmark(x=0,y=2),180)
])
def test_compute_angle_correct(p1,p2,p3,correct_angle):
    '''Test 4 different angles, acute, right, obtuse, straight.
    The output should be correct.
    '''
    print(p1,p2,p3,correct_angle)
    assert compute_angle(p1,p2,p3) == pytest.approx(correct_angle)

def test_compute_angle_none_input():
    """One of the points is None"""
    p1= Landmark(x=0,y=0)
    p2 = Landmark(x=1,y=0)
    p3 = None 
    with pytest.raises(TypeError,match="Input points must be Landmark objects"):
        compute_angle(p1,p2,p3)


### Tests for is_left_side funtion
MOCK_LANDMARK_LIST = [Landmark(x=0, y=0) for _ in range(15)]

def test_is_left_side_left():
    pose_ldmk = MOCK_LANDMARK_LIST
    pose_ldmk[13].visibility=0.75
    pose_ldmk[14].visibility=0.23
    assert is_left_side(pose_ldmk) == True

def test_is_left_side_right():
    pose_ldmk = MOCK_LANDMARK_LIST
    pose_ldmk[13].visibility=0.25
    pose_ldmk[14].visibility=0.63
    assert is_left_side(pose_ldmk) == False

def test_is_left_front():
    pose_ldmk = MOCK_LANDMARK_LIST
    pose_ldmk[13].visibility=0.5
    pose_ldmk[14].visibility=0.5
    assert is_left_side(pose_ldmk)==False

def test_is_left_empty_list():
    with pytest.raises(TypeError):
        is_left_side(pose_landmarks=None)
    

def test_is_left_list_too_short():
    short_list = MOCK_LANDMARK_LIST[:12]
    with pytest.raises(IndexError):
        is_left_side(short_list)
    with pytest.raises(IndexError):
        is_left_side([])

def test_is_left_shoulder_is_none():
    ldmk = MOCK_LANDMARK_LIST
    ldmk[13]=None
    with pytest.raises(AttributeError):
        is_left_side(ldmk)
    

### Tests For extend row function
def test_extend_row_with_typical_data():
    """
    Verifies that a typical list of landmark dictionaries is flattened correctly.
    """
    # Arrange: Create a list of landmark-like dictionaries
    input_row = [
        {"x": 0.1, "y": 0.2, "z": 0.3},
        {"x": 0.4, "y": 0.5, "z": 0.6},
        {"x": 0.7, "y": 0.8, "z": 0.9}
    ]
    expected_output = [0.1, 0.2, 0.4, 0.5, 0.7, 0.8]

    # Act: Call the function with the test data
    result = extend_row(input_row)

    # Assert: Check if the result matches the expected flat list
    assert result == expected_output

def test_extend_row_ignores_extra_keys():
    """
    Ensures that the function only extracts 'x' and 'y' keys, ignoring others.
    """
    # Arrange: Add extra keys like 'visibility'
    input_row = [
        {"x": 0.1, "y": 0.2, "visibility": 0.99},
        {"x": 0.4, "y": 0.5, "some_other_key": "test"}
    ]
    expected_output = [0.1, 0.2, 0.4, 0.5]

    # Act
    result = extend_row(input_row)

    # Assert
    assert result == expected_output


# --- Test for Edge Cases ---

def test_extend_row_handles_empty_list():
    """
    Verifies that providing an empty list results in an empty list.
    """
    # Arrange
    input_row = []
    expected_output = []

    # Act
    result = extend_row(input_row)

    # Assert
    assert result == expected_output


# --- Tests for Bad Input and Error Handling ---

@pytest.mark.parametrize("bad_input", [
    None,
    {"x": 1, "y": 2}, # A single dictionary, not a list of them
    "a string",
    123
])
def test_extend_row_raises_type_error_for_non_list_input(bad_input):
    """
    Verifies that the function raises a TypeError if the input is not iterable (a list).
    """
    with pytest.raises(TypeError):
        extend_row(bad_input)


def test_extend_row_raises_key_error_for_missing_coordinate():
    """
    Verifies that a KeyError is raised if a dictionary in the list is missing an 'x' or 'y' key.
    """
    # Arrange: A list where one dictionary is missing the 'y' key
    input_row_with_missing_key = [
        {"x": 0.1, "y": 0.2},
        {"x": 0.4}  # Missing 'y'
    ]

    # Act & Assert
    with pytest.raises(KeyError):
        extend_row(input_row_with_missing_key)


def test_extend_row_raises_type_error_for_non_dict_in_list():
    """
    Verifies that a TypeError is raised if an element in the list is not a dictionary.
    """
    # Arrange: A list containing a non-dictionary element
    input_row_with_bad_element = [
        {"x": 0.1, "y": 0.2},
        123 # This integer is not a dictionary
    ]

    # Act & Assert: This will fail when trying to do landmark["x"] on the integer 123.
    with pytest.raises(TypeError):
        extend_row(input_row_with_bad_element)
