from pylibfreenect2 import Freenect2, SyncMultiFrameListener
from pylibfreenect2 import FrameType, Registration, Frame
from datetime import datetime
import numpy as np
import open3d as o3d
import cv2
import os
import json

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

            output["scaled-color"] = cv2.cvtColor(
                self.registered.asarray(dtype=np.uint8), cv2.COLOR_RGBA2BGR
            )
            output["scaled-color"][:,:,[0, 2]] = output["scaled-color"][:,:, [2, 0]] # BGR to RGB

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
            output["ir_rgb"] = self.ir_enhance(output["scaled-color"], output["ir"])

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

        for detections in seg_labels.values():
            for detection in detections:
                mask = np.zeros((self.width, self.height), dtype=np.uint8)
                cv2.fillPoly(mask, [detection["2D_outline"]], 255)

                points_3d = []
                for seg_point in np.argwhere(mask == 255):
                    c, r = seg_point
                    x, y, z = self.registration.getPointXYZ(self.undistorted, c, r)
                    if not np.isnan(x) and not np.isnan(y) and not np.isnan(z):
                        points_3d.append([x, y, z])
                
                if len(points_3d) == 0:
                    continue
                
                detection["3D_point"] = np.mean(points_3d, axis=0)
                detection["3D_shimoni"] = self.get_point_shimino_space(*detection["3D_point"])
                detection["cm"] = detection["3D_shimoni"] # HACK: for compatibility with old code

        return seg_labels
    
    def get_point_3d(self, c, r):
        """Get the 3D location of a point in the depthmap."""

        x, y, z = self.registration.getPointXYZ(self.undistorted, c, r)

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

class KinectDummy(Kinect):
    """A dummy Kinect class that reads from video streams."""
    
    def __init__(self, depth_video_path, rgb_video_path, *args, **kwargs):
        """Initialize the dummy Kinect."""

        super().__init__(*args, **kwargs)

        # Open the video streams
        self.depth_video = cv2.VideoCapture(depth_video_path)
        self.rgb_video = cv2.VideoCapture(rgb_video_path)

        # Check that the videos are valid
        self.depth_video.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.rgb_video.set(cv2.CAP_PROP_POS_FRAMES, 0)

        # Get the video properties
        self.width = int(self.depth_video.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.depth_video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.frame_count = int(self.depth_video.get(cv2.CAP_PROP_FRAME_COUNT))

        assert self.width == int(self.rgb_video.get(cv2.CAP_PROP_FRAME_WIDTH))
        assert self.height == int(self.rgb_video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        assert self.frame_count == int(self.rgb_video.get(cv2.CAP_PROP_FRAME_COUNT))

        # Set the frame counter
        self.frame = 0
    
    def __next__(self):
        """Get the next frames from the Kinect device."""

        # Reset the frame counter to loop the video
        if self.frame >= self.frame_count:
            self.frame = 0

        self.depth_video.set(cv2.CAP_PROP_POS_FRAMES, self.frame)
        self.rgb_video.set(cv2.CAP_PROP_POS_FRAMES, self.frame)

        ret_depth, depth_frame = self.depth_video.read()
        ret_rgb, rgb_frame = self.rgb_video.read()

        # Check that the frames are valid
        if not ret_depth or not ret_rgb:
            raise StopIteration

        self.frame += 1

        output = {
            "scaled-color": rgb_frame,
            "depth": depth_frame
        }

        if self.flip:
            for k, v in output.items():
                output[k] = cv2.flip(v, 1)
                output[k] = cv2.flip(v, 0)

        return output
    
    def close(self):
        """Close the Kinect device."""

        self.depth_video.release()
        self.rgb_video.release()