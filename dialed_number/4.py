import time
import requests

def execute(rotary_dial):
    print("Executing action for dialed number 4")
    # Stop any currently playing sound
    rotary_dial.stop_sound()

    # Fetch joke and answer
    joke, answer = get_joke(rotary_dial.BLAGUESAPI_TOKEN)

    # Create temporary files for the joke and the answer
    joke_file = "/tmp/joke.mp3"
    answer_file = "/tmp/answer.mp3"

    # Convert text to speech
    rotary_dial.text_to_speech(joke, joke_file)
    rotary_dial.text_to_speech(answer, answer_file)

    # Play the joke first
    print(f"Joke: {joke}")
    rotary_dial.play_sound(joke_file)

    # Wait for the joke to finish playing
    while rotary_dial.sound_playing:
        time.sleep(0.1)

    # Play the answer next
    print(f"Answer: {answer}")
    rotary_dial.play_sound(answer_file)

def get_joke(api_token):
    try:
        headers = {'Authorization': f'Bearer {api_token}'}
        response = requests.get('https://www.blagues-api.fr/api/random', headers=headers)
        if response.status_code == 200:
            joke_data = response.json()
            joke = joke_data['joke']
            answer = joke_data['answer']
            return joke, answer
        else:
            print(f"Error fetching joke: {response.status_code}")
            return "Je n'ai pas pu obtenir de blague.", "Veuillez réessayer plus tard."
    except Exception as e:
        print(f"Error fetching joke: {e}")
        return "Je n'ai pas pu obtenir de blague.", "Veuillez réessayer plus tard."

