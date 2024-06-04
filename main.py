import os
import signal
import sys
import RPi.GPIO as GPIO
import time
import yaml
import subprocess
import requests
import json
from gtts import gTTS
from threading import Timer, Thread
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
        self.sound_process = None
        self.sound_thread = None
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
        self.RECORDINGS_DIRECTORY = "recordings"
        self.RECORDING_DURATION = config['recording']['max_duration']
        self.TELEGRAM_TOKEN = config['telegram'].get('token')
        self.TELEGRAM_CHAT_ID = config['telegram'].get('chat_id')
        self.BLAGUESAPI_TOKEN = config['blagues-api'].get('token')
        self.LED_ENABLED = config.get('led', {}).get('enabled', False)
        self.AUDIO_DEVICE_ADDRESS = config['audio_output']['device_address']

    def setup_gpio(self):
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.ROTARY_ENABLE_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.ROTARY_COUNT_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        GPIO.setup(self.HOOK_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)  # Hook pin setup

    def init_audio(self):
        pass  # No need to initialize audio here since we'll use ffplay

    def init_telegram(self):
        if self.TELEGRAM_TOKEN and self.TELEGRAM_CHAT_ID:
            self.bot = Bot(token=self.TELEGRAM_TOKEN)
        else:
            self.bot = None

    def play_sound(self, sound_file):
        def _play():
            audio_device_address = self.AUDIO_DEVICE_ADDRESS
            os.environ["SDL_AUDIODRIVER"] = "alsa"
            os.environ["AUDIODEV"] = audio_device_address

            self.sound_process = subprocess.Popen(['ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet', sound_file])
            self.sound_process.wait()
            self.sound_playing = False

        if self.sound_playing:
            self.stop_sound()  # Ensure the previous sound is stopped

        self.sound_playing = True
        self.sound_thread = Thread(target=_play)
        self.sound_thread.start()

    def stop_sound(self):
        if self.sound_playing and self.sound_process:
            print("Stopping currently playing sound")
            self.sound_process.terminate()
            self.sound_thread.join()
            self.sound_playing = False
            self.sound_process = None
            print("Sound playback stopped")

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

    def stop_recording(self):
        self.stop_recording_process()
        if self.bot:
            self.send_telegram_message(self.current_file_path)
        self.is_recording = False  # Reset recording flag

    def count_pulse(self, channel):
        self.pulse_count += 1

    def control_led(self, color, blinking=False):
        if not self.LED_ENABLED:
            print("LED is not enabled in the configuration.")
            return {'success': False, 'message': 'LED is not enabled in the configuration.'}
        url = "http://localhost:5000/led"
        data = {"color": color, "blinking": blinking}
        headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

        try:
            response = requests.post(url, data=json.dumps(data), headers=headers)
            if response.status_code == 200:
                print("LED controlled successfully")
            else:
                print("Failed to control LED")
        except Exception as e:
            print(f"Error while controlling LED: {e}")

    def handle_hook_state(self, channel):
        hook_state = GPIO.input(self.HOOK_PIN)
        if hook_state == GPIO.LOW:  # Hook is open (NO)
            print("Hook is open, ready for dialing")
            self.control_led([0, 255, 0], blinking=True)
            if not self.sound_playing:
                self.play_sound(self.HOOK_SOUND_FILE)
            self.dial_enabled = True
            GPIO.add_event_detect(self.ROTARY_ENABLE_PIN, GPIO.BOTH)
            self.reset_current_action()
            self.cancel_recording_timer()
            self.stop_recording_process()
        else:  # Hook is closed (NC)
            print("Hook is closed, dialing not allowed")
            self.control_led([0, 255, 0], blinking=False)
            if self.sound_playing:
                self.stop_sound()
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
        self.control_led([255, 165, 0], blinking=False)
        GPIO.cleanup()

    def signal_handler(self, sig, frame):
        print("Got Signal, Stopping...")
        self.cleanup()
        sys.exit(0)

    def run(self):
        signal.signal(signal.SIGINT, self.signal_handler)
        try:
            self.control_led([0, 255, 0], blinking=False)
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
                                    self.stop_sound()
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
            print(f"Handling dialed number: {number}")  # Debug message
            # Stop any currently playing sound before handling the new action
            if self.sound_playing:
                self.stop_sound()

            # Set the LED to blinking blue when an action starts
            self.control_led([0, 0, 255], blinking=True)
            action_module = __import__(f"dialed_number.{number}", fromlist=["execute"])
            print(f"Imported module for number: {number}")  # Debug message
            action_module.execute(self)
            self.control_led([0, 0, 255], blinking=False)
        except ImportError:
            print(f"No action defined for number {number}")
        except Exception as e:
            print(f"Error handling dialed number {number}: {e}")

if __name__ == "__main__":
    rotary_dial = RotaryDial()
    rotary_dial.run()

