# Prowlarr Mobile

A lightweight, mobile-friendly web UI for searching torrents via [Prowlarr](https://prowlarr.com/) and managing downloads in [qBittorrent](https://www.qbittorrent.org/). Designed to be accessed from your phone's browser on a local network.

## Screenshots

<p align="center">
  <img src="screenshots/search.png" width="300" alt="Search Tab">
  &nbsp;&nbsp;
  <img src="screenshots/downloads.png" width="300" alt="Downloads Tab">
</p>

## Features

- **Search** - Query all your Prowlarr indexers at once, sorted by seeders
- **Download** - Send torrents to qBittorrent with one tap
- **Manage Downloads** - View progress, speed, ETA, and seeder/leecher counts in real-time (auto-refreshes every 3 seconds)
- **Torrent Controls** - Pause, resume, stop (kills seeding), and delete torrents with optional file cleanup
- **Move Files** - Move completed downloads to your Plex Movies or TV Shows library folder with one tap
- **Mobile-First** - Dark theme UI optimized for phone screens, supports iOS home screen app mode

## Prerequisites

- Python 3.10+
- A running [Prowlarr](https://prowlarr.com/) instance with indexers configured
- A running [qBittorrent](https://www.qbittorrent.org/) instance with Web UI enabled
- All services accessible on the same network

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/ashep1337/prowlarr-mobile.git
cd prowlarr-mobile
```

### 2. Create a virtual environment and install dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` with your values:

```env
# Prowlarr Configuration
PROWLARR_URL=http://your-server-ip:9696
PROWLARR_API_KEY=your-api-key-here

# qBittorrent Configuration
QBITTORRENT_URL=http://your-server-ip:8080
QBITTORRENT_USERNAME=admin
QBITTORRENT_PASSWORD=your-password

# App Configuration
HOST=0.0.0.0
PORT=8888

# File Management (for Move to Movies/TV Shows feature)
TORRENTS_DIR=/path/to/your/torrent/downloads
MOVIES_DIR=/path/to/your/plex/movies
TV_SHOWS_DIR=/path/to/your/plex/tv-shows
```

You can find your Prowlarr API key in **Prowlarr > Settings > General > API Key**.

### 4. Run the app

```bash
python main.py
```

Then open `http://your-server-ip:8888` on your phone.

## Running in the Background

To keep the app running after closing your terminal session:

```bash
cd /path/to/prowlarr-mobile
source venv/bin/activate
nohup python main.py > app.log 2>&1 &
```

To check if it's running:

```bash
ps aux | grep "python main.py"
```

To stop it:

```bash
pkill -f "python main.py"
```

## Tech Stack

- **Backend** - [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/)
- **Frontend** - Vanilla HTML/CSS/JS (no build step, no frameworks)
- **API Clients** - [HTTPX](https://www.python-httpx.org/) for async Prowlarr/qBittorrent communication
