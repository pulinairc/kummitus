"""
disk_monitor.py - Sopel error handler and disk monitor module
Shuts down the bot gracefully on any error or when disk is full
Made by rolle
"""
import sopel
import sys
import os
from sopel import logger
from sopel.tools import events

LOGGER = logger.get_logger(__name__)

# Track if we've already initiated shutdown
shutdown_initiated = False

# Override Sopel's default error handler
def setup(bot):
    """Setup function to override error handling"""
    # Store original error handler
    original_error = bot.error

    def custom_error(trigger=None, exception=None, message=None):
        """Custom error handler that shuts down on any error"""
        global shutdown_initiated

        if shutdown_initiated:
            return

        shutdown_initiated = True
        LOGGER.error(f"Error detected: {exception or message}")

        # Ping rolle in #pulina
        try:
            bot.say(f"Virhe havaittu ({type(exception).__name__ if exception else 'unknown'}), sammutan itteni nyt, heippa! Ping rolle", '#pulina')
        except:
            pass

        # Quit from IRC gracefully
        try:
            bot.quit("Virhe havaittu, sammutetaan botti")
        except:
            pass

        # Exit the process
        LOGGER.error("Exiting due to error")
        sys.exit(1)

    # Replace error handler
    bot.error = custom_error

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
