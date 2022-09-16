import math
import os
import re
from time import sleep

import discord
import requests
from dotenv import load_dotenv
from rgbxy import Converter
from supabase import Client, create_client

load_dotenv()

DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN")
HUE_API = os.environ.get("HUE_API")
WAKE_SYMBOL = os.environ.get("WAKE_SYMBOL")
MAXIMUM_LINES_COUNT = int(os.environ.get("MAXIMUM_LINES_COUNT"))
TROLL_IMAGE_URL = os.environ.get("TROLL_IMAGE_URL")
SPEECH_ENABLED = os.environ.get("SPEECH_ENABLED")

converter = Converter()

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)


async def blink_hue(message):
    red_xy = converter.hex_to_xy("ff0000")
    green_xy = converter.hex_to_xy("00ff00")
    blue_xy = converter.hex_to_xy("0000ff")
    white_xy = converter.hex_to_xy("ffffff")

    await put({"on": True, "bri": 254, "xy": red_xy}, message)
    sleep(0.5)
    await put({"on": True, "bri": 254, "xy": green_xy}, message)
    sleep(0.5)
    await put({"on": True, "bri": 254, "xy": blue_xy}, message)
    sleep(0.5)
    await put({"on": True, "bri": 254, "xy": white_xy}, message)


async def handle_ok(message):
    await message.add_reaction("✋")
    await message.add_reaction("😎")


async def handle_bad_request(message):
    await message.add_reaction("🤔")
    await message.reply(TROLL_IMAGE_URL)


async def handle_failed(message):
    await message.add_reaction("🤮")


async def handle_lines_exceeded(message, exceeded_count):
    await message.add_reaction("🈵")
    await message.reply("だいたい{}行多すぎるゾ".format(exceeded_count))


async def put(json, message):
    try:
        requests.put(HUE_API + '/groups/1/action',
                     json=json)
    except requests.exceptions.RequestException as e:
        print("PUT error: ", e)
        await handle_failed(message)


@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')


@client.event
async def on_message(message):
    if message.author == client.user:
        return
    if len(message.content) == 0:
        return
    if message.content[0] != WAKE_SYMBOL:
        return
    split_list = re.split('\s|\n', message.content[1:])
    if len(split_list) < 2:
        return
    if split_list[0] == 'light':
        if split_list[1] == "on":
            await put({"on": True}, message)
            await handle_ok(message)
        if split_list[1] == "off":
            await put({"on": False}, message)
            await handle_ok(message)
        if split_list[1] == "party":
            await blink_hue(message)
            await handle_ok(message)
        if split_list[1] == "brightness":
            if len(split_list) != 3:
                await handle_bad_request(message)
                return
            brightness = math.floor((254 * int(split_list[2])) / 100)
            await put({"on": True, "bri": brightness}, message)
            await handle_ok(message)
        if split_list[1] == "hex":
            if len(split_list) != 3:
                await handle_bad_request(message)
                return
            hex = str(split_list[2])
            if hex.startswith('#'):
                hex = hex[1:]
            if int(hex, 16) == 0:
                await handle_bad_request(message)
                return
            xy = converter.hex_to_xy(hex)
            await put({"on": True, "xy": xy}, message)
            await handle_ok(message)
            return
    if split_list[0] == 'kds':
        if len(split_list) < 3:
            await handle_bad_request(message)
            return
        if split_list[1] == "pushNote":
            heading = split_list[2].strip()
            text = message.content[1:].replace(split_list[0], '').replace(
                split_list[1], '').replace(heading, '').strip()
            supabase.table("bulletinboard").insert(
                {"heading": heading, "text": text}).execute()
            await handle_ok(message)
            if text.count('\n') > MAXIMUM_LINES_COUNT:
                await handle_lines_exceeded(message, text.count('\n') - MAXIMUM_LINES_COUNT)
            return
        if split_list[1] == "speech":
            if SPEECH_ENABLED != "true":
                await handle_bad_request(message)
                return
            text = message.content[1:].replace(
                split_list[0], '').replace(split_list[1], '').strip()
            supabase.table("speechRequest").insert(
                {"text": text}).execute()
            await handle_ok(message)

client.run(DISCORD_TOKEN)
