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

# Regional city hubs (lat, lon, country_code, timezone) for fast zero-dependency offline lookup
OFFLINE_GEO_HUBS: List[Tuple[float, float, str, str]] = [
    (52.52, 13.40, "DE", "Europe/Berlin"),
    (51.48, 11.97, "DE", "Europe/Berlin"),  # Halle / Leipzig
    (48.14, 11.58, "DE", "Europe/Berlin"),  # Munich
    (50.11, 8.68, "DE", "Europe/Berlin"),   # Frankfurt
    (53.55, 9.99, "DE", "Europe/Berlin"),   # Hamburg
    (41.30, 69.24, "UZ", "Asia/Tashkent"),
    (39.65, 66.96, "UZ", "Asia/Samarkand"),
    (55.75, 37.62, "RU", "Europe/Moscow"),
    (59.93, 30.34, "RU", "Europe/Moscow"),
    (56.84, 60.60, "RU", "Asia/Yekaterinburg"),
    (55.01, 82.93, "RU", "Asia/Novosibirsk"),
    (43.12, 131.89, "RU", "Asia/Vladivostok"),
    (43.22, 76.85, "KZ", "Asia/Almaty"),
    (51.17, 71.45, "KZ", "Asia/Almaty"),
    (40.71, -74.01, "US", "America/New_York"),
    (41.88, -87.63, "US", "America/Chicago"),
    (39.74, -104.99, "US", "America/Denver"),
    (34.05, -118.24, "US", "America/Los_Angeles"),
    (51.51, -0.13, "GB", "Europe/London"),
    (47.37, 8.54, "CH", "Europe/Zurich"),
    (41.01, 28.98, "TR", "Europe/Istanbul"),
    (36.89, 30.71, "TR", "Europe/Istanbul"),
    (31.23, 121.47, "CN", "Asia/Shanghai"),
    (39.90, 116.41, "CN", "Asia/Shanghai"),
    (35.68, 139.65, "JP", "Asia/Tokyo"),
    (50.45, 30.52, "UA", "Europe/Kyiv"),
    (53.90, 27.57, "BY", "Europe/Minsk"),
    (52.23, 21.01, "PL", "Europe/Warsaw"),
    (48.86, 2.35, "FR", "Europe/Paris"),
    (41.90, 12.50, "IT", "Europe/Rome"),
    (40.42, -3.70, "ES", "Europe/Madrid"),
    (52.37, 4.90, "NL", "Europe/Amsterdam"),
    (48.21, 16.37, "AT", "Europe/Vienna"),
    (50.08, 14.44, "CZ", "Europe/Prague"),
    (25.20, 55.27, "AE", "Asia/Dubai"),
    (41.72, 44.83, "GE", "Asia/Tbilisi"),
    (40.18, 44.51, "AM", "Asia/Yerevan"),
    (40.41, 49.87, "AZ", "Asia/Baku"),
    (42.87, 74.59, "KG", "Asia/Bishkek"),
    (38.56, 68.77, "TJ", "Asia/Dushanbe"),
    (43.65, -79.38, "CA", "America/Toronto"),
    (49.28, -123.12, "CA", "America/Vancouver"),
    (-33.87, 151.21, "AU", "Australia/Sydney"),
    (28.61, 77.21, "IN", "Asia/Kolkata"),
    (37.57, 126.98, "KR", "Asia/Seoul"),
    (1.35, 103.82, "SG", "Asia/Singapore"),
    (13.76, 100.50, "TH", "Asia/Bangkok"),
    (31.77, 35.21, "IL", "Asia/Jerusalem"),
]

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
    Uses timezonefinder if installed, and falls back to nearest regional hub resolution.
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

    # Nearest regional hub fallback
    best_code = "DE"
    best_tz = "Europe/Berlin"
    best_dist = float("inf")
    for h_lat, h_lon, c_code, h_tz in OFFLINE_GEO_HUBS:
        dist = _haversine_km(latitude, longitude, h_lat, h_lon)
        if dist < best_dist:
            best_dist = dist
            best_code = c_code
            best_tz = h_tz

    best_profile = COUNTRIES.get(best_code, COUNTRIES["DE"])
    resolved_tz = tz_name if (tz_name and is_valid_timezone(tz_name)) else best_tz
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
