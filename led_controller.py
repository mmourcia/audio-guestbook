import sys
import time
from rpi_ws281x import PixelStrip, Color

def set_led(color, blinking=False):
    LED_COUNT = 1         # Nombre de LED
    LED_PIN = 21          # Broche GPIO utilisée pour contrôler la LED
    LED_FREQ_HZ = 800000  # Fréquence de la LED (Hz)
    LED_DMA = 10          # Canal DMA utilisé pour générer le signal PWM
    LED_BRIGHTNESS = 255  # Luminosité de la LED (0-255)
    LED_INVERT = False    # True pour une sortie inversée, False pour une sortie normale
    LED_CHANNEL = 0       # Numéro du canal GPIO utilisé pour envoyer le signal PWM

    # Initialise le contrôleur LED
    strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
    strip.begin()

    # Convertit la couleur RVB en un objet Color
    color = Color(*color)

    # Allume la LED avec la couleur spécifiée
    strip.setPixelColor(0, color)
    strip.show()

    # Si le clignotement est activé, alterne entre éteindre et allumer la LED
    if blinking:
        while True:
            strip.setPixelColor(0, Color(0, 0, 0))  # Éteint la LED
            strip.show()
            time.sleep(0.5)
            strip.setPixelColor(0, color)           # Allume la LED
            strip.show()
            time.sleep(0.5)

if __name__ == "__main__":
    
    red = int(sys.argv[1])
    green = int(sys.argv[2])
    blue = int(sys.argv[3])
    blinking = bool(int(sys.argv[4]))

    set_led((red, green, blue), blinking)

