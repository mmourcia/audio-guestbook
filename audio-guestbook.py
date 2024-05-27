import os
os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import signal
import sys
import RPi.GPIO as GPIO
import time
import yaml
import pygame
import subprocess
import glob
from threading import Timer
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError

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

    def play_leave_message_sound(self):
        leave_message_sound = pygame.mixer.Sound("sounds/leave_a_message.wav")
        leave_message_sound.play()

    def start_audio_recording(self):
        if not os.path.exists(self.RECORDINGS_DIRECTORY):
            os.makedirs(self.RECORDINGS_DIRECTORY)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"recorded_audio_{timestamp}.wav"
        self.current_file_path = os.path.join(self.RECORDINGS_DIRECTORY, file_name)
        self.current_recording_process = subprocess.Popen(["arecord", "-D", self.AUDIO_DEVICE_ADDRESS, "-f", "cd", "-c", "1", "-t", "wav", "-d", str(self.RECORDING_DURATION), self.current_file_path])
        self.recording_timer = Timer(self.RECORDING_DURATION, self.stop_recording)
        self.recording_timer.start()

    def stop_recording(self):
        self.stop_recording_process()
        if self.bot:
            self.send_telegram_message(self.current_file_path)

    def send_telegram_message(self, file_path):
        try:
            with open(file_path, 'rb') as audio_file:
                self.bot.send_audio(chat_id=self.TELEGRAM_CHAT_ID, audio=audio_file)
            print("Recording sent via Telegram")
        except TelegramError as e:
            print(f"Failed to send recording via Telegram: {e}")

    def play_last_recording(self):
        wav_files = glob.glob(os.path.join(self.RECORDINGS_DIRECTORY, "*.wav"))
        if wav_files:
            last_recording = sorted(wav_files, key=os.path.getctime)[-1]
            last_recording_sound = pygame.mixer.Sound(last_recording)
            last_recording_sound.play()
        else:
            print("No recordings found")

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
        if number == 1:
            self.current_action = pygame.mixer.Sound("sounds/greeting.wav")
            self.current_action.play()
        elif number == 2:
            self.play_leave_message_sound()
            time.sleep(5)
            self.start_audio_recording()
        elif number == 3:
            self.play_last_recording()

if __name__ == "__main__":
    rotary_dial = RotaryDial()
    rotary_dial.run()

