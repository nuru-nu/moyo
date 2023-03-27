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
    default="emo_out_0",
)
args = parser.parse_args()

logger = util.createLogger('speechGPT', debug=False)

openai.api_key = settings.openai_api_key

class ChatGPTComms:
    """Class for communicating with ChatGPT"""

    def __init__(self, integrator_sig_port, status_address, gpt_cmd_port, system_message):
        """Initialize the ChatGPTComms class"""

        self.integrator_sig_port = integrator_sig_port
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

        # Create threads for read_network_responses and read_audio_responses
        network_thread = threading.Thread(target=self.read_network_responses)
        audio_thread = threading.Thread(target=self.read_audio_responses, args=(responses,))

        # Start both threads
        network_thread.start()
        audio_thread.start()

        # Wait for both threads to complete
        network_thread.join()
        audio_thread.join()

    def read_network_responses(self):
        """Process and respond to user input from network"""

        while True:
            data = network.get_json(self.sock, None)
            if data and "gpt_msg" in data:

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

            transcript = result.alternatives[0].transcript
            overwrite_chars = " " * (num_chars_printed - len(transcript))

            if not result.is_final:
                sys.stdout.write(transcript + overwrite_chars + "\r")
                sys.stdout.flush()
                num_chars_printed = len(transcript)
            else:
                network.send(self.integrator_sig_port, dict(responding_speech_gpt=1))

                self.speech = transcript + overwrite_chars
                logger.info(f"Particapant: {self.speech}")

                # Send user input to the server
                network.send(self.integrator_sig_port, dict(speech_gpt=self.speech))

                # Generate a response using ChatGPT
                with self.lock:
                    self.answer = self.stream_chatGPT_response(self.speech)

                logger.info(f"ChatGPT: {self.answer}")
                num_chars_printed = 0
                network.send(self.integrator_sig_port, dict(responding_speech_gpt=0))


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
        emo = {"valence": float(emo[0]), "arousal": float(emo[1])}

        logger.info(f"EmoState: {emo}")
        network.send(self.integrator_sig_port, dict(valence_state_gpt=emo['valence']))
        network.send(self.integrator_sig_port, dict(arousal_state_gpt=emo['arousal']))

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

    listener = ChatGPTComms(
        settings.integrator_sig_port, 
        settings.status_address, 
        settings.gpt_cmd_port,
        settings.chatgpt_personas[args.chatgpt_persona]
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
