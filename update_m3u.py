import pyppeteer
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

async def fetch_new_stream_url(channel_page_url):
    try:
        # Launch browser in headless mode
        browser = await pyppeteer.launch(headless=True)
        page = await browser.newPage()
        
        # Navigate to channel page URL
        await page.goto(channel_page_url)
        await page.waitForLoadState('networkidle2')

        # Enable request interception
        await page.setRequestInterception(True)
        page.on('request', lambda req: req.continue_())

        # Get playlist URL from requests
        playlist_url = None
        page.on('request', lambda req: globals().update(playlist_url=req.url) 
                if req.url.startswith("playlist.m3u8?wmsAuthSign=") else None)
        
        # Wait for 5 seconds to capture requests
        await asyncio.sleep(5)

        # Close browser
        await browser.close()

        return playlist_url

    except Exception as e:
        logging.error(f"Failed to fetch stream URL from {channel_page_url}: {e}")
        return None

async def update_m3u_file(m3u_path, channel_updates):
    try:
        with open(m3u_path, 'r') as file:
            lines = file.readlines()

        with open(m3u_path, 'w') as file:
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
                            channel_url = new_url  # Update the URL
                            print(f"Updating tvg-id={tvg_id} with new URL: {new_url}")
                    file.write(f"{channel_info}\n{channel_url}\n")
                    i += 1  # Skip the URL line as it's already updated
                else:
                    file.write(line)
                i += 1
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
        "09": "https://adult-tv-channels.com/private-tv-online/"
    }
    await update_m3u_file(m3u_path, channel_updates)

if __name__ == "__main__":
    asyncio.run(main())
