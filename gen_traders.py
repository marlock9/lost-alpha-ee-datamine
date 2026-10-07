"""Generate TRADERS.md for the S.T.A.L.K.E.R. LAEE mod from gamedata LTX files."""

import os, re

ROOT = 'LAEE'
GAMEDATA = 'gamedata'
BASE = os.path.dirname(os.path.abspath(__file__))
TRADE_DIR = os.path.join(BASE, GAMEDATA, 'config', 'misc', 'trade')

# All item categories known across the trade system, split by side.
ALL_BUY_CATEGORIES = []
ALL_SELL_CATEGORIES = []

# Discount condition name -> Russian meaning (authoritative; corrected by user).
CONDITIONS = {
    'old_farm_bandit_hit': 'Игрок атаковал базу бандитов первым',
    'actor_in_dolg': 'Игрок стоит в "Долге"',
    'actor_in_freedom': 'Игрок состоит в "Свободе"',
    'out_lukash_task_complete': 'Выполнены квесты Лукаша',
    'forg_fuel_task_complete': 'Выполнено задание на подрыв бочек в Тёмной Лощине',
    'forg_mill_gauss_box_done': 'Выполнено задание на доставку Гаусс-бокса',
    'bar_last_job_done': 'Выполнено последнее задание для "Долга"',
    'out_barman_x7_switcher_talked': 'Бороде сообщено об отключении X-7',
}

# ---- Trader nice names + locations (static map of LAEE traders; no discovery) ----
# Each entry: (npc_class, name_key, russian_name, location). Names come from stable_bio_name.xml.
TRADERS = {
    'trade_bandit':        ('old_farm_bandit_trader',  'bandit_huckster_name',       'Торгаш',         'Старая дорога'),
    'trade_bandit_story':  ('old_svoboda_kostug',      'kostug_name',               'Костюг',         'Старая дорога'),
    'trade_barman':        ('bar_barman',              'bar_barmen_name',           'Бармен',         'Бар'),
    'trade_beard':         ('out_barman',              'out_beard_name',            'Борода',         'Окрестности припяти'),
    'trade_crash':         ('cit_trader',              'cit_trader_name',           'Филин',          'Мёртвый город'),
    'trade_deedee':        ('lost_ecolog_scientist',   'lost_deedee_name',          'Профессор Д.Д.', 'Цементный завод'),
    'trade_dolg':          ('bar_petrenko',            'bar_petrenko_name',         'Полковник Петренко', 'Бар'),
    'trade_forg_stalker':  ('forg_stalker_trader',     'forg_stalker_trader_name',  'Алекс',          'Стройплощадка'),
    'trade_freedom':       ('out_Svoboda_trader',      'mil_Svoboda_trader_name',   'Скряга',         'Окрестности припяти'),
    'trade_killer':        ('forg_killer_barman',      'forg_killer_barman_name',   'Паук',           'Стройплощадка'),
    'trade_sakharov':      ('yan_general_ecolog',      'yan_saharov_name',          'Профессор Сахаров', 'Янтарь'),
    'trade_secret':        ('bar_arena_manager',       'pri_trader_name',           'Увалень',        'Припять'),
    'trade_sidor':         ('escape_trader',           'escape_trader_name',        'Сидорович',      'Кордон'),
    'trade_suplier':       ('military_supplier',       'mil_ugrymiy_name',          'Угрюмый',        'Армейские склады'),
}


def trader_info(tid):
    return TRADERS.get(tid)


def parse_condition(s):
    """Yield (operator, name) pairs from a condition string like '+a -b =c'."""
    for m in re.finditer(r'([+-=!]?)([a-zA-Z_][a-zA-Z0-9_]*)', s or ''):
        op, name = m.group(1), m.group(2)
        yield (op if op else '+', name)


def slugify(text):
    """GitHub-style anchor slug: lowercase, keep Unicode letters/digits, spaces -> hyphens."""
    s = re.sub(r'[^\w\s]', '', text.lower())   # Unicode-aware: keeps Cyrillic letters + underscores; strips other punct with no gap
    s = re.sub(r'_', '_', s)                # keep underscores (GitHub preserves them)
    s = re.sub(r'\s+', '-', s)             # collapse whitespace -> single hyphens
    return s.strip('-')


def build_toc(items):
    """items: list of (anchor, link_text). Return 'Оглавление' section as markdown."""
    lines = ['# Оглавление', '']
    for anchor, text in items:
        lines.append(f'- [{text}](#{anchor})')
    return '\n'.join(lines) + '\n'


def render_conditions(disc):
    """Return [(op, name, meaning)] for every condition used in a trader's discounts."""
    out = []
    seen = set()
    for d in disc:
        if not d.get('condition'):
            continue
        for op, name in parse_condition(d['condition']):
            if name not in CONDITIONS or (op, name) in seen:
                continue
            seen.add((op, name))
            meaning = CONDITIONS[name]
            if op in ('-', '!'):
                meaning = negate(meaning)
            out.append((op, name, meaning))
    return out


def negate(meaning):
    """Insert НЕ before the verb of a Russian condition meaning."""
    if meaning.startswith('Игрок '):
        return f'Игрок НЕ {meaning[6:]}'
    if meaning.startswith('Выполнены '):
        return f'Не выполнены {meaning[10:]}'
    if meaning.startswith('Выполнено '):
        return f'Не выполнено {meaning[10:]}'
    if meaning.startswith('Бороде сообщено'):
        return f'Бороде НЕ сообщено {meaning[len("Бороде сообщено"):]}'
    return f'Не {meaning}'


# ---- item nice-name resolution: string tables + per-item inv_name_short/inv_name/scope_name ----
_NAME_STABLES = ["string_table_enc_weapons.xml", "string_table_enc_ammo.xml",
                 "string_table_outfit.xml", "string_table_items.xml", "string_table_enc_equipment.xml",
                 "string_table_general.xml", "string_table_artifacts.xml", "string_table_upgrades.xml"]

def _load_strings(path):
    d = {}
    if not os.path.exists(path):
        return d
    txt = open(path, 'rb').read().decode('cp1251', 'replace')
    for m in re.finditer(r'<string id="([^"]+)">.*?<text>([^<]+)</text>', txt, re.S):
        d[m.group(1)] = m.group(2).strip()
    return d

def _load_item_sections():
    """section id -> {inv_name_short, inv_name, scope_name} across item/ammo/weapons ltx."""
    secs = {}

    def walk(base):
        for dp, _, fns in os.walk(base):
            for fn in sorted(fns):
                if not fn.endswith('.ltx'):
                    continue
                p = os.path.join(dp, fn)
                txt = open(p, 'rb').read().decode('cp1251', 'replace')
                cur = None
                body = {}
                for line in txt.splitlines():
                    s = line.strip()
                    m = re.match(r'\[([^\]]+)\]\s*(.*)$', s)
                    if m:
                        cur = m.group(1)
                        parent = m.group(2).lstrip(':').strip() or None
                        body = {}
                        secs[cur] = {'body': body, 'parent': parent}
                        continue
                    if cur is not None and '=' in s:
                        k, _, v = s.partition('=')
                        body[k.strip()] = v.strip().strip('"').strip("'")

    for sub in ("config/items", "config/weapons"):
        base = os.path.join(BASE, GAMEDATA, sub)
        if os.path.isdir(base):
            walk(base)
    return secs


_NAME_TEXT = None
_ITEM_SECTIONS = None


def _build_name_map():
    global _NAME_TEXT
    names = {}
    for lang in ("eng", "rus"):
        d = os.path.join(BASE, GAMEDATA, 'config', 'text', lang)
        if not os.path.isdir(d):
            continue
        for t in _NAME_STABLES:
            names.update(_load_strings(os.path.join(d, t)))
    return names

def name_map():
    global _NAME_TEXT
    if _NAME_TEXT is None:
        _NAME_TEXT = _build_name_map()
    return _NAME_TEXT

def item_ltx(id):
    global _ITEM_SECTIONS
    if _ITEM_SECTIONS is None:
        _ITEM_SECTIONS = _load_item_sections()
    return _ITEM_SECTIONS.get(id, {'body': {}, 'parent': None})


STAGE_CONDITION_NAMES = {
    'esc_rescue_fox_done':        'Лис спасён',
    'agr_gunslinger_flash_have':  'Найдена флешка Стрелка',
    'dar_barman_has_all_x18_docs':'Все документы из X-18 доставлены Бармену',
    'yan_good_helmet_start':      'Получен настроенный пси-шлем',
    'yan_scientist_package_done': 'Пройдены все квесты учёных на Янтаре',
    'x16_main_power_disabled':    'Отключена установка в X-16',
    'deactivate_radar_done':      'Отключена установка в X-10',
    'bas_switcher_off':           'Отключена установка в X-7',
    'bar_forg_rg6_given':         'Пройдены все квесты Долга',
    'has_freeplay_info':          'Фриплей',
}


FALLBACKS = {}


def read(path):
    with open(os.path.join(TRADE_DIR, path), 'rb') as f:
        return f.read().replace(b'\x00', b'').decode('cp1251', 'replace')


HEADER_RE = re.compile(r'\s*\[([^\]]+)\](?::(.*))?')


def parse_sections(text):
    out = []
    lines = text.split('\n')
    i = 0
    while i < len(lines):
        m = HEADER_RE.match(lines[i])
        if not m:
            i += 1
            continue
        inh = (m.group(2) or '').strip()
        inh = re.sub(r'\s*;.*$', '', inh)
        inh = inh.split('\t')[0].strip()
        j = i + 1
        body = []
        while j < len(lines):
            if HEADER_RE.match(lines[j]):
                break
            body.append(lines[j])
            j += 1
        out.append((m.group(1).strip(), inh, '\n'.join(body).strip()))
        i = j
    yield from out


KV_RE = re.compile(r'^\s*([^\s=#]+)\s*=\s*(.*?)\s*;?\s*$')


def parse_kv(text):
    kv = {}
    for line in text.split('\n'):
        if HEADER_RE.match(line):
            continue
        line = line.strip()
        if not line or line.startswith('#') or line.startswith(';'):
            continue
        m = KV_RE.match(line)
        if m:
            kv[m.group(1)] = m.group(2)
    return kv


INCLUDED = set()


def parse_top_level(text):
    for line in text.split('\n'):
        if HEADER_RE.match(line):
            continue
        m = KV_RE.match(line)
        if not m:
            continue
        key = m.group(1).strip()
        val = re.sub(r'^\{[^}]*\}', '', m.group(2).strip().strip(';').strip())
        parents = re.sub(r'\s*;.*$', '', val).split('\t')[0].strip()
        yield (key, [p.strip() for p in parents.split(',') if p.strip()], '')


def load_sections(start_rel):
    included = set()
    sections = {}

    def norm(p):
        return os.path.normpath(os.path.join(TRADE_DIR, p))

    def walk(d, rel):
        f = os.path.join(d, rel)
        if f in included:
            return
        included.add(os.path.basename(f))
        txt = read(rel)
        for line in txt.splitlines():
            m = re.search(r'#include\s+"([^"]+)"', line)
            if not m:
                continue
            yield from walk(os.path.dirname(f), m.group(1))

    list(walk(TRADE_DIR, start_rel))
    for np in sorted(included):
        for sid, inh, body in parse_sections(read(np)):
            if not sid:
                continue
            if sid in ('default_weapon_params', 'identity_immunities'):
                continue
            parents = [p.strip() for p in inh.split(',') if p.strip()]
            kv = parse_kv(body)
            sections[sid] = {'file': np, 'parents': parents, 'body': kv}
        for tid, tp, tb in parse_top_level(read(np)):
            if not tid:
                continue
            sections[tid] = {'file': np, 'parents': tp, 'body': {}}
    return sections


def resolve(sections, sid):
    sec = sections.get(sid)
    if not sec:
        return {}
    props = dict(sec['body'])

    def rec(*parents, seen):
        cur = parents[0]
        p = sections.get(cur)
        if not p:
            return None
        for k, v in p['body'].items():
            sv = str(v).strip()
            if sv and k not in props:
                props[k] = sv
        rv = rec(*p['parents'], seen=seen | {cur}) if p['parents'] else {}
        if rv is not None:
            return rv
        return None

    r = rec(sid, seen=set())
    if r:
        return props
    wb = sections.get('trader_base')
    if wb:
        for k, v in wb['body'].items():
            sv = str(v).strip()
            if sv and k not in props:
                props[k] = sv
    return props


def friendly_category(key):
    """Map a raw $category_* key to its display name (e.g. $category_ammo -> 'Патроны')."""
    if key.startswith('$category_'):
        c = key[len('$category_'):]
    elif key.startswith('category_'):
        c = key[len('category_'):]
    else:
        c = key
    c = c.replace('_', ' ')
    return {
        'ammo': 'Патроны',
        'artefacts': 'Артефакты',
        'devices': 'Девайсы',
        'food': 'Еда',
    'meds': 'Медицина',
    'misc': 'Другое',
    'misc buy': 'Другое',
    'misc sell': 'Другое',
        'mutant': 'Части мутантов',
        'outfit': 'Броня',
        'weapons': 'Оружие',
    }.get(c, c)


def resolve_categories(group, sections):
    if group.startswith('category_'):
        group = group[len('category_'):]
    sec = sections.get('category_' + group)
    if not sec:
        return {group}
    parents = sec.get('parents') or ''
    if isinstance(parents, str):
        parents = [p.strip() for p in parents.split(',') if p.strip()]
    else:
        parents = [p.strip() for p in parents if p.strip()]
    if not parents:
        return {group}
    out = set()
    for p in parents:
        out |= resolve_categories(p, sections)
    return out


def collect_prices(sections, sec_id):
    cats = {}

    def rec(cur):
        p = sections.get(cur)
        if not p:
            return
        for k, v in p['body'].items():
            m = re.match(r'^\$category_(.+)$', k)
            if not m:
                continue
            group = m.group(1)
            parts = str(v).split(',')
            try:
                rate = (float(parts[0]), float(parts[1]))
            except ValueError:
                continue   # no_sell entries carry no value -> skip
            leaves = resolve_categories(group, sections)
            if len(leaves) == 1 and group in leaves:
                cats[group] = rate          # direct category: last-wins (unchanged)
            else:
                for leaf in leaves:         # alias group: fill missing leaves only
                    if leaf not in cats:
                        cats[leaf] = rate
        for parent in p['parents']:
            rec(parent)

    raw = re.sub(r'^\{[^}]*\}', '', sec_id.strip()).split(',')
    for part in raw:
        part = part.strip()
        if not part:
            continue
        rec(part)

    return [dict(cat=friendly_category(c), best_cond=m, worst_cond=x)
            for c, (m, x) in sorted(cats.items(), key=lambda kv: kv[1][0])]


def section_id(token):
    token = token.strip()
    if not token or token.startswith('#') or token.startswith(';'):
        return None
    if token in ('none', 'no', 'off', 'disabled'):
        return None
    parts = token.split(':')
    return parts[0].strip() or None


def resolve_supplies(sections, sid):
    props = {}

    def rec(*parents, seen):
        cur = parents[0]
        p = sections.get(cur)
        if not p:
            return {}
        body = dict(p['body'])
        for k, v in p['body'].items():
            props[k] = v
        rv = rec(*p['parents'], seen=seen | {cur}) if p['parents'] else {}
        if rv:
            props.update(rv)
        return {}

    rec(sid, seen=set())
    items = {}
    for k, v in props.items():
        if k.startswith('$'):
            continue
        q, pr = parse_val(v)
        if q is None:
            items.pop(k, None)
        else:
            items[k] = (q, pr)
    return items


def item_name(inv_name):
    mm = name_map()
    seen = set()
    cur = inv_name
    while cur and cur not in seen:
        seen.add(cur)
        sec = item_ltx(cur)
        for pref in (cur, 'st_' + cur, cur + '_name', 'st_' + cur + '_name',
                     cur + '_nam', 'st_' + cur + '_nam'):
            if pref in mm:
                return mm[pref]
        for key in ('inv_name', 'inv_name_short', 'scope_name'):
            v = sec['body'].get(key)
            if v and v in mm:
                return mm[v]
        inv = sec['body'].get('inv_name') or cur
        for suf in ('_name', '_nam'):
            k = inv + suf
            if k in mm:
                return mm[k]
        parents = [p for p in re.split('[,;]', sec['parent'] or '') if p.strip()]
        for anc in parents:
            anc = anc.strip()
            if anc and anc not in seen:
                seen.add(anc)
                asec = item_ltx(anc)
                for pref in (anc, 'st_' + anc):
                    if pref in mm:
                        return mm[pref]
                v = asec['body'].get('inv_name_short') or asec['body'].get('inv_name')
                if v and v in mm:
                    return mm[v]
        cur = parents[0] if parents else None
    return None


def num(value):
    value = str(value).strip()
    if not value:
        return None
    for ch in ('%', '×', 'x', 'X', ' ', '.'):
        value = value.replace(ch, '')
    try:
        return float(value)
    except ValueError:
        return None


def _pf(value):
    """Parse buy_item_condition_factor like num(), but keep the decimal point."""
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def fmt_num(n):
    if n is None or n == int(n):
        return str(int(n))
    return f'{n:.1f}'


def fmt_price(n):
    if n is None:
        return ''
    return f'{float(n):.2f}'


def fmt_percent(p):
    if p is None:
        return ''
    n = float(p) * 100
    return f'{n:g}%'


def fmt_paid(v):
    """Vanilla trade formula: trader pays (worst_cond + best_cond) / 2 * base_price. Return that as '% of base'."""
    if not v:
        return ''
    avg = (v.get('best_cond', 0) + v.get('worst_cond', 0)) / 2
    return fmt_percent(avg)


def parse_discounts(text, sections):
    text = (text or '').strip().replace('\n', ' ')
    if not text:
        return []
    out = []
    for part in text.split(','):
        part = part.strip()
        if not part:
            continue
        cond = ''
        m = re.search(r'\{([^}]*)\}', part)
        if m:
            cond = m.group(1).strip()
            part = re.sub(r'\{[^}]*\}', '', part).strip()
        sid = section_id(part)
        if not sid:
            continue
        body = sections.get(sid, {}).get('body', {}) or {}
        buy = body.get('buy')
        sell = body.get('sell')
        def f(v):
            try: return float(str(v).strip())
            except (ValueError, AttributeError): return None
        out.append({'section': sid, 'condition': cond, 'buy': f(buy), 'sell': f(sell)})
    return out


def resolve_supply_section(sections, sid, follow_parents=True):
    """Return a stage's supply items as {id: (qty, prob)}.
    When follow_parents is True the whole parent chain is accumulated (full assortment);
    when False only this stage's own body is returned — i.e. the incremental diff vs its parent."""
    props = {}

    def rec(cur):
        if cur in props:
            return
        props[cur] = True
        p = sections.get(cur)
        if not p:
            return
        for k, v in p['body'].items():
            if k not in props:
                props[k] = v
        if follow_parents:
            for anc in p['parents']:
                rec(anc)

    rec(sid)
    out = {}
    for k, v in props.items():
        key = k.strip()
        if key.startswith('$'):
            continue
        s = str(v).strip().strip("'").strip('"')
        parts = s.split(',')
        try:
            q = float(parts[0]) if len(parts) > 0 and parts[0] else None
            pr = float(parts[1]) if len(parts) > 1 and parts[1] else None
        except ValueError:
            q = pr = None
        if q is None:
            out.pop(key, None)
        else:
            out[key] = (q, pr)
    return out


def parse_supply_stages(value):
    """Split a buy_supplies/sell_supplies value into (stage_id, condition) pairs.
    Each comma-separated token may lead with one or more {condition} groups."""
    stages = []
    for tok in value.split(','):
        cond_exprs = []
        while True:
            m = re.match(r'^\s*\{\s*([^}]*)\}\s*(.*)$', tok, re.S)
            if not m:
                break
            cond_exprs.append(m.group(1).strip())
            tok = m.group(2).strip()
        sid = section_id(tok)
        if not sid or sid == 'supplies_no':
            continue
        stages.append({'id': sid, 'condition': ' '.join(cond_exprs)})
    return stages


def supply_stage_order(stage_ids, parents_map):
    """Order supply stages ascending from the earliest ('start') stage to the most advanced.
    Edges are parent references that point at other supply stages; item presets (basic_supplies, etc.) are ignored."""
    order = []
    done = set()
    def rec(sid, seen):
        if sid in done or sid in seen:
            return
        seen |= {sid}
        for p in parents_map.get(sid, ()):
            if p in stage_ids and p not in done:
                rec(p, seen)
        order.append(sid)
        done.add(sid)
    for sid in list(stage_ids):
        rec(sid, set())
    return [s for s in order if s in stage_ids]


def parse_trader_file(path):
    sections = load_sections(path)
    if 'trader' not in sections:
        return None
    kv = resolve(sections, 'trader')
    trader = os.path.splitext(path)[0]
    category = kv.get('$category')
    buy_cond = kv.get('buy_condition', '')
    sell_cond = kv.get('sell_condition', '')
    buy_supplies_raw = kv.get('buy_supplies', '')
    sell_supplies_raw = kv.get('sell_supplies', '')
    discounts_raw = kv.get('discounts', '')
    cond_factor = kv.get('condition_factor', '1')
    buy_prices = collect_prices(sections, buy_cond) if buy_cond else []
    sell_prices = collect_prices(sections, sell_cond) if sell_cond else []
    discounts = parse_discounts(discounts_raw, sections) if discounts_raw else []
    cond_factor = num(cond_factor) or 1.0
    stages = []
    for supply_field in (buy_supplies_raw, sell_supplies_raw):
        for stage in parse_supply_stages(supply_field):
            if not resolve_supply_section(sections, stage['id']):
                continue
            stages.append({**stage, 'items': resolve_supply_section(sections, stage['id'])})

    # Order stages ascending from the earliest ('start') stage to the most advanced (follows the parent chain),
    # and show only each stage's own diff (its body) rather than the accumulated parent assortment.
    stage_ids = [s['id'] for s in stages]
    parents_map = {sid: sections.get(sid, {}).get('parents', []) for sid in stage_ids}
    order = supply_stage_order(stage_ids, parents_map)
    ordered = []
    for sid in order:
        st = next((s for s in stages if s['id'] == sid), None)
        if st is None:
            continue
        diff = resolve_supply_section(sections, sid, follow_parents=False)
        if not diff:
            continue
        ordered.append({**st, 'items': diff})
    stages = ordered
    return {
        'trader': trader,
        'category': category,
        'sections': sections,
        'stages': stages,
        'buy_prices': buy_prices,
        'sell_prices': sell_prices,
        'discounts': discounts,
        'cond_factor': cond_factor,
        'buy_item_condition_factor': _pf(kv.get('buy_item_condition_factor')) or None,
    }


def items_table(items):
    rows = []
    for k, v in sorted(items.items(), key=lambda kv: kv[0]):
        nice = item_name(k)
        label = nice or k
        poss = fmt_percent(v[1]) if v[1] is not None else ''
        rows.append(f"| {label} | {fmt_num(v[0])} | {poss} |")
    if not rows:
        return ''
    return '\n'.join(['| Предмет | Кол-во | Вероятность |', '| --- | --- | --- |', *rows])


def indent(text, n):
    pad = ' ' * n
    return '\n'.join(pad + ln if ln.strip() else ln for ln in text.split('\n'))


def collect_categories(sections_map):
    """Split every $category_ key into buy-side (buy_*/generic_buy) vs sell-side (sell_*/generic_sell)."""
    seen_b, seen_s = set(), set()
    for info in sections_map.values():
        for sid, sec in info['sections'].items():
            for k in sec.get('body', {}):
                if not k.startswith('$category_'):
                    continue
                c = friendly_category(k)
                if sid.startswith('buy_') or sid == 'generic_buy':
                    if c not in seen_b:
                        seen_b.add(c); ALL_BUY_CATEGORIES.append(c)
                elif sid.startswith('sell_') or sid == 'generic_sell':
                    if c not in seen_s:
                        seen_s.add(c); ALL_SELL_CATEGORIES.append(c)
    return sorted(ALL_BUY_CATEGORIES), sorted(ALL_SELL_CATEGORIES)


def price_block(data, cats):
    """cats = (buy_categories, sell_categories). One table per trader.

    Each cell is the effective trade rate as '% of base price' (vanilla formula: (worst_cond + best_cond) / 2 * base_price).
    Buy = what the trader pays you; Sell = what you pay them. Higher % is always better for you.
    """
    buy = {p['cat']: p for p in (data.get('buy_prices') or [])}
    sell = {p['cat']: p for p in (data.get('sell_prices') or [])}
    rows = []
    for c in cats[0]:
        b = fmt_paid(buy.get(c)) if c in buy else 'Не покупает'
        s = fmt_paid(sell.get(c)) if c in sell else 'Не продаёт'
        rows.append(f"| {c} | {b} | {s} |")
    for c in cats[1]:
        if c not in cats[0] and c in sell:
            rows.append(f"| {c} | Не покупает | {fmt_paid(sell.get(c))} |")
    return '\n'.join(['| Категория | Множ. покупки | Множ. продажи |', '| --- | --- | --- |', *rows])


def build_trader_markdown(data, cats=None):
    if cats is None:
        seen_b, seen_s = set(), set()
        cats = ([], [])
        for sid, sec in data.get('sections', {}).items():
            for k in sec.get('body', {}):
                if not k.startswith('$category_'):
                    continue
                c = friendly_category(k)
                if c in seen_b or c in seen_s:
                    continue
                if sid.startswith('buy_') or sid == 'generic_buy':
                    seen_b.add(c); cats[0].append(c)
                if sid.startswith('sell_') or sid == 'generic_sell':
                    seen_s.add(c); cats[1].append(c)
    info = trader_info(data['trader'])
    if info is None:
        return ''
    _npc, _name_key, name_ru, loc = info

    lines = []
    lines.append("## " + name_ru + " (" + loc + "): " + "`" + _npc + "`")
    lines.append('')
    cat = data.get('category')
    lines.append(f"**Category:** `{cat}`" if cat else '')
    ctx = price_block(data, cats)
    if ctx:
        lines.append('### Множители цен')
        lines.append('Множители применяются к базовой цене предмета')
        lines.extend(ctx.split('\n'))
        lines.append('')
    fac = data.get('buy_item_condition_factor')
    if fac is not None:
        lines.append(f'_Не покупает предметы в состоянии хуже **{fmt_percent(fac)}**._')
        lines.append('')
    disc = data.get('discounts')
    if disc:
        lines.append('### Доп. множители цен')
        lines.append('В коде называется discount, по факту это доп. множители, применяющиеся при определённых условиях. Это не всегда скидки, могут наоборот отрицательно влиять на цены.')
        lines.append('')
        lines.append('| ID | Множ. покупки | Множ. продажи | Условия |')
        lines.append('| --- | --- | --- | --- |')
        for d in disc:
            buy = fmt_price(d['buy']) if d['buy'] is not None else '?'
            sell = fmt_price(d['sell']) if d['sell'] is not None else '?'
            c = (d.get('condition') or '').strip().strip('()').strip() or '-'
            lines.append(f"| {d['section']} | {buy} | {sell} | {c} |")
        lines.append('')
        for op, name, meaning in render_conditions(disc):
            lines.append(f"- `{op}{name}` — {meaning}")
        lines.append('')
    stages = data.get('stages', [])
    if stages:
        lines.append('### Ассортимент')
        for stage in stages:
            sid = stage['id']
            cond = stage.get('condition') or ''
            lines.append(f'#### {sid}')
            if cond:
                lines.append('')
                lines.append('Условия:')
                for raw in [t.strip() for t in cond.split()]:
                    op = ''
                    if raw and raw[0] in '+-=!':
                        op, raw = raw[0], raw[1:]
                    nice = STAGE_CONDITION_NAMES.get(raw, raw)
                    lines.append(f"- `{op}{raw}` — {nice}")
                lines.append('')
            items = stage.get('items', {})
            itbl = items_table(items)
            if itbl:
                lines.append(indent(itbl, 2))
        lines.append('')
    else:
        lines.append('_No supply stages._')
        lines.append('')
    return '\n'.join(lines).rstrip() + '\n'


def main():
    data = {}
    for path in sorted(os.listdir(TRADE_DIR)):
        if not path.endswith('.ltx'):
            continue
        info = parse_trader_file(path)
        if info is None:
            continue
        data[path] = dict(info)

    cats = collect_categories(data)

    tocs = []
    blocks = []
    for path, d in data.items():
        info = trader_info(d['trader'])
        if info is None:
            continue
        _npc, _name_key, name_ru, loc = info
        header = f"## {name_ru} ({loc}): `{_npc}`"
        tocs.append((slugify(header), f'{name_ru} ({loc})'))
        blocks.append(build_trader_markdown(d, cats))

    lines = []
    if tocs:
        lines.append('# Торговцы')
        lines.append('')
        lines.append(build_toc(tocs))
        lines.append('')
    lines.extend(blocks)
    with open(os.path.join(BASE, 'TRADERS.md'), 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines).rstrip() + '\n')


if __name__ == '__main__':
    main()
