"""Transport channel identifiers for web and phone sessions."""

from enum import Enum


class Channel(str, Enum):
    WEB = "web"
    PHONE = "phone"
