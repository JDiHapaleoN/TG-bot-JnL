"""Offline geolocation, country, currency, and timezone resolution."""

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo, available_timezones

try:
    from timezonefinder import TimezoneFinder

    _tf = TimezoneFinder(in_memory=True)
except Exception:
    _tf = None


@dataclass(frozen=True)
class CountryProfile:
    code: str
    name_ru: str
    name_en: str
    currency: str
    default_timezone: str
    flag: str
    lat: float
    lon: float


COUNTRIES: Dict[str, CountryProfile] = {
    "DE": CountryProfile("DE", "Германия", "Germany", "EUR", "Europe/Berlin", "🇩🇪", 52.52, 13.40),
    "UZ": CountryProfile("UZ", "Узбекистан", "Uzbekistan", "UZS", "Asia/Tashkent", "🇺🇿", 41.30, 69.24),
    "RU": CountryProfile("RU", "Россия", "Russia", "RUB", "Europe/Moscow", "🇷🇺", 55.75, 37.62),
    "US": CountryProfile("US", "США", "United States", "USD", "America/New_York", "🇺🇸", 40.71, -74.01),
    "GB": CountryProfile("GB", "Великобритания", "United Kingdom", "GBP", "Europe/London", "🇬🇧", 51.51, -0.13),
    "CH": CountryProfile("CH", "Швейцария", "Switzerland", "CHF", "Europe/Zurich", "🇨🇭", 47.37, 8.54),
    "TR": CountryProfile("TR", "Турция", "Turkey", "TRY", "Europe/Istanbul", "🇹🇷", 41.01, 28.98),
    "CN": CountryProfile("CN", "Китай", "China", "CNY", "Asia/Shanghai", "🇨🇳", 31.23, 121.47),
    "JP": CountryProfile("JP", "Япония", "Japan", "JPY", "Asia/Tokyo", "🇯🇵", 35.68, 139.65),
    "KZ": CountryProfile("KZ", "Казахстан", "Kazakhstan", "KZT", "Asia/Almaty", "🇰🇿", 43.22, 76.85),
    "UA": CountryProfile("UA", "Украина", "Ukraine", "UAH", "Europe/Kyiv", "🇺🇦", 50.45, 30.52),
    "BY": CountryProfile("BY", "Беларусь", "Belarus", "BYN", "Europe/Minsk", "🇧🇾", 53.90, 27.57),
    "PL": CountryProfile("PL", "Польша", "Poland", "PLN", "Europe/Warsaw", "🇵🇱", 52.23, 21.01),
    "FR": CountryProfile("FR", "Франция", "France", "EUR", "Europe/Paris", "🇫🇷", 48.86, 2.35),
    "IT": CountryProfile("IT", "Италия", "Italy", "EUR", "Europe/Rome", "🇮🇹", 41.90, 12.50),
    "ES": CountryProfile("ES", "Испания", "Spain", "EUR", "Europe/Madrid", "🇪🇸", 40.42, -3.70),
    "NL": CountryProfile("NL", "Нидерланды", "Netherlands", "EUR", "Europe/Amsterdam", "🇳🇱", 52.37, 4.90),
    "AT": CountryProfile("AT", "Австрия", "Austria", "EUR", "Europe/Vienna", "🇦🇹", 48.21, 16.37),
    "CZ": CountryProfile("CZ", "Чехия", "Czechia", "CZK", "Europe/Prague", "🇨🇿", 50.08, 14.44),
    "AE": CountryProfile("AE", "ОАЭ", "United Arab Emirates", "AED", "Asia/Dubai", "🇦🇪", 25.20, 55.27),
    "GE": CountryProfile("GE", "Грузия", "Georgia", "GEL", "Asia/Tbilisi", "🇬🇪", 41.72, 44.83),
    "AM": CountryProfile("AM", "Армения", "Armenia", "AMD", "Asia/Yerevan", "🇦🇲", 40.18, 44.51),
    "AZ": CountryProfile("AZ", "Азербайджан", "Azerbaijan", "AZN", "Asia/Baku", "🇦🇿", 40.41, 49.87),
    "KG": CountryProfile("KG", "Кыргызстан", "Kyrgyzstan", "KGS", "Asia/Bishkek", "🇰🇬", 42.87, 74.59),
    "TJ": CountryProfile("TJ", "Таджикистан", "Tajikistan", "TJS", "Asia/Dushanbe", "🇹🇯", 38.56, 68.77),
    "CA": CountryProfile("CA", "Канада", "Canada", "CAD", "America/Toronto", "🇨🇦", 43.65, -79.38),
    "AU": CountryProfile("AU", "Австралия", "Australia", "AUD", "Australia/Sydney", "🇦🇺", -33.87, 151.21),
    "IN": CountryProfile("IN", "Индия", "India", "INR", "Asia/Kolkata", "🇮🇳", 28.61, 77.21),
    "KR": CountryProfile("KR", "Южная Корея", "South Korea", "KRW", "Asia/Seoul", "🇰🇷", 37.57, 126.98),
    "SG": CountryProfile("SG", "Сингапур", "Singapore", "SGD", "Asia/Singapore", "🇸🇬", 1.35, 103.82),
    "TH": CountryProfile("TH", "Таиланд", "Thailand", "THB", "Asia/Bangkok", "🇹🇭", 13.76, 100.50),
    "IL": CountryProfile("IL", "Израиль", "Israel", "ILS", "Asia/Jerusalem", "🇮🇱", 31.77, 35.21),
}

# Mapping of IANA timezone -> Country Code for accurate offline lookup
TIMEZONE_TO_COUNTRY: Dict[str, str] = {
    "Europe/Berlin": "DE",
    "Europe/Busingen": "DE",
    "Asia/Tashkent": "UZ",
    "Asia/Samarkand": "UZ",
    "Europe/Moscow": "RU",
    "Europe/Kaliningrad": "RU",
    "Europe/Samara": "RU",
    "Asia/Yekaterinburg": "RU",
    "Asia/Novosibirsk": "RU",
    "Asia/Krasnoyarsk": "RU",
    "Asia/Irkutsk": "RU",
    "Asia/Vladivostok": "RU",
    "America/New_York": "US",
    "America/Chicago": "US",
    "America/Denver": "US",
    "America/Los_Angeles": "US",
    "Europe/London": "GB",
    "Europe/Zurich": "CH",
    "Europe/Istanbul": "TR",
    "Asia/Shanghai": "CN",
    "Asia/Urumqi": "CN",
    "Asia/Tokyo": "JP",
    "Asia/Almaty": "KZ",
    "Asia/Qyzylorda": "KZ",
    "Asia/Aqtobe": "KZ",
    "Asia/Aqtau": "KZ",
    "Asia/Atyrau": "KZ",
    "Asia/Oral": "KZ",
    "Europe/Kyiv": "UA",
    "Europe/Kiev": "UA",
    "Europe/Minsk": "BY",
    "Europe/Warsaw": "PL",
    "Europe/Paris": "FR",
    "Europe/Rome": "IT",
    "Europe/Madrid": "ES",
    "Europe/Amsterdam": "NL",
    "Europe/Vienna": "AT",
    "Europe/Prague": "CZ",
    "Asia/Dubai": "AE",
    "Asia/Tbilisi": "GE",
    "Asia/Yerevan": "AM",
    "Asia/Baku": "AZ",
    "Asia/Bishkek": "KG",
    "Asia/Dushanbe": "TJ",
    "America/Toronto": "CA",
    "America/Vancouver": "CA",
    "Australia/Sydney": "AU",
    "Australia/Melbourne": "AU",
    "Asia/Kolkata": "IN",
    "Asia/Seoul": "KR",
    "Asia/Singapore": "SG",
    "Asia/Bangkok": "TH",
    "Asia/Jerusalem": "IL",
}

POPULAR_TIMEZONES: List[str] = [
    "Europe/Berlin",
    "Europe/London",
    "Europe/Moscow",
    "Europe/Istanbul",
    "Europe/Zurich",
    "Europe/Kyiv",
    "Europe/Minsk",
    "Asia/Dubai",
    "Asia/Tashkent",
    "Asia/Almaty",
    "Asia/Shanghai",
    "Asia/Tokyo",
    "America/New_York",
    "America/Los_Angeles",
    "UTC",
]


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    )
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def resolve_location_offline(latitude: float, longitude: float) -> Tuple[CountryProfile, str]:
    """
    Determine CountryProfile and IANA timezone from GPS coordinates completely offline.
    Uses timezonefinder if installed, and falls back to nearest-country hub resolution.
    """
    tz_name: Optional[str] = None
    if _tf is not None:
        try:
            tz_name = _tf.timezone_at(lng=longitude, lat=latitude)
        except Exception:
            tz_name = None

    if tz_name and tz_name in TIMEZONE_TO_COUNTRY:
        c_code = TIMEZONE_TO_COUNTRY[tz_name]
        profile = COUNTRIES[c_code]
        return profile, tz_name

    # Nearest country hub fallback
    best_profile = COUNTRIES["DE"]
    best_dist = float("inf")
    for profile in COUNTRIES.values():
        dist = _haversine_km(latitude, longitude, profile.lat, profile.lon)
        if dist < best_dist:
            best_dist = dist
            best_profile = profile

    resolved_tz = tz_name if (tz_name and is_valid_timezone(tz_name)) else best_profile.default_timezone
    return best_profile, resolved_tz


def get_country_profile(country_code: str) -> CountryProfile:
    code = (country_code or "DE").upper().strip()
    return COUNTRIES.get(code, COUNTRIES["DE"])


def get_country_name(country_code: str, lang: str = "ru") -> str:
    code = (country_code or "DE").upper().strip()
    if code in COUNTRIES:
        c = COUNTRIES[code]
        return f"{c.flag} {c.name_ru if lang == 'ru' else c.name_en}"
    return code


def is_valid_timezone(tz_name: str) -> bool:
    if not tz_name:
        return False
    try:
        ZoneInfo(tz_name.strip())
        return True
    except Exception:
        return tz_name.strip() in available_timezones()


def format_timezone_with_offset(tz_name: str) -> str:
    try:
        tz = ZoneInfo(tz_name)
        now = datetime.now(timezone.utc).astimezone(tz)
        offset = now.strftime("%z")
        if len(offset) == 5:
            offset_fmt = f"UTC{offset[:3]}:{offset[3:]}"
        else:
            offset_fmt = "UTC"
        return f"{tz_name} ({offset_fmt})"
    except Exception:
        return tz_name

