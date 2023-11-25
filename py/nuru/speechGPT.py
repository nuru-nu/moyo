from __future__ import division

import re
import sys
import argparse
import threading
import time

from google.cloud import speech
import nuru.gc_speech_to_text as stt

from openai import OpenAI
from nuru import settings
from smanmi import network, util
import numpy as np

from collections import deque

import audonnx
import audinterface

parser = argparse.ArgumentParser(
    description='Reads audio from active microphone, converts to text and prompts ChatGPT'
)
parser.add_argument(
    '--chatgpt_persona',
    type=str,
    default="emo_state_1",
)
args = parser.parse_args()

logger = util.createLogger('speechGPT', debug=False)

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
        self.openai_client = OpenAI(api_key=settings.openai_api_key)
        self.ready_to_respond = False

        self.sock = network.create_udp_socket(gpt_cmd_port, status_address)
        self.lock = threading.Lock()
        self.messages = [
            {
                "role": "system",
                "content": system_message,
            },
        ]
        logger.info("ChatGPTComms Initialized...")

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
            data = network.get_json(self.sock, {})
            if "gpt_msg" in data:
                if data["gpt_msg"] == "ready_to_respond":
                    self.ready_to_respond = True
                elif data["gpt_msg"] == "not_ready_to_respond":
                    self.ready_to_respond = False

                # GPT still only capable of responding to audio data
                continue

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
                num_chars_printed = 0
                network.send(self.integrator_sig_port, dict(listening_gpt=0))

                # Ignore if not ready to respond
                ready_to_respond = network.get_json(self.sock, {}).get("ready_to_respond", 0) == 1
                if not self.ready_to_respond:
                    logger.info(f"Particapant: {transcript + overwrite_chars}")
                    logger.info(f"ChatGPT: Not listening!")
                    network.send(self.integrator_sig_port, dict(speech_gpt=transcript + overwrite_chars))
                    continue
                
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
                network.send(self.integrator_sig_port, dict(responding_speech_gpt=0))

    def transcribe_emotion_from_audio(self):
        """Transcribe emotion from audio"""

        # Send the audio buffer to the speech to emotion model
        print(self.audio_buffer.shape)
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

        response = self.openai_client.chat.completions.create(
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
        response = self.openai_client.chat.completions.create(
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
            # print(chunk.choices[0].delta.content or "")
            answer += chunk.choices[0].delta.content or ""
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
