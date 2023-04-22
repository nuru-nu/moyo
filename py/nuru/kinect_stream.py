import argparse
import numpy as np
import cv2
import os
import time
from argparse import ArgumentParser
from pylibfreenect2 import Freenect2, SyncMultiFrameListener
from pylibfreenect2 import FrameType, Registration, Frame
from ultralytics import YOLO
from collections import deque
from datetime import datetime
import colorsys
import open3d as o3d
import json

from nuru import settings
from smanmi import network, util

logger = util.createLogger('kinect', debug=False)

parser = argparse.ArgumentParser(description="Kinect Recorder")
parser.add_argument(
    '--streams', type=str, choices=['ir', 'color', 'depth', 'ir_rgb'], nargs='*', 
    default=['ir', 'color', 'depth', 'ir_rgb'], help='Stream types to subscribe to'
)
parser.add_argument(
    '--rec_stream', type=str, default='ir_rgb', help="Stream type to record"
)
parser.add_argument(
    '--yolo_model', type=str, default='yolov8n-seg', 
    help="YOLO model name. See settings.py for available models."
)
parser.add_argument(
    '--yolo_stream', type=str, default='ir_rgb', help="Kinect stream name for YOLO."
)
parser.add_argument(
    '--yolo_class_ids', type=str, nargs='*', default=None, help='YOLO class ids to detect. 0 for people.'
)
parser.add_argument(
    '--data_out', type=str, default=settings.kinect_data_path, help="Data output folder."
)
parser.add_argument(
    '--shimono_trafo_path', type=str, default=os.path.join(settings.blender_path, "data", "kinect_trafo.json"), 
    help="Kinect to Shimoni transform."
)
args = parser.parse_args()


class Kinect:
    def __init__(
            self, 
            streams=["color", "depth", "ir"], 
            shimono_trafo_path=None, 
            output_dir=None, 
            flip=False, 
            width = 512, 
            height = 424
        ):
        """Initialize the Kinect device."""

        self.freenect = Freenect2()
        num_devices = self.freenect.enumerateDevices()
        assert num_devices > 0, "No Kinect device detected"

        serial = self.freenect.getDeviceSerialNumber(0)
        self.device = self.freenect.openDevice(serial)
        
        self.streams = streams
        self.output_dir = output_dir
        self.flip = flip
        self.width = width
        self.height = height

        frame_types = 0
        if "ir_rgb" in streams:
            streams += ["color", "ir"]
        if "color" in streams:
            frame_types |= FrameType.Color
        if "depth" in streams:
            frame_types |= FrameType.Depth
        if "ir" in streams:
            frame_types |= FrameType.Ir

        self.listener = SyncMultiFrameListener(frame_types)
        self.device.setColorFrameListener(self.listener)
        self.device.setIrAndDepthFrameListener(self.listener)

        self.device.start()

        self.registration = Registration(
            self.device.getIrCameraParams(), self.device.getColorCameraParams()
        )

        self.undistorted = Frame(width, height, 4)
        self.registered = Frame(width, height, 4)

        self.shimoni_trafo = self.load_transform(shimono_trafo_path)

    def __iter__(self):
        return self

    def __next__(self):
        """Get the next frames from the Kinect device."""

        frames = self.listener.waitForNewFrame()

        # Apply registration if both color and depth are enabled
        if "color" in self.streams and "depth" in self.streams:
            self.registration.apply(
                frames["color"], frames["depth"], self.undistorted, self.registered
            )

        # Create output images
        output = {}
        if "color" in self.streams:
            color = frames["color"]
            output["color"] = cv2.cvtColor(
                color.asarray(dtype=np.uint8), cv2.COLOR_RGBA2BGR
            )
            output["color"][:,:,[0, 2]] = output["color"][:,:, [2, 0]] # BGR to RGB

            output["scaled_color"] = cv2.cvtColor(
                self.registered.asarray(dtype=np.uint8), cv2.COLOR_RGBA2BGR
            )
            output["scaled_color"][:,:,[0, 2]] = output["scaled_color"][:,:, [2, 0]] # BGR to RGB

        if "depth" in self.streams:
            depth = frames["depth"]
            output["depth"] = cv2.normalize(
                depth.asarray(dtype=np.float32),
                None,
                0,
                1,
                cv2.NORM_MINMAX,
                cv2.CV_32F,
            )

        if "ir" in self.streams:
            ir = frames["ir"]
            output["ir"] = cv2.normalize(
                ir.asarray(dtype=np.float32),
                None,
                0,
                1,
                cv2.NORM_MINMAX,
                cv2.CV_32F,
            )
        if "ir_rgb" in self.streams:
            output["ir_rgb"] = self.ir_enhance(output["scaled_color"], output["ir"])

        if self.flip:
            for k, v in output.items():
                output[k] = cv2.flip(v, 1)
                output[k] = cv2.flip(v, 0)

        self.listener.release(frames)
        return output
    
    def ir_enhance(self, rgb, ir):
        """Enhance the rgb image by adaptively adding IR to the V channel of the HSV image."""

        hsv_img = cv2.cvtColor(rgb, cv2.COLOR_BGR2HSV).astype(np.float32) / 255.0
        hsv_img[:,:,2] += np.clip(ir - hsv_img[:,:,2], 0, 1)
        rgb_img = cv2.cvtColor((hsv_img * 255).astype(np.uint8), cv2.COLOR_HSV2BGR)

        return rgb_img
    
    def get_mean_coords_for_segments(self, seg_labels):
        """Get the mean 3D location of each segmentation label."""

        for data in seg_labels.values():
            mask = np.zeros((self.width, self.height), dtype=np.uint8)
            cv2.fillPoly(mask, [data["seg"]], 255)

            points_3d = []
            for seg_point in np.argwhere(mask == 255):
                c, r = seg_point
                x, y, z = self.registration.getPointXYZ(kinect.undistorted, c, r)
                if not np.isnan(x) and not np.isnan(y) and not np.isnan(z):
                    points_3d.append([x, y, z])
            
            if len(points_3d) == 0:
                continue
            
            data["3D_point"] = np.mean(points_3d, axis=0)
            data["3D_shimoni"] = self.get_point_shimino_space(*data["3D_point"])
            data["cm"] = data["3D_shimoni"] # HACK: for compatibility with old code

        return seg_labels
    
    def get_point_3d(self, c, r):
        """Get the 3D location of a point in the depthmap."""

        x, y, z = self.registration.getPointXYZ(kinect.undistorted, c, r)

        if np.isnan(x) or np.isnan(y) or np.isnan(z):
            return None
        
        return x, y, z
    
    def get_point_shimino_space(self, x, y, z):
        """Gets 3D point in kinect space and transforms to shimoni space."""
        
        assert self.shimoni_trafo is not None, "Shimoni transformation not loaded"

        x_s, y_s, z_s, w = self.shimoni_trafo @ np.array([x, y, z, 1.0])

        return x_s/w, y_s/w, z_s/w
    
    def save_point_cloud(self):
        """Save the current point cloud to a PLY file."""

        assert self.output_dir is not None, "Output directory not specified"

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        ply_path = os.path.join(self.output_dir, f'pcl_{timestamp}.ply')

        # Get the point cloud
        pts = []
        for r in range(self.width ):
            for c in range(self.height):
                point = self.get_point_3d(c, r)
                if point is not None:
                    pts.append(point)

        pcd = o3d.geometry.PointCloud()
        pcd.points = o3d.utility.Vector3dVector(pts)

        o3d.io.write_point_cloud(ply_path, pcd, write_ascii=True)

    def load_transform(self, path):
        """Load the transformation matrix from the given path."""

        if path is None:
            return None
        
        with open(path, 'r') as file:
            data = json.load(file)

        return np.array(data['world_matrix'])

    def close(self):
        """Close the Kinect device."""

        self.device.stop()
        self.device.close()

class ImageAnnotator:
    def __init__(self, font_size=1, font_thickness=2, line_thickness=2, num_colors=100):
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

        for class_id, data in seg_labels.items():
            if class_ids is None or class_id in class_ids:
                color = self.colors[int(class_id) % len(self.colors)]

                # Draw polylines and text
                cv2.polylines(img, [data["seg"]], True, color, self.line_thickness)

                # Calculate the centroid of the segment
                r, c = np.int32(np.mean(np.array(data["seg"], dtype=np.float32), axis=0))
                
                # Check if the text will be inside the image boundaries
                h, w = img.shape[:2]
                if r - 10 >= 0 and r + 30 < h and c - 10 >= 0 and c + 10 < w:
                    self.write_text(img, data["class_name"], (r, c - 10), color)
                    
                    if "3D_shimoni" in data:
                        x, y, z = data["3D_shimoni"]
                        self.write_text(img, f"x: {x:.2f}, y: {y:.2f}", (r, c + 30), color)

    def write_text(self, img, text, pos, color):
        """Write text on the image."""

        cv2.putText(img, text, pos, cv2.FONT_HERSHEY_PLAIN, self.font_size, color, self.font_thickness)

class YOLOSegmentation:
    def __init__(self, model_path, class_ids_filter=None):
        """Initialize the YOLO segmentation model."""

        self.model = YOLO(model_path)
        self.class_ids_filter = class_ids_filter

    def detect(self, img):
        """Detect objects in the image."""

        height, width, channels = img.shape

        results = self.model.predict(source=img.copy(), save=False, save_txt=False)
        result = results[0]
                
        self.bboxes = np.array(result.boxes.xyxy.cpu(), dtype="int")
        self.class_ids = np.array(result.boxes.cls.cpu(), dtype="int")
        self.scores = np.array(result.boxes.conf.cpu(), dtype="float").round(2)

        self.segmentations = []
        if result.masks is not None:
            for seg in result.masks.xyn:
                # contours
                seg[:, 0] *= width
                seg[:, 1] *= height
                self.segmentations.append(np.array(seg, dtype=np.int32))

        img_segments = {}
        for class_id, seg, bbox, score in zip(self.class_ids, self.segmentations, self.bboxes, self.scores):
            if self.class_ids_filter is None or class_id in self.class_ids_filter:
                c, r = np.mean(seg, axis=0).astype(int)
                img_segments[class_id] = {
                    "rgb_loc": [c, r],
                    "seg": seg,
                    "bbox": bbox,
                    "score": score,
                    "class_name": self.model.names[int(class_id)],
                }
        return img_segments


class VideoWriter:
    def __init__(self, folder):
        """Initialize the video writer."""

        self.folder = folder
        self.video_writer = None
        self.recording = False
        self.nr_frames_rec = 0

    def start_recording(self, frame_size, fps=30):
        """Start recording a video."""

        if not self.recording:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            vid_path = os.path.join(self.folder, f'video_{timestamp}.mp4')
            fourcc = cv2.VideoWriter_fourcc(*'XVID')
            self.video_writer = cv2.VideoWriter(
                vid_path, fourcc, fps, frame_size, isColor=True
            )
            self.nr_frames_rec = 0
            self.recording = True
            logger.info(f"Starting recording to: {vid_path}")

    def stop_recording(self):
        """Stop recording a video."""

        if self.recording:
            logger.info(f"Stopping recording and storing: {self.folder}")
            self.recording = False
            self.video_writer.release()
            self.video_writer = None

    def save_frame(self, frame):
        """Save a frame to the video."""

        if self.recording:
            logger.info(f"Recording frame {self.nr_frames_rec}")
            self.nr_frames_rec += 1
            self.video_writer.write(frame)
    
    def is_recording(self):
        return self.recording

class FPSCounter:
    def __init__(self, chunk_size=5):
        """Initialize the FPS counter."""

        self.chunk_size = chunk_size
        self.dts = deque(maxlen=self.chunk_size)
        self.t = time.time()
        self.fps = 0

    def update(self):
        """Update the FPS counter."""

        self.dts.append(time.time() - self.t)
        self.t = time.time()
        self.fps = self.chunk_size / sum(self.dts)
        logger.info(f"{self.fps:.2f}fps")

if __name__ == "__main__":
    # Combine streams for Kinect 
    streams = set(args.streams + [args.rec_stream, args.yolo_stream])

    # Initialize modules
    video_writer = VideoWriter(args.data_out)
    dynamic_fps = FPSCounter()
    kinect = Kinect(streams=list(streams), shimono_trafo_path=args.shimono_trafo_path, output_dir=args.data_out)
    ys = YOLOSegmentation(settings.yolo_models[args.yolo_model], args.yolo_class_ids)
    annotator = ImageAnnotator()
    # tracker = Tracker()

    # Start Kinect frame stream   
    for frame_data in kinect:
        rec_frame = frame_data[args.rec_stream]
        dynamic_fps.update()
        key = cv2.waitKey(1)
        
        # If yolo_stream is grayscale, convert to RGB
        if len(frame_data[args.yolo_stream].shape) == 2:
            frame_data[args.yolo_stream] = cv2.cvtColor(frame_data[args.yolo_stream], cv2.COLOR_GRAY2RGB)
        
        # Run YOLO detection
        img_segments = ys.detect(frame_data[args.yolo_stream])

        # Get segment locations
        img_segments = kinect.get_mean_coords_for_segments(img_segments)

        # Draw detections
        annotator.draw_detections(frame_data[args.yolo_stream], img_segments)

        # Send detections to integrator
        people = [
            {"cm": np.array(seg["cm"]).tolist(), "id": class_id} 
            for class_id, seg in img_segments.items() if class_id == 0
        ]
        network.send(settings.integrator_sig_port, dict(people_sensor=people))

        # Start/stop record video when 's' is pressed
        if key == ord('s'):
            if not video_writer.is_recording():
                video_writer.start_recording(rec_frame.shape[1::-1], dynamic_fps.fps)
            else:
                video_writer.stop_recording()

        # Save point cloud when 'p' is pressed
        if key == ord('p'):
            kinect.save_point_cloud()

        # Save frame to the video file
        if video_writer.is_recording():
            video_writer.save_frame(rec_frame)

        if key == ord('q') or key == 27:  # Press 'q' or 'ESC' to exit
            break

        # Show frames
        for stream, frame in frame_data.items():
            cv2.imshow(stream, frame)  

    kinect.close()
