"""Minimal Discord bot — relays messages to Mai's local API.

Usage:
  1. Create a bot at https://discord.com/developers/applications
  2. Set DISCORD_TOKEN env var (or paste below)
  3. python -m integrations.discord_bot
"""

import json
import logging
import os
import sys
from urllib.error import URLError
from urllib.request import Request, urlopen

import discord
from discord.ext import commands

logging.basicConfig(level=logging.INFO, format="[Discord] %(levelname)s %(message)s")
logger = logging.getLogger("discord_bot")

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN", "")
MAI_API_URL = os.getenv("MAI_API_URL", "http://127.0.0.1:8000")
MAI_API_TOKEN = os.getenv("MAI_API_TOKEN", "")
PREFIX = os.getenv("DISCORD_PREFIX", "!")


def call_mai(message: str) -> str:
    payload = json.dumps({"message": message}).encode()
    headers = {"Content-Type": "application/json"}
    if MAI_API_TOKEN:
        headers["Authorization"] = f"Bearer {MAI_API_TOKEN}"
    req = Request(f"{MAI_API_URL}/api/chat", data=payload, headers=headers)
    try:
        with urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read())
        if "error" in data:
            return f"Something went wrong: {data['error']}"
        return data.get("response", "...")
    except URLError:
        return "Mai is sleeping right now. (Can't reach the API)"


bot = commands.Bot(command_prefix=PREFIX, intents=discord.Intents(
    messages=True, message_content=True, guilds=True
))


@bot.event
async def on_ready():
    logger.info("Connected as %s (%s guilds)", bot.user, len(bot.guilds))


@bot.command(name="mai")
async def mai_chat(ctx: commands.Context, *, message: str):
    if not message.strip():
        await ctx.send("What should I tell Mai?")
        return
    async with ctx.typing():
        response = await bot.loop.run_in_executor(None, call_mai, message)
    if len(response) > 2000:
        for i in range(0, len(response), 2000):
            await ctx.send(response[i:i + 2000])
    else:
        await ctx.send(response)


@mai_chat.error
async def mai_chat_error(ctx: commands.Context, error):
    await ctx.send("Say something after `!mai`. Example: `!mai hello`")


def main():
    if not DISCORD_TOKEN:
        logger.error("DISCORD_TOKEN not set. Create a bot at "
                      "https://discord.com/developers/applications")
        sys.exit(1)
    bot.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
