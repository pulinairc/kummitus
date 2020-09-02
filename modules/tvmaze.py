#import logging
import datetime
import dateutil.parser
import requests
import pytz
import sopel

def get_next_episode_info(show, output_timezone=pytz.timezone('UTC')):
	query = {'q': show, 'embed': 'nextepisode'}
	try:
		response = requests.get('http://api.tvmaze.com/singlesearch/shows', query)
		response.raise_for_status()
	except requests.exceptions.RequestException:
		#log.warning('TVMaze request caused an exception', exc_info=True)
		return None

	try:
		data = response.json()
	except ValueError:
		#log.warning('TVMaze returned invalid JSON: %r', response.text, exc_info=True)
		return None

	info = data['name']
	nextepisode = data.get('_embedded', {}).get('nextepisode')
	if nextepisode:
		#log.debug('next episode data: %r', nextepisode)
		dt = dateutil.parser.parse(nextepisode['airstamp'])
		info += ' - season %d, episode %d airs at %s' % (
			nextepisode['season'],
			nextepisode['number'],
			dt.astimezone(tz=output_timezone).strftime('%Y-%m-%d %H:%M %Z'),
		)
		now = datetime.datetime.now(dt.tzinfo)
		if dt > now:
			time_left = dt - now
			if time_left.days > 0:
				time_left_str = '%dd %dh' % (
					time_left.days,
					round(time_left.seconds / 3600),
				)
			elif time_left.seconds > 3600:
				time_left_str = '%dh %dm' % (
					round(time_left.seconds / 3600),
					round((time_left.seconds % 3600) / 60),
				)
			else:
				time_left_str = '%dm' % round(time_left.seconds / 60)
			#log.debug('time left: %r (%s)', time_left, time_left_str)
			info += ' (in %s)' % time_left_str
	else:
		info += ' - no next episode :('

	return info

@sopel.module.commands('next','n')
@sopel.module.example('.next Game of Thrones')
def next_ep(bot, trigger):
	search_for = trigger.group(2)
	if not trigger.group(2):
		return bot.say("🎬 Enter a TV Show to search for.")
	else:
		info = get_next_episode_info(''.join(search_for))
		return bot.say("🎬 %s" % info)
