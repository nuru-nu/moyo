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

from nuru import settings
from smanmi import network, util

logger = util.createLogger('videoGPT', debug=False)

parser = argparse.ArgumentParser(description="GPT Video Stream")
parser.add_argument(
    '--rec_streams', action='store_true',
   help="Stream type to record"
)
parser.add_argument(
    '--data_out', type=str, default=settings.kinect_data_path, help="Data output folder."
)
parser.add_argument(
    '--display_stream', action='store_true',
    help="Streams to show in the UI."
)
parser.add_argument(
    '--dummy_stream', type=str, default=None, help="Add stream video paths."
)
parser.add_argument(
    '--chatgpt_persona',
    type=str,
    default="emo_state_image_input",
)
parser.add_argument(
    '--gpt_responses_file_path',
    type=str,
    default=settings.gpt_responses_file_path,
)
parser.add_argument(
    '--img_gpt_stream', action='store_true',
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
    default=1,
    help="Factor by which to downscale images sent to chat gpt.",
)
parser.add_argument(
    '--webcam_index',
    type=int,
    default=0,
    help="Index of the Webcam. Default 0.",
)
args = parser.parse_args()

class VideoWriter:
    def __init__(self, output_dir):
        """Initialize the video writer."""

        self.output_dir = output_dir
        self.video_writer = None
        self.video_path = None
        self.recording = False
        self.fps = 30
        self.nr_frames_rec = 0
        self.t_prev = time.time()

    def create_recorder(self, frame_size, fps):
        """Create a video recorder."""

        self.fps = fps
        self.t_prev = time.time()
        self.nr_frames_rec = 0
        self.recording = True
        is_color = True if len(frame_size) == 3 else False
        logger.info(f"Creating video recorder for stream: RGB={is_color}")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.video_path = os.path.join(self.output_dir, f'video_stream_{timestamp}.mp4')
        fourcc = cv2.VideoWriter_fourcc(*'XVID')

        return cv2.VideoWriter(
            self.video_path, fourcc, self.fps, frame_size[1::-1], isColor=is_color
        )

    def start_recording(self, frame, fps=30):
        """Start recording a video."""

        if not self.recording:
            self.video_writer = self.create_recorder(frame.shape, fps)
            logger.info(f"Starting recording video stream: {self.video_path}")

    def stop_recording(self):
        """Stop recording a video."""

        if self.recording:
            logger.info(f"Stopping recording and storing: {self.video_path}")
            self.recording = False
            self.video_writer.release()
            self.video_writer = None

    def save_frames(self, frame):
        """Save a dict of frames to video."""

        # If there is time remaining, skip
        if time.time() - self.t_prev < 1 / self.fps:
            return
        self.t_prev = time.time()

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
        # logger.info(f"{self.fps:.2f}fps")

class StreamWebcam:
    """
    A Python class for iterating over webcam frames.
    """

    def __init__(self, webcam_index=0):
        """
        Initializes the video capture object.
        """
        self.cap = cv2.VideoCapture(webcam_index)
        if not self.cap.isOpened():
            raise ValueError("Could not open webcam. Please check the webcam index.")

    def __iter__(self):
        """
        Returns the iterator object (self).
        """
        return self

    def __next__(self):
        """
        Returns the next frame from the webcam.
        """
        ret, frame = self.cap.read()
        if not ret:
            self.cap.release()  # Release the resource if no frame is captured
            raise StopIteration("No more frames to show.")
        return frame

    def release(self):
        """
        Releases the video capture resource.
        """
        self.cap.release()

class StreamDummy:
    def __init__(self, video_path):
        self.name = os.path.basename(video_path)
        self.video_stream = cv2.VideoCapture(video_path)
        self.video_stream.set(cv2.CAP_PROP_POS_FRAMES, 0)

        self.frame_dt = 1 / self.video_stream.get(cv2.CAP_PROP_FPS)
        self.frame_count = int(self.video_stream.get(cv2.CAP_PROP_FRAME_COUNT))

        # Set the frame counter
        self.t_prev = time.time()
        self.frame = 0
    
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

        ret_stream_val, frame = self.video_stream.read()

        # Check that the frames are valid
        if not ret_stream_val:
            raise StopIteration

        self.frame += 1
        self.t_prev = time.time()

        return frame

    def close(self):
        """Close stream."""

        self.video_stream.release()

class ImageGPTComms:
    """Class for communicating image data with ChatGPT"""

    def __init__(
        self, 
        integrator_sig_port, 
        status_address, 
        gpt_cmd_port, 
        system_message, 
        interval_s, 
        gpt_responses_file_path,
        max_nr_msgs=50,
        max_tokens=1000,
        temperature=1,
        write_image_height=400,
        fake_gpt_response_time_s=4
    ):
        """Initialize the ChatGPTComms class"""

        self.integrator_sig_port = integrator_sig_port
        self.emo_state = {"valence": 0, "arousal": 0}
        self.answer = ""
        self.network_msg = ""   
        self.openai_client = OpenAI(api_key=settings.openai_api_key)
        self.next_gpt_phrase = None
        self.interval_s = interval_s
        self.t_prev = time.time()
        self.image = None
        self.next_image = None
        self.stop_threads = False
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.write_image_height = write_image_height
        self.fake_gpt_response_time_s = fake_gpt_response_time_s
        self.gpt_responses_file_path = gpt_responses_file_path
        self.copying_image = False

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

    def append_response_to_file(self, response):
        """Appends the response to file"""

        with open(self.gpt_responses_file_path, 'a') as file:
            file.write(response + '\n')

    def stop_all_threads(self):
        """Stops all threads"""

        self.stop_threads = True
        self.network_thread.join()
        self.image_to_gpt_thread.join()

    def __call__(self, image):
        """Send image to chatGPT"""

        if self.image is not None:
            return

        if image is None:
            return
        
        if self.next_image is not None:
            image = self.next_image
            self.write_image(image)
            self.next_image = None
        else:
            return
        
        if time.time() - self.t_prev > self.interval_s:
            logger.info(f"Idle dt: {(time.time() - self.t_prev):.2f}s. Sending Image...")
            self.copying_image = True
            self.image = image.copy()
            self.copying_image = False
            self.t_prev = time.time()

    def send_image_thread(self):
        """Waits for image to send to gpt server, extracts response and sends to server"""
        
        while not self.stop_threads:
            # Sleep if no image queued up
            if self.image is None or self.copying_image:
                time.sleep(1 / settings.gpt_hz)
                continue

            if not self.next_gpt_phrase:
                self.get_gpt_image_response(self.image)
            else:
                self.get_fake_gpt_response()

            self.image = None

    def get_fake_gpt_response(self):
        """Simulate gpt response"""

        # Set variables
        response_dt = self.fake_gpt_response_time_s
        answer = self.next_gpt_phrase
        self.next_gpt_phrase = None

        # "Thinking..."
        network.send(self.integrator_sig_port, dict(thinking_gpt=1))
        network.send(self.integrator_sig_port, dict(answer_gpt="Thinking..."))
        time.sleep(response_dt)
        network.send(self.integrator_sig_port, dict(thinking_gpt=0))

        # Responding
        network.send(self.integrator_sig_port, dict(speaking_gpt=1))
        logger.info(f"FAKE GPT API dt: {response_dt:.2f}s - Response: {answer}")
        self.emo_state = self.find_emo_state(answer)
        network.send(self.integrator_sig_port, dict(answer_gpt=answer))
        network.send(self.integrator_sig_port, dict(gpt_response_dt_min=response_dt/60))
        network.send(self.integrator_sig_port, dict(speaking_gpt=0))

    def get_gpt_image_response(self, image, new_image_height = 200):
        """Send image caht gpt and process response"""

        t0 = time.time()

        # Generate message
        ratio = new_image_height / image.shape[0]
        image = cv2.resize(image, (int(image.shape[1] * ratio), new_image_height))
        img_base64 = self.encode_image_to_base64(image)
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
        network.send(self.integrator_sig_port, dict(answer_gpt="Thinking..."))
        response = self.openai_client.chat.completions.create(
            model=settings.chat_gpt_model,
            messages=self.system_message + list(self.messages),
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            stream=True
        )
        network.send(self.integrator_sig_port, dict(thinking_gpt=0))

        # Get chatGPT response
        answer = ""
        network.send(self.integrator_sig_port, dict(speaking_gpt=1))
        for chunk in response:
            answer += chunk.choices[0].delta.content or ""
            network.send(self.integrator_sig_port, dict(answer_gpt=answer))
            self.emo_state = self.find_emo_state(answer)
        response_dt = time.time() - t0

        self.append_response_to_file(answer)
        logger.info(f"GPT API dt: {response_dt:.2f}s - Response: {answer}")
        network.send(self.integrator_sig_port, dict(gpt_response_dt_min=response_dt/60))
        network.send(self.integrator_sig_port, dict(speaking_gpt=0))
        
        # Append to message list
        self.messages.append({"role": "assistant", "content": answer})

    def set_next_image(self, next_image):
        """Sets next image for gpt to consume and writes to file for webserver."""

        self.next_image = next_image.copy()

    def write_image(self, image):
        """Resize and write image for web server"""   

        # Resize the image
        ratio = self.write_image_height / image.shape[0]
        image = cv2.resize(image, (int(image.shape[1] * ratio), self.write_image_height))

        # Write image
        ext = os.path.splitext(settings.disp_img_path)[-1]
        tmp_disp_img_path = os.path.join(os.path.dirname(settings.disp_img_path), f"tmp{ext}")
        cv2.imwrite(tmp_disp_img_path, image)
        os.rename(tmp_disp_img_path, settings.disp_img_path)
    
    def read_network_responses(self):
        """Process and respond to user input from network"""

        while not self.stop_threads:
            data = network.get_json(self.sock, {})
            if data.get("next_gpt_phrase", "Auto") != "Auto":
                self.next_gpt_phrase = data["next_gpt_phrase"]  
                logger.info(f"Set next phrase: {self.next_gpt_phrase}")
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
        """Encodes a NumPy array image to a base64 string."""

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


class MouseGPT:
    def __init__(self, image_gpt):
        """Initialize callback object with ImageGPTComms object."""

        self.image_gpt = image_gpt
        self.frame = None

    def set_frame(self, frame):
        """Set image frame for callback function."""

        self.frame = frame

    def mouse_click(self, event, x, y, flags, param):
        """Mouse Click callback function set next frame for ImageGPTComms"""

        if event == cv2.EVENT_LBUTTONDOWN and self.frame is not None:
            self.image_gpt.set_next_image(self.frame)


if __name__ == "__main__":
    # Print interface info
    logger.info("Press 'q' or 'ESC' to exit. Press 'r' to start recording video stream.")

    # Initialize modules
    video_writer = VideoWriter(args.data_out)
    dynamic_fps = FPSCounter()
    if args.dummy_stream:
        video_stream = StreamDummy(video_path=args.dummy_stream)
    else:
        video_stream = StreamWebcam(webcam_index=args.webcam_index)
    
    if args.img_gpt_stream:
        image_gpt = ImageGPTComms(
            settings.integrator_sig_port, 
            settings.status_address, 
            settings.gpt_cmd_port,
            settings.chatgpt_personas[args.chatgpt_persona],
            args.gpt_interval_s,
            args.gpt_responses_file_path,
        )

    if args.display_stream:
        cv2.namedWindow("video_stream", cv2.WND_PROP_AUTOSIZE)
        if args.img_gpt_stream:
            mouse_gpt = MouseGPT(image_gpt)
            cv2.setMouseCallback("video_stream", mouse_gpt.mouse_click)

    # Start video stream
    for frame in video_stream:
        mouse_gpt.set_frame(frame)
        dynamic_fps.update()
        key = cv2.waitKey(1)

        # Resize video
        if args.gpt_img_div != 1:
            im_shape = np.array(frame).shape
            frame = cv2.resize(
                frame, 
                dsize=(im_shape[1] // args.gpt_img_div, im_shape[0] // args.gpt_img_div),
                interpolation=cv2.INTER_CUBIC
            )

        # Send image to chatgpt
        if args.img_gpt_stream:
            image_gpt(frame)
    
        # Save frame to the video file
        if video_writer.is_recording():
            video_writer.save_frames(frame)

        # Press 's' to select next frame for image GPT
        if key == ord('s') and args.img_gpt_stream:
            image_gpt.set_next_image(frame)

        # Start/stop record video when 'r' is pressed
        if key == ord('r'):
            if not video_writer.is_recording():
                video_writer.start_recording(frame, dynamic_fps.fps / 2)
            else:
                video_writer.stop_recording()

        # Press 'q' or 'ESC' to exit
        if key == ord('q') or key == 27:
            break

        # Show frames
        if args.display_stream:
            cv2.imshow("video_stream", frame)  

    if args.img_gpt_stream:
        image_gpt.stop_all_threads()
