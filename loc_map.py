# loc_map.py
# Location names for the LAEE mod. SINGLE source of truth:
#   config/misc/treasure_manager.ltx   (cache drop zones grouped by location)
# Nothing else is consulted here.

import re

TM = open('gamedata/config/misc/treasure_manager.ltx', encoding='utf-8').read()
HEADER = re.compile(r';\s*-{2,}\s*(.+?)\s*-{2,}\s*$')
SECTION = re.compile(r'\[([a-z_]+)_')

# 1) location header -> set of cache prefixes used under it (derived from config)
loc_prefixes = {}
cur = None
for ln in TM.split('\n'):
    hm = HEADER.match(ln)
    if hm:
        cur = hm.group(1).strip()
        loc_prefixes.setdefault(cur, set())
        continue
    sm = SECTION.match(ln.strip())
    if sm and cur:
        loc_prefixes[cur].add(sm.group(1).split('_')[0])

# 2) every canonical location name present in the config
LOCATIONS = dict(loc_prefixes)

def parse_treasure_prefixes():
    """{location_name: [tech prefixes]} — cache prefixes derived from the config,
       listed under their Russian location name. Single source of truth."""
    return {n: sorted(ps) for n, ps in loc_prefixes.items()}

# 3) anomaly-zone id prefix -> location. Some anomaly ids were NOT named after
#    the config's cache prefix (anomaly ids use 'army' while the config uses
#    'mil'). These renamed pairs are listed explicitly per location so the
#    correspondence is self-documenting — no separate implicit bridge. Every
#    other anomaly prefix already matches a cache prefix above, needs nothing.
ANOM_ALIASES = {
    'Кордон': ['escape'],
    'Армейские склады': ['army'],
    'Тёмная Долина': ['dol'],
    'Большие болота': ['swamp'],
    'Радар': ['radar'],
    'Припять': ['pry'],
    'Лес': ['fore'],
}

# 4) THE location map: Russian name -> all tech prefixes (cache + anomaly).
#    ANOM_ALIASES only ADDS anomaly-zone aliases to the config-derived lists; it
#    must not replace them, otherwise real stash prefixes (e.g. 'mil') get dropped.
LOC_PREFIXES = {**parse_treasure_prefixes()}
for loc, pfxs in ANOM_ALIASES.items():
    for p in pfxs:
        if p not in LOC_PREFIXES.setdefault(loc, []):
            LOC_PREFIXES[loc].append(p)

# relocate: the agr_ cache prefix sits under a "Свалка" comment header in
# treasure_manager.ltx, but it actually belongs to НИИ "Агропром". Pull it out of
# Свалка and register it under its true location.
if 'agr' in LOC_PREFIXES.get('Свалка', []):
    LOC_PREFIXES['Свалка'].remove('agr')
LOC_PREFIXES['НИИ \'Агропром\''] = ['agr']

def name_for(prefix):
    """anomaly-zone prefix -> canonical location name, or None if not in config.
       Resolves by checking whether the prefix is present in a location's list."""
    for loc, pfxs in LOC_PREFIXES.items():
        if prefix in pfxs:
            return loc
    return None

def resolve(name):
    """Normalize any location string to its canonical form (config names only)."""
    return name if name in LOCATIONS else name
