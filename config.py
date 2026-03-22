import os
from dotenv import load_dotenv

load_dotenv()

PROWLARR_URL = os.getenv("PROWLARR_URL", "http://localhost:9696")
PROWLARR_API_KEY = os.getenv("PROWLARR_API_KEY", "")

QBITTORRENT_URL = os.getenv("QBITTORRENT_URL", "http://localhost:8080")
QBITTORRENT_USERNAME = os.getenv("QBITTORRENT_USERNAME", "admin")
QBITTORRENT_PASSWORD = os.getenv("QBITTORRENT_PASSWORD", "adminadmin")

TORRENTS_DIR = os.getenv("TORRENTS_DIR", "/home/ashep/share/Media/Downloads/Torrents")
MOVIES_DIR = os.getenv("MOVIES_DIR", "/home/ashep/share/Media/Plex_Media/Movies")
TV_SHOWS_DIR = os.getenv("TV_SHOWS_DIR", "/home/ashep/share/Media/Plex_Media/TV_Shows")

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8888"))
