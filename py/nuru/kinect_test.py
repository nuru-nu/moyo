import numpy as np
import cv2
from pylibfreenect2 import Freenect2, SyncMultiFrameListener
from pylibfreenect2 import FrameType, Registration, Frame
# import pcl.ply as ply

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

while True:
    frames = listener.waitForNewFrame()
    
    ir = frames["ir"]
    color = frames["color"]
    depth = frames["depth"]

    registration.apply(color, depth, undistorted, registered)

    color_image = cv2.cvtColor(color.asarray(dtype=np.uint8), cv2.COLOR_RGBA2BGRA)
    color_image[:,:,[0, 2]] = color_image[:,:, [2, 0]] # BGR to RGB
    depth_image = cv2.normalize(depth.asarray(dtype=np.float32), None, 0, 1, cv2.NORM_MINMAX, cv2.CV_32F)
    ir_image = cv2.normalize(ir.asarray(dtype=np.float32), None, 0, 1, cv2.NORM_MINMAX, cv2.CV_32F)

    cv2.imshow('Color', color_image)
    cv2.imshow('Depth', depth_image)
    cv2.imshow('ir', ir_image)

    key = cv2.waitKey(1)
    if key == ord('s'):
        point_cloud = registration.getPointXYZRGBArray()
        save_point_cloud(point_cloud, 'pointcloud.ply')
        print("Point cloud saved as pointcloud.ply")

    if key == ord('q') or key == 27:  # Press 'q' or 'ESC' to exit
        break

    listener.release(frames)

device.stop()
device.close()

cv2.destroyAllWindows()
