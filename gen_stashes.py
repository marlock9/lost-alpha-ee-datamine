#!/usr/bin/env python3
"""Generate STASHES.md from gamedata/config/misc/treasure_manager.ltx.

Resolves every field directly from game config, no mod merge:
  * Cache name / description refs -> string_table_*_rus.xml (id == the ref verbatim).
  * Item tokens (wpn_*, ammo_*, af_*, detector_*, outfits, meds, ...) -> their
    inv_name carried by the matching [section] in gamedata/config/*.ltx, then looked
    up in the same string tables. A few LAEE ids use a prefixed key (st_/enc_/item_/anom_)
    so those prefixes are tried as fallbacks before falling back to the bare token.
  * Location grouping: each stash's id prefix (first segment before '_') is resolved
    to its canonical location via loc_map.name_for(). File comments are ignored here.

Reuses the exact string-table reader pattern from parse_weapons.py / gen_weapons.py.
"""
import re, os, glob

from cond_map import INFOPORTIONS  # single source of truth for infoportion names
from loc_map import name_for  # prefix -> canonical location (id-based, not file comments)

ROOT=os.path.dirname(os.path.abspath(__file__))
LTX=os.path.join(ROOT,"gamedata/config/misc/treasure_manager.ltx")

# ---- string tables: id -> russian text (same regex as the weapons/ammo generators) ----
ST={}
for f in glob.glob(ROOT+"/gamedata/config/text/rus/*.xml")+glob.glob(ROOT+"/gamedata/config/text/rus/stable_*.xml"):
    txt=open(f,'rb').read().decode('cp1251')
    for m in re.finditer(r'<string id="([^"]+)">.*?<text>([^<]+)</text>', txt, re.S):
        ST[m.group(1)]=m.group(2).strip()

# ---- section id -> inv_name across every ltx (base occurrence wins) ----
sec_inv={}
for f in glob.glob(ROOT+"/gamedata/config/**/*.ltx", recursive=True):
    txt=open(f,'rb').read().replace(b'\x00',b'').decode('cp1251','replace')
    for mm in re.finditer(r'\[([^\]]+)\]', txt):
        body=txt[mm.end():txt.find('[',mm.end())]
        iv=re.search(r'inv_name\s*=\s*([^\s#]+)', body)
        if iv: sec_inv.setdefault(mm.group(1), iv.group(1))

def nice(token):
    for cand in (token, f'{token}_name', f'{token}_bio',
                 'st_'+token,'enc_'+token,'item_'+token,'anom_'+token,
                 'st_'+token+'_name','enc_'+token+'_name'):
        if cand in ST: return ST[cand]
    inv=sec_inv.get(token)
    if inv and inv in ST: return ST[inv]
    return token

# ---- story id -> NPC tech name (game_story_ids.ltx), then bio name from strings ----
STORY_IDS={}
for f in glob.glob(ROOT+"/gamedata/config/game_story_ids.ltx"):
    txt=open(f,'rb').read().decode('cp1251')
    for m in re.finditer(r'^\s*(\d{4,5})\s*=\s*"([^"]+)"', txt, re.M):
        STORY_IDS[m.group(1)]=m.group(2)

# ---- story tech ids with no rus string entry: explicit display override ----
STORY_NICKS={'out_bar_informator':'Осведомитель'}

# ---- NPC display names from character_desc_*.xml (authoritative, handles dev typos):
#    each specific_character's <name>/<bio> tag points to a string id that carries the
#    display text. Refs resolving to long task/description strings are ignored -> nice().
CHAR={}
for f in glob.glob(ROOT+"/gamedata/config/gameplay/npc/character_desc_*.xml"):
    txt=open(f,encoding='cp1251').read()
    for m in re.finditer(r'<specific_character\s+id="([^"]+)".*?<name>([^<]+)</name>', txt, re.S):
        CHAR.setdefault(m.group(1),{})['name']=m.group(2)
    for m in re.finditer(r'<specific_character\s+id="([^"]+)".*?<(?:bio|description)>([^<]+)</(?:bio|description)>', txt, re.S):
        d=m.group(2).strip()
        if d: CHAR.setdefault(m.group(1),{})['bio']=d

def npc_names(story_id):
    """is_dead_one id(s) -> NPC display names. Colon-separated ids (a dead group) are
       resolved individually; each id goes story id -> tech name, then prefers the
       character_desc_*.xml <name>/<bio> string (authoritative), then the _name/_bio
       string (stable_bio_name.xml), then nice()."""
    out=[]
    for i in story_id.split(':'):
        tech=STORY_IDS.get(i.strip())
        if not tech:
            out.append(i.strip() or '')
            continue
        nick=STORY_NICKS.get(tech)
        if nick: out.append(nick); continue
        for ref in (CHAR.get(tech,{}).get('name'), CHAR.get(tech,{}).get('bio')):
            if ref and ref in ST:
                v=ST[ref].strip()
                if v and len(v)<=20: out.append(v); break
        else:
            for suf in ('_name','_bio'):
                k=f'{tech}{suf}'
                if k in ST and ST[k].strip():
                    out.append(ST[k]); break
            else:
                n=nice(tech)
                out.append(n if n else tech)
    return ', '.join(x for x in out if x)

def npc_name(story_id):
    return npc_names(story_id)

RANK={1:'новичок',2:'опытный',3:'ветеран',4:'мастер'}   # player rank; same scale for npc_rank
RANK_NAME={'novice':1,'experienced':2,'veteran':3,'master':4,'stalker':2}
def nice_of_rank(n):
    try: return RANK[int(n)]
    except (KeyError,ValueError): return str(n)
def name_to_rank(name):
    k=RANK_NAME.get((name or '').lower())
    return RANK[k] if k else (name or '')

def render_conditions(cond):
    """Render a stash condlist string as markdown bullets. Each space-separated
       token is looked up in the infoportion map; known flags get their Russian
       description, npc_rank_not_lower checks render as 'Ранг NPC ≥ {rank}', and
       any other predicate (e.g. npc death) falls back to the raw token."""
    out=[]
    for tok in (cond or '').replace('{','').replace('}','').split():
        m=re.match(r'^([+\-=!]?)([a-zA-Z_][a-zA-Z0-9_]*)(.*)$', tok)
        if not m: continue
        op,name,rest=m.group(1),m.group(2),m.group(3)
        label=f"{op}{name}{rest}"
        if name=='is_dead_one':
            out.append(f"- Должен быть мёртв NPC: {npc_name(rest.strip('()'))}")
        elif name=='npc_rank_not_lower':
            out.append(f"- Ранг NPC ≥ {name_to_rank(rest.strip('()'))}")
        elif desc:=INFOPORTIONS.get(name):
            out.append(f"- {desc}")
        else:
            out.append(f"- `{label}`")
    return '\n'.join(out)

# ---- parse the ltx into caches + group by id-prefix -> canonical location ----
txt=open(LTX,encoding='utf-8').read()
KV=re.compile(r'(\w[\w\-\.]*)\s*=\s*(.*)$')
SEC=re.compile(r'\[([^\]]+)\]')

order=[]            # location name -> {'name':.., 'stashes':[{id:row}, ...]}
cur=None; cur_row=None
for line in txt.split('\n'):
    sm=SEC.match(line.strip())
    if sm and sm.group(1).endswith('_cache'):
        pfx=sm.group(1).split('_')[0]
        loc=name_for(pfx)
        idx=[i for i,e in enumerate(order) if e['name']==loc]
        if idx: order[idx[0]]['stashes'].append({}); cur_row=order[idx[0]]['stashes'][-1]
        else: order.append({'name':loc,'stashes':[]})
        cur_row={}; order[-1]['stashes'].append(cur_row)
        continue
    if cur_row is not None:
        m=KV.match(line)
        if m and m.group(1) in ('target','name','description','items','community','rank','condlist'):
            cur_row[m.group(1)]=m.group(2).strip()

# ---- build per-stash item list with counts + nice names ----
def parse_items(s):
    parts=s.split(','); out=[]; i=0
    while i < len(parts):
        tok=parts[i].strip()
        if not tok: i+=1; continue
        count=1
        nxt=parts[i+1].strip() if i+1 < len(parts) else ''
        if nxt.isdigit(): count=int(nxt); i+=2
        else: i+=1
        out.append((tok,count))
    return out

# ---- group stash rows + resolved item lists by unique location name ----
by_loc={}
for entry in order:
    for row in entry['stashes']:
        if not row: continue
        items=[(nice(t),c) for t,c in parse_items(row.get('items',''))]
        by_loc.setdefault(entry['name'],[]).append((row,items))

# ---- item-category summary (derived from token prefix, purely data-driven) ----
def category(tok):
    if tok.startswith('wpn_'): return 'оружие'
    if tok.startswith('ammo_'): return 'патроны'
    if tok.startswith('af_'): return 'артефакты'
    if tok.startswith('detector_') or tok.startswith('device_'): return 'оборудование'
    if tok.startswith('booster_'): return 'усилители'
    if tok.startswith('grenade_'): return 'гранаты'
    if re.search(r'outfit|helm|stalker_|military_|svoboda|scientific|protection|killer_|dolg_', tok): return 'экипировка'
    if tok in ('rubles_100','rubles_500','rubles_1000'): return 'деньги'
    if re.search(r'medkit|bandage|antirad|energy_drink|vodka|mineral_water|tushenka|korn_conserva|cmuphob_vodka|hemupob_vodka|med_', tok): return 'аптечки и еда'
    return 'предметы'

def rank_word(rank):
    return {1:'новичка',2:'ветерана',3:'мастера',4:'мастера'}[rank]

COMM={
  'stalker':'Одиночки','bandit':'Бандиты','dolg':'Долг','freedom':'Свобода',
  'killer':'Наёмники','military':'Военные','ecolog':'Экологи','monolith':'Монолит',
  'dark_stalker':'Грех','clear_sky':'Чистое Небо','milstalker':'Военные сталкеры'}

def comm_word(c): return COMM.get(c,c)

def fmt_items(items):
    parts=[]
    for nice_,c in items:
        if c and c>1: parts.append(f"{nice_} ×{c}")
        else: parts.append(nice_)
    return "; ".join(parts)

out=[]

for loc, rows in by_loc.items():
    out.append(f"# {loc}\n\n")
    for row,items in rows:
        nice_name=row.get('name','')
        if nice_name and nice_name in ST: nice_name=ST[nice_name]
        nice_name=re.sub(r'\s+',' ',nice_name.strip())
        out.append(f"## {nice_name}\n\n")
        desc=row.get('description','')
        if desc and desc in ST: desc=ST[desc]
        desc=re.sub(r'\s+',' ',desc.strip())
        if desc: out.append(f"> {desc}\n\n")
        cond=row.get('condlist','')
        parts=cond.rsplit(None,1)
        if len(parts)==2 and parts[1].isdigit(): condition,chance=parts[0],parts[1]
        else: condition,chance='',cond
        out.append(f"Шанс: {chance}%\n\n")
        rank_nice=nice_of_rank(row.get('rank',''))
        bullets=[]
        if condition.strip():
            for line in render_conditions(condition).split('\n'):
                if line: bullets.append(line)
        if not bullets and rank_nice:
            bullets.append(f"- Ранг игрока ≥ {rank_nice}")
        elif bullets:
            bullets.insert(0, f"- Ранг игрока ≥ {rank_nice}")
        # NPC faction grouping: community is a comma-separated list in the ltx
        seen=set(); comm_tokens=[]
        for t in row.get('community','').split(','):
            t=t.strip()
            if t and t not in seen: seen.add(t); comm_tokens.append(t)
        if comm_tokens:
            comm_nice=[comm_word(t) for t in comm_tokens]
            bullets.append(f"- Группировка NPC: {', '.join(comm_nice)}")
        out.append('Условия:\n')
        for b in bullets:
            out.append(f"{b}\n")
        out.append('\n\n')
        if items:
            out.append("| Содержимое |\n| --- |\n")
            for nice_,c in items:
                cell = f'{nice_} ×{c}' if c and c>1 else nice_
                out.append(f"| {cell} |\n")

open(os.path.join(ROOT,"STASHES.md"),"w",encoding="utf-8").write("".join(out))
print(f"wrote STASHES.md with {len(by_loc)} locations, {sum(len(v) for v in by_loc.values())} stashes")
