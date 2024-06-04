import os
import time
import subprocess
from threading import Timer
from datetime import datetime

def execute(rotary_dial):
    rotary_dial.play_sound("sounds/leave_a_message.wav")
    while rotary_dial.sound_playing:
        time.sleep(0.1)


    rotary_dial.play_sound("sounds/beep.wav")
    while rotary_dial.sound_playing:
        time.sleep(0.1)

    start_audio_recording(rotary_dial)

def start_audio_recording(rotary_dial):
    if not os.path.exists(rotary_dial.RECORDINGS_DIRECTORY):
        os.makedirs(rotary_dial.RECORDINGS_DIRECTORY)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"recorded_audio_{timestamp}.wav"
    rotary_dial.current_file_path = os.path.join(rotary_dial.RECORDINGS_DIRECTORY, file_name)
    rotary_dial.current_recording_process = subprocess.Popen(
        ["arecord", "-D", rotary_dial.AUDIO_DEVICE_ADDRESS, "-f", "cd", "-c", "1", "-t", "wav", "-d", str(rotary_dial.RECORDING_DURATION), rotary_dial.current_file_path]
    )
    rotary_dial.recording_timer = Timer(rotary_dial.RECORDING_DURATION, stop_recording, [rotary_dial])
    rotary_dial.recording_timer.start()
    rotary_dial.is_recording = True

def stop_recording(rotary_dial):
    if rotary_dial.current_recording_process:
        rotary_dial.current_recording_process.terminate()
        rotary_dial.current_recording_process = None
    if rotary_dial.bot:
        rotary_dial.send_telegram_message(rotary_dial.current_file_path)
    rotary_dial.is_recording = False

