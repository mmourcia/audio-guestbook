# dialed_number/9.py

import subprocess
import time

def execute(rotary_dial):
    try:
        # Commande pour placer un appel SIP vers 1001
        call_command = f"linphonecsh generic 'call sip:1001@192.168.0.251'"
        subprocess.Popen(call_command, shell=True)  # Utilisation de Popen pour lancer le processus en arrière-plan
        print("Appel vers 1001 en cours...")

        rotary_dial.play_sound("sounds/test.wav")  # Jouer un son dans le téléphone immédiatement

        # Attendre un court délai pour que l'appel commence
        time.sleep(5)

        # Vérifier l'état de l'appel jusqu'à ce que le destinataire décroche
        while True:
            calls_output = subprocess.check_output("linphonecsh generic 'calls'", shell=True, universal_newlines=True)
            if "OutgoingRinging" in calls_output:
                print("Appel en cours de sonnerie...")
                time.sleep(0.1)  # Attendre 0,10 seconde avant de vérifier à nouveau
            else:
                print("Le destinataire a décroché.")
                rotary_dial.stop_sound()  # Arrêter le son dans le téléphone
                break

    except subprocess.CalledProcessError as e:
        print(f"Erreur lors de la tentative d'appel SIP vers 1001 : {e}")
    except Exception as ex:
        print(f"Erreur inattendue : {ex}")

