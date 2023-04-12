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

from nuru import settings
from smanmi import util

logger = util.createLogger('kinect', debug=False)

class Kinect:
    def __init__(self, streams=["color", "depth", "ir"]):
        self.freenect = Freenect2()
        num_devices = self.freenect.enumerateDevices()
        assert num_devices > 0, "No Kinect device detected"

        serial = self.freenect.getDeviceSerialNumber(0)
        self.device = self.freenect.openDevice(serial)

        self.streams = streams
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

        self.undistorted = Frame(512, 424, 4)
        self.registered = Frame(512, 424, 4)

    def __iter__(self):
        return self

    def __next__(self):
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

        self.listener.release(frames)
        return output
    
    def ir_enhance(self, rgb, ir):
        """Enhance the rgb image by adaptively adding IR to the V channel of the HSV image."""

        hsv_img = cv2.cvtColor(rgb, cv2.COLOR_BGR2HSV).astype(np.float32) / 255.0
        hsv_img[:,:,2] += np.clip(ir - hsv_img[:,:,2], 0, 1)
        rgb_img = cv2.cvtColor((hsv_img * 255).astype(np.uint8), cv2.COLOR_HSV2BGR)

        return rgb_img
    
    def get_point_3d(self, c, r):
        """Get the 3D location of a point in the depthmap."""

        x, y, z = self.registration.getPointXYZ(kinect.undistorted, c, r)

        return x, y, z

    def close(self):
        self.device.stop()
        self.device.close()

class ImageAnnotator:
    def __init__(self, font_size=1, font_thickness=2, color=(0, 0, 255)):
        self.font_size = font_size
        self.font_thickness = font_thickness
        self.color = color

    def draw_detections(self, img, seg_labels, class_ids=None):
        for class_id, data in seg_labels.items():
            if class_ids is None or class_id in class_ids:
                r, c = data["rgb_loc"]
                x, y, z = data["3D_loc"]

                # Draw polylines and text
                cv2.polylines(img, [data["seg"]], True, self.color, 4)
                self.write_text(img, data["class_name"], (r, c - 10))
                self.write_text(img, f"x: {x:.2f}, y: {y:.2f}, z: {z:.2f}", (r, c + 30))

    def write_text(self, img, text, pos):
        cv2.putText(img, text, pos, cv2.FONT_HERSHEY_PLAIN, self.font_size, self.color, self.font_thickness)

class YOLOSegmentation:
    def __init__(self, model_path, class_ids_filter=None):
        self.model = YOLO(model_path)
        self.class_ids_filter = class_ids_filter

    def detect(self, img):
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
        self.folder = folder
        self.video_writer = None
        self.recording = False
        self.nr_frames_rec = 0

    def start_recording(self, frame_size, fps=30):
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
        if self.recording:
            logger.info(f"Stopping recording and storing: {self.folder}")
            self.recording = False
            self.video_writer.release()
            self.video_writer = None

    def save_frame(self, frame):
        if self.recording:
            logger.info(f"Recording frame {self.nr_frames_rec}")
            self.nr_frames_rec += 1
            self.video_writer.write(frame)
    
    def is_recording(self):
        return self.recording

class FPSCounter:
    def __init__(self, chunk_size=5):
        self.chunk_size = chunk_size
        self.dts = deque(maxlen=self.chunk_size)
        self.t = time.time()
        self.fps = 0

    def update(self):
        self.dts.append(time.time() - self.t)
        self.t = time.time()
        self.fps = self.chunk_size / sum(self.dts)
        logger.info(f"{self.fps:.2f}fps")

if __name__ == "__main__":
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
        '--yolo_classe_ids', type=str, nargs='*', default=None, help='YOLO class ids to detect.'
    )
    parser.add_argument(
        '--data_out', type=str, default=settings.kinect_data_path, help="Data output folder."
    )
    args = parser.parse_args()

    video_writer = VideoWriter(args.data_out)
    dynamic_fps = FPSCounter()
    kinect = Kinect(streams=args.streams + [args.rec_stream])
    ys = YOLOSegmentation(settings.yolo_models[args.yolo_model], args.yolo_classe_ids)
    annotator = ImageAnnotator()
    # tracker = Tracker()
    for frame_data in kinect:
        rec_frame = frame_data[args.rec_stream]
        dynamic_fps.update()
        key = cv2.waitKey(1)
        if "ir_rgb" in frame_data:
            # Detect objects
            img_segments = ys.detect(frame_data["ir_rgb"])

            # Get 3D locations
            for class_id, data in img_segments.items():
                data["3D_loc"] = kinect.get_point_3d(*data["rgb_loc"])

            # tracker.update(img_segments)
            annotator.draw_detections(frame_data["ir_rgb"], img_segments)

        # Start/stop record video when 's' is pressed
        if key == ord('s'):
            if not video_writer.is_recording():
                video_writer.start_recording(rec_frame.shape[1::-1], dynamic_fps.fps)
            else:
                video_writer.stop_recording()

        # Save frame to the video file
        if video_writer.is_recording():
            video_writer.save_frame(rec_frame)

        if key == ord('q') or key == 27:  # Press 'q' or 'ESC' to exit
            break

        # Show frames
        for stream, frame in frame_data.items():
            cv2.imshow(stream, frame)  

    kinect.close()
