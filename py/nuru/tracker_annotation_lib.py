import colorsys
import cv2
import numpy as np

class ImageAnnotator:
    def __init__(self, font_size=1, font_thickness=2, line_thickness=2, num_colors=8):
        """Initialize the image annotator."""

        self.font_size = font_size
        self.font_thickness = font_thickness
        self.colors = self.generate_colors(num_colors)
        self.line_thickness = line_thickness

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
                color = self.colors[(int(class_id) + idx) % len(self.colors)]

                # Draw polylines and text
                cv2.polylines(img, [detection["2D_outline"]], True, color, self.line_thickness)

                # Calculate the centroid of the segment
                r, c = np.int32(np.mean(np.array(detection["2D_outline"], dtype=np.float32), axis=0))
                
                # Check if the text will be inside the image boundaries
                h, w = img.shape[:2]
                if r - 10 >= 0 and r + 30 < h and c - 10 >= 0 and c + 10 < w:
                    self.write_text(img, detection["class_name"], (r, c - 10), color)
                    
                    if "3D_shimoni" in detection:
                        x, y, z = detection["3D_shimoni"]
                        self.write_text(img, f"x: {x:.2f}, y: {y:.2f}", (r, c + 30), color)

    def write_text(self, img, text, pos, color):
        """Write text on the image."""

        cv2.putText(img, text, pos, cv2.FONT_HERSHEY_PLAIN, self.font_size, color, self.font_thickness)