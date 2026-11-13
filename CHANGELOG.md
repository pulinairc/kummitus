### 2.13.4: 2026-11-13

* Remove AI image and travel answers in private

### 2.13.3: 2026-11-13

* Remove AI chat in private messages
* Fix flood breaks resetting on restart

### 2.13.2: 2026-11-13

* Change YouTube numbers to use a dot, like 89.27k

### 2.13.1: 2026-11-13

* Change bot flood breaks to 5, 15, 30 and 60 minutes

### 2.13.0: 2026-11-13

* Change bot flood breaks to grow when someone keeps on
* Fix kummitus flirting back

### 2.12.2: 2026-11-13

* Change YouTube numbers to short forms like 89,27k

### 2.12.1: 2026-11-13

* Fix replying in English when asked to
* Remove autokick, Portsari judges slurs

### 2.12.0: 2026-11-13

* Add likes and length to YouTube titles with an API key

### 2.11.1: 2026-11-13

* Fix YouTube links in capitals getting no title

### 2.11.0: 2026-11-13

* Add channel rules and conduct to AI replies

### 2.10.4: 2026-11-13

* Add the pulina.fi stats that statbot kept

### 2.10.3: 2026-11-12

* Fix autokick reacting to private messages, hosts and ops

### 2.10.2: 2026-11-12

* Fix YouTube titles missing on the server

### 2.10.1: 2026-11-12

* Change YouTube separators to center dots

### 2.10.0: 2026-11-12

* Add YouTube title, uploader, date, views and likes

### 2.9.1: 2026-11-11

* Remove the wit.ai token from the code

### 2.9.0: 2026-11-11

* Add Pulina account application notices

### 2.8.1: 2026-11-11

* Add video resolution, length and description

### 2.8.0: 2026-11-11

* Upgrade to Sopel 8 and Python 3.12
* Patch vulnerable dependencies
* Drop unused aiohttp, praw and geoip2
* Replace removed sopel.web helpers
* Fix reminders and apua on Sopel 8

### 2.7.2: 2026-11-11

* Fix Dropbox image links without a description

### 2.7.1: 2026-11-10

* Rewrite !matka as travel module
* Show car, bike, walk and flight times
* Parse inflected place names with AI
* Remove dead vaelimatka.org lookup

### 2.7.0: 2026-11-09

* Add media info module for image links
* Describe images with cheap vision model
* Block private and loopback URLs
* Let aibot read linked media and pages
* Resolve links posted by other users

### 2.6.1: 2026-09-30

* Always use 2 minute flood break

### 2.6.0: 2026-09-21

* Let model choose who to address
* Add Finnish flag days to daily announcements
* Fetch flag days from live source
* Trim model run-on in IRC replies
* Fix summary 404 with stable model and fallback
* Add build and version badges to README

### 2.5.0: 2026-03-26

* Add per-user flood protection: max 3/min and 8/hour with warning message

### 2.4.0: 2026-03-07

* Focus short summary on topics instead of nick roll call

### 2.3.0: 2026-03-06

* Move daily summary from midnight to morning (06:00)
* Improve summary prompts with nick attribution and topic grouping
* Update model to gemini-3.1-flash-lite-preview

### 2.2.0: 2026-03-02

* Disable channel rules feature via flag (lite model too eager)
* Add channel rules feature: fetch from WP API, cache, and inject on relevant questions
* Add retry logic to summary, skip posting on failure
* Strip leaked thinking tokens from Gemini responses

### 2.1.0: 2026-02-13

* Fix summary: no markdown or formatting in output
* Fix summary prompt: English, strict 200 char limit for IRC

### 2.0.0: 2026-01-22

* Add GitHub Actions for automatic releases and deployment
* Add dual model setup: gemini-3-flash for main, lite for helpers
* Add retry logic with progressive delays and error details
* Reduce token usage: memory 10/500, context 600
* Disable auto-memory, use manual memories only
* Fix bot referring to itself in third person
* Strip :) and ;) randomly with 50% probability

### 1.9.0: 2026-01-17

* Switch to OpenRouter API with Google Gemini models
* Add comprehensive Latin-only emoticon list
* Add time awareness to responses
* Add flood protection with 3s cooldown per user
* Fix context handling and user attribution

### 1.8.0: 2026-01-16

* Add AI-based log search with automatic file selection
* Add memory consolidation with batching
* Add frequency/presence penalty to reduce repetition

### 1.7.0: 2026-01-15

* Add auto memory extraction
* Add Finnish holidays to daily messages
* Add AI-categorized oraakkeli answers

### 1.6.0: 2026-01-14

* Add nickname recognition
* Add disk monitor and error handler
* Add explicit no-repeat instructions

### 1.5.0: 2025-12-01

* Add long-term memory feature
* Add random participation when not mentioned
* Add cooldown period and summary feature

### 1.4.0: 2025-11-01

* Add OpenAI-powered bot
* Add scheduler for timed messages

### 1.3.0: 2025-10-01

* Rewrite weather module for Foreca
* Add autokick and ruuvitag weather

### 1.2.0: 2025-09-01

* Add chatterbot with MongoDB
* Add megahal and randomline

### 1.1.0: 2025-08-01

* Add trivia, fingerpori, tvmaze, YouTube search

### 1.0.0: 2025-07-01

* Initial release with FMI weather, horoscope, battle, jokes
