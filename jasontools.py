import os
from dotenv import load_dotenv
import json
from openai import OpenAI

load_dotenv()

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

def readCommandList(master=False):
    
    with open('commands.json') as file:
        data = json.load(file)
    
    # print(data)

    if master:
        commandlist = data['mastercommands']

    else:
        commandlist = data['commands']

    allcommands = ""
        
    for command in commandlist:
        allcommands += f"{command} | {commandlist[command]}" + "\n"

    return allcommands

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