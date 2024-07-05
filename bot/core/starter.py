import asyncio
from time import time
from datetime import datetime

import aiohttp
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from pyrogram import Client
from pyrogram.errors import Unauthorized, UserDeactivated, AuthKeyUnregistered
from pyrogram.raw.functions.messages import RequestWebView

from bot.config import settings
from bot.utils import logger
from bot.exceptions import InvalidSession


class Starter:
    def __init__(self, tg_client: Client):
        self.session_name = tg_client.name
        self.tg_client = tg_client

    async def start_bot(self, bot: str, url_bot: str, ref: str, proxy: str | None) -> bool:
        if proxy:
            proxy = Proxy.from_str(proxy)
            proxy_dict = dict(
                scheme=proxy.protocol,
                hostname=proxy.host,
                port=proxy.port,
                username=proxy.login,
                password=proxy.password
            )
        else:
            proxy_dict = None

        self.tg_client.proxy = proxy_dict

        try:
            if not self.tg_client.is_connected:
                try:
                    await self.tg_client.connect()
                    msrf = f"/start {ref}"
                    als = False
                    async for message in self.tg_client.get_chat_history(bot):
                        if message.text == msrf:
                            als = True
                            logger.info(f"{self.session_name} |The {bot} Already Started")
                            break

                    if not als:
                        await self.tg_client.send_message(bot, msrf, disable_notification=True)
                        logger.success(f"{self.session_name} | Started {bot} Successfully.")

                except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                    raise InvalidSession(self.session_name)


            web_view = await self.tg_client.invoke(RequestWebView(
                peer=await self.tg_client.resolve_peer(bot),
                bot=await self.tg_client.resolve_peer(bot),
                platform='android',
                from_bot_menu=False,
                url=url_bot
            ))

            if self.tg_client.is_connected:
                await self.tg_client.disconnect()

            return True

        except InvalidSession as error:
            raise error
            return False

        except Exception as error:
            logger.error(f"{self.session_name} | Bot: {bot} | Unknown error during Authorization: {error}")
            await asyncio.sleep(delay=3)
            return False

    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy) -> None:
        try:
            response = await http_client.get(url='https://httpbin.org/ip', timeout=aiohttp.ClientTimeout(5))
            ip = (await response.json()).get('origin')
            logger.info(f"{self.session_name} | Proxy IP: {ip}")
        except Exception as error:
            logger.error(f"{self.session_name} | Proxy: {proxy} | Error: {error}")

    async def run(self, proxy: str | None) -> None:
        proxy_conn = ProxyConnector().from_url(proxy) if proxy else None

        async with aiohttp.ClientSession(connector=proxy_conn) as http_client:
            if proxy:
                await self.check_proxy(http_client=http_client, proxy=proxy)

            while True:
                try:
                    for attr in dir(settings):
                        if attr.startswith('START_') and not attr.endswith(('_STR', '_URL')):
                            start_value = getattr(settings, attr)
                            ref_value = getattr(settings, attr + "_STR", None)
                            url_value = getattr(settings, attr + "_URL", None)
                            bot_username = attr.split('START_')[1]

                            if (start_value is True 
                                and ref_value != ""
                                and url_value != ""):
                                status = await self.start_bot(bot=bot_username, url_bot=url_value, ref=ref_value, proxy=proxy)
                                if not status:
                                    continue

                            logger.info(f"{self.session_name} | Wait for 3 Sec to start next bot")
                            await asyncio.sleep(delay=3)
                            

                except InvalidSession as error:
                    raise error

                except Exception as error:
                    logger.error(f"{self.session_name} | Unknown error: {error}")
                    await asyncio.sleep(delay=3)

                else:
                    await http_client.close()
                    logger.info(f"{self.session_name} | Session Closed.")
                    return


async def run_starter(tg_client: Client, proxy: str | None):
    try:
        await Starter(tg_client=tg_client).run(proxy=proxy)
    except InvalidSession:
        logger.error(f"{tg_client.name} | Invalid Session")
