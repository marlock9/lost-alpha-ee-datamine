# loc_map.py
# Location names for the LAEE mod. SINGLE source of truth: the canonical Russian
# location name -> every tech/cache/anomaly prefix used under it. Previously parsed
# from config/misc/treasure_manager.ltx; now a complete static map, like cond_map.py.
# Nothing else is consulted here — add a new entry the first time a prefix is found.
# Unknown prefixes simply return None from name_for(); do not invent locations.

LOC_PREFIXES = {
    # ---- config cache drop zones (treasure_manager.ltx) ----
    'Кордон': ['esc', 'escape'],
    'Свалка': ['gar'],
    'Тёмная Долина': ['dol', 'dolina'],
    'Бар': ['bar', 'secret'],
    'Армейские склады': ['mil', 'army'],
    'Янтарь': ['yan'],
    'Радар': ['rad', 'radar'],
    'Мёртвый город': ['cit'],
    'Тёмная лощина': ['ds'],
    'Металлургический завод': ['rosf'],
    'Большие болота': ['swa', 'swamp'],
    'Окрестности припяти': ['out'],
    'Цементный завод': ['lost'],
    'Стройплощадка': ['forg'],
    'Припять': ['pri', 'pry'],
    'ЧАЭС': ['aes'],
    'Лес': ['forest', 'fore'],
    'Северные холмы': ['bcr'],
    'Старая дорога': ['old'],
    'НИИ \'Агропром\'': ['agr'],

    # ---- provenance notes ----
    # escape/army/dol/swamp/radar/pry/fore are anomaly-zone aliases added to the
    # config lists (they never replace real stash prefixes like mil/gar/swa).
    # 'agr' was read from under "Свалка" but belongs to НИИ "Агропром".
}

LOCATIONS = dict(LOC_PREFIXES)

def parse_treasure_prefixes():
    """{location_name: [tech prefixes]} — the full static location map.
       Single source of truth for locations and their prefixes."""
    return {n: list(ps) for n, ps in LOC_PREFIXES.items()}

def name_for(prefix):
    """anomaly-zone prefix -> canonical location name, or None if not in map.
       Resolves by checking whether the prefix is present in a location's list."""
    for loc, pfxs in LOC_PREFIXES.items():
        if prefix in pfxs:
            return loc
    return None

def resolve(name):
    """Normalize any location string to its canonical form (map names only)."""
    return name if name in LOCATIONS else name
