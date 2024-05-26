import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"

import RPi.GPIO as GPIO
import time
import yaml
import pygame
import subprocess
import glob
from threading import Timer
from datetime import datetime

# Load configuration from YAML file
with open('config.yaml', 'r') as config_file:
    config = yaml.safe_load(config_file)

# Pin configuration from YAML
ROTARY_ENABLE_PIN = config['rotary']['enable_pin']
ROTARY_COUNT_PIN = config['rotary']['count_pin']
BOUNCE_TIME = config['rotary']['bounce_time']
DEBOUNCE_DELAY = config['rotary']['debounce_delay']
HOOK_PIN = config['hook']['pin']
HOOK_SOUND_FILE = config['hook']['sound_file']
AUDIO_DEVICE_ADDRESS = config['audio_output']['device_address']
RECORDINGS_DIRECTORY = "recordings"
RECORDING_DURATION = 10  # Duration in seconds for recording

# Initialize pygame mixer
pygame.mixer.init()

# Set the audio output device
pygame.mixer.pre_init(devicename=AUDIO_DEVICE_ADDRESS)

# Load the hook sound file
hook_sound = pygame.mixer.Sound(HOOK_SOUND_FILE)

# Global variable to store pulse count
pulse_count = 0
last_state = 1
dial_enabled = False
sound_playing = False  # Flag to track sound playback status
current_action = None  # Variable to track the current action
current_recording_process = None  # Variable to track the current recording process
recording_timer = None  # Variable to track the recording timer

# Callback function to count pulses
def count_pulse(channel):
    global pulse_count
    pulse_count += 1

# Callback function to handle hook state changes
def handle_hook_state(channel):
    global dial_enabled, sound_playing, current_action, current_recording_process
    hook_state = GPIO.input(HOOK_PIN)
    if hook_state == GPIO.LOW:  # Hook is open (NO)
        print("Hook is open, ready for dialing")
        if not sound_playing:
            hook_sound.play()  # Play the hook sound if not already playing
            sound_playing = True
        dial_enabled = True
        GPIO.add_event_detect(ROTARY_ENABLE_PIN, GPIO.BOTH)
        # Reset current action
        if current_action:
            current_action.stop()
            current_action = None
        # Cancel any pending recording timer
        cancel_recording_timer()
        # Stop any ongoing recording process
        if current_recording_process:
            current_recording_process.terminate()
            current_recording_process = None
    else:  # Hook is closed (NC)
        print("Hook is closed, dialing not allowed")
        if sound_playing:
            hook_sound.stop()  # Stop the sound playback if already playing
            sound_playing = False
        dial_enabled = False
        GPIO.remove_event_detect(ROTARY_ENABLE_PIN)
        GPIO.remove_event_detect(ROTARY_COUNT_PIN)
        # Reset current action
        if current_action:
            current_action.stop()
            current_action = None

# Function to play leave a message sound
def play_leave_message_sound():
    leave_message_sound = pygame.mixer.Sound("sounds/leave_a_message.mp3")
    leave_message_sound.play()

# Function to generate a beep sound
def generate_beep_sound():
    # You can implement the beep sound generation logic here
    pass

# Function to start recording audio
def start_audio_recording():
    global current_recording_process, recording_timer
    # Create recordings directory if it doesn't exist
    if not os.path.exists(RECORDINGS_DIRECTORY):
        os.makedirs(RECORDINGS_DIRECTORY)
    # Generate file name with current timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    file_name = f"recorded_audio_{timestamp}.wav"
    file_path = os.path.join(RECORDINGS_DIRECTORY, file_name)
    # Start audio recording with arecord
    current_recording_process = subprocess.Popen(["arecord", "-D", AUDIO_DEVICE_ADDRESS, "-f", "cd", "-c", "1", "-t", "wav", "-d", str(RECORDING_DURATION), file_path])
    # Start a timer to stop recording after specified duration
    recording_timer = Timer(RECORDING_DURATION, stop_recording)
    recording_timer.start()

# Function to cancel the recording timer
def cancel_recording_timer():
    global recording_timer
    if recording_timer:
        recording_timer.cancel()
        recording_timer = None

# Function to stop recording after specified duration
def stop_recording():
    global current_recording_process
    if current_recording_process:
        current_recording_process.terminate()
        current_recording_process = None

# Function to play the last recorded audio
def play_last_recording():
    # Get the list of wav files in the recordings directory
    wav_files = glob.glob(os.path.join(RECORDINGS_DIRECTORY, "*.wav"))
    if wav_files:
        # Get the last recorded audio file
        last_recording = sorted(wav_files, key=os.path.getctime)[-1]
        # Load and play the last recorded audio file
        last_recording_sound = pygame.mixer.Sound(last_recording)
        last_recording_sound.play()
    else:
        print("No recordings found")

# Setup GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.setup(ROTARY_ENABLE_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(ROTARY_COUNT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(HOOK_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Hook pin setup

# Add event detection for the hook pin
GPIO.add_event_detect(HOOK_PIN, GPIO.BOTH, callback=handle_hook_state, bouncetime=BOUNCE_TIME)

try:
    while True:
        if dial_enabled and GPIO.event_detected(ROTARY_ENABLE_PIN):
            current_state = GPIO.input(ROTARY_ENABLE_PIN)
            
            if last_state != current_state:
                if current_state == 0:  # Dial turned
                    GPIO.add_event_detect(ROTARY_COUNT_PIN, GPIO.BOTH, callback=count_pulse, bouncetime=BOUNCE_TIME)
                else:  # Dial released
                    if GPIO.event_detected(ROTARY_COUNT_PIN):  # Only print if counting was allowed
                        # Since we count both rising and falling edges, we divide by 2
                        dialed_number = int(pulse_count / 2)
                        
                        # Handle the '0' case (10 pulses)
                        if dialed_number == 10:
                            dialed_number = 0
                        
                        print(f"Dialed number: {dialed_number}")
                        if sound_playing:
                            hook_sound.stop()  # Stop the hook sound if playing
                            sound_playing = False
                        
                        # Check dialed numbers and perform corresponding actions
                        if dialed_number == 1:
                            current_action = pygame.mixer.Sound("sounds/greeting.wav")
                            current_action.play()
                        elif dialed_number == 2:
                            play_leave_message_sound()
                            generate_beep_sound()
                            start_audio_recording()
                        elif dialed_number == 3:
                            play_last_recording()
                        
                        GPIO.remove_event_detect(ROTARY_COUNT_PIN)
                        pulse_count = 0
                
                last_state = current_state

        time.sleep(DEBOUNCE_DELAY)  # Small delay to prevent high CPU usage

except KeyboardInterrupt:
    print("Program terminated")

finally:
    GPIO.cleanup()

