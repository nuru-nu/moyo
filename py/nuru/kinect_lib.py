from pylibfreenect2 import Freenect2, SyncMultiFrameListener
from pylibfreenect2 import FrameType, Registration, Frame
from datetime import datetime
import numpy as np
import open3d as o3d
import cv2
import os
import json
import time

class Kinect:
    def __init__(
            self, 
            streams=["color", "depth", "ir"], 
            shimono_trafo_path=None, 
            output_dir=None, 
            flip=False, 
            width = 512, 
            height = 424,
            subsample_step_size = 10,
        ):
        """Initialize the Kinect device."""

        self.freenect = Freenect2()
        num_devices = self.freenect.enumerateDevices()
        assert num_devices > 0, "No Kinect device detected"

        serial = self.freenect.getDeviceSerialNumber(0)
        self.device = self.freenect.openDevice(serial)
        
        self.streams = set(streams)
        self.output_dir = output_dir
        self.flip = flip
        self.width = width
        self.height = height
        self.subsample_step_size = subsample_step_size

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

        self.np_frames = {}

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
        self.np_frames = {}
        if "color" in self.streams:
            color = frames["color"]
            self.np_frames["color"] = cv2.cvtColor(
                color.asarray(dtype=np.uint8), cv2.COLOR_RGBA2BGR
            )
            self.np_frames["color"][:,:,[0, 2]] = self.np_frames["color"][:,:, [2, 0]] # BGR to RGB

            self.np_frames["scaled-color"] = cv2.cvtColor(
                self.registered.asarray(dtype=np.uint8), cv2.COLOR_RGBA2BGR
            )
            self.np_frames["scaled-color"][:,:,[0, 2]] = self.np_frames["scaled-color"][:,:,[2, 0]] # BGR to RGB

        if "depth" in self.streams:
            self.np_frames["depth"] = cv2.normalize(
                self.undistorted.asarray(dtype=np.float32),
                None,
                0,
                1,
                cv2.NORM_MINMAX,
                cv2.CV_32F,
            )

        if "ir" in self.streams:
            ir = frames["ir"]
            self.np_frames["ir"] = cv2.normalize(
                ir.asarray(dtype=np.float32),
                None,
                0,
                1,
                cv2.NORM_MINMAX,
                cv2.CV_32F,
            )
        if "ir_rgb" in self.streams:
            self.np_frames["ir_rgb"] = self.ir_enhance(self.np_frames["scaled-color"], self.np_frames["ir"])

        if self.flip:
            for k, v in self.np_frames.items():
                self.np_frames[k] = cv2.flip(v, 1)
                self.np_frames[k] = cv2.flip(v, 0)

        self.listener.release(frames)
        return self.np_frames
    
    def ir_enhance(self, rgb, ir):
        """Enhance the rgb image by adaptively adding IR to the V channel of the HSV image."""

        hsv_img = cv2.cvtColor(rgb, cv2.COLOR_BGR2HSV).astype(np.float32) / 255.0
        hsv_img[:,:,2] += np.clip(ir - hsv_img[:,:,2], 0, 1)
        rgb_img = cv2.cvtColor((hsv_img * 255).astype(np.uint8), cv2.COLOR_HSV2BGR)

        return rgb_img
    
    def get_mean_coords_for_segments(self, seg_labels):
        """Get the mean 3D location of each segmentation label using optimized numpy operations."""

        for detections in seg_labels.values():
            for detection in detections:
                detection["cm"] = [-99,-99,-99]
                mask = np.zeros((self.width, self.height), dtype=np.uint8)
                cv2.fillPoly(mask, [detection["2D_outline"]], 255)

                # Get indices of all points with value 255 in the mask.
                seg_points = np.argwhere(mask == 255)[::self.subsample_step_size]

                if len(seg_points) == 0:
                    continue

                # Extract 3D points
                points_3d = []
                for c, r in seg_points:
                    point_3d = self.get_point_3d(c, r)
                    if point_3d is not None:
                        points_3d.append(point_3d)

                if len(points_3d) == 0:
                    continue

                # Calculate color histogram
                colors = self.np_frames["scaled-color"][seg_points[:, 0], seg_points[:, 1]]
                detection["color_histogram"] = create_color_histogram(colors)

                detection["3D_point"] = np.mean(points_3d, axis=0)
                detection["cm"] = self.get_point_shimino_space(*detection["3D_point"])

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
    
    def __init__(self, depth_video_path, scaled_color_video_path, *args, **kwargs):
        """Initialize the dummy Kinect."""

        super().__init__(*args, **kwargs)

        # Open the video streams
        self.depth_video = cv2.VideoCapture(depth_video_path)
        self.rgb_video = cv2.VideoCapture(scaled_color_video_path)

        # Check that the videos are valid
        self.depth_video.set(cv2.CAP_PROP_POS_FRAMES, 0)
        self.rgb_video.set(cv2.CAP_PROP_POS_FRAMES, 0)

        # Get the video properties
        self.width = int(self.depth_video.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.depth_video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.frame_count = int(self.depth_video.get(cv2.CAP_PROP_FRAME_COUNT))
        self.frame_dt = 1 / self.depth_video.get(cv2.CAP_PROP_FPS)
        self.t_prev = time.time()

        assert self.width == int(self.rgb_video.get(cv2.CAP_PROP_FRAME_WIDTH))
        assert self.height == int(self.rgb_video.get(cv2.CAP_PROP_FRAME_HEIGHT))
        assert self.frame_count == int(self.rgb_video.get(cv2.CAP_PROP_FRAME_COUNT))

        self.bytes_per_pixel = 4  # Assuming 4 bytes per pixel (RGBA), adjust according to your needs

        # Set the frame counter
        self.frame = 0

        self.np_frames = {}

    def __next__(self):
        """Get the next color and depth frames."""

        # Reset the frame counter to loop the video
        if self.frame >= self.frame_count:
            self.frame = 0

        # If there is time remaining, wait
        time_elapsed = time.time() - self.t_prev
        time_to_wait = self.frame_dt - time_elapsed
        if time_to_wait > 0:
            time.sleep(time_to_wait)

        self.depth_video.set(cv2.CAP_PROP_POS_FRAMES, self.frame)
        self.rgb_video.set(cv2.CAP_PROP_POS_FRAMES, self.frame)

        self.np_frames = {}
        ret_depth, self.np_frames["depth"] = self.depth_video.read()
        self.np_frames["depth"] = cv2.cvtColor(self.np_frames["depth"], cv2.COLOR_RGB2GRAY).astype(np.float32) / 255.0
        ret_rgb, self.np_frames["scaled-color"] = self.rgb_video.read()

        self.depth = self.np_frames["depth"]

        # Check that the frames are valid
        if not ret_depth or not ret_rgb:
            raise StopIteration

        self.frame += 1
        self.t_prev = time.time()

        return self.np_frames
    
    def get_point_3d(self, c, r):
        """Get the 3D location of a point in the depthmap."""

        undistorted = Frame(
            self.width, 
            self.height, 
            self.bytes_per_pixel, 
            FrameType.Depth,
            self.depth * 4500.0
        )

        x, y, z = self.registration.getPointXYZ(undistorted, c, r)

        if np.isnan(x) or np.isnan(y) or np.isnan(z):
            return None
        
        return x, y, z
    
    def close(self):
        """Close the Kinect device."""

        self.depth_video.release()
        self.rgb_video.release()

class StreamDummy:
    def __init__(self, video_path):
        self.name = os.path.basename(video_path)
        self.video_stream = cv2.VideoCapture(video_path)
        self.video_stream.set(cv2.CAP_PROP_POS_FRAMES, 0)

        self.frame_dt = 1 / self.video_stream.get(cv2.CAP_PROP_FPS)
        self.width = int(self.video_stream.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.video_stream.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.frame_count = int(self.video_stream.get(cv2.CAP_PROP_FRAME_COUNT))

        # Set the frame counter
        self.t_prev = time.time()
        self.frame = 0
        self.np_frames = {}
    
    def __iter__(self):
        return self

    def __next__(self):
        """Get next frame."""

        # Reset the frame counter to loop the video
        if self.frame >= self.frame_count:
            self.frame = 0

        # If there is time remaining, wait
        time_elapsed = time.time() - self.t_prev
        time_to_wait = self.frame_dt - time_elapsed
        if time_to_wait > 0:
            time.sleep(time_to_wait)

        self.video_stream.set(cv2.CAP_PROP_POS_FRAMES, self.frame)

        self.np_frames = {}
        ret_stream_val, self.np_frames["vid_stream"] = self.video_stream.read()

        # Check that the frames are valid
        if not ret_stream_val:
            raise StopIteration

        self.frame += 1
        self.t_prev = time.time()

        return self.np_frames

    def close(self):
        """Close stream."""

        self.video_stream.release()

def create_color_histogram(rgb_colors, num_bins=8):
    # Initialize histogram
    histogram = np.zeros((3, num_bins))

    if len(rgb_colors) == 0:
        return histogram

    # Convert list of tuples to a NumPy array
    rgb_array = np.array(rgb_colors)

    # Calculate the bin size
    bin_size = 256 / num_bins

    # Find the appropriate bin for each color channel
    bin_indices = np.floor(rgb_array / bin_size).astype(int)

    # Update histogram counts
    for i in range(3):
        np.add.at(histogram[i], bin_indices[:, i], 1)

    return histogram