import sys
import time
import threading
import yaml
from rpi_ws281x import PixelStrip, Color
from flask import Flask, request, jsonify

app = Flask(__name__)

class LEDController:
    def __init__(self, config_file='config.yaml'):
        self.load_config(config_file)
        self.setup_led()

        self.blinking = False  # Flag to control blinking
        self.blink_thread = None  # Thread object for blinking
        self.blink_orange()

    def blink_orange(self):
        orange_color = (255, 165, 0)  # RGB value for orange color
        self.blink_led(orange_color)

    def load_config(self, config_file):
        with open(config_file, 'r') as file:
            config = yaml.safe_load(file)
        self.LED_PIN = config['led']['pin']
        self.LED_COUNT = config['led']['num_leds']
        self.LED_BRIGHTNESS = config['led']['brightness']

    def setup_led(self):
        LED_FREQ_HZ = 800000  # Fréquence de la LED (Hz)
        LED_DMA = 10          # Canal DMA utilisé pour générer le signal PWM
        LED_INVERT = False    # True pour une sortie inversée, False pour une sortie normale
        LED_CHANNEL = 0       # Numéro du canal GPIO utilisé pour envoyer le signal PWM

        # Initialise le contrôleur LED
        self.strip = PixelStrip(self.LED_COUNT, self.LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, self.LED_BRIGHTNESS, LED_CHANNEL)
        self.strip.begin()

    def set_led(self, color):
        # Convertit la couleur RVB en un objet Color
        color = Color(*color)

        # Allume la LED avec la couleur spécifiée
        self.strip.setPixelColor(0, color)
        self.strip.show()

    def blink_led(self, color):
        # Stop any previous blinking thread if it exists
        self.stop_blinking()
        # Define the blink function to run in a separate thread
        def blink_thread():
            while self.blinking:
                # Turn the LED on with the specified color
                self.set_led(color)
                time.sleep(0.5)
                # Turn the LED off
                self.set_led((0, 0, 0))
                time.sleep(0.5)

        # Create and start the thread
        self.blinking = True
        self.blink_thread = threading.Thread(target=blink_thread)
        self.blink_thread.start()

    def stop_blinking(self):
        self.blinking = False  # Set the flag to False to stop blinking
        if self.blink_thread:
            self.blink_thread.join()  # Wait for the thread to finish

led_controller = LEDController()

@app.route('/led', methods=['POST'])
def control_led():
    data = request.get_json()
    color = data.get('color')
    blinking = data.get('blinking', False)

    if blinking:
        led_controller.blink_led(color)
    else:
        led_controller.stop_blinking()
        led_controller.set_led(color)

    return jsonify({'success': True})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)

