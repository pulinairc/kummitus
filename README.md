# kummitus IRC bot

Current version of the IRC bot kummitus (Finnish for "ghost"). Mostly Finnish stuff. Based on [Sopel IRC Bot](https://github.com/sopel-irc/) that is written on Python.

## Systemd service

```ini
[Unit]
Description=Sopel IRC Bot (version 7.1.7, Python 3.9 via pyenv)
After=syslog.target network.target mongodb.service

[Service]
User=rolle
# Ensure Sopel runs inside the correct pyenv virtualenv
Environment=PATH=/home/rolle/.pyenv/versions/sopel-7-env/bin:/home/rolle/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/home/rolle/apps/node-v14.17.0-linux-x64/bin
Type=simple
KillMode=process
WorkingDirectory=/home/rolle/.sopel
ExecStart=/home/rolle/.pyenv/versions/sopel-7-env/bin/sopel
ExecStop=/bin/kill -s QUIT $MAINPID
PrivateTmp=true
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
```
