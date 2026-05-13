# Gas Prices Dashboard

A local web dashboard that pulls gas prices from GasBuddy for specific stations and displays them with historical price graphs.

---

## Table of Contents

1. [Running Locally on Mac](#1-running-locally-on-mac)
2. [Finding Station IDs](#2-finding-station-ids)
3. [Configuring Stations Locally](#3-configuring-stations-locally)
4. [Building the Docker Image](#4-building-the-docker-image)
5. [Transferring the Image to Your Server](#5-transferring-the-image-to-your-server)
6. [Deploying in Portainer](#6-deploying-in-portainer)
7. [Usage](#7-usage)
8. [Resetting](#8-resetting)
9. [Environment Variable Reference](#9-environment-variable-reference)

---

## 1. Running Locally on Mac

### Install Python 3.13

```bash
# Install Homebrew if you don't have it
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.13
brew install python@3.13
```

### Set Up the Project

```bash
# Clone the repo and enter the directory
git clone <your-repo-url>
cd gas-prices

# Create a virtual environment using Python 3.13
python3.13 -m venv .venv

# Activate the virtual environment
source .venv/bin/activate
# Your prompt will now show (.venv)

# Install dependencies
pip install -r requirements.txt
```

### Run the App

```bash
python app.py
```

Open your browser to `http://localhost:5050`

### Stopping the App

Press `Ctrl + C` in the terminal.

### Deactivating the Virtual Environment

```bash
deactivate
```

### Returning Later

Every time you open a new terminal session you need to reactivate the virtual environment before running:

```bash
cd gas-prices
source .venv/bin/activate
python app.py
```

---

## 2. Finding Station IDs

1. Go to [gasbuddy.com](https://www.gasbuddy.com) and search for a gas station near you
2. Click on the station to open its detail page
3. Look at the URL — it will look like: `https://www.gasbuddy.com/station/44946`
4. The number at the end (`44946`) is the station ID

---

## 3. Configuring Stations Locally

Open `config.py` and edit the `STATIONS` list:

```python
STATIONS = [
    {"id": "44946",  "nickname": "Costco North"},
    {"id": "164236", "nickname": "Murphy Express 144th"},
]
```

You can also change the cache duration and port here, or via environment variables (see [Section 7](#7-environment-variable-reference)).

---

## 4. Building the Docker Image

Install [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/) and make sure it is running (whale icon in menu bar).

### If your server is x86_64 / AMD64 (most home servers, NAS devices, Intel machines)

```bash
docker build --platform linux/amd64 -t gas-prices:latest .
```

### If your server is ARM64 (Raspberry Pi 4+, Apple Silicon server)

```bash
docker build --platform linux/arm64 -t gas-prices:latest .
```

### Verify the image was built

```bash
docker images | grep gas-prices
```

---

## 5. Transferring the Image to Your Server

### Step 1 — Save the image to a file on your Mac

```bash
docker save gas-prices:latest | gzip > gas-prices.tar.gz
```

### Step 2 — Copy it to your server

```bash
scp gas-prices.tar.gz user@192.168.1.x:/tmp/
```

Replace `user` and `192.168.1.x` with your server's username and IP address.

### Step 3 — Load it into Docker on the server

```bash
ssh user@192.168.1.x "docker load < /tmp/gas-prices.tar.gz && rm /tmp/gas-prices.tar.gz"
```

### Step 4 — Verify it loaded

```bash
ssh user@192.168.1.x "docker images | grep gas-prices"
```

### Updating the Image Later

Repeat Steps 1–4 whenever you rebuild. Portainer will use the new image the next time you redeploy the stack.

---

## 6. Deploying in Portainer

### Create the Stack

1. In Portainer, go to **Stacks → Add Stack**
2. Give it a name (e.g. `gas-prices`)
3. Select **Web editor** and paste the contents of `docker-compose.portainer.yml`

### Set Environment Variables

Scroll down to the **Environment variables** section and add:

| Variable | Example Value |
|---|---|
| `STATIONS` | `[{"id":"44946","nickname":"Costco North"},{"id":"164236","nickname":"Murphy Express 144th"}]` |
| `PORT` | `5050` |
| `CACHE_TTL_SECONDS` | `900` |

The `STATIONS` value must be a single-line JSON array. Copy and paste this as a starting point and edit the IDs and nicknames:

```
[{"id":"44946","nickname":"Costco North"},{"id":"164236","nickname":"Murphy Express 144th"},{"id":"119297","nickname":"King Soopers 136th"},{"id":"208619","nickname":"Costco Work"}]
```

### Deploy

Click **Deploy the stack**. The app will be available at `http://192.168.1.x:5050`.

### Editing Variables After Deployment

1. In Portainer go to **Stacks → gas-prices**
2. Click **Editor** to edit the compose file, or scroll down to update environment variables
3. Click **Update the stack** to apply changes — the container will restart automatically

### Persistent Data

Price history is stored in a Docker named volume (`gas-prices-data`). It persists across container restarts and stack redeployments. The SQLite database file lives at `/data/gas_prices.db` inside the container.

---

## 7. Usage

### Viewing Prices

Open the dashboard in your browser. Each station shows its current prices by fuel grade. Prices are fetched from GasBuddy and cached — the card header shows how long ago they were last updated. The page auto-refreshes every 5 minutes.

### Price History Graph

Each card has a line graph showing price history per fuel grade. Use the **1d / 7d / 30d** buttons to change the time range. History is recorded every time prices are fetched (every 15 minutes by default), so the graph fills in over time.

### Adding a Station

1. Click **+ Add Station** in the top right
2. Enter the GasBuddy station ID (see [Section 2](#2-finding-station-ids) for how to find it)
3. Enter a nickname (optional — defaults to "Station {id}")
4. Click **Add** — the app validates the ID by fetching prices before saving

Added stations are stored in the database and persist across restarts.

### Removing a Station

Click the **✕** button in the top right corner of any card. The station is removed immediately and will not reappear on restart. Price history for that station is kept in the database in case you re-add it later.

### Reordering Cards

Drag the **⠿** handle on the left side of any card header to reorder. The order is saved in your browser's local storage and persists across page refreshes.

### Force Refreshing Prices

Click **Force refresh** in the header to clear the cache and immediately re-fetch prices from GasBuddy for all stations.

---

## 8. Resetting

Deleting the stack in Portainer removes the container but **leaves the database volume intact**. To fully reset:

### Full reset (wipes all stations and price history)

1. In Portainer: **Stacks → gas-prices → Delete**
2. In Portainer: **Volumes → gas-prices-data → Remove**

On next deploy the stations will be re-seeded from the `STATIONS` environment variable.

### Reset stations only (keeps price history)

SSH into the server and run:

```bash
sqlite3 /var/lib/docker/volumes/gas-prices-data/_data/gas_prices.db \
  "DELETE FROM stations;"
```

On next restart the stations table is empty so it re-seeds from the `STATIONS` env var.

### Reset price history only (keeps stations)

```bash
sqlite3 /var/lib/docker/volumes/gas-prices-data/_data/gas_prices.db \
  "DELETE FROM price_history;"
```

---

## 9. Environment Variable Reference

| Variable | Default | Description |
|---|---|---|
| `PORT` | `5050` | Port the web server listens on |
| `CACHE_TTL_SECONDS` | `900` | How long to cache prices before re-fetching (seconds). 900 = 15 minutes |
| `DB_PATH` | `/data/gas_prices.db` | Path to the SQLite database file |
| `STATIONS` | *(hardcoded fallback in config.py)* | JSON array of stations to track |

### STATIONS format

```json
[
  {"id": "44946",  "nickname": "Costco North"},
  {"id": "164236", "nickname": "Murphy Express 144th"}
]
```

When set as an environment variable it must be on a single line with no extra spaces.
