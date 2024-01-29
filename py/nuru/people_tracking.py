import numpy as np
import cv2
from filterpy.kalman import KalmanFilter
from scipy.optimize import linear_sum_assignment
from collections import namedtuple, deque
import time

class SimilarityMeasure:
    def __init__(self, use_distance = False, use_color_histogram = False):
        self.max_dists = {}
        self.use_distance = use_distance
        self.use_color_histogram = use_color_histogram
        self.seg_mask_1 = None
        self.seg_mask_2 = None
        self.seg_area_1 = 0
        self.seg_area_2 = 0
        self.intersection_area = 0
        self.union_area = 0
        self.difference_area = 0
        self.iou = 1  # Intersection ove Union
        self.area_change_rate = 0 # people1 sections area / people2 sections area -1
        self.norm_dist_meters = 0 # 3D euclidean distance
        self.norm_dist_color = 0 # Normalize distance color hist (Need to test!)

    def __call__(self, people1, people2, img_shape=(512, 424)):
        """
        The lower the value the most similar the image segments
        """

        people1_2d_outlines = [person.get("2D_outline", []) for person in people1]
        people2_2d_outlines = [person.get("2D_outline", []) for person in people2]
        if len(people1_2d_outlines) == 0 and len(people1_2d_outlines) == 0:
            return 0
        self.create_segment_masks(people1_2d_outlines, people2_2d_outlines, img_shape)

        # Measure IOU
        self.iou = self.polygon_iou()

        # Measure area difference ratio
        self.area_change_rate = self.segment_area_change()

        self.norm_dist_meters = 0
        if self.use_distance:
            assert len(people1) == len(people2)
            for p_idx in range(len(people1)): 
                norm_dist_meters += self.norm_dist(people1[p_idx], people2[p_idx], "cm")
            
        self.norm_dist_color = 0
        if self.use_color_histogram:
            assert len(people1) == len(people2)
            for p_idx in range(len(people1)): 
                norm_dist_color += self.norm_dist(people1[p_idx], people2[p_idx], "color_histogram")

        return (1 - self.iou) + 5 * np.abs(self.area_change_rate) + self.norm_dist_meters + self.norm_dist_color

    def create_segment_masks(self, segments_1, segments_2, img_shape):

        # Create two blank images
        self.seg_mask_1 = np.zeros(img_shape, dtype=np.uint8)
        self.seg_mask_2 = np.zeros(img_shape, dtype=np.uint8)

        # Draw the polygons
        cv2.fillPoly(self.seg_mask_1, segments_1, 255)
        cv2.fillPoly(self.seg_mask_2, segments_2, 255)

        # Calculate area of segments
        self.seg_area_1 = cv2.countNonZero(self.seg_mask_1)
        self.seg_area_2 = cv2.countNonZero(self.seg_mask_2)

    def segment_area_change(self):

        if self.seg_area_1 == 0:
            return 0
        else:
            return (self.seg_area_2 / self.seg_area_1) - 1

    def polygon_iou(self):
        """Calculate the Intersection over Union (IoU) between two image segments."""

        # Calculate total intersection area
        intersection = cv2.bitwise_and(self.seg_mask_1, self.seg_mask_2)
        self.intersection_area = cv2.countNonZero(intersection)

        # Calculate Union area
        union = cv2.bitwise_or(self.seg_mask_1, self.seg_mask_2)
        self.union_area = cv2.countNonZero(union)

        # Calculate Difference area
        difference = cv2.bitwise_xor(self.seg_mask_1, self.seg_mask_2)
        self.difference_area = cv2.countNonZero(difference)

        # Growing areas (in seg_mask_1 but not in seg_mask_2)
        growing_areas = cv2.bitwise_and(self.seg_mask_1, cv2.bitwise_not(self.seg_mask_2))
        self.growing_area = cv2.countNonZero(growing_areas)

        # Shrinking areas (in seg_mask_2 but not in seg_mask_1)
        shrinking_areas = cv2.bitwise_and(self.seg_mask_2, cv2.bitwise_not(self.seg_mask_1))
        self.shrinking_area = cv2.countNonZero(shrinking_areas)

        # Calculate IoU
        return self.intersection_area / self.union_area if self.union_area != 0 else 1

    def norm_dist(self, p1, p2, key):
        if key not in p1 or key not in p2:
            print(f"{key} not found!")
            return 0
        dist = np.linalg.norm(np.array(p1[key]) - np.array(p2[key]))
        self.max_dists[key] = np.max([self.max_dists.get(key, 1), dist])
        return dist / self.max_dists[key]

class PersonTracker:
    """PersonTracker class uses the Kalman filter to track individual people."""

    def __init__(self, person, person_id, max_away_frames=3):
        self.max_away_frames = max_away_frames
        self.frames_since_seen = 0
        self.person = person
        self.person["person_id"] = person_id

        self.kf = KalmanFilter(dim_x=6, dim_z=3)

        # Initial state
        self.kf.x = np.array([
            self.person["cm"][0], self.person["cm"][1], self.person["cm"][2], 0, 0, 0]
        )

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

    def update(self, person):
        self.person = person
        self.kf.update(person["cm"])

    def get_current_person_state(self):
        self.person["cm"] = self.get_position()
        self.person["velocity"] = self.get_velocity()
        return self.person

    def get_velocity(self):
        vx, vy, vz = self.kf.x[3], self.kf.x[4], self.kf.x[5]
        return vx, vy, vz
    
    def get_position(self):
        x, y, z = self.kf.x[0], self.kf.x[1], self.kf.x[2]
        return x, y, z


class Tracker():
    """Class to track people using the image segment IoU."""

    def __init__(self, forget_dt, nr_people_queue_size = 5, max_person_id=10):
        self.forget_dt = forget_dt  # Max time person can not be seen
        self.max_person_id = max_person_id  # Max allowed person ID
        self.tracked_people = []  # List of PersonTracker objects
        self.person_id_count = 0  # Counter to assign unique IDs to people
        self.nr_people_queue = deque(maxlen = nr_people_queue_size)
        self.similarity_measure = SimilarityMeasure()

    def __call__(self, new_people, img_shape):
        """Update the trackers and return the list of of people tracked by the kalman filter tracker."""

        # Associate new people with existing trackers
        associations = self.associate_new_people_with_trackers(new_people, img_shape)

        # Update the trackers
        self.update_trackers(associations, new_people)
            
        return self.tracked_people 
    
    def update_trackers(self, associations, new_people):
        """Update the trackers with the associated detections and remove the lost trackers."""

        # Allocate current time to all new people tracked
        for new_person in new_people:
            new_person["t_last_seen"] = time.time()

        # Update tracked people with the associated detections
        for association in associations.T:
            tracked_person_idx, new_person_idx = association
            for key, new_value in new_people[new_person_idx].items():
                self.tracked_people[tracked_person_idx][key] = new_value
            dt_seen =  time.time() - self.tracked_people[tracked_person_idx]["first_seen"]
            self.tracked_people[tracked_person_idx]["time_known"] = dt_seen
        
        # Remove tracked people that have reached forget time away
        self.tracked_people = [
            tracked_person 
            for tracked_person in self.tracked_people 
            if time.time() - tracked_person["t_last_seen"] <= self.forget_dt
        ]

        # Only consider adding new people if expected number larger than tracked number
        self.nr_people_queue.append(len(new_people))
        expected_nr_people = int(np.round(np.mean(self.nr_people_queue)))
        if len(self.tracked_people) >= expected_nr_people:
            return

        # Create new trackers for unassociated detections (new people)
        for new_person_idx, new_person in enumerate(new_people):
            new_person_idxs = associations[1,:]
            if new_person_idx in new_person_idxs:
                continue

            # If no association found for new person add to tracked people
            self.person_id_count = (self.person_id_count + 1) % self.max_person_id
            new_people[new_person_idx]["id"] = self.person_id_count
            new_people[new_person_idx]["first_seen"] = time.time()
            self.tracked_people.append(new_people[new_person_idx])
    
    # Function to associate data between trackers and people
    def associate_new_people_with_trackers(self, new_people, img_shape):
        """Associate new people with existing trackers using the Hungarian algorithm."""

        # Initialize the cost matrix with zeros
        cost_matrix = np.zeros((len(self.tracked_people), len(new_people)))

        # Calculate the similarity between each tracker and person
        for tracked_person_idx, tracked_person in enumerate(self.tracked_people):
            for new_person_idx, new_person in enumerate(new_people):
                similarity = self.similarity_measure([tracked_person], [new_person], img_shape[:2])
                cost_matrix[tracked_person_idx, new_person_idx] = similarity

        # Use the Hungarian algorithm to find the best association based on the cost matrix
        return np.array(linear_sum_assignment(cost_matrix))


class MotionDetection:
    def __init__(self, max_motion_threshold, min_motion_threshold, nr_frames = 1):
        self.max_motion_threshold = max_motion_threshold
        self.min_motion_threshold = min_motion_threshold
        self.nr_frames = nr_frames
        self.similarities = deque(maxlen = self.nr_frames)
        self.area_change_rates = deque(maxlen = self.nr_frames)
        self.prev_people = []
        self.similarity_measure = SimilarityMeasure()
        self.motion_detected = False
        self.motion = 0
        self.last_motion_trigger_t = time.time()

    def __call__(self, new_people, img_shape):

        # Measure motion
        self.similarities.append(self.similarity_measure(new_people, self.prev_people, img_shape[:2]))
        self.area_change_rates.append(self.similarity_measure.area_change_rate)
        self.prev_people = new_people
        self.motion = np.mean(self.similarities)

        return self.motion

    def get_area_change_ratio(self):

        return np.mean(self.area_change_rates)

    def scene_changed(self):

        # Detect motion
        if self.motion > self.max_motion_threshold:
            self.motion_detected = True

        # Continue only if motion detecion queued
        if not self.motion_detected:
            return False

        # Continue only when frame is still
        if self.motion > self.min_motion_threshold:
            return False

        self.last_motion_trigger_t = time.time()
        self.motion_detected = False
        return True       
