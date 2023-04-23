import numpy as np
import cv2
from filterpy.kalman import KalmanFilter
from scipy.optimize import linear_sum_assignment
from collections import namedtuple

def polygon_iou(segmentsA, segmentsB):
    """Calculate the Intersection over Union (IoU) between two image segments."""

    # Calculate the intersection area between the two polygons
    _, intersection = cv2.intersectConvexConvex(segmentsA, segmentsB)
    intersection_area = cv2.contourArea(intersection)

    # Calculate the individual areas of the polygons
    areaA = cv2.contourArea(segmentsA)
    areaB = cv2.contourArea(segmentsB)

    # Calculate the union area between the two polygons
    union_area = areaA + areaB - intersection_area

    # Calculate the IoU
    iou = intersection_area / union_area

    return iou

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
    """Class to track people using the Kalman filter tracker."""

    AssociationResult = namedtuple(
        "AssociationResult", 
        ["people_tracker_associations", "new_people_indices", "lost_tracker_indices"]
    )

    def __init__(self, max_iou_threshold=0.3, max_away_frames=3):
        self.max_iou_threshold = max_iou_threshold  # Threshold to consider a detection as a new person
        self.max_away_frames = max_away_frames  # Number of frames to wait before removing a tracker
        self.trackers = []  # List of PersonTracker objects
        self.id_count = 0  # Counter to assign unique IDs to people

    def __call__(self, people):
        """Update the trackers and return the list of of people tracked by the kalman filter tracker."""
        
        # Associate new people with existing trackers
        associations = self.associate_new_people_with_trackers(self.trackers, people)

        # Update the trackers
        self.update_trackers(associations, people)

        # Get the current person state of each tracker
        tracked_people = [t.get_current_person_state for t in self.trackers]

        # Predict the next position for each tracker
        for t in self.trackers:
            t.predict()

        # Increment frames_since_seen for all trackers
        for t in self.trackers:
            t.frames_since_seen += 1
            
        return tracked_people
    
    def update_trackers(self, associations, people):
        """Update the trackers with the associated detections and remove the lost trackers."""     

        # Update trackers with the associated detections
        for tracker_idx, detection_idx in associations.people_tracker_associations:
            self.trackers[tracker_idx].update(people[detection_idx])
            self.trackers[tracker_idx].frames_since_seen = 0

        # Call predict() an for the lost trackers
        for tracker_idx in associations.lost_tracker_indices:
            self.trackers[tracker_idx].predict()

        # Create new trackers for unassociated detections (new people)
        for new_person_idx in associations.new_people_indices:
            self.id_count += 1
            self.trackers.append(
                PersonTracker(
                    people[new_person_idx],
                    self.id_count,
                    self.max_away_frames,
                )
            )
        
        # Remove trackers that have reached the max_away_frames
        self.trackers = [t for t in self.trackers if t.frames_since_seen <= self.max_away_frames]
    
    # Function to associate data between trackers and people
    def associate_new_people_with_trackers(self, people):
        """Associate new people with existing trackers using the Hungarian algorithm."""

        # Initialize the cost matrix with zeros
        cost_matrix = np.zeros((len(self.trackers), len(people)))

        # Calculate the IoU between each tracker and person
        for tracker_idx, tracker in enumerate(self.trackers):
            for person_idx, person in enumerate(people):
                iou = polygon_iou(tracker._2d_outline, person["2d_outline"])
                # TODO Add 3D dist cost here if necessary
                cost_matrix[tracker_idx, person_idx] = 1 - iou

        # Use the Hungarian algorithm to find the best association based on the cost matrix
        row_indices, col_indices = linear_sum_assignment(cost_matrix)

        # Create a list of associated tracker-person pairs
        people_tracker_associations = [
            (tracker_idx, person_idx) 
            for tracker_idx, person_idx in zip(row_indices, col_indices)
        ]

        # Find the new people (if any)
        new_people_indices = [
            person_idx 
            for person_idx in range(len(people)) 
            if person_idx not in col_indices
        ]

        # Find the lost self.trackers (if any)
        lost_tracker_indices = [
            tracker_idx 
            for tracker_idx in range(len(self.trackers)) 
            if tracker_idx not in row_indices
        ]

        # Return the list of associations and new people indices
        return self.AssociationResult(people_tracker_associations, new_people_indices, lost_tracker_indices)
