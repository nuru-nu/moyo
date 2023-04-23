import numpy as np
from filterpy.kalman import KalmanFilter
from scipy.optimize import linear_sum_assignment

# Function to calculate the Intersection over Union (IoU) between two bounding boxes
def bbox_iou(boxA, boxB):
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interArea = max(0, xB - xA + 1) * max(0, yB - yA + 1)
    boxAArea = (boxA[2] - boxA[0] + 1) * (boxA[3] - boxA[1] + 1)
    boxBArea = (boxB[2] - boxB[0] + 1) * (boxB[3] - boxB[1] + 1)
    iou = interArea / float(boxAArea + boxBArea - interArea)

    return iou

# PersonTracker class uses the Kalman filter to track individual people
class PersonTracker:
    def __init__(self, initial_cm, initial_2d_outline, max_nr_frames_missing=3):
        self.max_nr_frames_missing = max_nr_frames_missing
        self.frames_since_seen = 0

        self.kf = KalmanFilter(dim_x=6, dim_z=3)
        self._2d_outline = initial_2d_outline  # Store the 2D outline

        # Initial state
        self.kf.x = np.array([initial_cm[0], initial_cm[1], initial_cm[2], 0, 0, 0])

        # State transition matrix
        self.kf.F = np.array([[1, 0, 0, 1, 0, 0],
                              [0, 1, 0, 0, 1, 0],
                              [0, 0, 1, 0, 0, 1],
                              [0, 0, 0, 1, 0, 0],
                              [0, 0, 0, 0, 1, 0],
                              [0, 0, 0, 0, 0, 1]])

        # Measurement function
        self.kf.H = np.array([[1, 0, 0, 0, 0, 0],
                              [0, 1, 0, 0, 0, 0],
                              [0, 0, 1, 0, 0, 0]])

        # Covariance matrices
        self.kf.R *= 10  # Measurement noise
        self.kf.Q *= 0.1  # Process noise

    def predict(self):
        self.kf.predict()

    def update(self, cm, _2d_outline):
        self.kf.update(cm)
        self._2d_outline = _2d_outline  # Update the 2D outline

    def get_velocity(self):
        vx, vy, vz = self.kf.x[3], self.kf.x[4], self.kf.x[5]
        return vx, vy, vz
    
    def get_position(self):
        x, y, z = self.kf.x[0], self.kf.x[1], self.kf.x[2]
        return x, y, z

# Function to associate data between trackers and people
def associate_data(trackers, people):
    # Initialize the cost matrix with zeros
    cost_matrix = np.zeros((len(trackers), len(people)))

    # Calculate the IoU between each tracker and person
    for tracker_idx, tracker in enumerate(trackers):
        for person_idx, person in enumerate(people):
            iou = bbox_iou(tracker._2d_outline, person["2d_outline"])
            cost_matrix[tracker_idx, person_idx] = 1 - iou

    # Use the Hungarian algorithm to find the best association based on the cost matrix
    row_indices, col_indices = linear_sum_assignment(cost_matrix)

    # Create a list of associated tracker-person pairs
    people_tracker_associations = [
        (tracker_idx, person_idx) 
        for tracker_idx, person_idx in zip(row_indices, col_indices)
    ]

    # Find the new people (if any)
    new_people_indices = [person_idx for person_idx in range(len(people)) if person_idx not in col_indices]

    # Return the list of associations and new people indices
    return people_tracker_associations, new_people_indices


class Tracker():
    def __init__(self, max_iou_threshold=0.3, max_nr_frames_missing=3):
        self.max_iou_threshold = max_iou_threshold  # Threshold to consider a detection as a new person
        self.max_nr_frames_missing = max_nr_frames_missing  # Number of frames to wait before removing a tracker
        self.trackers = []  # List of PersonTracker objects

    def __call__(self, people):
        # Call the associate_data function to get associations and new people
        people_tracker_associations, new_people_indices = associate_data(self.trackers, people)

        # Update trackers with the associated detections
        for tracker_idx, detection_idx in people_tracker_associations:
            self.trackers[tracker_idx].update(people[detection_idx]["cm"],
                                              people[detection_idx]["2d_outline"])
            self.trackers[tracker_idx].frames_since_seen = 0

        # Increment frames_since_seen for all trackers
        for t in self.trackers:
            t.frames_since_seen += 1

        # Remove trackers that have reached the max_nr_frames_missing
        self.trackers = [t for t in self.trackers if t.frames_since_seen <= self.max_nr_frames_missing]

        # Create new trackers for unassociated detections (new people)
        for new_person_idx in new_people_indices:
            self.trackers.append(
                PersonTracker(
                    people[new_person_idx]["cm"], 
                    people[new_person_idx]["2d_outline"]
                )
            )

        # Predict the next position for each tracker
        for t in self.trackers:
            t.predict()

        # Display or process the tracked data as needed
        for t in self.trackers:
            print(t.kf.x[:3])


max_iou_threshold = 0.3  # Threshold to consider a detection as a new person

trackers = []  # List of PersonTracker objects
tracker = Tracker()
for frame_data in kinect:
    # (existing loop code)

    # Get cm and segment locations of detected people
    people = kinect.get_mean_coords_for_segments(img_segments)

    tracked_people = tracker(people)
