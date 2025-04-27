from urllib.parse import urlencode

from dlsite_async import PlayAPI


async def get_m3u8_urls(
    product_id: str,
    login_id: str | None = None,
    password: str | None = None,
    **kwargs,
) -> dict[str, str]:
    """Return .m3u8 playlist URLs for all videos in a work."""
    async with PlayAPI(**kwargs) as play:
        await play.login(login_id=login_id, password=password)
        token = await play.download_token(product_id)
        tree = await play.ziptree(token)
        urls = {}
        for filename, playfile in tree.items():
            if playfile.type != "video":
                continue
            qs = urlencode(
                {
                    "path": f"optimized/{playfile.optimized_name}",
                    "workno": token.workno,
                    "expiration": token.expiration,
                    "token": token.token,
                }
            )
            urls[filename] = f"https://play.dlsite.com/api/video/playlist.m3u8?{qs}"
        return urls
