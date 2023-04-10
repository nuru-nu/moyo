import numpy as np
import cv2
from pylibfreenect2 import Freenect2, SyncMultiFrameListener
from pylibfreenect2 import FrameType, Registration, Frame
import os
import time

from nuru import settings
from smanmi import util

logger = util.createLogger('speechGPT', debug=False)

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
start_time = time.time()
num_frames = 0
while True:
    frames = listener.waitForNewFrame()
        
    num_frames += 1
    elapsed_time = time.time() - start_time
    fps = num_frames / elapsed_time
    
    ir = frames["ir"]
    color = frames["color"]
    depth = frames["depth"]

    registration.apply(color, depth, undistorted, registered)

    color_image = cv2.cvtColor(color.asarray(dtype=np.uint8), cv2.COLOR_RGBA2BGR)
    color_image[:,:,[0, 2]] = color_image[:,:, [2, 0]] # BGR to RGB
    depth_image = cv2.normalize(depth.asarray(dtype=np.float32), None, 0, 1, cv2.NORM_MINMAX, cv2.CV_32F)
    ir_image = cv2.normalize(ir.asarray(dtype=np.float32), None, 0, 1, cv2.NORM_MINMAX, cv2.CV_32F)

    cv2.imshow('Color', color_image)
    cv2.imshow('Depth', depth_image)
    cv2.imshow('ir', ir_image)

    key = cv2.waitKey(1)
    
    # Record video when 's' is pressed
    if key == ord('s'):
        if not recording:
            logger.info(f"Starting recording @ {fps:.2f}fps")
            recording = True
            start_frame_nr = num_frames
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
        logger.info(f"Recording RGB frame {num_frames - start_frame_nr}")
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
