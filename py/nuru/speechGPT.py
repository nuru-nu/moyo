from __future__ import division

import re
import sys
import argparse
import threading
import time

from google.cloud import speech
import nuru.gc_speech_to_text as stt

import openai
from nuru import settings
from smanmi import network, util
import numpy as np

from scipy.signal import butter, filtfilt
from collections import deque

import audonnx
import audinterface

parser = argparse.ArgumentParser(
    description='Reads audio from active microphone, converts to text and prompts ChatGPT'
)
parser.add_argument(
    '--integrator_address',
    type=str,
    default='127.0.0.1',
)
parser.add_argument(
    '--chatgpt_persona',
    type=str,
    default="emo_state_1",
)
args = parser.parse_args()

logger = util.createLogger('speechGPT', debug=False)

openai.api_key = settings.openai_api_key

class ChatGPTComms:
    """Class for communicating with ChatGPT"""

    def __init__(self, integrator_sig_port, status_address, gpt_cmd_port, system_message, speech_to_emo_model):
        """Initialize the ChatGPTComms class"""

        self.integrator_sig_port = integrator_sig_port
        self.speech_to_emo_model = speech_to_emo_model
        self.emo_state = {"valence": 0, "arousal": 0}
        self.speech = ""
        self.answer = ""
        self.network_msg = ""   

        self.sock = network.create_udp_socket(gpt_cmd_port, status_address)
        self.lock = threading.Lock()
        self.messages = [
            {
                "role": "system",
                "content": system_message,
            },
        ]

    def __call__(self, responses):
        """Run read_network_responses and read_audio_responses in parallel."""

        self.recieving_input_audio = False
        self.audio_buffer = np.array([], dtype=np.float32)

        # Create threads for read_network_responses and read_audio_responses
        network_thread = threading.Thread(target=self.read_network_responses)
        speech_to_text_thread = threading.Thread(target=self.read_audio_responses, args=(responses,))
        audio_thread = threading.Thread(target=self.stream_audio)

        # Start all threads
        network_thread.start()
        speech_to_text_thread.start()
        audio_thread.start()

        # Wait for all threads to complete
        network_thread.join()
        speech_to_text_thread.join()
        audio_thread.join()

    def stream_audio(self):
        """Stream audio from microphone to audio buffer if speaking"""

        with stt.MicrophoneStream(settings.rate, settings.chunk) as stream:
            audio_generator = stream.generator()
            for audio_chunk in audio_generator:
                if self.recieving_input_audio:
                    audio_data = np.frombuffer(audio_chunk, dtype=np.int16).astype(np.float32)
                    self.audio_buffer = np.append(self.audio_buffer, audio_data)

    def read_network_responses(self):
        """Process and respond to user input from network"""

        while True:
            data = network.get_json(self.sock, None)
            if data and "gpt_msg" in data:
                logger.info('received gpt_action={data}')

                network.send(self.integrator_sig_port, dict(responding_network_gpt=1))

                self.network_msg = data["gpt_msg"]
                logger.info(f"Network: {self.network_msg}")

                # Generate a response using ChatGPT
                with self.lock:
                    self.answer = self.get_chatGPT_response(self.network_msg)

                logger.info(f"ChatGPT: {self.answer}")
                network.send(self.integrator_sig_port, dict(responding_network_gpt=0))
            time.sleep(1 / settings.gpt_hz)


    def read_audio_responses(self, responses):
        """Process and respond to user input from speech-to-text API."""

        num_chars_printed = 0
        for response in responses:
            if not response.results:
                continue
            
            result = response.results[0]
            if not result.alternatives:
                continue

            self.recieving_input_audio = True

            transcript = result.alternatives[0].transcript
            overwrite_chars = " " * (num_chars_printed - len(transcript))

            if not result.is_final:
                network.send(self.integrator_sig_port, dict(listening_gpt=1))
                sys.stdout.write(transcript + overwrite_chars + "\r")
                sys.stdout.flush()
                num_chars_printed = len(transcript)
            else:
                network.send(self.integrator_sig_port, dict(listening_gpt=0))
                network.send(self.integrator_sig_port, dict(responding_speech_gpt=1))

                # Send audio to the speech to emotion model
                self.recieving_input_audio = False
                emo_response = self.transcribe_emotion_from_audio()

                self.speech = emo_response + transcript + overwrite_chars
                logger.info(f"Particapant: {self.speech}")

                # Send user input to the server
                network.send(self.integrator_sig_port, dict(speech_gpt=self.speech))

                # Generate a response using ChatGPT
                with self.lock:
                    self.answer = self.stream_chatGPT_response(self.speech)

                logger.info(f"ChatGPT: {self.answer}")
                num_chars_printed = 0
                network.send(self.integrator_sig_port, dict(responding_speech_gpt=0))

    def transcribe_emotion_from_audio(self):
        """Transcribe emotion from audio"""

        # Send the audio buffer to the speech to emotion model
        emo_response = self.speech_to_emo_model.process_signal(self.audio_buffer, settings.rate)
        
        # Reset the audio buffer
        self.audio_buffer = np.array([], dtype=np.float32)

        # Create the formatted string
        emo_string = f"[{emo_response.iloc[0]['valence']:.2f}, "
        emo_string += f"{emo_response.iloc[0]['arousal']:.2f}, "
        emo_string += f"{emo_response.iloc[0]['dominance']:.2f}]"

        return emo_string

    def get_chatGPT_response(self, msg):
        """Get a response from ChatGPT"""
        
        self.messages.append({"role": "user", "content": msg})

        network.send(self.integrator_sig_port, dict(thinking_gpt=1))
        network.send(self.integrator_sig_port, dict(speaking_gpt=1))
        response = openai.ChatCompletion.create(
            model=settings.chat_gpt_model,
            messages=self.messages,
        )
        answer = response.choices[0].message.content
        self.emo_state = self.find_emo_state(answer)

        network.send(self.integrator_sig_port, dict(answer_gpt=answer))
        network.send(self.integrator_sig_port, dict(thinking_gpt=0))
        network.send(self.integrator_sig_port, dict(speaking_gpt=0))

        self.messages.append({"role": "assistant", "content": answer})
        return answer

    def stream_chatGPT_response(self, msg):
        """Get a streamed response from ChatGPT"""

        self.messages.append({"role": "user", "content": msg})

        network.send(self.integrator_sig_port, dict(thinking_gpt=1))
        response = openai.ChatCompletion.create(
            model=settings.chat_gpt_model,
            messages=self.messages,
            temperature=0,
            stream=True
        )
        network.send(self.integrator_sig_port, dict(thinking_gpt=0))

        answer = ""
        self.emo_state=None
        network.send(self.integrator_sig_port, dict(speaking_gpt=1))
        for chunk in response:
            answer += chunk['choices'][0]['delta'].get('content', '')
            network.send(self.integrator_sig_port, dict(answer_gpt=answer))

            print(answer, end='\r')
            sys.stdout.flush()
            if not self.emo_state:
                self.emo_state = self.find_emo_state(answer)
    
        network.send(self.integrator_sig_port, dict(speaking_gpt=0))

        self.messages.append({"role": "assistant", "content": answer})
        return answer

    def find_emo_state(self, response):
        """Find the emotional state in the response from ChatGPT"""

        if "[" not in response or "]" not in response:
            return None
        
        emo = response[response.find('[')+1:].split("]")[0].split(",")
        if len(emo) == 3:
            emo = [float(emo[0]), float(emo[1]), float(emo[2])]
        elif len(emo) == 2:
            emo = [float(emo[0]), float(emo[1]), 0]

        logger.info(f"EmoState: {emo}")
        network.send(self.integrator_sig_port, dict(target_css=emo[:2]))

        return emo

# import numpy as np
# from nuru import settings
# import time
# import cv2

# class AudioProcessor:
#     def __init__(self, lp_cutoff_freq=10, sampling_rate=settings.rate, threshold_alpha=0.1):
#         self.threshold_alpha = threshold_alpha
#         self.lp_cutoff_freq = lp_cutoff_freq
#         self.sampling_rate = sampling_rate
#         self.speaking_threshold = 0

#     def word_square_wave(self, envelope):
#         # Calculate the dynamic speaking threshold based on the rolling average
#         self.speaking_threshold = max(self.speaking_threshold, self.threshold_alpha * np.mean(envelope))

#         # Generate a square wave indicating speaking (1) and non-speaking (0) segments
#         square_wave = np.where(envelope > self.speaking_threshold, 1, 0)

#         return square_wave

#     def low_pass_filter(self, data, cutoff, fs, order=5):
#         nyq = 0.5 * fs
#         normal_cutoff = cutoff / nyq
#         b, a = butter(order, normal_cutoff, btype='low', analog=False)
#         return filtfilt(b, a, data)

#     def envelope_detector(self, audio_data):
#         # Calculate the absolute value of the audio signal
#         audio_abs = np.abs(audio_data)

#         # Apply low-pass filter to extract the envelope
#         envelope = self.low_pass_filter(audio_abs, self.lp_cutoff_freq, self.sampling_rate)

#         return envelope


# class RealTimeEnvelopeDisplay:
#     def __init__(self, num_buffers, buffer_length, width=600, height=300):
#         self.num_buffers = num_buffers
#         self.buffer_length = buffer_length
#         self.width = width
#         self.height = height
#         self.buffers = [deque(maxlen=buffer_length) for _ in range(num_buffers)]
#         self.all_time_max = 0
#         self.colors = [(255, 255, 255), (0, 255, 0), (0, 0, 255), (255, 255, 0), (0, 255, 255), (255, 0, 255)]

#     def update_buffer(self, index, envelope):
#         self.buffers[index].extend(envelope)
#         self.all_time_max = max(self.all_time_max, np.max(envelope))

#     def draw_legend(self, img):
#         legend_y_offset = 20
#         legend_x_offset = 5
#         legend_spacing = 20

#         for i in range(self.num_buffers):
#             color = self.colors[i % len(self.colors)]
#             cv2.line(img, (legend_x_offset, legend_y_offset + i * legend_spacing), (legend_x_offset + 20, legend_y_offset + i * legend_spacing), color, 1)
#             cv2.putText(img, f"Buffer {i + 1}", (legend_x_offset + 25, legend_y_offset + i * legend_spacing + 4), cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

#     def display(self):
#         img = np.zeros((self.height, self.width, 3), dtype=np.uint8)

#         for buf_index, buffer in enumerate(self.buffers):
#             if len(buffer) == 0:
#                 continue

#             n_points = len(buffer)
#             x_step = self.width / n_points
#             normalized_buffer = np.array(buffer) / self.all_time_max
#             color = self.colors[buf_index % len(self.colors)]

#             for i in range(1, n_points):
#                 x1 = int(x_step * (i - 1))
#                 x2 = int(x_step * i)
#                 y1 = int(self.height - normalized_buffer[i - 1] * self.height)
#                 y2 = int(self.height - normalized_buffer[i] * self.height)
#                 cv2.line(img, (x1, y1), (x2, y2), color, 1)

#         self.draw_legend(img)

#         cv2.imshow("Envelope", img)
#         cv2.waitKey(1)

def main():
    """
    Starts recording and streaming the microphone input to the speech API 
    and parses the responses to ChatGPT.
    """

    language_code = "en-US"

    client = speech.SpeechClient()
    config = speech.RecognitionConfig(
        encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
        sample_rate_hertz=settings.rate,
        language_code=language_code,
    )

    streaming_config = speech.StreamingRecognitionConfig(
        config=config, interim_results=True
    )

    model = audonnx.load(settings.ser_model_path)
    speech_to_emo = audinterface.Feature(
        model.labels('logits'),
        process_func=model,
        process_func_args={
            'outputs': 'logits',
        },
        sampling_rate=settings.ser_sampling_rate,
        resample=True,    
        verbose=True,
    )

    listener = ChatGPTComms(
        settings.integrator_sig_port, 
        settings.status_address, 
        settings.gpt_cmd_port,
        settings.chatgpt_personas[args.chatgpt_persona],
        speech_to_emo,
    )
    with stt.MicrophoneStream(settings.rate, settings.chunk) as stream:
        audio_generator = stream.generator()

        requests = (
            speech.StreamingRecognizeRequest(audio_content=content)
            for content in audio_generator
        )
        responses = client.streaming_recognize(streaming_config, requests)
        listener(responses)


if __name__ == "__main__":
    main()
