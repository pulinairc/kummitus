"""
lastfm.py - last.fm now playing module for Sopel
Copyright 2015, Marcus Leivo <meicceli@sopel.mail.kapsi.fi>
Licensed under the Eiffel Forum License 2.
http://sopel.chat/
"""
from sopel import web
from sopel.module import commands, example
from bs4 import BeautifulSoup
import json
import urllib
import os
from dotenv import load_dotenv

load_dotenv()
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")


def get_lastfm_username(args, db_nick):
    if args and len(args.strip()) > 0:
        return args
    if db_nick:
        return db_nick
    return None


def get_np_info(username):
    username = web.quote(username)
    recent_tracks = web.get("http://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&format=json&user=%s&api_key=%s" % (username, LASTFM_API_KEY))

    #now playing track, or most recently scrobbled track
    now_playing = json.loads(recent_tracks)

    # if the user does not exist
    if 'recenttracks' not in now_playing:
        return None

    now_playing = now_playing['recenttracks']['track'][0]

    track = now_playing['name']
    album = now_playing['album']['#text']
    artist = now_playing['artist']['#text']

    # why the fuck doesnt this work with web.get() ???
    track_page = urllib.request.urlopen("http://ws.audioscrobbler.com/2.0/?method=track.getInfo&format=json&artist=%s&track=%s&username=%s&api_key=%s" % (web.quote(artist), web.quote(track), username, LASTFM_API_KEY))
    track_info = json.loads(track_page.read().decode())['track']
    user_playcount = "0"
    if 'userplaycount' in track_info:
        user_playcount = track_info['userplaycount']
    user_loved = False
    if int(track_info['userloved']) > 0:
        user_loved = True

    return {"track": track, "album": album, "artist": artist, "user_playcount": user_playcount, "user_loved": user_loved}


def generate_np_output(trackinfo):
    output = ""
    if trackinfo['user_loved']:
        # a red heart
        output += "\x035\u2665\x03 "

    output += "%s: %s" % (trackinfo['artist'], trackinfo['track'])

    if trackinfo['album']:
        output += " (%s)" % (trackinfo['album'])
    if trackinfo['user_playcount']:
        output += " (%s plays)" % (trackinfo['user_playcount'])
    return output


@commands('fm', 'np', 'last', 'lastfm')
def lastfm(bot, trigger):
    username = get_lastfm_username(trigger.group(2), bot.db.get_nick_value(trigger.nick, 'lastfm_user'))
    if not username:
        bot.reply("No username given. Set a username with .fmset <username>")
        return

    trackinfo = get_np_info(username)
    if not trackinfo:
        bot.reply("Couldn't find user.")
        return

    output = generate_np_output(trackinfo)
    bot.say(output)


@commands('fmset')
def set_lastfm_username(bot, trigger):
    if not trigger.group(2):
        bot.reply("No username given.")
        return
    user = trigger.group(2)
    bot.db.set_nick_value(trigger.nick, 'lastfm_user', user)
    bot.reply('Thanks, ' + user)


def get_lastfm_collage(url, username, modes):
    if len(modes) == 1:
        return 'http://%s/lastfm/collage.php?user=%s&type=7day&size=3x3' % (url, modes[0])
    elif len(modes) == 2:
        return 'http://%s/lastfm/collage.php?user=%s&type=%s&size=3x3' % (url, modes[0], modes[1])
    elif len(modes) == 3:
        return 'http://%s/lastfm/collage.php?user=%s&type=%s&size=%s' % (url, modes[0], modes[1], modes[2])
    elif len(modes) == 4:
        return 'http://%s/lastfm/collage.php?user=%s&type=%s&size=%s&caption=%s' % (url, modes[0], modes[1], modes[2], modes[3])
    elif len(modes) == 5:
        return 'http://%s/lastfm/collage.php?user=%s&type=%s&size=%s&caption=%s&artistonly=%s' % (url, modes[0], modes[1], modes[2], modes[3], modes[4])
    elif len(modes) == 6:
        return 'http://%s/lastfm/collage.php?user=%s&type=%s&size=%s&caption=%s&artistonly=%s&playcount=%s' % (url, modes[0], modes[1], modes[2], modes[3], modes[4], modes[5])
    elif len(modes) > 6:
        return 'Too many arguments! Input has to be: User Period Size Caption ArtistOnly Playcount'
    else:
        return 'http://%s/lastfm/collage.php?user=%s&type=7day&size=3x3' % (url, username)


@commands('col')
@example('.col neekeri 1month 4x4 true false true')
def lastfm_collage(bot, trigger):
    """user, type, size, caption, artistonly, playcount"""
    modes = trigger.group()[5:].split()
    username = get_lastfm_username(trigger.group(2), bot.db.get_nick_value(trigger.nick, 'lastfm_user'))
    output = get_lastfm_collage("tapmusic.net", username, modes)
    bot.reply(output)


@commands('col2')
@example('.col2 neekeri 1month 4x4 true false true')
def lastfm_collage_2(bot, trigger):
    """user, type, size, caption, artistonly, playcount"""
    modes = trigger.group()[5:].split()
    username = get_lastfm_username(trigger.group(2), bot.db.get_nick_value(trigger.nick, 'lastfm_user'))
    output = get_lastfm_collage("nsfcd.com", username, modes)
    bot.reply(output)


def get_lastfm_status():
    url = "http://status.last.fm/"
    soup = BeautifulSoup(web.get(url))
    output = ""
    statukset = soup.find_all('td', attrs={"class": "statussvc"})
    tilat = soup.find_all('span', attrs={"class": True})
    output = ""
    for i in range(len(statukset)):
        try:
            name = statukset[i].text
            status = tilat[i].text[2:]
            output += "%s %s; " % (name, status)
        except:
            pass
    return(output[:-2])


@commands('fmstatus', 'npstatus')
def fmstatusget(bot, trigger):
    bot.say(get_lastfm_status() + " - http://status.last.fm/")
