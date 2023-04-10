import numpy as np
import cv2
from pylibfreenect2 import Freenect2, SyncMultiFrameListener
from pylibfreenect2 import FrameType, Registration, Frame
import os
import time
import sympy
from ultralytics import YOLO
from collections import deque


from nuru import settings
from smanmi import util

logger = util.createLogger('speechGPT', debug=False)

class YOLOSegmentation:
    def __init__(self, model_path, class_id=0):
        self.model = YOLO(model_path)

    def detect(self, img):
        height, width, channels = img.shape

        results = self.model.predict(source=img.copy(), save=False, save_txt=False)
        result = results[0]

        self.segmentations = []
        if result.masks is not None:
            for seg in result.masks.xyn:
                # contours
                seg[:, 0] *= width
                seg[:, 1] *= height
                segment = np.array(seg, dtype=np.int32)
                self.segmentations.append(segment)

        self.bboxes = np.array(result.boxes.xyxy.cpu(), dtype="int")
        # Get class ids
        self.class_ids = np.array(result.boxes.cls.cpu(), dtype="int")
        # Get scores
        self.scores = np.array(result.boxes.conf.cpu(), dtype="float").round(2)
        
        return self.bboxes, self.class_ids, self.segmentations, self.scores
    
    def draw_detections(self, img, seg_labels, class_ids=None):
        for class_id, seg in seg_labels.items():
            if class_ids is None or class_id in class_ids:
                # (x, y, x2, y2) = bbox
                x, y = np.mean(seg, axis=0).astype(int)
                # cv2.rectangle(img, (x, y), (x2, y2), (255, 0, 0), 2)
                cv2.polylines(img, [seg], True, (0, 0, 255), 4)
                cv2.putText(
                    img, self.model.names[int(class_id)], (x, y - 10), 
                    cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 2
                )

# Segmentation detector
ys = YOLOSegmentation(settings.yolo_models["yolov8n-seg"])

# import pcl.ply as ply

# Additional imports for video writing
from datetime import datetime

# Function to create video writer
def create_video_writer(frame_size, filename):
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    return cv2.VideoWriter(filename, fourcc, 30, frame_size, isColor=True)

def save_point_cloud(cloud, filename):
    points = np.hstack((cloud[..., 0:3].reshape(-1, 3), np.ones((cloud.size // 3, 1))))
    # header = ply.make_header([('x', 'f4'), ('y', 'f4'), ('z', 'f4'), ('scalar', 'f4')])
    # ply.save_ply(filename, points, header, binary=True)
    return points

def ir_enhance(rgb, ir):
    """Enhance the rgb image by adaptively adding IR to the V channel of the HSV image."""

    hsv_img = cv2.cvtColor(rgb, cv2.COLOR_BGR2HSV).astype(np.float32) / 255.0
    hsv_img[:,:,2] += np.clip(ir - hsv_img[:,:,2], 0, 1)
    rgb_img = cv2.cvtColor((hsv_img * 255).astype(np.uint8), cv2.COLOR_HSV2BGR)

    return rgb_img

freenect = Freenect2()
num_devices = freenect.enumerateDevices()
assert num_devices > 0, "No Kinect device detected"

serial = freenect.getDeviceSerialNumber(0)
device = freenect.openDevice(serial)

listener = SyncMultiFrameListener(FrameType.Color | FrameType.Ir | FrameType.Depth)
device.setColorFrameListener(listener)
device.setIrAndDepthFrameListener(listener)

device.start()

registration = Registration(device.getIrCameraParams(), device.getColorCameraParams())

undistorted = Frame(512, 424, 4)
registered = Frame(512, 424, 4)

def create_video_writer(frame_size, filename, fps):
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    return cv2.VideoWriter(filename, fourcc, fps, frame_size, isColor=True)

recording = False
fps_chunk_size = 5
dts = deque(maxlen=fps_chunk_size)
t = time.time()
while True:
    dts.append(time.time()-t)
    t = time.time()
    fps = fps_chunk_size / np.sum(dts)
    logger.info(f"{fps:.2f}fps")
    
    # Get libfreect frames
    frames = listener.waitForNewFrame()
    ir = frames["ir"]
    color = frames["color"]
    depth = frames["depth"]
    registration.apply(color, depth, undistorted, registered)

    # Convert libfreect image data to OpenCV format
    color_image = cv2.cvtColor(color.asarray(dtype=np.uint8), cv2.COLOR_RGBA2BGR)
    color_image[:,:,[0, 2]] = color_image[:,:, [2, 0]] # BGR to RGB
    depth_image = cv2.normalize(depth.asarray(dtype=np.float32), None, 0, 1, cv2.NORM_MINMAX, cv2.CV_32F)
    ir_image = cv2.normalize(ir.asarray(dtype=np.float32), None, 0, 1, cv2.NORM_MINMAX, cv2.CV_32F)
    depth_color = cv2.cvtColor(registered.asarray(dtype=np.uint8), cv2.COLOR_RGBA2BGR)
    depth_color[:,:,[0, 2]] = depth_color[:,:, [2, 0]] # BGR to RGB

    ir_enhanced_rgb = ir_enhance(depth_color, ir_image)

    # Get YOLO detections
    ts = time.time()
    bboxes, classes, segmentations, scores = ys.detect(ir_enhanced_rgb)
    seg_labels = {class_id: seg for class_id, seg in zip(classes, segmentations)}
    ys.draw_detections(ir_enhanced_rgb, seg_labels)
    logger.info(f"Found {[ys.model.names[int(class_id)] for class_id in classes]}")
    logger.debug(f"YOLO took {time.time() - ts:.2f}s")

    # Draw Images
    cv2.putText(color_image, f"{fps:.2f}fps", (0, 30), cv2.FONT_HERSHEY_PLAIN, 2, (0, 0, 255), 2)
    cv2.imshow('Color', color_image)
    cv2.imshow('Depth', depth_image)
    cv2.imshow('IR', ir_image)
    cv2.imshow('IR Enhanced RGB', ir_enhanced_rgb)

    key = cv2.waitKey(1)
    
    # Record video when 's' is pressed
    if key == ord('s'):
        if not recording:
            nr_frames_rec = 0
            recording = True
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            vid_path = os.path.join(settings.kinect_data_path, f'video_{timestamp}.mp4')
            video_writer = create_video_writer(color_image.shape[1::-1], vid_path, fps)
        else:
            logger.info(f"Stopping recording and storing: {vid_path}")
            recording = False
            video_writer.release()
            video_writer = None

    # Save frame to the video file
    if recording:
        nr_frames_rec += 1
        logger.info(f"Recording RGB frame {nr_frames_rec}")
        video_writer.write(color_image)

    if key == ord('p'):
        point_cloud = registration.getPointXYZRGBArray()
        save_point_cloud(point_cloud, 'pointcloud.ply')
        logger.info("Point cloud saved as pointcloud.ply")

    if key == ord('q') or key == 27:  # Press 'q' or 'ESC' to exit
        break

    listener.release(frames)

# Release the video writer if it's still active
if video_writer:
    video_writer.release()

device.stop()
device.close()

cv2.destroyAllWindows()
