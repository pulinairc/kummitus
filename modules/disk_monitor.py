"""
disk_monitor.py - Sopel disk monitor module
Monitors for disk errors and gracefully shuts down the bot when disk is full
Made by rolle
"""
import sopel
import sys
import os
from sopel import logger

LOGGER = logger.get_logger(__name__)

# Track if we've already initiated shutdown
shutdown_initiated = False

@sopel.module.interval(60)
@sopel.module.require_owner()
def check_disk_space(bot):
    """Check disk space every 60 seconds and shut down if critically low"""
    global shutdown_initiated

    if shutdown_initiated:
        return

    try:
        # Check disk space on current filesystem
        stat = os.statvfs('/home/rolle/.sopel')

        # Calculate free space in MB
        free_space_mb = (stat.f_bavail * stat.f_frsize) / (1024 * 1024)

        # If less than 100MB free, initiate shutdown
        if free_space_mb < 100:
            LOGGER.error(f"Critical: only {free_space_mb:.1f}MB disk space remaining. Initiating graceful shutdown.")
            shutdown_initiated = True

            # Ping rolle in #pulina
            try:
                bot.say(f"Levy täynnä ({free_space_mb:.0f}MB vapaana), sammutan itteni nyt, heippa! Ping rolle", '#pulina')
            except:
                pass

            # Quit from IRC gracefully
            try:
                bot.quit("Levy täynnä, sammutetaan botti")
            except:
                pass

            # Exit the process
            LOGGER.error("Exiting due to disk space")
            sys.exit(1)

    except Exception as e:
        LOGGER.error(f"Error checking disk space: {e}")
