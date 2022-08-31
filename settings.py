import json
import os
import langcodes
import re
import trakt

# by default everything will be set to none/false
CONFIG = {
    "Library Services": {"Plex": {"active": False}, "Trakt": {"active": False},},
    "Content Services": {
        "Plex": {"active": False},
        "Trakt": {"active": False},
        "Overseerr": {"active": False},
    },
    "Scraper Settings": {
        "Sources": {"rarbg": {"active": True}, "1337x": {"active": False}},
        "Languages": [
            "English",
            "Italian",
            "Spanish",
            "Chinese",
            "Mandarin",
            "Korean",
            "Russian",
            "German",
            "Portuguese",
            "Arabic",
            "French",
            "Hindi",
            "Japanese",
        ],
    },
    "Debrid Services": {
        "Real Debrid": {"active": False},
        "All Debrid": {"active": False},
        "Premiumize": {"active": False},
        "Debrid Link": {"active": False},
        "PUT.io": {"active": False},
    },
    "Debrid Settings": {"uncached_release": False},
    "UI Settings": {},
}


try:
    if os.path.exists("settings.json"):
        with open("settings.json", "r") as f:
            CONFIG = json.load(f)
except Exception as e:
    print(e)
    print("Potentially malformed settings file.")

VERSION = [
    "1.2",
    "Special character renaming have been updated. You now have more control over how characters are renamed for scraping.",
    ["Special character renaming",],
]

RUN_DIRECTLY = "true"
DEBUG = "false"
STOP = False
AVAILABLE_SCRAPERS = [
    "1337x",
    "solidtorrents",
    "bt4g",
    "limetorrents",
    "zooqle",
    "piratebay",
    "torrentdownload",
    "nyaa",
    "magnetdl",
    "uniondht",
    "torlock",
    "torrentdownloads",
    "kickasstorrents",
]
# todo make a setting to include/exclude languages
COMMON_LANGUAGES = CONFIG["Scraper Settings"]["Languages"]
try:
    COMMON_LANGUAGE_ALPHAS = [
        langcodes.find(x).to_alpha3().upper() for x in COMMON_LANGUAGES
    ]
except:
    print(
        "Invalid language has been added to settings file. Please check the spelling before running scraper."
    )
RESOLUTION_SCORE = {
    "None": 0,
    "CAM": 1,
    "SD": 2,
    "240": 1,
    "480": 2,
    "720": 3,
    "HD": 3,
    "1080": 4,
    "FHD": 4,
    "2160": 5,
    "4K": 5,
    "UHD": 5,
    "4320": 6,
    "8K": 6,
    "WEB": 2.5,
}
# will need to double back on this bc 0 can represent none found but for all we know it is unmarked but 1080p
MINIMUM_RESOLUTION = 0

RE_SHOW_TITLE = "([A-z0-9\-\.\_\s'\"\!\?\(\)].*?)"
RE_SEPARATORS = "(?:[\-\s\_\.])"
RE_SITE_INFO = "(?:\[.*?\]%s\-%s)" % (RE_SEPARATORS, RE_SEPARATORS,)
RE_SEASON = "(?:S(?:(?:EASONE?|ERIES)%s?)?((?:[0-9]){1,5}))(?:%s(COMPLETE))?%s?" % (
    RE_SEPARATORS,
    RE_SEPARATORS,
    RE_SEPARATORS,
)
RE_EPISODE = "(?:(?:E(?:PISODE%s?)?)((?:[0-9]\-?[0-9]?){1,5}))?" % (RE_SEPARATORS)
RE_TV_SHOW = re.compile(
    r"%s?%s%s?%s%s"
    % (RE_SITE_INFO, RE_SHOW_TITLE, RE_SEPARATORS, RE_SEASON, RE_EPISODE),
    flags=re.IGNORECASE,
)

RE_RESOLUTION = re.compile(
    r"(4320|4K|2160|FHD|UHD|HD|1080|720|480|SD|240|CAM|WEB)p?", flags=re.IGNORECASE
)
REPLACE_CHARS = [
    ("&", "and"),
    ("ü", "ue"),
    ("ä", "ae"),
    ("ö", "oe"),
    ("ß", "ss"),
    ("é", "e"),
    ("è", "e"),
    ("sh!t", "shit"),
    (".", ""),
    (":", ""),
    ("(", ""),
    (")", ""),
    ("`", ""),
    ("´", ""),
    (",", ""),
    ("!", ""),
    ("?", ""),
    (" - ", ""),
    ("'", ""),
    ("\u200b", ""),
    (" ", "."),
]
