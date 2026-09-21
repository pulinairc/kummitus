# kummitus IRC bot

![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![Build](https://img.shields.io/github/actions/workflow/status/pulinairc/kummitus/deploy.yml?style=for-the-badge&logo=githubactions&logoColor=white)
![Version](https://img.shields.io/github/v/release/pulinairc/kummitus?style=for-the-badge&logo=github&logoColor=white)

Current version of the IRC bot kummitus (Finnish for "ghost").<br>
Mostly Finnish stuff.

Based on [Sopel IRC Bot](https://github.com/sopel-irc/) that is written on Python.

<img width="128" height="128" alt="image" src="https://github.com/user-attachments/assets/dc48b684-d9a9-42a8-8fe9-16222925d5dc" />

## Systemd service

```ini
[Unit]
Description=Sopel IRC Bot
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
