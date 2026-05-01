import os
import requests
import logging
import re
import shutil

logging.basicConfig(level=logging.INFO)


class DiscordListener:
    def __init__(self, token, base_dir='data'):
        self.token = token
        self.headers = {"authorization": self.token}
        self.base_dir = base_dir

        # Dictionary mapping Discord Channel IDs to Folder Names
        self.channels = {
            "879894919131570206": "breakouts",
            "1406770966117224458": "trendlines",
            "1428152678248091669": "fibonacci"
        }

    def fetch_new_images(self, limit=15):
        logging.info("Fetching raw images from Discord API across all channels...")

        for channel_id, category_name in self.channels.items():
            category_dir = os.path.join(self.base_dir, f"discord_{category_name}")

            # --- NEW FEATURE: CLEAR FOLDER BEFORE SYNCING ---
            # If the folder exists, delete all its contents to keep the scanner fresh
            if os.path.exists(category_dir):
                for filename in os.listdir(category_dir):
                    file_path = os.path.join(category_dir, filename)
                    try:
                        if os.path.isfile(file_path):
                            os.unlink(file_path)
                    except Exception as e:
                        logging.warning(f"Failed to delete {file_path}. Reason: {e}")
            else:
                os.makedirs(category_dir, exist_ok=True)
            # ------------------------------------------------

            url = f"https://discord.com/api/v9/channels/{channel_id}/messages?limit={limit}"

            try:
                response = requests.get(url, headers=self.headers)
                if response.status_code == 200:
                    messages = response.json()
                    self._process_messages(messages, category_dir)
                else:
                    logging.error(f"Failed to fetch channel {channel_id}: {response.status_code}")
            except Exception as e:
                logging.error(f"Error connecting to Discord API for {category_name}: {e}")

    def _process_messages(self, messages, save_dir):
        for msg in messages:
            content = msg.get('content', '')
            snowflake = msg.get('id', '0')

            # 1. Smart Ticker Extraction from text
            ticker = "SETUP"
            if content:
                # Looks for standalone uppercase words between 2 to 5 characters
                match = re.search(r'\b[A-Z]{2,5}\b', content)
                if match:
                    ticker = match.group(0)

            def process_image(img_url, orig_filename, unique_id):
                nonlocal ticker
                current_ticker = ticker

                # 2. Fallback: Extract from filename if no ticker was found in text
                if current_ticker == "SETUP":
                    match = re.match(r'^([A-Za-z]{2,5})', orig_filename)
                    if match:
                        candidate = match.group(1).upper()
                        # Ignore generic discord filenames
                        if candidate not in ["IMAGE", "IMG", "EMBED", "FILE", "UNKNOWN"]:
                            current_ticker = candidate

                filename = f"{current_ticker}_{unique_id}.png"
                filepath = os.path.join(save_dir, filename)

                # Download using the FULL URL
                if not os.path.exists(filepath):
                    self._download_image(img_url, filepath)

            # A. Process Direct Attachments
            for attachment in msg.get('attachments', []):
                if 'image' in attachment.get('content_type', 'image'):
                    process_image(
                        attachment.get('url'),
                        attachment.get('filename', 'image.png'),
                        attachment.get('id', snowflake)
                    )

            # B. Process TradingView Embeds
            for embed in msg.get('embeds', []):
                if 'image' in embed and 'url' in embed['image']:
                    process_image(
                        embed['image']['url'],
                        "embed.png",
                        msg.get('id', snowflake)
                    )

    def _download_image(self, url, path):
        try:
            resp = requests.get(url, stream=True, timeout=10)
            if resp.status_code == 200:
                with open(path, 'wb') as f:
                    for chunk in resp.iter_content(2048):
                        f.write(chunk)
        except Exception as e:
            logging.error(f"Failed to download image: {e}")