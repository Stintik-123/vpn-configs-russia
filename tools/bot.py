import os
import json
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

BOT_TOKEN = os.getenv("BOT_TOKEN")
GH_TOKEN = os.getenv("GH_TOKEN")
REPO = "Stintik-123/vpn-configs-russia"
ARTIFACT_NAME = "tcp-alive"

bot = Bot(BOT_TOKEN)
dp = Dispatcher()


async def get_latest_artifact():
    async with aiohttp.ClientSession(headers={"Authorization": f"Bearer {GH_TOKEN}"}) as s:
        url = f"https://api.github.com/repos/{REPO}/actions/artifacts?name={ARTIFACT_NAME}&per_page=1"
        async with s.get(url) as r:
            data = await r.json()
            artifacts = data.get("artifacts", [])
            if not artifacts:
                return None
            download_url = artifacts[0]["archive_download_url"]
            async with s.get(download_url) as dr:
                content = await dr.read()
                import zipfile, io
                with zipfile.ZipFile(io.BytesIO(content)) as z:
                    with z.open("tcp_alive.txt") as f:
                        lines = [l.strip().decode() for l in f if l.strip()]
                        return lines


@dp.message(Command("get"))
async def cmd_get(message: types.Message):
    configs = await get_latest_artifact()
    if not configs:
        await message.answer("Нет доступных конфигов")
        return
    batch = configs[:50]
    await message.answer("\n".join(batch))


@dp.message(Command("report"))
async def cmd_report(message: types.Message):
    if not message.document:
        await message.answer("Пришли JSON-файл с отчётом")
        return
    file = await bot.download(message.document)
    data = json.loads(file.read().decode())
    await message.answer(f"Принято: {data.get('passed', 0)}/{data.get('total', 0)}")


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
