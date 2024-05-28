import os
import signal
import sys
import RPi.GPIO as GPIO
import time
import yaml
import pygame
import subprocess
import glob
import requests
from gtts import gTTS
from threading import Timer
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError
import tempfile

class RotaryDial:
    def __init__(self, config_file='config.yaml'):
        self.load_config(config_file)
        self.setup_gpio()
        self.init_audio()
        self.init_telegram()
        self.pulse_count = 0
        self.last_state = 1
        self.dial_enabled = False
        self.sound_playing = False
        self.current_action = None
        self.current_recording_process = None
        self.recording_timer = None
        self.is_recording = False  # Track if recording is in progress
        GPIO.add_event_detect(self.HOOK_PIN, GPIO.BOTH, callback=self.handle_hook_state, bouncetime=self.BOUNCE_TIME)

    def load_config(self, config_file):
        with open(config_file, 'r') as file:
            config = yaml.safe_load(file)
        self.ROTARY_ENABLE_PIN = config['rotary']['enable_pin']
        self.ROTARY_COUNT_PIN = config['rotary']['count_pin']
        self.BOUNCE_TIME = config['rotary']['bounce_time']
        self.DEBOUNCE_DELAY = config['rotary']['debounce_delay']
        self.HOOK_PIN = config['hook']['pin']
        self.HOOK_SOUND_FILE = config['hook']['sound_file']
        self.AUDIO_DEVICE_ADDRESS = config['audio_output']['device_address']
        self.RECORDINGS_DIRECTORY = "recordings"
        self.RECORDING_DURATION = config['recording']['max_duration']
        self.TELEGRAM_TOKEN = config['telegram'].get('token')
        self.TELEGRAM_CHAT_ID = config['telegram'].get('chat_id')
        self.BLAGUESAPI_TOKEN = config['blagues-api'].get('token')

    def setup_gpio(self):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.ROTARY_ENABLE_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.ROTARY_COUNT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.HOOK_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Hook pin setup

    def init_audio(self):
        os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
        pygame.mixer.init()
        pygame.mixer.pre_init(devicename=self.AUDIO_DEVICE_ADDRESS)
        self.hook_sound = pygame.mixer.Sound(self.HOOK_SOUND_FILE)

    def init_telegram(self):
        if self.TELEGRAM_TOKEN and self.TELEGRAM_CHAT_ID:
            self.bot = Bot(token=self.TELEGRAM_TOKEN)
        else:
            self.bot = None

    def play_sound(self, sound_file):
        sound = pygame.mixer.Sound(sound_file)
        sound.play()
        while pygame.mixer.get_busy():
            time.sleep(0.1)  # Wait for the sound to finish playing

    def text_to_speech(self, text, file_path):
        try:
            tts = gTTS(text=text, lang='fr')  # Assuming text is in French
            tts.save(file_path)
        except Exception as e:
            print(f"Failed to convert text to speech: {e}")

    def send_telegram_message(self, file_path):
        if self.bot:
            try:
                with open(file_path, 'rb') as audio_file:
                    self.bot.send_audio(chat_id=self.TELEGRAM_CHAT_ID, audio=audio_file)
                print("Recording sent via Telegram")
            except TelegramError as e:
                print(f"Failed to send recording via Telegram: {e}")
        else:
            print("Telegram bot is not initialized")

    def count_pulse(self, channel):
        self.pulse_count += 1

    def handle_hook_state(self, channel):
        hook_state = GPIO.input(self.HOOK_PIN)
        if hook_state == GPIO.LOW:  # Hook is open (NO)
            print("Hook is open, ready for dialing")
            if not self.sound_playing:
                self.hook_sound.play()
                self.sound_playing = True
            self.dial_enabled = True
            GPIO.add_event_detect(self.ROTARY_ENABLE_PIN, GPIO.BOTH)
            self.reset_current_action()
            self.cancel_recording_timer()
            self.stop_recording_process()
        else:  # Hook is closed (NC)
            print("Hook is closed, dialing not allowed")
            if self.sound_playing:
                self.hook_sound.stop()
                self.sound_playing = False
            self.dial_enabled = False
            GPIO.remove_event_detect(self.ROTARY_ENABLE_PIN)
            GPIO.remove_event_detect(self.ROTARY_COUNT_PIN)
            self.reset_current_action()
            if self.is_recording:  # Stop recording if the phone is hung up
                self.stop_recording()
                self.is_recording = False

    def reset_current_action(self):
        if self.current_action:
            self.current_action.stop()
            self.current_action = None

    def cancel_recording_timer(self):
        if self.recording_timer:
            self.recording_timer.cancel()
            self.recording_timer = None

    def stop_recording_process(self):
        if self.current_recording_process:
            self.current_recording_process.terminate()
            self.current_recording_process = None

    def cleanup(self):
        print("Cleaning up resources...")
        GPIO.cleanup()
        pygame.mixer.quit()

    def signal_handler(self, sig, frame):
        print("Got Signal, Stopping...")
        self.cleanup()
        sys.exit(0)

    def run(self):
        signal.signal(signal.SIGINT, self.signal_handler)
        try:
            while True:
                if self.dial_enabled and GPIO.event_detected(self.ROTARY_ENABLE_PIN):
                    current_state = GPIO.input(self.ROTARY_ENABLE_PIN)
                    if self.last_state != current_state:
                        if current_state == 0:  # Dial turned
                            GPIO.add_event_detect(self.ROTARY_COUNT_PIN, GPIO.BOTH, callback=self.count_pulse, bouncetime=self.BOUNCE_TIME)
                        else:  # Dial released
                            if GPIO.event_detected(self.ROTARY_COUNT_PIN):
                                dialed_number = int(self.pulse_count / 2)
                                if dialed_number == 10:
                                    dialed_number = 0
                                print(f"Dialed number: {dialed_number}")
                                if self.sound_playing:
                                    self.hook_sound.stop()
                                    self.sound_playing = False
                                self.handle_dialed_number(dialed_number)
                                GPIO.remove_event_detect(self.ROTARY_COUNT_PIN)
                                self.pulse_count = 0
                        self.last_state = current_state
                time.sleep(self.DEBOUNCE_DELAY)
        except KeyboardInterrupt:
            print("Program terminated")
        finally:
            self.cleanup()

    def handle_dialed_number(self, number):
        try:
            action_module = __import__(f"dialed_number.{number}", fromlist=["execute"])
            action_module.execute(self)
        except ImportError:
            print(f"No action defined for number {number}")

if __name__ == "__main__":
    rotary_dial = RotaryDial()
    rotary_dial.run()

