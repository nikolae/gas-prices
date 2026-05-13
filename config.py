# Station IDs from GasBuddy — find them in the URL on gasbuddy.com/station/XXXXXX
# Example: https://www.gasbuddy.com/station/41800 -> id is "41800"
STATIONS = [
    {"id": "44946", "Costco": "Costco North"},
    {"id": "164236", "Murphy Express": "Murphy Express 144th"},
    {"id": "119297", "King Soopers": "King Soopers 136th"},
    {"id": "208619", "Costco Work": "Costco Work"},
]

# How long to cache prices before re-fetching (seconds)
CACHE_TTL_SECONDS = 900  # 15 minutes

# Flask port
PORT = 5000
