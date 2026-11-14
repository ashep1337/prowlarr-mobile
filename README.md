# Prowlarr Mobile

A lightweight, mobile-friendly web UI for searching torrents via [Prowlarr](https://prowlarr.com/) and managing downloads in [qBittorrent](https://www.qbittorrent.org/). Designed to be accessed from your phone's browser on a local network.

## Screenshots

<p>
<img width="680" height="363" alt="image" src="https://github.com/user-attachments/assets/0e8df1fa-f6c3-432e-becd-22bdec481e87" />

<img width="655" height="327" alt="image" src="https://github.com/user-attachments/assets/377c28e0-51f3-4e2a-8d92-21d4b96a3ad2" />
</p>

## Features

- **Search** - Query all your Prowlarr indexers at once, sorted by seeders
- **Download** - Send torrents to qBittorrent with one tap
- **Manage Downloads** - View progress, speed, ETA, and seeder/leecher counts in real-time (auto-refreshes every 3 seconds)
- **Torrent Controls** - Pause, resume, stop (kills seeding), and delete torrents with optional file cleanup
- **Move Files** - Move completed downloads to your Plex Movies or TV Shows library folder with one tap
- **Mobile-First** - Dark theme UI optimized for phone screens, supports iOS home screen app mode

## Prerequisites

- Debian 13 with systemd for the `.deb` installation below; APT installs Python and the required libraries
- A running [Prowlarr](https://prowlarr.com/) instance with indexers configured
- A running [qBittorrent](https://www.qbittorrent.org/) instance with Web UI enabled
- All services accessible on the same network

## Setup

### 1. Download the package

Download `prowlarr-mobile_0.1.0-2_all.deb` from the [0.1.0-2 release](https://github.com/ashep1337/prowlarr-mobile/releases/tag/v0.1.0-2), currently marked as a prerelease. You can also download it from a terminal:

```bash
sudo apt update
sudo apt install curl ca-certificates

curl -fL -o prowlarr-mobile_0.1.0-2_all.deb \
  https://github.com/ashep1337/prowlarr-mobile/releases/download/v0.1.0-2/prowlarr-mobile_0.1.0-2_all.deb
```

### 2. Install the package

From the directory containing the downloaded file:

```bash
sudo apt install ./prowlarr-mobile_0.1.0-2_all.deb
```

The package installs its dependencies, creates a dedicated `prowlarr-mobile` service account, and enables/starts the systemd service. No source checkout, virtual environment, or build tools are needed.

If you previously started the app manually, stop that instance before installation so port `8888` is available.

### 3. Configure your connections

```bash
sudoedit /etc/prowlarr-mobile/prowlarr-mobile.env
```

Set your service addresses and credentials in this installed configuration file:

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

You can find your Prowlarr API key in **Prowlarr > Settings > General > API Key**. Use the actual server addresses if Prowlarr or qBittorrent runs on another machine. The file-management paths are optional; configure them before using the move buttons.

### 4. Restart and open the app

```bash
sudo systemctl restart prowlarr-mobile
systemctl status prowlarr-mobile --no-pager
curl --fail http://127.0.0.1:8888/health
```

The health check should return `{"status":"ok"}`. It checks the app itself; it does not test the external services.

Open `http://your-server-ip:8888` on your phone. By default the package listens on `0.0.0.0:8888`; use the server's actual IP address in your browser. The app has no built-in login, so use it on a trusted local network or behind an authentication layer.

## Managing the Service

The service runs in the background and starts automatically at boot.

```bash
# Check status
systemctl status prowlarr-mobile --no-pager

# Restart after changing configuration
sudo systemctl restart prowlarr-mobile

# Stop or start the app
sudo systemctl stop prowlarr-mobile
sudo systemctl start prowlarr-mobile

# Follow application logs; press Ctrl+C to stop viewing
sudo journalctl -u prowlarr-mobile -f
```

## Updating

Download the new `.deb` from [Releases](https://github.com/ashep1337/prowlarr-mobile/releases), then install that local file with APT:

```bash
sudo apt install ./prowlarr-mobile_VERSION_all.deb
```

Replace `VERSION` with the downloaded filename's version. Installing the new package upgrades the existing installation and restarts the service. If APT asks about a modified configuration file, keep your current settings and merge any new options as needed. A changed package default may not replace a value already saved in your configuration.

Updates are installed from the downloaded packages; a GitHub release alone does not add an APT update repository.

## Uninstalling

```bash
# Remove the app while retaining its configuration
sudo apt remove prowlarr-mobile

# Also remove package-managed configuration
sudo apt purge prowlarr-mobile
```

The service account and any runtime state are retained. Download and media directories are not removed.

## Moving Files to Your Media Server

The Downloads tab includes **Move to Movies** and **Move to TV Shows** buttons. These move the contents of your configured download directory to the folder your media server (Plex, Jellyfin, Emby, etc.) is watching for new content. The current move action does not check qBittorrent completion status, so configure a directory containing only completed downloads.

Set the three path variables in `/etc/prowlarr-mobile/prowlarr-mobile.env` to match your setup, then restart the service:

- `TORRENTS_DIR` - Where qBittorrent saves completed downloads
- `MOVIES_DIR` - The folder your media server scans for movies
- `TV_SHOWS_DIR` - The folder your media server scans for TV shows

Once files are moved, your media server will automatically pick them up and add them to your library.

**Note:** These paths must be accessible on the machine running Prowlarr Mobile. For storage on another machine, mount it locally first. The `prowlarr-mobile` service account needs read/write access to the source and destination directories and access through their parent directories. If your media is on a network share (NAS), configure its mount permissions for that service account; `id prowlarr-mobile` shows its UID and GID.

## Tech Stack

- **Backend** - [FastAPI](https://fastapi.tiangolo.com/) + [Uvicorn](https://www.uvicorn.org/)
- **Frontend** - Vanilla HTML/CSS/JS (no build step, no frameworks)
- **API Clients** - [HTTPX](https://www.python-httpx.org/) for async Prowlarr/qBittorrent communication
