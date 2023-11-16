import colorsys
import cv2
import numpy as np
from collections import defaultdict
from collections import deque

class ImageAnnotator:
    def __init__(
            self,
            font_size=1,
            font_thickness=2,
            line_thickness=2,
            num_colors=8,
            track_img_size=(512,512),
            kinect_2d_fov=((-3,3), (0,6)),
            max_track_length=50
        ):
        """Initialize the image annotator."""

        self._font_size = font_size
        self._font_thickness = font_thickness
        self._colors = self.generate_colors(num_colors)
        self._line_thickness = line_thickness
        self._tracks_2d = defaultdict(lambda: deque(maxlen=max_track_length))  # Modified to use deque
        self._track_2d_img = np.zeros(list(track_img_size) + [3])
        self._kinect_2d_x_range, self._kinect_2d_y_range = kinect_2d_fov
        self._kinect_2d_width = self._kinect_2d_x_range[1] - self._kinect_2d_x_range[0]
        self._kinect_2d_height = self._kinect_2d_y_range[1] - self._kinect_2d_y_range[0]

    def generate_colors(self, n):
        """Generate n colors for segmentation masks."""

        colors = []
        for i in range(n):
            hue = float(i) / n
            saturation = 0.9
            lightness = 0.6
            r, g, b = colorsys.hls_to_rgb(hue, lightness, saturation)
            colors.append([int(r * 255), int(g * 255), int(b * 255)])

        return colors

    def draw_detections(self, img, seg_labels, class_ids=None):
        """Draw the segmentation masks and class names on the image."""

        for class_id, detections in seg_labels.items():
            if class_ids is not None and class_id not in class_ids:
                continue

            for idx, detection in enumerate(detections):
                color = self._colors[detection["id"] % len(self._colors)]

                # Draw polylines and text
                cv2.polylines(img, [detection["2D_outline"]], True, color, self._line_thickness)

                # Calculate the centroid of the segment
                r, c = np.int32(np.mean(np.array(detection["2D_outline"], dtype=np.float32), axis=0))

                # Check if the text will be inside the image boundaries
                h, w = img.shape[:2]
                if r - 10 >= 0 and r + 30 < h and c - 10 >= 0 and c + 10 < w:
                    self.write_text(img, detection["class_name"], (r, c - 10), color)

                    if "3D_shimoni" in detection:
                        x, y, _ = detection["3D_shimoni"]
                        self.write_text(img, f"x: {x:.2f}, y: {y:.2f}", (r, c + 30), color)

    def draw_2d_track(self, people):
        """Draw the 2D tracks on the image."""

        # Tmp HACK
        people = {idx: person for idx, person in enumerate(people)}

        # Append the newest coordinates to each track
        img = self._track_2d_img.copy()
        for idx, person in people.items():
            assert "3D_shimoni" in person, "get_mean_coords_for_segments() must be run prior to this function."
            x, y, _ = person["3D_shimoni"]

            x_img = self._track_2d_img.shape[1] - int(((x - self._kinect_2d_x_range[0]) / self._kinect_2d_width) * self._track_2d_img.shape[1])
            y_img = int(((y - self._kinect_2d_y_range[0]) / self._kinect_2d_height) * self._track_2d_img.shape[0])

            self._tracks_2d[idx].append((x_img, y_img))

        # Fade out lost tracks
        for lost_person in list(set(self._tracks_2d) - set(people)):
            self._tracks_2d[lost_person].popleft()
            if len(self._tracks_2d[lost_person]) == 0:
                self._tracks_2d.pop(lost_person)

        # Draw all tracks
        for idx, track in enumerate(self._tracks_2d.values()):
            color = self._colors[(int(idx) + idx) % len(self._colors)]
            self._draw_2d_track(img, track, color)

        return img

    def _draw_2d_track(self, img, track, color):
        """Draw a single track on an image."""

        assert len(track) > 0
        
        p_prev = track[0]
        for p_curr in list(track)[1:]:
            cv2.circle(img, p_prev, 3, color, -1)
            cv2.line(img, p_prev, p_curr, color, self._line_thickness)
            p_prev = p_curr

    def write_text(self, img, text, pos, color):
        """Write text on the image."""

        cv2.putText(img, text, pos, cv2.FONT_HERSHEY_PLAIN, self._font_size, color, self._font_thickness)
