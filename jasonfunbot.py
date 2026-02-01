import os
import json
import jasontools
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackContext
import random
import sys
from datetime import datetime
import re
import asyncio

from bully import bully
from stories import stories
from flights import flights

BOT_TOKEN = jasontools.parseEnvFile("BOT_TOKEN")
BOT_USERNAME = jasontools.parseEnvFile("BOT_USERNAME")

MASTER_USERNAME = jasontools.parseEnvFile("TELE_MASTERNAME")
MASTER_ID = jasontools.parseEnvFile("TELE_MASTERID")
HERMES_ID = jasontools.parseEnvFile("TELE_HERMESID")
TELE_DRANKSID = jasontools.parseEnvFile("TELE_DRANKSID")
TELE_MILE_HIGH_CLUBID = jasontools.parseEnvFile("TELE_MILE_HIGH_CLUBID")
TELE_HALLS_OF_VALORID= jasontools.parseEnvFile("TELE_HALLS_OF_VALORID")
userstates = {}

async def startMessage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # logAttempts("/help",update)

    welcome_one = "Welcome..."
    welcome_two = "You have chosen poorly..."
    welcome_three = "You are now apart of something larger."
    welcome_four = "/help will always be given here to those who ask for it."
    
    await context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_one)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_two)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_three)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_four)

async def touchMessage(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # logAttempts("/help",update)

    touch_one = "Scanning Device..."
    touch_two = "Analysis Complete..."

    touchroll = random.randint(0, 1)

    username = update.message.from_user.username
    if username == MASTER_USERNAME:
        touch_three = f"Oh hey master! Didnt see you there. You are definitely not gay!"
        
    elif touchroll == 1:
        touch_three = f"{username} is definitely gay."
    
    else:
        touch_three = f"{username} has been scanned is not gay."
    
    await context.bot.send_message(chat_id=update.effective_chat.id, text=touch_one)
    await asyncio.sleep(3)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=touch_two)
    await asyncio.sleep(2)
    await context.bot.send_message(chat_id=update.effective_chat.id, text=touch_three)

async def helpPeon(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # logAttempts("/help",update)

    commands = jasontools.readCommandList()

    await context.bot.send_message(chat_id=update.effective_chat.id, text=commands)

async def helpMaster(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # logAttempts("/help",update)

    commands = jasontools.readCommandList(master=True)

    await context.bot.send_message(chat_id=update.effective_chat.id, text=commands)

async def alertMaster(update: Update, context: ContextTypes.DEFAULT_TYPE, alertMessage):

    message_type: str = update.message.chat.type

    username: str = update.message.from_user.username

    if message_type != "private":
        message_type = update.message.chat.title                 

    alert = f"ALERT: {username} ({message_type}) | {alertMessage}"

    print(f"{alert}")
    await context.bot.send_message(chat_id=HERMES_ID,text=alert)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #FLIGHTS MODULE
    msg = update.effective_message
    chat = update.effective_chat


    if chat.id == TELE_MILE_HIGH_CLUBID and msg.document:
        if msg.document:
            print(msg.document)
            flights_file = await msg.document.get_file()
            await flights.save_raw_pdf_telegram(update, context)
    
    #Gets the username of sender
    username: str = update.message.chat.username

    #Checks if its "private" or "group" message
    message_type: str = update.message.chat.type

    if message_type != "private":
        message_type = update.message.chat.title

    tele_userid = update.message.chat.id

    text: str = update.message.text

    targetsName = update.message.from_user.username
    incomingmessage = f'{targetsName} ({tele_userid}) in {message_type}: "{text}"'

    # print(incomingmessage, message_type)
    messagelog(incomingmessage, message_type, targetsName)

    #REPLYING AN INSULT
    if str(targetsName) == MASTER_USERNAME:
        bullyroll = random.randint(0, bully.MASTER_BULLYTOLERANCE)
    else:
        bullyroll = random.randint(0, bully.BULLYTOLERANCE)
    # bullyroll = random.randint(0, 1)

    #CREATES MESSAGE ALERT
    if str(targetsName) != MASTER_USERNAME:
        messagealert = f"{bullyroll} / {bully.BULLYTOLERANCE}" + " Sent: " + "\n" + text

        await alertMaster(update, context, messagealert)


    #ADD NEW USER TO DATABASE-BULLY
    if await bully.checkTarget(update,context):
        useralert = f"Added {username} ({tele_userid}) to Jason's Pokédex"

        await alertMaster(update, context, useralert)

    # else:
    #     user_error = f"Error "

    #     await alertMaster(update, context, user_error)
    if str(targetsName) == MASTER_USERNAME:
        print(f"Bully rolled a {bullyroll} of {bully.MASTER_BULLYTOLERANCE}")
    else:
        print(f"Bully rolled a {bullyroll} of {bully.BULLYTOLERANCE}")
    

    if bullyroll == 0 and bully.BULLYSTATE == True:
        bullyinsult = bully.getInsult(targetsName)
        
        if bullyinsult == None:
            await alertMaster(update, context, f'Error when giving insult to {targetsName}')
        else:
            await update.message.reply_text(f"{bullyinsult}")



async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #Can be used to get user information
    print(f'ERROR: Update {update} caused error {context.error}')
    await alertMaster(update, context, f'Update {update} caused error {context.error}')
    return

def logAttempts(commandName, update: Update):
    
    user = update.effective_user.username
    
    message_type: str = update.message.chat.type

    if message_type != "private":
        message_type = update.message.chat.title
    
    logAttempt = f"{user} used the {commandName} command."
    
    messagelog(logAttempt, message_type, user)    
    alert = f"{user} used the {commandName} command."
    print(f"{alert}")
    return

def messagelog(incoming_message, grouptype, person):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    if grouptype == "private":
        filename = f'messagelogs/{grouptype}/{person}.txt'
    else:
        filename = f'messagelogs/{grouptype}/{grouptype}.txt'
    if not os.path.isfile(filename):
        print(f"Creating {filename}")
        os.makedirs(os.path.dirname(filename), exist_ok=True)

    with open(filename, 'a') as file:
        file.write("(" + current_time + ") " + incoming_message + '\n')

if __name__ == "__main__":
    print("Jason Intializing...")
    
    print(f"Bully Levels: {bully.BULLYTOLERANCE}")
    print(f"Master Bully Levels: {bully.MASTER_BULLYTOLERANCE}")

    app = Application.builder().token(BOT_TOKEN).build()

    # Normal Commands
    app.add_handler(CommandHandler('start', startMessage))
    app.add_handler(CommandHandler('help', helpPeon))
    app.add_handler(CommandHandler('touch', touchMessage))
    app.add_handler(CommandHandler('helpmaster', helpMaster, filters.User(username=MASTER_USERNAME)))
    # app.add_handler(CommandHandler('helpMaster', helpPeon))

    # MASTER Commands
    
    #BULLY MODULE
    app.add_handler(CommandHandler('makeMyselfAdmin', bully.admin_attempt))
    app.add_handler(CommandHandler('bullystatus', bully.bullystatus))
    app.add_handler(CommandHandler('bullyenable', bully.bullyenable, filters.User(username=MASTER_USERNAME)))
    app.add_handler(CommandHandler('bullydisable', bully.bullydisable, filters.User(username=MASTER_USERNAME)))
    app.add_handler(CommandHandler('setbullylevel', bully.set_bullytolerance, filters.User(username=MASTER_USERNAME)))
    app.add_handler(CommandHandler('getbullylevel', bully.get_bullytolerance))
    app.add_handler(CommandHandler('nextflight', flights.next_flight_details , filters.User(username=MASTER_USERNAME)))
    app.add_handler(CommandHandler('currentflight', flights.current_flight_details, filters.User(username=MASTER_USERNAME)))
    

    #STORY MODULE
    app.add_handler(CommandHandler('storytime', stories.tell_story))

    #app.add_handler(MessageHandler(filters.TEXT, handle_message))
    app.add_handler(MessageHandler(filters.TEXT | filters.Document.ALL, handle_message))

    # Errors
    app.add_error_handler(error) 

    app.run_polling(poll_interval=1)