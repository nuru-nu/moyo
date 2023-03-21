from __future__ import division

import re
import sys
import os

from google.cloud import speech

import gc_speech_to_text as stt

import openai
import settings

import json
from smanmi import network, util

logger = util.createLogger('speechGPT', debug=False)

openai.api_key = settings.openai_api_key

messages = [
    {"role": "system", "content": settings.chatgpt_personas["emo_out_1"]},
]

class EmoStateListener:
    def __init__(self):
        # Initialize the emo_state member variable with default values
        self.emo_state = {"valence": 0, "arousal": 0}

    def __call__(self, responses):
        # Process the streaming responses from the speech recognizer
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
                speech_txt = transcript + overwrite_chars
                logger.info(f"You: {speech_txt}\n")

                messages.append({"role": "user", "content": speech_txt})
                chat_completion = openai.ChatCompletion.create(
                    model=settings.chat_gpt_model,
                    messages=messages
                )
                answer = chat_completion.choices[0].message.content
                logger.info(f"ChatGPT: {answer}")

                self.emo_state = self.find_emo_state(answer)
                messages.append({"role": "assistant", "content": answer})

                if re.search(r"\b(exit|quit)\b", transcript, re.I):
                    logger.info("Exiting..")
                    break

                num_chars_printed = 0

    def find_emo_state(self, response):
        # Extract the emo_state from the response
        try:
            emo = response[response.find('[')+1:].split("]")[0].split(",")
            emo = {"valence": float(emo[0]), "arousal": float(emo[1])}

            logger.info(f"EmoState: {emo}")

            return emo
        except IndexError:
            logger.warning(f"Emotional state response format incorrect: {response}")
            return self.emo_state


def main():
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

    listener = EmoStateListener()
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
