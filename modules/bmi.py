"""
bmi.py - Sopel BMI Module
Copyright 2015, Marcus Leivo <meicceli@sopel.mail.kapsi.fi>
Licensed under the Eiffel Forum License 2.
http://sopel.chat/
"""

from sopel.module import commands, example, rate


#@rate(60)
@commands('bmi')
@example('.bmi 60 1.90')
def bmi(bot, trigger):
    """.bmi <paino> <pituus>"""
    args = trigger.group()[5:].split()
    #Tarkastaa onko molemmat, paino ja pituus annettu
    if len(args) < 2:
        bot.reply("Voi vitun urpo :D Se on .bmi <paino> <pituus>")
        return

    #Asettaa painoksi ensiksi annetun luvun ja
    #pituudeksi jalkimmaisen luvun
    paino = str(args[0]).replace(',', '.')
    pituus = str(args[1]).replace(',', '.')

    #Tarkastaa onko painossa kirjaimia ja
    #jos on, keskeyttaa ohjelman
    numerot = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', '.']
    for i in range(len(paino)):
        if str(paino[i]) not in numerot:
            bot.reply(".bmi <paino> <pituus>")
            return

    #Tarkastaa onko pituudessa kirjaimia
    for i in range(len(pituus)):
        if str(pituus[i]) not in numerot:
            bot.reply(".bmi <paino> <pituus>")
            return

    #Laskee painoindeksin ja vastaa asianmukaisesti
    else:
        #Jos annettu pituus on yli 3, oletettavasti on syotetty
        #pituus senttimetreina. Tama muuntaa pituuden metreiksi
        if float(pituus) > 3:
            pituus = float(float(pituus) / 100)

        #Laskee painoindeksin
        fatness = float(paino) / float(pituus) ** 2
        #Laskee kuinka paljon tulee laihduttaa astraalipainoon
        laihdutettava = round(float(paino) - float(pituus) ** 2 * 17.0, 2)
        kasvettava = round(((float(paino) / 17.0) ** 0.5 - float(pituus)) * 100.0, 2)

        #Vertaa painoindeksia asettamiini arvoihin
        if fatness < 17.0:
            if round(fatness, 2) == 17.0:
                bot.reply("painoindeksisi on hitusen alle %s eli astraalipaino 5/5" % (round(fatness, 2)))
            else:
                bot.reply("painoindeksisi on %s eli astraalipaino 5/5" % (round(fatness, 2)))
        elif 17.0 <= fatness < 18.5:
            if round(fatness) == 18.5:
                bot.reply("painoindeksisi on hitusen alle %s eli et oo sami (mut laihduta yli %s kiloo tai kasva pituutta %s senttii et oot astraalitier)" % (round(fatness, 2), laihdutettava, kasvettava))
            else:
                bot.reply("painoindeksisi on %s eli et oo sami (mut laihduta yli %s kiloo tai kasva pituutta %s senttii et oot astraalitier)" % (round(fatness, 2), laihdutettava, kasvettava))
        elif 18.5 <= fatness < 20:
            if round(fatness) == 20:
                bot.reply("vitun sami :D sul kyl viel toivoo ku bmi hitusen alle 20 (kahen desimaalin tarkkuudel se on %s). laihduta %s kiloo tai kasva %s senttii nii oot astraalitieris" % (round(fatness, 2), laihdutettava, kasvettava))
            else:
                bot.reply("vitun sami :D sul kyl viel toivoo ku bmi alle 20 (kahen desimaalin tarkkuudel se on %s). laihduta %s kiloo tai kasva %s senttii nii oot astraalitieris" % (round(fatness, 2), laihdutettava, kasvettava))
        else:
            bot.reply("EI JUMALAUTA EI HELVETTI BMI %s SAATANAN SAMI JUMALAUTA EI VITTU SULLA ON YLI %s KILOO LAIHDUTETTAVANA TAI %s SENTTII KASVETTAVANA ASTRAALITIERII EI HELVETTI OIKEESTI" % (round(fatness, 2), laihdutettava, kasvettava))
