import os
import glob
import asyncio
import argparse
from itertools import cycle

from pyrogram import Client
from better_proxy import Proxy

from bot.config import settings
from bot.utils import logger
from bot.core.starter import run_starter
from bot.core.registrator import register_sessions


start_text = """
88888888888 .d8888b.        .d8888b.  888                     888                    888888b.            888    
    888    d88P  Y88b      d88P  Y88b 888                     888                    888  "88b           888    
    888    888    888      Y88b.      888                     888                    888  .88P           888    
    888    888              "Y888b.   888888  8888b.  888d888 888888 .d88b.  888d888 8888888K.   .d88b.  888888 
    888    888  88888          "Y88b. 888        "88b 888P"   888   d8P  Y8b 888P"   888  "Y88b d88""88b 888    
    888    888    888            "888 888    .d888888 888     888   88888888 888     888    888 888  888 888    
    888    Y88b  d88P      Y88b  d88P Y88b.  888  888 888     Y88b. Y8b.     888     888   d88P Y88..88P Y88b.  
    888     "Y8888P88       "Y8888P"   "Y888 "Y888888 888      "Y888 "Y8888  888     8888888P"   "Y88P"   "Y888 
                                                                                                                
                                                                                                                
                                        || Created By Sudolite ||

Select an action:

    1. Create session
    2. Run starter
"""


def get_session_names() -> list[str]:
    session_names = glob.glob('sessions/*.session')
    session_names = [os.path.splitext(os.path.basename(file))[0] for file in session_names]

    return session_names


def get_proxies() -> list[Proxy]:
    if settings.USE_PROXY_FROM_FILE:
        with open(file='bot/config/proxies.txt', encoding='utf-8-sig') as file:
            proxies = [Proxy.from_str(proxy=row.strip()).as_url for row in file]
    else:
        proxies = []

    return proxies


async def get_tg_clients() -> list[Client]:
    session_names = get_session_names()

    if not session_names:
        raise FileNotFoundError("Not found session files")

    if not settings.API_ID or not settings.API_HASH:
        raise ValueError("API_ID and API_HASH not found in the .env file.")

    tg_clients = [Client(
        name=session_name,
        api_id=settings.API_ID,
        api_hash=settings.API_HASH,
        workdir='sessions/',
        plugins=dict(root='bot/plugins')
    ) for session_name in session_names]

    return tg_clients


async def process() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('-a', '--action', type=int, help='Action to perform')

    logger.info(f"Detected {len(get_session_names())} sessions | {len(get_proxies())} proxies")

    action = parser.parse_args().action

    if not action:
        print(start_text)

        while True:
            action = input("> ")

            if not action.isdigit():
                logger.warning("Action must be number")
            elif action not in ['1', '2']:
                logger.warning("Action must be 1 or 2")
            else:
                action = int(action)
                break

    if action == 1:
        await register_sessions()
    elif action == 2:
        tg_clients = await get_tg_clients()

        await run_tasks(tg_clients=tg_clients)


async def run_tasks(tg_clients: list[Client]):
    proxies = get_proxies()
    proxies_cycle = cycle(proxies) if proxies else None
    tasks = [asyncio.create_task(run_starter(tg_client=tg_client, proxy=next(proxies_cycle) if proxies_cycle else None))
             for tg_client in tg_clients]

    await asyncio.gather(*tasks)
