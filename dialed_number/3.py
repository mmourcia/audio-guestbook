import glob
import os
import pygame

def execute(rotary_dial):
    play_last_recording(rotary_dial)

def play_last_recording(rotary_dial):
    wav_files = glob.glob(os.path.join(rotary_dial.RECORDINGS_DIRECTORY, "*.wav"))
    if wav_files:
        last_recording = sorted(wav_files, key=os.path.getctime)[-1]
        rotary_dial.play_sound(last_recording)
    else:
        print("No recordings found")

