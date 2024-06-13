# Actions

## 9

From scratch

Execute linphonec at first

```
linphonec
soundcard list
soundcard show
soundcard use <index>
register sip:1003@192.168.0.251 sip:192.168.0.251 1003pass
```

Then try to place a call

```
call sip:1001@192.168.0.251
```

If all is ok, you can go on.

```
quit
```

At this point, you'll have a working `~/.linphonerc` file and we'll be able to use it with linphonecsh

```
linphonecsh init -c ~/.linphonerc
linphonecsh generic "call sip:1001@192.168.0.251"
linphonecsh generic "terminate"
linphonecsh generic "answer"
linphonecsh generic "calls"
```
