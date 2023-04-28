import argparse
import numpy as np
import cv2
import os
import time
from ultralytics import YOLO
from collections import deque
from datetime import datetime
from collections import defaultdict

from nuru import settings, people_tracking, kinect_lib, tracker_annotation_lib
from smanmi import network, util

PERSON_ID = 0

logger = util.createLogger('kinect', debug=False)

parser = argparse.ArgumentParser(description="Kinect Recorder")
parser.add_argument(
    '--streams', type=str, choices=['ir', 'color', 'depth', 'ir_rgb', 'scaled-color'], nargs='*', 
    default=['ir', 'color', 'depth', 'ir_rgb'], help='Stream types to subscribe to'
)
parser.add_argument(
    '--rec_streams', type=str, choices=['ir', 'color', 'depth', 'ir_rgb', 'scaled-color'], nargs='*', 
   default=['scaled-color', 'depth'],  help="Stream type to record"
)
parser.add_argument(
    '--yolo_model', type=str, default='yolov8n-seg', 
    help="YOLO model name. See settings.py for available models."
)
parser.add_argument(
    '--yolo_stream', type=str, default='ir_rgb', help="Kinect stream name for YOLO."
)
parser.add_argument(
    '--yolo_class_ids', type=int, nargs='*', default=[PERSON_ID], help='YOLO class ids to detect. 0 for people.'
)
parser.add_argument(
    '--data_out', type=str, default=settings.kinect_data_path, help="Data output folder."
)
parser.add_argument(
    '--flip', action='store_true', default=False, help="If kinect upside down."
)
parser.add_argument(
    '--run_yolo', action='store_true', default=False, help="Run yolo detector."
)
parser.add_argument(
    '--shimono_trafo_path', type=str, default=os.path.join(settings.blender_path, "data", "kinect_trafo.json"), 
    help="Kinect to Shimoni transform."
)
parser.add_argument(
    '--max_person_away_frames', type=int, default=3, 
    help="Number of frames to wait for a person to reappear after being lost."
)
parser.add_argument(
    '--display_streams', type=str, nargs='*', default=None, help="Streams to show in the UI."
)
parser.add_argument(
    '--dummy_kinect', type=str, nargs='*', default=None, help="Add depth and rgb video paths."
)
args = parser.parse_args()

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

        img_segments = defaultdict(list)
        for class_id, seg, bbox, score in zip(self.class_ids, self.segmentations, self.bboxes, self.scores):
            if self.class_ids_filter is None or class_id in self.class_ids_filter:
                c, r = np.mean(seg, axis=0).astype(int)
                img_segments[class_id].append({
                    "rgb_loc": [c, r],
                    "2D_outline": seg,
                    "bbox": bbox,
                    "score": score,
                    "class_name": self.model.names[int(class_id)],
                })
        return img_segments

class VideoWriter:
    def __init__(self, folder, record_streams):
        """Initialize the video writer."""

        self.folder = folder
        self.video_writers = {record_stream: None for record_stream in record_streams}
        self.recording = False
        self.nr_frames_rec = 0

    def create_recorder(self, frame_size, fps, name):
        """Create a video recorder."""

        is_color = True if len(frame_size) == 3 else False
        logger.info(f"Creating video recorder for stream: {name} RGB={is_color}")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        vid_path = os.path.join(self.folder, f'video_{name}_{timestamp}.mp4')
        fourcc = cv2.VideoWriter_fourcc(*'XVID')

        return cv2.VideoWriter(
            vid_path, fourcc, fps, frame_size[1::-1], isColor=is_color
        )

    def start_recording(self, frames, fps=30):
        """Start recording a video."""

        if not self.recording:
            for record_stream in self.video_writers.keys():
                self.video_writers[record_stream] = self.create_recorder(frames[record_stream].shape, fps=fps, name=record_stream)
            self.nr_frames_rec = 0
            self.recording = True
            logger.info(f"Starting recording for stream: {self.video_writers.keys()}")

    def stop_recording(self):
        """Stop recording a video."""

        if self.recording:
            logger.info(f"Stopping recording and storing: {self.folder}")
            self.recording = False
            for video_writer in self.video_writers.values():
                video_writer.release()
                video_writer = None

    def save_frames(self, frames):
        """Save a dict of frames to video."""

        if self.recording:
            logger.info(f"Recording frame {self.nr_frames_rec}")
            self.nr_frames_rec += 1
            for stream_name, video_writer in self.video_writers.items():

                assert stream_name in frames, f"Stream {stream_name} not recorded!"
                if len(frames[stream_name].shape) == 2:
                    frame = np.uint8(frames[stream_name] * 255)
                else:
                    frame = frames[stream_name]
                video_writer.write(frame)
    
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
    streams = set(args.streams + [args.yolo_stream] + args.rec_streams)

    # Initialize modules
    video_writer = VideoWriter(args.data_out, args.rec_streams)
    dynamic_fps = FPSCounter()
    if args.dummy_kinect:
        kinect = kinect_lib.KinectDummy(
            depth_video_path=args.dummy_kinect[0], 
            rgb_video_path=args.dummy_kinect[1],
            streams=list(streams), 
            shimono_trafo_path=args.shimono_trafo_path, 
            output_dir=args.data_out, 
            flip=args.flip
        )
    else:
        kinect = kinect_lib.Kinect(
            streams=list(streams), 
            shimono_trafo_path=args.shimono_trafo_path, 
            output_dir=args.data_out, 
            flip=args.flip
        )

    # Initialize YOLO tracking objects if specified
    if args.run_yolo:
        ys = YOLOSegmentation(settings.yolo_models[args.yolo_model], args.yolo_class_ids)
        annotator = tracker_annotation_lib.ImageAnnotator()
        # tracker = people_tracking.Tracker(args.max_person_away_frames)

    # Start Kinect frame stream   
    for frame_data in kinect:
        dynamic_fps.update()
        key = cv2.waitKey(1)
        
        # If yolo_stream is grayscale, convert to RGB
        if len(frame_data[args.yolo_stream].shape) == 2:
            frame_data[args.yolo_stream] = cv2.cvtColor(frame_data[args.yolo_stream], cv2.COLOR_GRAY2RGB)
        
        if args.run_yolo:
            # Run YOLO detection
            img_segments = ys.detect(frame_data[args.yolo_stream])

            # Get segment locations
            img_segments = kinect.get_mean_coords_for_segments(img_segments)

            # Track people only if cm coordinates are available
            tracked_people = img_segments
            # tracked_people = tracker.update(
            #     [seg for seg in img_segments[PERSON_ID] if "cm" in seg]
            # )

            # Draw detections
            annotator.draw_detections(frame_data[args.yolo_stream], tracked_people)

            # Send tracked people to integrator
            # network.send(settings.integrator_sig_port, dict(people_sensor=tracked_people))

        # Start/stop record video when 's' is pressed
        if key == ord('s'):
            if not video_writer.is_recording():
                video_writer.start_recording(frame_data, dynamic_fps.fps)
            else:
                video_writer.stop_recording()

        # Save point cloud when 'p' is pressed
        if key == ord('p'):
            kinect.save_point_cloud()

        # Save frame to the video file
        if video_writer.is_recording():
            video_writer.save_frames(frame_data)

        if key == ord('q') or key == 27:  # Press 'q' or 'ESC' to exit
            break

        # Show frames
        for stream, frame in frame_data.items():
            if args.display_streams is None:
                break
            if stream in args.display_streams:
                cv2.imshow(stream, frame)  

    kinect.close()
