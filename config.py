# Station IDs from GasBuddy — find them in the URL on gasbuddy.com/station/XXXXXX
# Example: https://www.gasbuddy.com/station/41800 -> id is "41800"
STATIONS = [
    {"id": "44946", "nickname": "Costco North"},
    {"id": "164236", "nickname": "Murphy Express 144th"},
    {"id": "119297", "nickname": "King Soopers 136th"},
    {"id": "208619", "nickname": "Costco Work"},
]

# How long to cache prices before re-fetching (seconds)
CACHE_TTL_SECONDS = 900  # 15 minutes

# Flask port
PORT = 5000
