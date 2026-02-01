import random
import csv
import json
from datetime import datetime
import os
import asyncio
from openai import OpenAI
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, CallbackContext 
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

BULLYSTATE = True

db_config = json.loads(os.getenv("DB_CONFIG"))

def parseEnvFile(itemName):
    itemSecret = os.getenv(str(itemName))

    if itemSecret:
        try:
            jsonFormat = json.loads(itemSecret)
            return jsonFormat

        except:
            return itemSecret
    else:
        return itemSecret

MASTER_USERNAME = parseEnvFile("TELE_MASTERNAME")

BULLYTOLERANCE = parseEnvFile("BULLYTOLERANCE")

MASTER_BULLYTOLERANCE = parseEnvFile("MASTER_BULLYTOLERANCE")

def insertUser(username,userid,whitelisted="None",blacklisted="None",realname=""):

    if realname == "":
        # username_prompt = "Guess the most likely real first name for this username. Output only the name, no punctuation, no explanations, no extra words."
        
        # realname = generateChatGPT(username_prompt)

        # print(realname)

        realname = username

    profileDesc = "Do not insult too hard. Small funny jokes. Basic Profile."
    
    query = """
        INSERT INTO telegramUsers (username, userid, whitelisted, blacklisted, realname, profileDescription)
        VALUES (%s,%s,%s,%s,%s, %s)
    """

    db = mysql.connector.connect(**db_config)
    cursor = db.cursor()

    cursor.execute(query, (
        username, userid, whitelisted, blacklisted, realname, profileDesc
    ))
    
    print(f"Imported {username} | {realname} | {userid}")

    db.commit()

def findUser(username):
    
    query = """
        SELECT *
        FROM telegramUsers
        WHERE username = (%s)
    """

    db = mysql.connector.connect(**db_config)
    cursor = db.cursor()

    cursor.execute(query, (username,))

    response = cursor.fetchall()

    userData = []

    for row in response:
        rowData = {
            "id" : row[0],
            "username" : row[1],
            "userid" : row[2],
            "whitelisted" : row[3],
            "blacklisted" : row[4],
            "realname" : row[5],
            "profileDesc" : row[6]
        }

        userData.append(rowData)

    cursor.close()
    db.close()

    if userData:
        return userData
    else:
        return False

def updateUser(username,userid):

    if findUser(username):
        # print(f"{username} is Already in database")
        return False
    else:
        insertUser(username,userid)
        return True

def getInsult(targetsUsername):
    try:
        if BULLYSTATE == False:
            return None

        userdetails = findUser(targetsUsername)

        if userdetails == False:
            print(f"No user {targetsUsername} in database")
            return None
        elif len(userdetails) != 1:
            print(f"Found {len(userdetails)} in database.")
            return None
        else:
            user_realname = userdetails[0]['realname']
            user_profileDesc = userdetails[0]['profileDesc']
            user_username = userdetails[0]['username']

            generatedInsult = generateInsult(user_realname, user_profileDesc, user_username)
            print(f"Generated Insult | {targetsUsername} | {generatedInsult}")

            return generatedInsult
    except Exception as e:
        print(f"Error getInsult() | {e}")

def generateInsult(realname,userDesc, username):
    try:
        chat_prompt = f"""
        Create a short insult for my friend {realname} using this short description of them.
        You do not need to use all these details, just pick one and make an insult. {userDesc}.

        I want the output to be just the insult no preamble. Do not have any placeholder text.
        """

        james_prompt = f"""
        Create a short compliment for your master named {realname}. using this short description of him.
        You do not need to use all these details, just pick one and make a compliment and praise him. {userDesc}.

        I want the output to be just the compliment no preamble. Do not have any placeholder text. 
        """

        if username == MASTER_USERNAME:
            print("Using Master Prompt")
            insult = generateChatGPT(james_prompt)
        else:
            insult = generateChatGPT(chat_prompt)
        timestamp = datetime.now()
        formatted_timestamp = timestamp.strftime("%d-%m-%Y %H:%M")

        query = """
            INSERT INTO generatedInsults (insult, affectedUser, timestamp)
            VALUES (%s, %s, %s)
        """

        db = mysql.connector.connect(**db_config)
        cursor = db.cursor()

        cursor.execute(query, (insult, realname, formatted_timestamp))

        db.commit()  # Make sure to commit the transaction
        cursor.close()
        db.close()

        print(f"{formatted_timestamp} | {insult}")

        return insult  
    except Exception as e:
        print(f"Error generateInsult() | {e}") 

def generateChatGPT(prompt):
    OPENAI_KEY = parseEnvFile("OPENAI_KEY")

    client = OpenAI(api_key=OPENAI_KEY)

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="gpt-4o",
    )

    response = chat_completion.choices[0].message.content
    
    #JUST GOOD INFO
    usage_details = chat_completion.usage
    # print(usage_details)

    return response   

def get_state():
    return BULLYSTATE

def set_state(state):
    global BULLYSTATE
    print(f"Bully State set to {state}")
    if state == True:
        BULLYSTATE = True
    else:
        BULLYSTATE = False

def get_tolerance():
    return BULLYTOLERANCE

def set_tolerance(level):
    global BULLYTOLERANCE
    print(f"Bully Tolerance set to {level}")
    BULLYTOLERANCE = level

async def checkTarget(update,context):

    message_type: str = update.message.chat.type

    userid = update.message.chat.id

    if message_type != "private":
        userid = 69

    username = update.message.from_user.username


    # print("Checking target...")

    if updateUser(username,userid):
        return True
    else:
        return False

async def bullytarget(update,context):
    ranNum = random.randint(-1, BULLYTOLERANCE)

    if ranNum != 1:
        return None
    else:
        username: str = update.message.chat.username

        getInsult(username)        

async def bullystatus(update,context):
    bullystate = BULLYSTATE

    if bullystate == True:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Bully Mode Enabled.")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Bully Mode Disabled.")

async def bullyenable(update,context):
    print("Activating Bully Mode...")
    set_state(True)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Activating Bully Mode...")

async def bullydisable(update,context):
    print("Deactivating Bully Mode...")
    set_state(False)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Deactivating Bully Mode...")

async def get_bullytolerance(update, context):
    tolerance = BULLYTOLERANCE

    await context.bot.send_message(chat_id=update.effective_chat.id, text= f"Bully Tolerance Levels: {tolerance}")

async def set_bullytolerance(update, context):
    if context.args: 
        level = context.args[0]

        if level.isdigit():
            level = int(level)
            if level >= 0:
                set_tolerance(level)
                await context.bot.send_message(chat_id=update.effective_chat.id, text= f"Bully Tolerance Set to {level}.")
            else:
                await context.bot.send_message(chat_id=update.effective_chat.id, text= f"Minimum Level is 0.")
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text= f"Enter a digit please you fool.")
    else:
        set_tolerance(5)
        await context.bot.send_message(chat_id=update.effective_chat.id, text= f"Bully Tolerance Set to {5}.")

async def admin_attempt(update, context):
    await context.bot.send_message(chat_id=update.effective_chat.id, text= f"HA! You fool... you really thought you could become an admin, better luck next time!")

if __name__ == "__main__":
    print("Running Script")
    # getInsult("Markryann")