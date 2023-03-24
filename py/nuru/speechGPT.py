from __future__ import division

import re
import sys
import argparse

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

    def __init__(self, integrator_sig_port, system_message):
        """Initialize the ChatGPTComms class"""

        self.emo_state = {"valence": 0, "arousal": 0}
        self.speech = ""
        self.answer = ""
        self.integrator_sig_port = integrator_sig_port

        self.messages = [
            {
                "role": "system",
                "content": system_message,
            },
        ]

    def __call__(self, responses):
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
                self.speech = transcript + overwrite_chars

                logger.info(f"You: {self.speech}")

                # Send user input to the server
                network.send(self.integrator_sig_port, dict(speech_gpt=self.speech))

                # Generate a response using ChatGPT
                self.answer = self.stream_chatGPT_response(self.speech)

                logger.info(f"ChatGPT: {self.answer}")

                # Check for exit command
                if re.search(r"\b(exit|quit)\b", transcript, re.I):
                    logger.info("Exiting..")
                    break

                num_chars_printed = 0

    def get_chatGPT_response(self, msg):
        """Get a response from ChatGPT"""
        self.messages.append({"role": "user", "content": msg})
        response = openai.ChatCompletion.create(
            model=settings.chat_gpt_model,
            messages=self.messages,
        )
        answer = response.choices[0].message.content
        self.emo_state = self.find_emo_state(answer)
        network.send(self.integrator_sig_port, dict(answer_gpt=answer))
        self.messages.append({"role": "assistant", "content": answer})
        return answer

    def stream_chatGPT_response(self, msg):
        """Get a streamed response from ChatGPT"""
        self.messages.append({"role": "user", "content": msg})

        response = openai.ChatCompletion.create(
            model=settings.chat_gpt_model,
            messages=self.messages,
            temperature=0,
            stream=True
        )

        answer = ""
        self.emo_state=None
        for chunk in response:
            answer += chunk['choices'][0]['delta'].get('content', '')
            network.send(self.integrator_sig_port, dict(answer_gpt=answer))

            print(answer, end='\r')
            sys.stdout.flush()
            if not self.emo_state:
                self.emo_state = self.find_emo_state(answer)

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
        settings.integrator_sig_port, settings.chatgpt_personas[args.chatgpt_persona]
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
