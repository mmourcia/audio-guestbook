# Audio Guestbook

**WIP, wait a little bit ;)**

## Context

Some good friends are leaving the area and we wanted to give them a gift, an audio guest book.  
As we're french, we decided to use the famous old rotary phone made by [Socotel, the `S63`](https://fr.wikipedia.org/wiki/T%C3%A9l%C3%A9phone_S63).

Must have features are :

* Be able to use the rotary dialer to execute some actions
* Be able to leave an audio message
* Be able to use mic and speaker from the main phone as well as the secondary speaker
* Be able to make it ring as it used to (Spoiler : I didn't managed to make it work snirf ...) 
* Use a rgb led to provide a status to users

Here are some credits I'd like to give because the authors inspired me :

* https://www.hackster.io/carolinebuttet/turn-a-rotary-phone-into-a-radio-and-travel-through-time-14fd79
* https://github.com/ThomasChappe/S63_Arduino
* https://github.com/revolunet/s63/

## Unboxing and understanding what's inside the S63

Here it is !

![s63_unboxing1](./img/s63_unboxing1.png)

### The rotary dialer

The rotary dialer is composed of 2 dry contacts related to :

* Is the rotary in use ? (blue and blue/while wires)
* Pulses counter linked to the dialed number (red and red/white wires)

### Mic and speakers

I found the speaker quality good enough to listen to messages while I found the quality of the microphone very poor.  
I decided to change the micro by one from an old unsed headset I had somewhere ;)

### Phone line

This part is absolutely not necessary. I'll maybe just use wires to power the raspberry pi.

## Setup

### Hardware

| Item               | Photo                                          | Description |
| ------------------ | ---------------------------------------------- | ----------- |
| Socotel S63 Phone  | ![Socotel S63](./img/socotel_s63.png)          | The phone !!(bought on [le bon coin](https://leconcoin.fr)) | 
| Raspberry pi 2 W   | ![raspberry pi 0 2w](./img/raspberrypi02w.jpg) | |
| USB sound card     | ![usb sound card](./img/usbsoundcard.jpg)      | To connect mic and speaker from the main phone              |
| Jack 3,5mm adapter | ![jack_screw](./img/jack_screw.png)            | To connect the secondary speaker                            |

### OS

Raspberry pi OS LITE 64 bits

With rpi-imager and options to 

* set username as guestbook
* set wifi settings

### Packages

**System**

```sh
sudo apt update
sudo apt install git python3-yaml mpg321 python3-pip
sudo apt remove python3-rpi.gpio
sudo apt install python3-rpi-lgpio
```

**Audio guestbook itself**

Note that most of that code has been written by chatpgt.

```sh
git clone https://github.com/mmourcia/audio-guestbook.git
cd audio-guestbook
```

**Systemd unit to launch the program at start**

```sh
sudo cp contrib/audio-guestbook.service /etc/systemd/system/
sudo chmod 644 /etc/systemd/system/audio-guestbook.service 
sudo systemctl daemon-reload
sudo systemctl enable audio-guestbook.service
sudo systemctl start audio-guestbook.service
```

## Wiring

### On hook contact

| Pin    | Endpoint |                 |
| ------ | -------- | --------------- |
| GPIO22 | Hook 1   | On hook contact |
| GND    | Hook 2   | |

### Rotary dialer

| Pin    | Endpoint  | Description   |
| ------ | --------- | ------------- |
| GPIO23 | Red       | Pulse counter |
| GND    | Red/White | |
| GPIO18 | Blue      | Rotary enable |

### Mic and speakers

## Troubleshooting

**Set capture volume**

First get the name of the mixer

```
amixer
```

And then set the volume capture

```
amixer sset 'Mic' 90%
```

**Get logs**

```sh
sudo journalctl -fu audio-guestbook.service
```
