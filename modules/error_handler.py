"""
error_handler.py - Sopel error handler and disk monitor module
Shuts down the bot gracefully on disk I/O errors or when disk is full
Made by rolle
"""
import sopel
import sys
import os
from sopel import logger
import sqlite3

LOGGER = logger.get_logger(__name__)

# Track if we've already initiated shutdown
shutdown_initiated = False

# Killswitch file to prevent bot from starting after error
KILLSWITCH_FILE = '/home/rolle/.sopel/KILLSWITCH'

# Override Sopel's default error handler
def setup(bot):
    """Setup function to override error handling for specific errors"""
    # Check for killswitch file on startup
    if os.path.exists(KILLSWITCH_FILE):
        LOGGER.error("Killswitch file detected! Bot will not start. Remove /home/rolle/.sopel/KILLSWITCH to allow startup.")
        bot.quit("Killswitch active, not starting")
        sys.exit(1)

    # Store original error handler
    original_error = bot.error

    def custom_error(trigger=None, exception=None, message=None):
        """Custom error handler that shuts down only on disk/database errors"""
        global shutdown_initiated

        if shutdown_initiated:
            return

        # Convert error to string for checking
        error_str = str(exception) if exception else str(message) if message else ""
        error_type = type(exception).__name__ if exception else ""

        # Only catch specific disk/database errors
        is_disk_error = (
            "disk I/O error" in error_str.lower() or
            "sqlite3.OperationalError" in error_type or
            isinstance(exception, sqlite3.OperationalError) or
            "Unexpected error" in error_str
        )

        if is_disk_error:
            shutdown_initiated = True
            LOGGER.error(f"Disk/database error detected: {exception or message}")

            # Create killswitch file to prevent restart
            try:
                with open(KILLSWITCH_FILE, 'w') as f:
                    f.write(f"Killswitch activated at {os.popen('date').read().strip()}\n")
                    f.write(f"Error: {exception or message}\n")
                LOGGER.error(f"Killswitch file created at {KILLSWITCH_FILE}")
            except:
                pass

            # Ping rolle in #pulina
            try:
                bot.say(f"Levy-/tietokantavirhe havaittu, sammutan itteni nyt, heippa! Ping rolle", '#pulina')
            except:
                pass

            # Quit from IRC gracefully
            try:
                bot.quit("Levy-/tietokantavirhe, sammutetaan botti")
            except:
                pass

            # Exit the process
            LOGGER.error("Exiting due to disk/database error")
            sys.exit(1)
        else:
            # For other errors, call the original error handler
            if original_error:
                original_error(trigger, exception, message)

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
