import os
from openai import OpenAI
import time
import mysql.connector
from datetime import date
import random
import asyncio
import json
from dotenv import load_dotenv

load_dotenv()

start_time = time.time()

GPT_KEY = os.getenv("OPENAI_KEY")
HERMES_ID = os.getenv("TELE_HERMESID")

DB_CONFIG = json.loads(os.getenv("DB_CONFIG"))

THEMES = {
    "Galactic Rebellion": "Write a story about an unlikely hero rising in the midst of a galactic rebellion against an oppressive empire.",
    "Jedi vs. Sith": "Create a tale of an epic duel between a Jedi and a Sith, exploring themes of power, loss, and redemption.",
    "Smuggler's Run": "Write about a charismatic smuggler navigating dangerous deals in the underworld of a galaxy far, far away.",
    "Throne of Betrayal": "Craft a story about political intrigue, betrayal, and the fight for a powerful throne in a medieval fantasy world.",
    "Winter’s Shadow": "Tell the tale of a kingdom preparing for an impending invasion of an ancient, icy evil.",
    "House of Fire and Blood": "Write a saga about a noble family and their legendary dragons battling for survival and dominance.",
    "The Dark Portal": "Spin an epic story about a group of heroes venturing through a mysterious portal to face demonic adversaries.",
    "Clash of Factions": "Describe a brutal conflict between two factions, each fighting for their homeland and honor.",
    "The Forgotten Titan": "Tell the story of a long-lost Titan awakening to bring judgment upon Azeroth.",
    "The Lost Relic": "Write about an archaeologist's race against time to recover a relic with mysterious powers.",
    "Temple of Peril": "Create a high-stakes adventure through ancient temples filled with traps and secrets.",
    "Treasure of the Deep": "Write about an underwater expedition to uncover a lost civilization's treasure.",
    "Wrath of the Gods": "Tell a story about a mortal defying the gods and facing their wrath.",
    "The Labyrinth": "Describe a hero's perilous journey through a labyrinth guarded by a monstrous Minotaur.",
    "Titan's Revenge": "Spin a tale about the Titans rising from imprisonment to overthrow Mount Olympus.",
    "Dungeon Heist": "Write about a band of adventurers embarking on a daring heist in a dragon's treasure hoard.",
    "Cursed Artifact": "Describe the consequences of an adventuring party finding an artifact cursed by ancient magic.",
    "The Shadow Lich": "Tell the story of a legendary lich whose return threatens the fabric of reality.",
    "Vampire’s Pact": "Craft a gothic tale of a vampire who forms an unlikely alliance with a human.",
    "Time Traveler’s Dilemma": "Write about a time traveler who must decide whether to change a catastrophic event in history.",
    "Pirate’s Legacy": "Tell a story of a pirate searching for the fabled treasure of an infamous ancestor.",
    "Steampunk Revolution": "Describe a rebellion in a steampunk city where gears and steam power the fight for freedom.",
    "Cosmic Horror": "Create a chilling story of explorers discovering ancient, mind-bending horrors in the far reaches of space."
}

async def alertMaster(update, context, alertMessage):
    message_type: str = update.message.chat.type

    username: str = update.message.from_user.username

    if message_type != "private":
        message_type = update.message.chat.title                 

    alert = f"ALERT: {username} ({message_type}) | {alertMessage}"

    print(alert)
    await context.bot.send_message(chat_id=HERMES_ID,text=alert)

def select_theme():
    theme = random.choice(list(THEMES.keys()))
    return theme, THEMES[theme]

async def generate_story():
    print("Generating story...")
    client = OpenAI(api_key=GPT_KEY)

    theme_key, theme_prompt = select_theme()

    prompt = (
        f"Theme: {theme_key}\n"
        f"{theme_prompt}\n\n"
        "Write this story for a high-level audience. Use sophisticated language, complex storytelling techniques, "
        "and ensure the narrative is mature and thought-provoking."
    )

    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="gpt-4o",
    )

    story = chat_completion.choices[0].message.content
    usage_details = chat_completion.usage

    elapsed_time = time.time() - start_time

    store_story(story, theme_key, theme_prompt)
    return story

def get_db_connection():
    try:
        return mysql.connector.connect(**DB_CONFIG)

    except e as Exception:
        print(e)
        return e 

def store_story(story, theme_key, prompt):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        today = date.today()
        cursor.execute("INSERT INTO stories (date, story, themekey, prompt) VALUES (%s, %s, %s, %s)", (today, story, theme_key, prompt))
        conn.commit()
        story_id = cursor.lastrowid
        cursor.close()
        conn.close()
        return story_id
    except e as Exception:
        print(e)
        return e

async def tell_story(update, context):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="Thinking of a story...")

    try:
        # Generate the story asynchronously
        story = await generate_story()

        # Check if the story is generated successfully
        if story:
            print("Story generation finished.")
            print(story)  # This prints the story for debugging purposes

            # Split the story into paragraphs to preserve their integrity
            story_paragraphs = story.split('\n\n')

            # Initialize an empty string to hold the current chunk of text
            current_chunk = ''

            # Iterate over the paragraphs and add them to the current chunk
            for paragraph in story_paragraphs:
                # If adding this paragraph exceeds the chunk_size limit, send the current chunk and reset
                if len(current_chunk) + len(paragraph) + 2 > 4096:  # +2 for the newline between paragraphs
                    await context.bot.send_message(chat_id=update.effective_chat.id, text=current_chunk)
                    current_chunk = paragraph  # Start a new chunk with the current paragraph
                else:
                    if current_chunk:
                        current_chunk += '\n\n' + paragraph  # Add the paragraph to the current chunk with a newline
                    else:
                        current_chunk = paragraph  # Start the first chunk with the current paragraph

            # Send any remaining chunk (if there is one)
            if current_chunk:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=current_chunk)
        else:
            await context.bot.send_message(chat_id=update.effective_chat.id, text="My apologies, I could not think of a story.")
    except Exception as e:
        # Handle any errors that may occur during story generation or sending the message
        print(f"An error occurred while generating or sending the story: {e}")
        await context.bot.send_message(chat_id=update.effective_chat.id, text="There was an issue generating the story. Please try again later.")

    alert = f"Story told by Jason"
    await alertMaster(update, context, alert)

if __name__ == "__main__":
    print("Running Script")
    generate_story()
    # asyncio.run(generate_story())
