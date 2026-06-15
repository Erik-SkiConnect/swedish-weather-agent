"""
Region definitions for the Swedish weather agent.

Each region maps to a representative coordinate used for the Open-Meteo
forecast. The postal_codes field uses the format "XX-YY" where XX and YY
are two-digit postal code prefixes. Together, the 10 regions cover all
prefixes from 10 to 99 with no gaps or overlaps.
"""

REGIONS = [
    {"name": "Stockholm-Malardalen", "postal_codes": "10-19", "lat": 59.33, "lon": 18.07},
    {"name": "Skane", "postal_codes": "20-29", "lat": 55.60, "lon": 13.00},
    {"name": "Smaland-SouthCoast", "postal_codes": "30-39", "lat": 56.85, "lon": 14.80},
    {"name": "Gothenburg-WestCoast", "postal_codes": "40-49", "lat": 57.70, "lon": 11.97},
    {"name": "VastraGotaland-East", "postal_codes": "50-59", "lat": 58.40, "lon": 15.60},
    {"name": "Varmland-Orebro", "postal_codes": "60-69", "lat": 59.30, "lon": 14.50},
    {"name": "Vastmanland-Dalarna", "postal_codes": "70-79", "lat": 60.00, "lon": 16.00},
    {"name": "Gavleborg-Vasternorrland", "postal_codes": "80-89", "lat": 62.39, "lon": 17.30},
    {"name": "Vasterbotten-Norrbotten", "postal_codes": "90-94", "lat": 64.75, "lon": 20.95},
    {"name": "NorthLapland", "postal_codes": "95-99", "lat": 67.85, "lon": 20.23},
]
