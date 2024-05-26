# Audio Guestbook

**WIP**

## Context

## Setup

### OS

Raspberry pi 2 W
Raspberry pi OS LITE 64 bits

With rpi-imager and options to 

* set username as guestbook
* set wifi settings

### Packages

**Via SSH**

```sh
sudo apt update
sudo apt install git python3-yaml mpg321
sudo apt remove python3-rpi.gpio
sudo apt install python3-rpi-lgpio
```

**Systemd**

```sh
sudo cp contrib/audio-guestbook.service /etc/systemd/system/
sudo chmod 644 /etc/systemd/system/audio-guestbook.service 
sudo systemctl daemon-reload
sudo systemctl enable audio-guestbook.service
sudo systemctl start audio-guestbook.service
```


## Code

Note that most of that code has been written by chatpgt.

```sh
git clone https://github.com/mmourcia/audio-guestbook.git
cd audio-guestbook
```


## Divers

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

