import math

import os
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
tree = discord.app_commands.CommandTree(client)

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(url, key)


async def blink_hue():
    red_xy = converter.hex_to_xy("ff0000")
    green_xy = converter.hex_to_xy("00ff00")
    blue_xy = converter.hex_to_xy("0000ff")
    white_xy = converter.hex_to_xy("ffffff")

    await put({"on": True, "bri": 254, "xy": red_xy})
    sleep(0.5)
    await put({"on": True, "bri": 254, "xy": green_xy})
    sleep(0.5)
    await put({"on": True, "bri": 254, "xy": blue_xy})
    sleep(0.5)
    await put({"on": True, "bri": 254, "xy": white_xy})


async def handle_ok(ctx: discord.Interaction):
    await ctx.response.send_message("😎")


async def handle_bad_request(ctx: discord.Interaction):
    await ctx.response.send_message(TROLL_IMAGE_URL)


async def handle_failed(ctx: discord.Interaction):
    await ctx.response.send_message("🤮")


async def handle_lines_exceeded(ctx: discord.Interaction, exceeded_count):
    await ctx.response.send_message("だいたい{}行多すぎるゾ".format(exceeded_count))


async def put(json):
    try:
        requests.put(HUE_API + '/groups/1/action',
         json=json)
    except requests.exceptions.RequestException as e:
        print("PUT error: ", e)
        tree.error(e)


@client.event
async def on_ready():
    print(f'We have logged in as {client.user}')
    # 何度もおっ叩くと規制される
    await tree.sync()

@tree.command(
    name="light_on",
    description="ライトON"
)
async def light_on(ctx: discord.Interaction):
    await put({"on": True})
    await handle_ok(ctx)

@tree.command(
    name="light_off",
    description="ライトOFF"
)
async def light_off(ctx: discord.Interaction):
    await put({"on": False})
    await handle_ok(ctx)

@tree.command(
    name="light_brightness",
    description="ライト輝度"
)
@discord.app_commands.describe(
    brightness="輝度"
)
async def light_brightness(ctx: discord.Interaction, brightness: str):
    brightness = math.floor((254 * int(brightness)) / 100)
    await put({"on": True, "bri": brightness})
    await handle_ok(ctx)

@tree.command(
    name="party",
    description="パリピ"
)
async def party(ctx: discord.Interaction):
    await ctx.response.defer()
    await blink_hue()
    await handle_ok(ctx)

@tree.command(
    name="light_hex",
    description="カラーコード"
)
@discord.app_commands.describe(
    hex="カラーコード"
)
async def light_hex(ctx: discord.Interaction, hex: str):
    if hex.startswith('#'):
        hex = hex[1:]
    if int(hex, 16) == 0:
        await handle_bad_request(ctx)
        return
    xy = converter.hex_to_xy(hex)
    await put({"on": True, "xy": xy})
    await handle_ok(ctx)

@tree.command(
    name="kds_pop",
    description="KDS掲示板情報一つ吹っ飛ばす"
)
async def kds_pop(ctx: discord.Interaction):
    target = supabase.table("bulletinboard").select('id').order(column="id",desc="dest").limit(1).execute()
    target_id = target.data[0]['id']
    supabase.table('bulletinboard').delete().match(query={'id': target_id}).execute()
    await handle_ok(ctx)

@tree.command(
    name="kds_set",
    description="KDS掲示板情報登録"
)
@discord.app_commands.describe(
    heading="なんかタイトルみたいなやつ",
    text="何書くの"
)
async def kds_set(ctx: discord.Interaction,heading:str, text: str):
    supabase.table("bulletinboard").insert(
    {"heading": heading, "text": text}).execute()
    await handle_ok(ctx)
    if text.count('\n') > MAXIMUM_LINES_COUNT:
        await handle_lines_exceeded(ctx, text.count('\n') - MAXIMUM_LINES_COUNT)

@tree.command(
    name="kds_speech",
    description="KDS喋らせるやつ"
)
@discord.app_commands.describe(
    text="NSFW"
)
async def kds_speech(ctx: discord.Interaction, text: str):
    if SPEECH_ENABLED != "true":
        await handle_bad_request(ctx)
        return
    supabase.table("speechRequest").insert(
        {"text": text}).execute()
    await handle_ok(ctx)

client.run(DISCORD_TOKEN)
