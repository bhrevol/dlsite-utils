"""Utilities."""
import aiohttp
from dlsite_async import Work


async def get_work(product_id: str) -> Work:
    """Return work from API mirror."""
    url = f"https://dlsite-mirror.pmrowla.com/dlsite/work/{product_id}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            data = await resp.json()
            return Work.from_dict(data.get("result", {}))
