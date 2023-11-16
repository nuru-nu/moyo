import argparse
import numpy as np
import cv2
import os
import time
from collections import deque
from datetime import datetime

from nuru import settings, people_tracking, kinect_lib, tracker_annotation_lib, object_detection_lib
from smanmi import network, util

PERSON_ID = 0

logger = util.createLogger('kinect', debug=False)

parser = argparse.ArgumentParser(description="Kinect Recorder")
parser.add_argument(
    '--streams', type=str, choices=['ir', 'color', 'depth', 'ir_rgb', 'scaled-color', 'tracks'], nargs='*', 
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
    '--detection_steam', type=str, default='ir_rgb', help="Kinect stream name for YOLO."
)
parser.add_argument(
    '--detection_class_ids', type=int, nargs='*', default=[PERSON_ID], help='YOLO class ids to detect. 0 for people.'
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
    '--person_forget_time_s', type=float, default=2, 
    help="Time in seconds to wait for a person to reappear after being lost."
)
parser.add_argument(
    '--nr_frames_to_estimate_nr_people', type=int, default=10, 
    help="Size of people count queue. Larger values will increase detection time. Lower values will decrease accuracy"
)
parser.add_argument(
    '--display_streams', type=str, nargs='*', default=None, help="Streams to show in the UI."
)
parser.add_argument(
    '--dummy_kinect', type=str, nargs='*', default=None, help="Add depth and color stream video paths."
)
parser.add_argument(
    '--max_nr_people', type=int, default=10, 
    help="Number of people to uniquly identify, assigns ID and annotation color."
)
args = parser.parse_args()

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
        vid_path = os.path.join(self.folder, f'video_{name}_{timestamp}.avi')
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
    # Print interface info
    print("Save point cloud when 'p' is pressed.\nPress 'q' or 'ESC' to exit.")

    # Combine streams for Kinect 
    streams = set(args.streams + [args.detection_steam] + args.rec_streams)

    # Initialize modules
    video_writer = VideoWriter(args.data_out, args.rec_streams)
    dynamic_fps = FPSCounter()
    if args.dummy_kinect:
        kinect = kinect_lib.KinectDummy(
            depth_video_path=args.dummy_kinect[0], 
            scaled_color_video_path=args.dummy_kinect[1],
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
        image_detector = object_detection_lib.YOLOSegmentation(
            settings.yolo_models[args.yolo_model], 
            args.detection_class_ids,
        )
        annotator = tracker_annotation_lib.ImageAnnotator(num_colors=args.max_nr_people)
        tracker = people_tracking.Tracker(
            forget_dt=args.person_forget_time_s, 
            nr_people_queue_size=args.nr_frames_to_estimate_nr_people,
            max_person_id=args.max_nr_people,
        )

    for stream_name in args.display_streams:
        cv2.namedWindow(stream_name, cv2.WND_PROP_AUTOSIZE)

    # Start Kinect frame stream   
    for frame_data in kinect:
        dynamic_fps.update()
        key = cv2.waitKey(1)
        
        # If detection_steam is grayscale, convert to RGB
        if len(frame_data[args.detection_steam].shape) == 2:
            frame_data[args.detection_steam] = cv2.cvtColor(frame_data[args.detection_steam], cv2.COLOR_GRAY2RGB)
        
        # Save frame to the video file
        if video_writer.is_recording():
            video_writer.save_frames(frame_data)

        if args.run_yolo:
            # Run object detection
            img_segments = image_detector.detect(frame_data[args.detection_steam])

            # Get segment locations
            img_segments = kinect.get_mean_coords_for_segments(img_segments)

            # Track people only if cm coordinates are available
            tracked_people = tracker(img_segments.get(PERSON_ID, []))

            # Draw detections
            annotator.draw_detections(frame_data[args.detection_steam], {PERSON_ID: tracked_people})
            # annotator.draw_detections(frame_data[args.detection_steam], img_segments)

            # Draw 2d tracks
            if "tracks" in args.display_streams:
                frame_data["tracks"] = annotator.draw_2d_track(tracked_people)

            # Send tracked people to integrator
            people = [
                {
                    "cm": person.get("cm", []), 
                    "id": person["id"], 
                    "time_known": person.get("time_known", -1), 
                } 
                for person in tracked_people
            ]
            network.send(settings.integrator_sig_port, dict(people_sensor=people))


        # Start/stop record video when 's' is pressed
        if key == ord('s'):
            if not video_writer.is_recording():
                video_writer.start_recording(frame_data, dynamic_fps.fps)
            else:
                video_writer.stop_recording()

        # Save point cloud when 'p' is pressed
        if key == ord('p'):
            kinect.save_point_cloud()

        if key == ord('q') or key == 27:  # Press 'q' or 'ESC' to exit
            break

        # Show frames
        for stream, frame in frame_data.items():
            if args.display_streams is None:
                break
            if stream in args.display_streams:
                cv2.imshow(stream, frame)  

    kinect.close()
