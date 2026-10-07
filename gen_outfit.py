#!/usr/bin/env python3
"""Parse LAEE outfit data (outfit.ltx + outfit_upgrades/) and generate OUTFIT.md."""
import os, math, re
from collections import OrderedDict

ROOT="/var/home/anton/.var/app/com.usebottles.bottles/data/bottles/bottles/LAEE/drive_c/mods"
OUTFITS=os.path.join(ROOT,"gamedata","config","items","equipments","outfit.ltx")
UPDIR=os.path.join(ROOT,"gamedata","config","items","equipments","outfit_upgrades")
TXT=os.path.join(ROOT,"gamedata","config","text","eng","string_table_outfit.xml")
RU_TXT=os.path.join(ROOT,"gamedata","config","text","rus","string_table_outfit.xml")
UPG_TXT=os.path.join(ROOT,"gamedata","config","text","rus","string_table_upgrades.xml")
UPG_ENG=os.path.join(ROOT,"gamedata","config","text","eng","string_table_upgrades.xml")
ITEMS_TXT=os.path.join(ROOT,"gamedata","config","text","rus","string_table_items.xml")

def read(p): return open(p,'rb').read().replace(b'\x00',b'').decode('utf-8','replace')

def parse_sections(txt):
    secs,cur=[],None
    for line in txt.splitlines():
        s=line.strip()
        m=re.match(r'\[([^\]]+)\]',s)
        if m: cur=(m.group(1),s[m.end():].lstrip(':').strip(),[]);secs.append(cur);continue
        if cur and '=' in s: cur[2].append(s)
    return secs

def parse_kv_all(body):
    out={}
    for line in body:
        if "=" not in line: continue
        k,_,v=line.partition("=");k=k.strip();v=v.split(";")[0].strip()
        out[k]=v
    return out

# ---- string tables (outfit names/descriptions + upgrade element labels) ----
def load_strings(path):
    d={}
    txt=open(path,'rb').read().decode('cp1251')
    for m in re.finditer(r'<string id="([^"]+)">.*?<text>([^<]+)</text>',txt,re.S):
        d[m.group(1)]=m.group(2).strip()
    return d
OUTFITS_STR=load_strings(TXT); OUTFITS_RU=load_strings(RU_TXT); ITEMS_RU=load_strings(ITEMS_TXT)
UPG_STR=load_strings(UPG_ENG); UPG_RU=load_strings(UPG_TXT)
def resolve(ref):
    for d in (OUTFITS_RU,OUTFITS_STR,UPG_RU,UPG_STR):
        if ref and ref in d: return d[ref]
    return None

# ---- RUSSIAN labels ----
BONE={  # bones_koeff_protection constants
 "actor_body_zero":"Без защиты от скелетных аномалий",
 "actor_body_minimal":"Минимальная защита от скелетных аномалий",
 "actor_body_light":"Лёгкая защита от скелетных аномалий",
 "actor_body_medium":"Средняя защита от скелетных аномалий",
 "actor_body_halfheavy":"Полутяжёлая защита от скелетных аномалий",
 "actor_body_medium_plus":"Средне-тяжёлая защита от скелетных аномалий",
 "actor_body_heavy":"Тяжёлая защита от скелетных аномалий",
 "actor_body_ultralight":"Ультра-лёгкая защита от скелетных аномалий",
 "actor_body_mail":"Лёгкая кольчуга (защита от скелетных аномалий)",
 "actor_body_ultraheavy":"Ультра-тяжёлая защита от скелетных аномалий",
 "actor_full_ps5m":"Полная (психоматрица 5M) защита от скелетных аномалий",
 "actor_full_exo":"Полная экзозащита от скелетных аномалий",
 "actor_full_exo_svoboda":"Полная экзозащита от скелетных аномалий (Свобода)",
 "actor_full_exo_dolg":"Полная экзозащита от скелетных аномалий (ДОГЛ)",
 "actor_full_exo_heavy":"Полная тяжёлая экзозащита от скелетных аномалий",
 "actor_full_seva":"Полная защита от скелетных аномалий (СЕВА)",
 "actor_full_ssp10":"Полная защита от скелетных аномалий (SSP-10)",
 "actor_full_ssp99":"Полная защита от скелетных аномалий (SSP-99)",
 "actor_full_ssp99m":"Полная защита от скелетных аномалий (SSP-99M)",
}
TIER_RANK={"actor_body_zero":0,"actor_body_minimal":0,"actor_body_ultralight":0,"actor_body_mail":1,
"actor_body_light":1,"actor_body_medium":2,
"actor_body_halfheavy":3,"actor_body_medium_plus":3,"actor_body_heavy":4,"actor_body_ultraheavy":5,
"actor_full_ps5m":5,"actor_full_exo":5}
def tier_rank(v):
    if v in BONE: return TIER_RANK.get(v,5)
    return 9

PROT={"burn_protection":"Термозащита","chemical_burn_protection":"Химзащита",
"explosion_protection":"Взрывоустойчивость","radiation_protection":"Радиозащита",
"shock_protection":"Электрозащита",
"strike_protection":"Ударостойкость","telepatic_protection":"Пси-защита","wound_protection":"Разрывоустойчивость"}
IMM={"burn_immunity":"Износ: Терм.","chemical_burn_immunity":"Износ: Хим.",
"explosion_immunity":"Износ: Взрыв","radiation_immunity":"Износ: Радиация",
"fire_wound_immunity":"Износ: Пуля","shock_immunity":"Износ: Ток",
"strike_immunity":"Износ: Удар","telepatic_immunity":"Износ: Пси","wound_immunity":"Износ: Разрыв"}
MOV={"additional_run_coef":"Скорость бега","additional_sprint_koef":"Скорость спринта",
"additional_jump_speed":"Высота прыжка","additional_inventory_weight":"Грузоподъёмность"}
RESOURCE_LABEL="Ресурс"

# ---- outfit upgrade property -> RU stat (secondary grouping; element description is primary) ----
UPG_PROP={"prop_chem":"Хим. ожоги (×)","prop_electro":"Электроток (×)","prop_explo":"Взрывы (×)",
"prop_power":"Потеря энергии","prop_radio":"Радиация (×)","prop_thermo":"Огневые волны (×)",
"prop_wound":"Раны (×)","prop_damage":"Защита от скелетных аномалий (×)",
"prop_durability":"Прочность комплекта","prop_restore_health":"Восстановление здоровья",
"prop_restore_bleeding":"Остановка кровотечения","prop_psy":"Психика (×)",
"prop_psy_2":"Психика 2 (×)","prop_psyhelmet":"Психика шлема (×)",
"prop_armor_1":"Броня +1","prop_armor_2":"Броня +2","prop_armor_3":"Броня +3",
"prop_sprint":"Скорость спринта","prop_tonnage":"Грузоподъёмность","prop_weightoutfit":"Вес комплекта"}

# ---- gather outfit sections ----
OUTFITS_STR_KV={}
for name,parents,body in parse_sections(read(OUTFITS)):
    OUTFITS_STR_KV[name]=parse_kv_all(body)

# single section lookup across outfit.ltx + upgrades (so immunity sects resolve too)
SECKV={}
for name,parents,body in parse_sections(read(OUTFITS)):
    SECKV[name]={"parents":parents,"kv":parse_kv_all(body)}
for fn in sorted(os.listdir(UPDIR)):
    if not fn.endswith("_up.ltx"): continue
    for name,parents,body in parse_sections(read(os.path.join(UPDIR,fn))):
        SECKV[name]={"parents":parents,"kv":parse_kv_all(body)}

def parents_of(id_): return SECKV.get(id_,{}).get("parents","").split(",")

# ---- resolve outfit stats by walking parent chain ----
OUTFITS={}
for id_,sec in SECKV.items():
    if id_ in ("outfit_base","without_outfit"): continue
    seen=set(); stack=[id_]
    while stack:
        c=stack.pop()
        if c in seen: break
        seen.add(c)
        for p in parents_of(c):
            if p in ("outfit_base","without_outfit"): seen.add(p);continue
            stack.append(p)
    if "outfit_base" not in seen: continue
    merged={}
    for c in parents_of(id_)+[id_]:
        kv=SECKV.get(c,{})["kv"]
        for k,v in kv.items(): merged[k]=v
    OUTFITS[id_]={"kv":merged,"parent":parents_of(id_)[0] if parents_of(id_) else "outfit_base"}

def fmt(v):
    if v is None: return "—"
    s=str(v)
    try:
        f=float(s)
        if f==0.0: return "—"
        if "." not in s: return f"{int(round(f))}"
        return str(f)
    except ValueError:
        return s

def bone_label(v): return BONE.get(v, v)

# ---- outfit armor protection coefficients from creatures/damages.ltx ----
# Each damage section: `bone = k, protection`; protection is the value AFTER the comma.
# A full kit (`actor_full_*`) inherits a body preset + head preset; walk parents transitively.
DAMAGES=os.path.join(ROOT,"gamedata","config","creatures","damages.ltx")
def parse_damages():
    sec={}; parents={}
    rx=re.compile(r'\[[^\]]+\]:\s*(.+)$')
    for l in open(DAMAGES,'rb').read().decode('cp1251','replace').splitlines():
        s=l.strip()
        if rx.match(s):
            cur=s[1:s.index(']')]; parents[cur]=s[s.index(':')+1:].strip(); continue
        hm=re.match(r'\[([^\]]+)\]',s)
        if hm: cur=hm.group(1).strip()
        bm=re.match(r'(\S+)\s*=\s*(-?\d*\.?\d+),\s*(-?\d*\.?\d+)',s)
        if bm and cur: sec.setdefault(cur,{}); sec[cur][bm.group(1).strip()]=float(bm.group(3))
    return sec,parents
DSEC,DPARS=parse_damages()
def armor_coef(preset,bone):
    if not preset: return None
    seen=set(); stack=[preset]
    while stack:
        p=stack.pop()
        if p in seen: continue
        seen.add(p)
        for par in DPARS.get(p,'').split(','):
            par=par.strip()
            if par and par[0]!='$' and par!='actor_visual' and par not in seen: stack.append(par)
        if p in DSEC:
            for b,v in DSEC[p].items():
                if b==bone: return v
    return None
def torso_head(preset):
    t=armor_coef(preset,'bip01_pelvis'); h=armor_coef(preset,'bip01_head')
    return (f"{t:.2f}" if t is not None else "—", f"{h:.2f}" if h is not None else "—")

# immunity values live in separate `sect_<name>_immunities` sections (referenced by immunities_sect),
# NOT in class-parent inheritance — resolve them from the sect directly
def outfit_imm(id_):
    m=OUTFITS.get(id_,{}).get("kv",{})
    sect=m.get('immunities_sect')
    if not sect: return None
    d=SECKV.get(sect,{}).get("kv",{})
    return (d.get('burn_immunity'),d.get('chemical_burn_immunity'),d.get('explosion_immunity'),
            d.get('radiation_immunity'),d.get('fire_wound_immunity'),d.get('shock_immunity'),
            d.get('strike_immunity'),d.get('telepatic_immunity'),d.get('wound_immunity'))

_IMM_KEYS=("burn_immunity","chemical_burn_immunity","explosion_immunity",
"radiation_immunity","fire_wound_immunity","shock_immunity",
"strike_immunity","telepatic_immunity","wound_immunity")
# max durability-bar value (floor(total_resource * 3)); in-game get_immunity_value sums base + _add, so resource uses merged values here only. Outfits read SECKV(+_add); helmets read helmet immunity sects (no _add).
def imm_resource(id_, kv):
    if id_ in OUTFITS:
        m=OUTFITS.get(id_,{}).get("kv",{})
        sect=m.get('immunities_sect')
        if not sect: return None
        base=SECKV.get(sect,{})["kv"]
        add=SECKV.get(sect+"_add",{}).get("kv",{})
    else:
        sect=HELMETS.get(id_,{}).get('immunities_sect')
        if not sect: return None
        base={kk:vv for kk,vv in zip(_IMM_KEYS, imm_sect.get(sect,((),)))}
        add={}
    pos=[]
    for k in _IMM_KEYS:
        b=base.get(k); a=add.get(k); v=None
        if b and a:
            try: v=float(b)+float(a)
            except ValueError: continue
        elif b:
            try: v=float(b)
            except ValueError: continue
        elif a:
            try: v=float(a)
            except ValueError: continue
        if v is not None and v>0: pos.append(v)
    if not pos: return None
    return math.floor((sum(1.0/v for v in pos)/len(pos))*3)

# ---- OUTFIT.md ----
lines=[]
lines.append("# 🎽 Комплекты брони (Outfits)")
lines.append("")

def get(k): return fmt(m.get(k,""))

# group outfits into tables by tier, taken from the RU nice-name prefix (Т1..Т4), matching WEAPONS.md
TIER_ORDER=["T1","T2","T3","T4"]
tgroups={t:[] for t in TIER_ORDER}
for id_,o in OUTFITS.items():
    m=o["kv"]
    inv=m.get("inv_name") or m.get("inv_name_short")
    nn=(OUTFITS_RU.get(inv) if inv else None) or "<нет названия>"
    tm=re.match(r'[Тт]\d',nn)
    tier=(tm.group().replace("Т","T") if tm else "?")
    tgroups[tier].append((id_,m,nn,outfit_imm(id_)))

def header(cols):
    lines.append("| " + " | ".join(cols) + " |")
    lines.append("|" + " | ".join(["--:"]*len(cols)) + " |")

for t in TIER_ORDER:
    rows=tgroups[t]
    if not rows: continue
    lines.append(f"## {t}")
    lines.append("")
    MOV_KEYS=("additional_run_coef","additional_sprint_koef","additional_inventory_weight")
    header(["#", "Комплект", "Файл", "Заброневая травма", "Утомляемость", *PROT.values(), "Броня туловища", "Броня головы", *IMM.values(), *list(MOV[k] for k in MOV_KEYS[:-1]), "Вес", *list(MOV[k] for k in MOV_KEYS[2:]), RESOURCE_LABEL, "Стоимость"])
    prot_keys=list(PROT); imm_keys=list(IMM)
    for i,(id_,m,nn,imm) in enumerate(rows,1):
        # TODO: later — take protection coefficients into account for EVERY bone.
        # bones_koeff_protection sets a per-bone factor (1.0, X.X); the column should
        # aggregate them instead of a single resolved "Скел. ан." value.
        prot=[fmt(m.get(k)) for k in prot_keys]
        t,h=torso_head(m.get('bones_koeff_protection'))
        immv=[fmt(imm[j]) for j in range(9)] if imm else [None]*9
        c=fmt(m.get('cost')); rc=fmt(m.get('repair_compatibility'))
        line=f"| {i} | {nn} | `{id_}` | {fmt(m.get('hit_fraction_actor'))} | {fmt(m.get('power_loss'))} | " + " | ".join(prot) + f" | {t} | {h} | " + " | ".join(immv) + f" | {fmt(m.get('additional_run_coef'))} | {fmt(m.get('additional_sprint_koef'))} | {fmt(m.get('inv_weight'))} | {fmt(m.get('additional_inventory_weight'))} | {fmt(imm_resource(id_, m))} | {c} |"
        lines.append(line)
    lines.append("")

w="\n".join(lines)
open("OUTFIT.md","w").write(w+"\n")
print(f"OUTFIT.md: {len(OUTFITS)} outfits (T1={len(tgroups['T1'])} T2={len(tgroups['T2'])} T3={len(tgroups['T3'])} T4={len(tgroups['T4'])})")

# ---- HELMETS (headgear; protection via immunity sects, not body values) ----
HELM=os.path.join(ROOT,"gamedata","config","items","equipments","helmets.ltx")
raw=open(HELM,'rb').read()
helmet_txt=bytes(b for b in raw if not (0x80<=b<0xa0) and b!=0).decode('cp1251')
hsecs=[];hcur=None
for line in helmet_txt.splitlines():
    s=line.strip();m=re.match(r'\[([^\]]+)\]',s)
    if m:hcur=(m.group(1),s[m.end():].lstrip(':').strip(),[]);hsecs.append(hcur);continue
    if hcur and '=' in s:hcur[2].append(s)
def kv_from(body):
    o={}
    for l in body:
        if '=' in l:k,_,v=l.partition('=');o[k.strip()]=v.split(';')[0].strip()
    return o
HELMETS={n:kv_from(b)for n,_,b in hsecs if n!="helmet_base" and not n.startswith('sect_helm_')}
imm_sect={}
for n,_,b in hsecs:
    if n.startswith('sect_helm_') and 'immunities' in n:
        d=kv_from(b)
        imm_sect[n]=(d.get('burn_immunity'),d.get('chemical_burn_immunity'),d.get('explosion_immunity'),
        d.get('radiation_immunity'),d.get('fire_wound_immunity'),d.get('shock_immunity'),
        d.get('strike_immunity'),d.get('telepatic_immunity'),d.get('wound_immunity'))
def helmet_imm(id_):
    sect=HELMETS.get(id_,{}).get('immunities_sect')
    return imm_sect.get(sect) if sect else None
CLASS_TIER={"actor_helm_respirator":"Т1","actor_helm_helmet":"Т1","actor_helm_hardhat":"Т1",
"actor_helm_protective":"Т2","actor_helm_tactic":"Т2",
"actor_helm_battle":"Т3","actor_helm_battle_military":"Т3",
"actor_helm_battle_heavy":"Т4","actor_helm_battle_heavy_military":"Т4"}
hrows=[]
for id_,m in HELMETS.items():
    inv=m.get('inv_name') or m.get('inv_name_short')
    nn=(((OUTFITS_RU.get(inv)) or ITEMS_RU.get(inv)) if inv else "<нет названия>")
    tm=re.match(r'[Тт]\d',nn)
    tier=((tm.group() if tm else CLASS_TIER.get(m.get('bones_koeff_protection'),"?")).replace("Т","T"))
    if not tier:continue
    hrows.append((id_,m,nn,tier,helmet_imm(id_)))
htier={t:[] for t in TIER_ORDER}
for id_,m,nn,tier,imm in hrows:htier[tier].append((id_,m,nn,imm))
HL_COLS=["#", "Шлем", "Файл", "Заброневая травма", "Вес", "Утомляемость", *PROT.values(), *IMM.values(), "Броня головы", RESOURCE_LABEL, "Стоимость"]
prot_keys=list(PROT)
hlines=["## Шлемы (Helmets)", ""]
for t in TIER_ORDER:
    rows=sorted(htier[t],key=lambda r:r[1].get('cost') or 0)
    if not rows:continue
    hlines.append(f"## Шлемы — {t}")
    hlines.append("")
    hlines.append("| " + " | ".join(HL_COLS) + " |")
    hlines.append("|" + " | ".join(["--:"]*len(HL_COLS)) + " |")
    for i,(id_,m,nn,imm) in enumerate(rows,1):
        iv=imm or [None]*9
        prot=[fmt(m.get(k)) for k in prot_keys]
        immv=[fmt(iv[j]) for j in range(9)]
        _,h=torso_head(m.get('bones_koeff_protection'))
        c=fmt(m.get('cost')); rc=fmt(m.get('repair_compatibility'))
        line=f"| {i} | {nn} | `{id_}` | {fmt(m.get('hit_fraction_actor'))} | {fmt(m.get('inv_weight'))} | {fmt(m.get('power_loss_add'))} | " + " | ".join(prot) + " | " + " | ".join(immv) + f" | {h} | {fmt(imm_resource(id_, m))} | {c} |"
        hlines.append(line)
    hlines.append("")
w="\n".join(hlines)
open("OUTFIT.md","a").write(w+"\n")
print(f"  +helmets: {sum(len(v) for v in htier.values())} helmets (T1={len(htier['T1'])} T2={len(htier['T2'])} T3={len(htier['T3'])} T4={len(htier['T4'])})")
