import asyncio
from playwright.async_api import async_playwright
import logging
import os
import re

logging.basicConfig(level=logging.INFO)

async def fetch_new_stream_url(channel_page_url):
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=[
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--single-process',
                    '--disable-gpu',
                    '--disable-blink-features=AutomationControlled',
                ]
            )
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)',
            )
            page = await context.new_page()

            playlist_url = None

            # Define the block patterns as regular expressions
            block_patterns = [
                r".*/start_scriptBus\.js$",  # Matches any URL ending with /start_scriptBus.js
                r".*/scriptBus\.js$",        # Matches any URL ending with /scriptBus.js
                r".*/adManager\.js$",        # Matches any URL ending with /adManager.js
                r".*disable-devtool.*",      # Matches any URL containing disable-devtool
                r".*disable-adblock.*",      # Matches any URL containing disable-adblock
            ]

            # Intercept requests
            async def handle_route(route, request):
                nonlocal playlist_url
                request_url = request.url

                # Log every request URL
                logging.info(f"Request URL: {request_url}")

                # Check if request URL matches any block patterns using regex (case-insensitive)
                if any(re.match(pattern, request_url, re.IGNORECASE) for pattern in block_patterns):
                    logging.info(f"Blocked script due to pattern: {request_url}")
                    await route.abort()
                    return

                # Check for playlist URL
                if ".m3u8?" in request_url:
                    playlist_url = request_url
                    logging.info(f"Captured playlist URL: {playlist_url}")

                # Continue with the request
                await route.continue_()

            # Set up route interception
            await page.route("**/*", handle_route)

            try:
                await page.goto(channel_page_url, wait_until='domcontentloaded', timeout=60000)
            except Exception as e:
                logging.error(f"Error loading page {channel_page_url}: {e}")
                await browser.close()
                return None

            # Wait for the playlist URL to be captured
            max_wait_time = 30  # seconds
            waited_time = 0
            while not playlist_url and waited_time < max_wait_time:
                await asyncio.sleep(1)
                waited_time += 1

            await browser.close()

            if playlist_url and ".m3u8?" in playlist_url:
                logging.info(f"Found valid playlist URL: {playlist_url}")
            else:
                logging.warning(f"No valid playlist URL found for {channel_page_url}")
            return playlist_url

    except Exception as e:
        logging.error(f"Failed to fetch stream URL: {e}")
        return None




async def update_m3u_file(m3u_path, channel_updates):
    if not os.path.exists(m3u_path):
        logging.error(f"File not found: {m3u_path}")
        return
    
    try:
        with open(m3u_path, 'r') as file:
            lines = file.readlines()
        
        updated_lines = []
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.startswith('#EXTINF:') and 'group-title="NEW-XXX"' in line:
                channel_info = line.strip()
                channel_url = lines[i + 1].strip()
                tvg_id = channel_info.split('tvg-id="')[1].split('"')[0]
                if tvg_id in channel_updates:
                    new_url = await fetch_new_stream_url(channel_updates[tvg_id])
                    if new_url:
                        channel_url = new_url
                        logging.info(f"Updated tvg-id={tvg_id} with new URL: {new_url}")
                    else:
                        logging.error(f"Failed to fetch stream URL for {tvg_id}")
                updated_lines.append(f"{channel_info}\n")
                updated_lines.append(f"{channel_url}\n")
                i += 2
            else:
                updated_lines.append(line)
                i += 1
        
        with open(m3u_path, 'w') as file:
            file.writelines(updated_lines)
        
        logging.info(f"Successfully updated M3U file: {m3u_path}")
    
    except Exception as e:
        logging.error(f"Failed to update M3U file: {e}")
    

async def main():
    m3u_path = 's18.m3u'
    channel_updates = {
        "01": "https://adult-tv-channels.com/redlight-hd-online/",
        "02": "https://adult-tv-channels.com/dorcel-tv-online/",
        "03": "https://adult-tv-channels.com/penthouse-passion-online/",
        "04": "https://adult-tv-channels.com/penthouse-passion-tv-online/",
        "05": "https://adult-tv-channels.com/vivid-tv-online/",
        "06": "https://adult-tv-channels.com/eroxxx-hd-tv-online/",
        "07": "https://adult-tv-channels.com/extasy-tv-online/",
        "08": "https://adult-tv-channels.com/pink-erotic-tv-online/",
        "09": "https://adult-tv-channels.com/private-tv-online/",
        "10": "https://fuckflix.click/vixen/",
        "11": "https://freeshot.live/live-tv/vixen/848",
        "12": "https://adult-tv-channels.click/vixen/",
        "13": "https://adult-tv-channels.com/ox-ax-tv-online/",
        "14": "https://adult-tv-channels.com/evil-angel-tv-online/"
    }
    await update_m3u_file(m3u_path, channel_updates)


if __name__ == "__main__":
    asyncio.run(main())
