import argparse
import numpy as np
import cv2
import os
import time
from collections import deque
from datetime import datetime

from openai import OpenAI
import base64
from io import BytesIO
from PIL import Image
import threading
import sys
import re

from nuru import settings, people_tracking, kinect_lib, tracker_annotation_lib, object_detection_lib
from nurulib import network, util

PERSON_ID = 0

logger = util.createLogger('kinect', debug=False)

parser = argparse.ArgumentParser(description="Kinect Recorder")
parser.add_argument(
    '--streams', type=str, choices=['vid_stream', 'ir', 'color', 'depth', 'ir_rgb', 'scaled-color', 'tracks'], nargs='*', 
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
    '--display_streams', type=str, choices=['vid_stream', 'ir', 'color', 'depth', 'ir_rgb', 'scaled-color', 'tracks', 'untracked_detections'], nargs='*', 
    default=[], help="Streams to show in the UI."
)
parser.add_argument(
    '--dummy_kinect', type=str, nargs='*', default=None, help="Add depth and color stream video paths."
)
parser.add_argument(
    '--dummy_stream', type=str, default=None, help="Add stream video paths."
)
parser.add_argument(
    '--max_nr_people', type=int, default=10, 
    help="Number of people to uniquly identify, assigns ID and annotation color."
)
parser.add_argument(
    '--chatgpt_persona',
    type=str,
    default="emo_state_image_input",
)
parser.add_argument(
    '--img_gpt_stream', type=str, choices=['vid_stream', 'ir', 'color', 'depth', 'ir_rgb', 'scaled-color', 'tracks', 'untracked_detections'], 
    help="Send image stream to chatGPT",
)
parser.add_argument(
    '--gpt_interval_s',
    type=float,
    default=2.0,
    help="Seconds interval to send image to chatGPT",
)
parser.add_argument(
    '--gpt_img_div',
    type=int,
    default=4,
    help="Factor by which to downscale images sent to chat gpt.",
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
        # logger.info(f"{self.fps:.2f}fps")


def decode_base64_to_image(base64_string):
    """
    Decodes a base64 string to a NumPy array image.

    Args:
    base64_string (str): A base64 encoded string of the image.

    Returns:
    numpy.ndarray: A NumPy array representing the image.
    """
    # Extract the base64 part of the string
    encoded_data = base64_string.split(',')[1]

    # Decode the base64 string
    img_data = base64.b64decode(encoded_data)

    # Convert the byte data to a NumPy array
    np_arr = np.frombuffer(img_data, np.uint8)

    # Convert NumPy array to image
    img_bgr = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

    # Convert the image from BGR to RGB
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

    return img_rgb

class ImageGPTComms:
    """Class for communicating image data with ChatGPT"""

    def __init__(
        self, 
        integrator_sig_port, 
        status_address, 
        gpt_cmd_port, 
        system_message, 
        interval_s, 
        max_nr_msgs=50,
        max_tokens=1000,
        temperature=1,
    ):
        """Initialize the ChatGPTComms class"""

        self.integrator_sig_port = integrator_sig_port
        self.emo_state = {"valence": 0, "arousal": 0}
        self.answer = ""
        self.network_msg = ""   
        self.openai_client = OpenAI(api_key=settings.openai_api_key)
        self.ready_to_respond = False
        self.interval_s = interval_s
        self.t_prev = time.time()
        self.image = None
        self.stop_threads = False
        self.max_tokens = max_tokens
        self.temperature = temperature

        self.sock = network.create_udp_socket(gpt_cmd_port, status_address)
        self.lock = threading.Lock()
        self.messages = deque(maxlen=max_nr_msgs)
        self.system_message = [
            {
                "role": "system",
                "content": system_message,
            },
        ]

        # Create threads for read_network_responses and read_audio_responses
        self.network_thread = threading.Thread(target=self.read_network_responses)
        self.image_to_gpt_thread = threading.Thread(target=self.send_image_thread)

        # Start all threads
        self.network_thread.start()
        self.image_to_gpt_thread.start()


        logger.info("ChatGPTComms Initialized...")
    
    def stop_all_threads(self):
        self.stop_threads = True
        self.network_thread.join()
        self.image_to_gpt_thread.join()

    def __call__(self, image):
        """Send image to chatGPT"""

        if self.image is not None:
            return

        if image is None:
            return
        
        if time.time() - self.t_prev > self.interval_s:
            logger.info(f"Sending Image. dt: {time.time() - self.t_prev}s")
            self.image = image.copy()
            self.t_prev = time.time()

    def send_image_thread(self):
        
        while not self.stop_threads:
            t0 = time.time()
            if self.image is None:
                time.sleep(1 / settings.gpt_hz)
                continue

            # Generate message
            img_base64 = self.encode_image_to_base64(self.image)
            tmp_disp_img_path = os.path.join(os.path.dirname(settings.disp_img_path), f"toets.jpg")
            cv2.imwrite(tmp_disp_img_path, decode_base64_to_image(img_base64))
            self.messages.append(
                {
                    "role": "user", 
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": img_base64,
                                "detail": "low",
                            }
                        },
                    ]
                }
            )

            # Send to chatGPT
            network.send(self.integrator_sig_port, dict(thinking_gpt=1))
            response = self.openai_client.chat.completions.create(
                model=settings.chat_gpt_model,
                messages=self.system_message + list(self.messages),
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stream=True
            )
            network.send(self.integrator_sig_port, dict(thinking_gpt=0))

            # Write image
            ext = os.path.splitext(settings.disp_img_path)[-1]
            tmp_disp_img_path = os.path.join(os.path.dirname(settings.disp_img_path), f"tmp{ext}")
            cv2.imwrite(tmp_disp_img_path, self.image)
            os.rename(tmp_disp_img_path, settings.disp_img_path)

            # Get chatGPT response
            answer = ""
            network.send(self.integrator_sig_port, dict(speaking_gpt=1))
            for chunk in response:
                answer += chunk.choices[0].delta.content or ""
                network.send(self.integrator_sig_port, dict(answer_gpt=answer))

                # print(answer, end='\r')
                # sys.stdout.flush()
                self.emo_state = self.find_emo_state(answer)
            response_dt = time.time() - t0
            logger.info(f"{response_dt:.2f}s - GPT Response: {answer}")
            network.send(self.integrator_sig_port, dict(gpt_response_dt_min=response_dt/60))
            network.send(self.integrator_sig_port, dict(speaking_gpt=0))

            self.messages.append({"role": "assistant", "content": answer})
            self.image = None            
    
    def read_network_responses(self):
        """Process and respond to user input from network"""

        while not self.stop_threads:
            data = network.get_json(self.sock, {})
            if "gpt_msg" in data:
                if data["gpt_msg"] == "ready_to_respond":
                    self.ready_to_respond = True
                elif data["gpt_msg"] == "not_ready_to_respond":
                    self.ready_to_respond = False

                # GPT still only capable of responding to audio data
                continue

                # logger.info('received gpt_action={data}')
                # network.send(self.integrator_sig_port, dict(responding_network_gpt=1))

                # self.network_msg = data["gpt_msg"]
                # logger.info(f"Network: {self.network_msg}")

                # # Generate a response using ChatGPT
                # with self.lock:
                #     self.answer = self.get_chatGPT_response(self.network_msg)

                # logger.info(f"ChatGPT: {self.answer}")
                # network.send(self.integrator_sig_port, dict(responding_network_gpt=0))
            time.sleep(1 / settings.gpt_hz)

    def find_emo_state(self, response):
        """Find the emotional state in the response from ChatGPT"""

        matches = re.findall(r"\[.*?([-+]?\d*\.?\d+).*?,.*?([-+]?\d*\.?\d+).*?\]", response)
        
        if not matches:
            return None

        emo = [float(matches[0][0]), float(matches[0][1])]

        # logger.info(f"EmoState: {emo}")
        network.send(self.integrator_sig_port, dict(target_css=emo))

        return emo

    def encode_image_to_base64(self, np_image, mime_type="image/png"):
        """
        Encodes a NumPy array image to a base64 string.
        """

        # Convert the PIL image to a byte stream
        img_byte_arr = BytesIO()
        
        # Ensure rgb image
        if len(np_image.shape) == 2:
            np_image = np_image[...,None].repeat(3, axis=-1)*255
        assert len(np_image.shape) == 3

        pil_img = Image.fromarray(np_image.astype('uint8'), 'RGB')
        pil_img.save(img_byte_arr, format=mime_type.split('/')[-1])

        # Encode the byte stream to base64
        encoded_string = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')

        return f"data:{mime_type};base64,{encoded_string}"

if __name__ == "__main__":
    # Print interface info
    print("Save point cloud when 'p' is pressed.\nPress 'q' or 'ESC' to exit.")

    # Combine streams for Kinect 
    streams = set(args.streams + [args.detection_steam] + [args.img_gpt_stream]  + args.rec_streams)

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
    elif args.dummy_stream:
        kinect = kinect_lib.StreamDummy(
            video_path=args.dummy_stream
        )
    else:
        kinect = kinect_lib.Kinect(
            streams=list(streams), 
            shimono_trafo_path=args.shimono_trafo_path, 
            output_dir=args.data_out, 
            flip=args.flip
        )
    
    if args.img_gpt_stream:
        image_gpt = ImageGPTComms(
            settings.integrator_sig_port, 
            settings.status_address, 
            settings.gpt_cmd_port,
            settings.chatgpt_personas[args.chatgpt_persona],
            args.gpt_interval_s,
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
        
        if args.run_yolo:    
            # If detection_steam is grayscale, convert to RGB
            if len(frame_data[args.detection_steam].shape) == 2:
                frame_data[args.detection_steam] = cv2.cvtColor(frame_data[args.detection_steam], cv2.COLOR_GRAY2RGB)

            # Run object detection
            img_segments = image_detector.detect(frame_data[args.detection_steam])

            # Get segment locations
            img_segments = kinect.get_mean_coords_for_segments(img_segments)

            # Track people only if cm coordinates are available
            tracked_people = tracker(img_segments.get(PERSON_ID, []))

            # Draw detections
            if "untracked_detections" in args.display_streams:
                frame_data["untracked_detections"] = frame_data[args.detection_steam].copy()
                annotator.draw_detections(frame_data["untracked_detections"], img_segments)
            annotator.draw_detections(frame_data[args.detection_steam], {PERSON_ID: tracked_people})

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

        # Send image to chatgpt
        if args.img_gpt_stream in frame_data:
            im_shape = np.array(frame_data[args.img_gpt_stream]).shape
            frame_data[args.img_gpt_stream] = cv2.resize(
                frame_data[args.img_gpt_stream], 
                dsize=(im_shape[1]//args.gpt_img_div, im_shape[0]//args.gpt_img_div), 
                interpolation=cv2.INTER_CUBIC
            )
            image_gpt(frame_data[args.img_gpt_stream])
    
        # Save frame to the video file
        if video_writer.is_recording():
            video_writer.save_frames(frame_data)

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
            if args.img_gpt_stream is not None:
                image_gpt.stop_all_threads()
            break

        # # Write frame to file TODO Optimidp socket transfer
        # write_stream = args.img_gpt_stream if args.img_gpt_stream else args.detection_steam
        # if write_stream in frame_data:
        #     ext = os.path.splitext(settings.disp_img_path)[-1]
        #     tmp_disp_img_path = os.path.join(os.path.dirname(settings.disp_img_path), f"tmp{ext}")
        #     cv2.imwrite(tmp_disp_img_path, frame_data[write_stream])
        #     os.rename(tmp_disp_img_path, settings.disp_img_path)

        # Show frames
        for stream, frame in frame_data.items():
            if args.display_streams is None:
                break
            if stream in args.display_streams:
                cv2.imshow(stream, frame)  

    kinect.close()
