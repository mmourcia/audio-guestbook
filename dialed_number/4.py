import os
import requests
import pygame
import time
from gtts import gTTS

def execute(rotary_dial):
    if not rotary_dial.BLAGUESAPI_TOKEN:
        print("Token is not provided. Action disabled.")
        return

    headers = {"Authorization": f"Bearer {rotary_dial.BLAGUESAPI_TOKEN}"}
    response = requests.get("https://www.blagues-api.fr/api/random", headers=headers)
    if response.status_code == 200:
        joke_data = response.json()
        joke = joke_data.get("joke")
        answer = joke_data.get("answer")

        if joke:
            print(f"Joke: {joke}")
            joke_audio_file = os.path.join(rotary_dial.RECORDINGS_DIRECTORY, "joke_audio.wav")
            rotary_dial.text_to_speech(joke, joke_audio_file)
            rotary_dial.play_sound(joke_audio_file)
            while pygame.mixer.get_busy():
                time.sleep(0.1)

        if answer:
            print(f"Answer: {answer}")
            answer_audio_file = os.path.join(rotary_dial.RECORDINGS_DIRECTORY, "answer_audio.wav")
            rotary_dial.text_to_speech(answer, answer_audio_file)
            rotary_dial.play_sound(answer_audio_file)
            while pygame.mixer.get_busy():
                time.sleep(0.1)
    else:
        print(f"Failed to retrieve joke. Status code: {response.status_code}")

