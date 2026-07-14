"""Domain Filtering Logic Module.

Responsible for matching job criteria profiles against targeting scopes.
"""

import config

def is_relevant(title, location):
    """Filters incoming postings based on target role classifications and locations.

    Args:
        title (str): Scraped posting job title.
        location (str): Physical work location string.

    Returns:
        bool: True if title contains target keywords AND location matches regional setup.
    """
    title_lower = title.lower()
    location_lower = location.lower()

    role_match = any(k in title_lower for k in config.ROLE_KEYWORDS)
    if not role_match:
        return False

    location_match = any(k in location_lower for k in config.LOCATIONS)
    return location_match