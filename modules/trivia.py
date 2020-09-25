'''
Trivia.py
2016 Mattia "DeederVel" Dui
Just a simple trivia script for your Sopel IRC Bot

Question files must be written with this format,
one question per line:

question**answer**points
another question**yet another answer**points

You can omit the points for the question by simply writing:

this has no points?**Exactly

Answers (both from the file and user input) are transformed
in lower case strings, where possible.
The script is full UTF-8 compatible.

############################
############################

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
'''

# coding=utf-8
import time, re, operator, threading
from sopel import module
from sopel.formatting import bold, color, underline
from sopel.module import priority, OP, HALFOP, require_privilege, require_chanmsg

#################
# CONFIGURATION #
#################
# The questions file
filequiz = "/home/user/.sopel/modules/q.txt"
# Insert here the path of the folder where the chart files will be stored
resultsPath = "/home/user/.sopel/modules/"
quizGeneral = resultsPath+"g.csv"
# Seconds of delay before the start of the trivia
defaultStartDelay = 3
# Seconds of delay BETWEEN the answer and the next question
defaultQuesDelay = 3
# Default points given to the user if not specified otherwise in the question line
defaultPoints = 2
# Leave autoNext to True if you want the bot to go to the successive question defaultQuesDelay seconds after a correct answer.
# Set this to False if you want to go to the successive question using the command .next
autoNext = True

####################
# LANGUAGE STRINGS #
####################

STR_ANS_RIGHT = "Congrats to {nick} that scores {points!s} points!"
STR_CHART_GENERAL = "General"
STR_CHART_LISTING_T = "{nick} is #{position!s} with {points!s} point(s)"
STR_CHART_LISTING_PTS_SING = "point"
STR_CHART_LISTING_PTS_PLUR = "points"
STR_CHART_MATCH = "Match"
STR_CHART_HEAD_PARTIAL = " chart (first {people!s}): "
STR_CHART_HEAD_TOTAL = " chart (FULL): "
STR_CHART_RESET = "Match chart resetted!"
STR_CHART_SAVED = "Chart saved and resetted"
STR_CSV_HEAD = "Nick,Points,Total"
STR_LOADING_ALLOK = "-- ALL OK, YOU CAN START WITH .trivia-start --"
STR_LOADING_ALLCREATED = "Questions and chart created, please wait the start by a moderator."
STR_LOADING_ALLLOADED = "Questions and chart loaded, please wait the start by a moderator."
STR_LOADING_CHART_CREATED = "General chart created"
STR_LOADING_CHART_CREATION = "The general chart has to be created. Trying..."
STR_LOADING_CHART_LOADED = "General chart loaded"
STR_LOADING_QLOADED = "Questions file LOADED. Questions loaded: {questions!s}"
STR_LOADING_WAIT = "-- WAIT THE ALL OK FROM THE BOT --"
STR_LOADING_QFILE_NOTFOUND = "ERROR: Questions file NOT found. Can't start the trivia."
STR_LOADING_ERR_UNK = "Unknown ERROR. Can't start the trivia."
STR_NOT_AUTH = "You are not authorized for this command :c"
STR_NO_CHART = "No chart available!"
STR_QUESTION_FIN = "I think there are no more questions!"
STR_QUESTION_ASK = "[Question #{question_n!s} ({question_pts!s} pts)] {question_text}"
STR_TRIVIA_ACTIVE = "Trivia is already active!"
STR_TRIVIA_OVER_ANN = "{nick} goes to {points!s} points"
STR_TRIVIA_OVER_SYNTAX = "Syntax: .quiz-over nick points"
STR_TRIVIA_STARTING = "Starting Trivia in...{seconds!s} seconds!"
STR_TRIVIA_TOLOAD = "You have to load up the questions and the standings with .trivia-load"
STR_TRIVIA_FIN = "Trivia is finished!"

################################################
################################################
## ACTUAL CODE, DON'T TOUCH IF YOU DON'T KNOW ##
## WHAT ARE YOU ACTUALLY DOING #LifeProTips   ##
################################################
################################################

###############
# GLOBAL VARS #
###############

questions = {}
userPoints = {}
genPoints = {}
questionIndex = 0
isStarted = False
isActive = False
tb = None

########################
# MSG FUNCTIONS        #
# It has to be pretty. #
########################

#Quiz info public msg
def quizinfo(bot, text):
	bot.say(bold(color(text.decode('utf-8'), 12, 8)))
#Quiz question/answer public msg
def quizqa(bot, text):
	bot.say(bold(color(text.decode('utf-8'), 8, 12)))
#Quiz alert public msg
def quizal(bot, text):
	bot.say(bold(color(text.decode('utf-8'), 8, 4)))
#Quiz standings public msg
def quizsth(bot, text):
	bot.say(bold(color(text.decode('utf-8'), 9, 2)))
def quizst(bot, text):
	bot.say(bold(color(text.decode('utf-8'), 11, 2)))
#Quiz bold public msg
def quizev(bot, text):
	bot.say(bold(text.decode('utf-8')))
#Quiz private msg
def quizmsg(bot, text, nick):
	bot.say(text.decode('utf-8'), nick)
#Notice msgs
def quiznot(bot, text, nick):
	bot.notice(bold(color(text.decode('utf-8'), 2)), nick)
def quiznotS(bot, text, nick):
	bot.notice(bold(color(text.decode('utf-8'), 3)), nick)
def quiznotE(bot, text, nick):
	bot.notice(bold(color(text.decode('utf-8'), 4)), nick)

##################
# CORE FUNCTIONS #
##################

############################
#Listen to every message wrote in the channel, but 
#discard it if the Trivia is not active
############################
@module.rule('(.*)')
def answers(bot, trigger):
	global isActive, questionIndex, userPoints, genPoints, tb
	if isActive:
		answer = questions[questionIndex]['a']
		if trigger.group(1).lower().strip().encode('utf-8') == answer.lower():
			points = questions[questionIndex]['p']
			rightnick = str(trigger.nick)
			userPoints[rightnick] = userPoints.get(rightnick, {"n":0})
			genPoints[rightnick] = genPoints.get(rightnick, {"n":0})

			quizqa(bot, STR_ANS_RIGHT.format(nick=trigger.nick, points=questions[questionIndex]['p'] ) )

			userPoints[rightnick]["n"] += int(questions[questionIndex]['p'])
			genPoints[rightnick]["n"] += int(questions[questionIndex]['p'])
			questionIndex += 1
			isActive = False		
			if autoNext:
				time.sleep(defaultQuesDelay)
				isActive = True
				next(bot, trigger)

############################
#Go to the successive question (it's also called at the start)
############################
def next(bot, trigger):
	global isActive
	if (questionIndex == (len(questions))):
		isActive = False
		quizinfo(bot, STR_QUESTION_FIN)
	else:
		isActive = True
		quizqa(bot, STR_QUESTION_ASK.format(question_n=questionIndex+1, question_pts=questions[questionIndex]['p'], question_text=questions[questionIndex]['q']))

############################
#Save the chart(s)
############################
def savePoints(bot, trigger):
	global userPoints, genPoints
	############################
	#Saving the match chart
	############################
	userPointsList = sorted(userPoints.items(),key=lambda x: (x[1]['n']),reverse=True)
	quizSerata = resultsPath+"quiz"+time.strftime("%Y-%m-%d@%H%M%S")+".csv"
	qs = open(quizSerata,"w")
	qs.write(STR_CSV_HEAD+"\n")
	for item in userPointsList:
		qs.write(str(item[0]) + "," + str(item[1]["n"]) + ","  + str((item[1]['n'])) + "\n")
	qs.close()
	############################
	#Saving the general chart
	############################
	genPointsList = sorted(genPoints.items(),key=lambda x: (x[1]['n']),reverse=True)
	qg = open(quizGeneral,"w")
	qg.write(STR_CSV_HEAD+"\n")
	for item in genPointsList:
		qg.write(str(item[0]) + "," + str(item[1]["n"]) + ","  + str((item[1]['n'])) + "\n")	
	qg.close() 
	############################
	#Reset chart in memory
	############################
	userPoints = {}
	genPoints = {}
	quiznotS(bot, STR_CHART_SAVED, trigger.nick)

############################
#Stop the Trivia
############################
def fermatutto(bot, trigger):
	global questionIndex, isActive, isStarted, isLoaded
	isStarted = False
	isActive = False
	quizinfo(bot, STR_TRIVIA_FIN)
	questionIndex = 0
	isLoaded = False

############################
#Show the pointz!!
############################
def listPoints(bot, trigger, isGen, howmuch):
	if len(userPoints) != 0:
		maxView = 0
		pointlist = sorted(genPoints.items(),key=lambda x: x[1]['n'],reverse=True) if isGen else sorted(userPoints.items(),key=lambda x: x[1]['n'],reverse=True)
		chartType = STR_CHART_GENERAL if isGen else STR_CHART_MATCH
		if (howmuch != 0):
			quizsth(bot, chartType + STR_CHART_HEAD_PARTIAL.format(people=howmuch))
			for item in pointlist:
				if maxView < howmuch:
					quizst(bot, STR_CHART_LISTING_T.format(nick=item[0], position=maxView+1, points=item[1]['n']))
					maxView += 1
		else:
			quizsth(bot, chartType + STR_CHART_HEAD_TOTAL)
			for item in pointlist:
				quizst(bot, STR_CHART_LISTING_T.format(nick=item[0], position=maxView+1, points=item[1]['n']))
				maxView += 1
	else:
		quizsth(bot, STR_NO_CHART)


################################
# COMMAND FUNCTIONS            #
#                              #
# If you want to change them,  #
# look in the                  #
# module.commands('something') #
# line in the head of          #
# each block of code           #
################################

############################
#Questions and chart files load command
############################
@require_chanmsg
@require_privilege(OP, STR_NOT_AUTH)
@module.commands('trivia-load')
@module.nickname_commands('.*load.*')
def load(bot, trigger):
	global questions, genPoints, isLoaded 
	q = 0
	questions = {}
	genPoints = {}
	areQuestionsOK = False
	try:
		with open(filequiz) as f:
			for line in f:
				lista = line.split("**")
				if (len(lista) == 3):
					lista = {'q': lista[0].strip('\n'), 'a': lista[1].strip('\n'), 'p': lista[2].strip('\n')}
				else:
					lista = {'q': lista[0].strip('\n'), 'a': lista[1].strip('\n'), 'p': defaultPoints}
				questions[q] = lista
				q += 1
		quiznotS(bot, STR_LOADING_QLOADED.format(questions=q), trigger.nick)
		quiznot(bot, STR_LOADING_WAIT, trigger.nick)
		areQuestionsOK = True
	except IOError as e:
		quiznotE(bot, STR_LOADING_QFILE_NOTFOUND, trigger.nick)
		areQuestionsOK = False
	except:
		quiznotE(bot, STR_LOADING_ERR_UNK, trigger.nick)
		areQuestionsOK = False
	if areQuestionsOK:
		try:
			with open(quizGeneral, 'r+') as f:
				currLine = -1
				for line in f:
					if (currLine !=  -1):
						lista = line.split(",")
						genPoints[lista[0].strip('\n')] = genPoints.get(lista[0].strip('\n'), {'n': int(lista[1].strip('\n'))})
					currLine += 1
			quiznotS(bot, STR_LOADING_CHART_LOADED, trigger.nick)
			quiznot(bot, STR_LOADING_ALLOK, trigger.nick)
			quizev(bot, STR_LOADING_ALLLOADED)
			isLoaded = True
		except IOError as e:
			quiznot(bot, STR_LOADING_CHART_CREATION, trigger.nick)
			qg = open(quizGeneral,"w")
			qg.write(STR_CSV_HEAD)	
			qg.close()
			quiznotS(bot, STR_LOADING_CHART_CREATED, trigger.nick)
			quiznot(bot, STR_LOADING_ALLOK, trigger.nick)
			quizev(bot, STR_LOADING_ALLCREATED)
			isLoaded = True
		except:
			quiznotE(bot, STR_LOADING_ERR_UNK, trigger.nick)
			isLoaded = False
		
############################
#Trivia start command
############################
@require_chanmsg
@require_privilege(OP, STR_NOT_AUTH)
@module.commands('trivia-start')
@module.nickname_commands('.*start.*', '.*go.*')
def start(bot, trigger):
	global isActive, isStarted
	if len(questions) != 0 and isLoaded:
		if (not isActive and not isStarted):
			isActive = True
			isStarted = True
			quizinfo(bot, STR_TRIVIA_STARTING.format(seconds=defaultStartDelay) )
			time.sleep(defaultStartDelay)
			next(bot, trigger)
		else: 
			quiznot(bot, STR_TRIVIA_ACTIVE, trigger.nick)
	else:
		quiznotE(bot, STR_TRIVIA_TOLOAD, trigger.nick)

############################
#Trivia stop command
############################
@require_chanmsg
@require_privilege(OP, STR_NOT_AUTH)
@module.commands('trivia-stop')
@module.nickname_commands('.*stop.*')
def stop(bot, trigger):
	global isStarted
	if isStarted:
		fermatutto(bot, trigger)
		listPoints(bot, trigger, False, 0)
		savePoints(bot, trigger)

############################
#Match chart command
############################
@require_chanmsg
@require_privilege(OP, STR_NOT_AUTH)
@module.commands('trivia-chart', 'trivia-points')
def points(bot, trigger):
	global isStarted
	if isStarted:
		try: 
			listPoints(bot, trigger, False, (int(trigger.group(3)) if trigger.group(3) != None else 0))
		except ValueError:
			listPoints(bot, trigger, False, 0)

############################
#General chart command
############################
@require_chanmsg
@require_privilege(OP, STR_NOT_AUTH)
@module.commands('trivia-general', 'trivia-standings')
def general(bot, trigger):
	global isStarted
	if isStarted:
		try: 
			listPoints(bot, trigger, True, (int(trigger.group(3)) if trigger.group(3) != None else 0))
		except ValueError:
			listPoints(bot, trigger, True, 0)
	
############################
#Points override command
#
#Use this to change manually the points of a user
#during the Trivia match. Work both with positive
#and negative values.
#NOTE: does NOT OVERWRITES, but SUMS the value specified.
############################
@require_chanmsg
@require_privilege(OP, STR_NOT_AUTH)
@module.commands('trivia-over')
def over(bot, trigger):
	global userPoints, isStarted
	if isStarted:
		if ((trigger.group(3) != None) and (trigger.group(4) != None)):
			userPoints[trigger.group(3)] = userPoints.get(trigger.group(3), 0) + int(trigger.group(4))
			quizal(bot, STR_TRIVIA_OVER_ANN.format(nick=trigger.group(3), points=trigger.group(4)))
		else:
			quiznot(bot, STR_TRIVIA_OVER_SYNTAX, trigger.nick)

############################
#Match chart reset command
############################
@require_chanmsg
@require_privilege(OP, STR_NOT_AUTH)
@module.commands('trivia-reset')
def reset(bot, trigger):
	global userPoints, isStarted
	if isStarted:
		userPoints = {}
		quiznotS(bot, STR_CHART_RESET, trigger.nick)

############################
#Next question command
############################
@require_chanmsg
@require_privilege(OP, STR_NOT_AUTH)
@module.commands('next')
@module.nickname_commands('.*next.*', '.*go on.*')
def quizNext(bot, trigger):
	global isStarted, isActive
	if (isStarted and not isActive):
		next(bot, trigger)
