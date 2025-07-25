import os

YOUTUBE_MAX_DESCRIPTION_LENGTH = 500
DEFAULT_YOUTUBE_SEARCH_LANGUAGE = os.getenv("ARCADE_YOUTUBE_SEARCH_LANGUAGE")
DEFAULT_YOUTUBE_SEARCH_COUNTRY = os.getenv("ARCADE_YOUTUBE_SEARCH_COUNTRY")
DEFAULT_GOOGLE_LANGUAGE = os.getenv("ARCADE_GOOGLE_LANGUAGE", "en")
DEFAULT_GOOGLE_COUNTRY = os.getenv("ARCADE_GOOGLE_COUNTRY")
