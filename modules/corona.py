#!/usr/bin/python
# -*- coding: utf-8 -*-
# Module for sopel, will fetch coronavirus data
# Codebase by Falconix - the legend
# 2020-03-05

import re
from collections import defaultdict
from datetime import datetime, timedelta

from bs4 import BeautifulSoup
from sopel import module
from sopel.formatting import *
import requests
import csv


class Corona:
    __deaths = 0
    __recovered = 0
    __confirmed = 0
    __critical = 0
    __new_deaths = ''
    __new_cases = ''

    @property
    def deaths(self):
        return self.__deaths

    @deaths.setter
    def deaths(self, value):
        self.__deaths += value

    @property
    def new_deaths(self):
        return self.__new_deaths

    @new_deaths.setter
    def new_deaths(self, value):
        self.__new_deaths += value

    @property
    def recovered(self):
        return self.__recovered

    @recovered.setter
    def recovered(self, value):
        self.__recovered += value

    @property
    def confirmed(self):
        return self.__confirmed

    @confirmed.setter
    def confirmed(self, value):
        self.__confirmed += value

    @property
    def new_cases(self):
        return self.__new_cases

    @new_cases.setter
    def new_cases(self, value):
        self.__new_cases += value

    @property
    def critical(self):
        return self.__critical

    @critical.setter
    def critical(self, value):
        self.__critical += value


@module.commands('corona', 'cor')

def coronavirus(bot, trigger):

    if trigger.group(2) == None:
        country = 'ALL'
    else:
        country = trigger.group(2).lower()



    base_url = 'https://www.worldometers.info/coronavirus/'
    response = requests.get(base_url)
    if not response.status_code == 200:
        return None

    content = response.content
    if not content:
        return None

    soup = BeautifulSoup(response.content.decode(), "html.parser")
    cases = defaultdict(Corona)

    table = soup.find('table', {'id': 'main_table_countries'}).find("tbody", recursive=True)
    rows = table.find_all('tr')

    tag_re = re.compile(r'(<!--.*?-->|<[^>]*>)')
    total = Corona
    for row in rows:
        columns = row.find_all('td')
        columns = [tag_re.sub('', str(x)).strip() for x in columns]
        if columns[0].lower() == 'total:':
            total.deaths = int(columns[3].replace(',', '') or 0)
            total.confirmed = int(columns[1].replace(',', '') or 0)
            total.recovered = int(columns[6].replace(',', '') or 0)
            total.new_deaths = str(columns[4])
            total.new_cases = str(columns[2])

            continue
        cases[columns[0].lower()].deaths = int(columns[3].replace(',', '') or 0)
        cases[columns[0].lower()].confirmed = int(columns[1].replace(',', '') or 0)
        cases[columns[0].lower()].recovered = int(columns[6].replace(',', '') or 0)
        cases[columns[0].lower()].new_deaths = str(columns[4])
        cases[columns[0].lower()].new_cases = str(columns[2])

    if country == 'ALL':
        bot.say(f'😷 \x0308{total.confirmed}\x03'
                f'(+\x0308{total.new_cases}\x03) '
                f'⚰️ \x0304{total.deaths}\x03'
                f'(+\x0304{total.new_deaths}\x0304) '
                f'👍 \x0303{total.recovered}\x03 '
                f'☠️ \x0305{round(total.deaths / total.confirmed * 100, 2)}%\x03')

    else:
        if str(country) in cases:
            bot.say(f'😷 \x0308{cases[str(country)].confirmed}\x03'
                    f'(\x0308{cases[str(country)].new_cases}\x03) '
                    f'⚰️ \x0304{cases[str(country)].deaths}\x03'
                    f'(\x0304{cases[str(country)].new_deaths}\x03) '
                    f'👍 \x0303{cases[str(country)].recovered}\x03 '
                    f'☠️ \x0305{round(cases[str(country)].deaths / cases[str(country)].confirmed * 100, 2)}%\x03')
        else:
            bot.say(f'Country not in the list')
