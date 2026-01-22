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
