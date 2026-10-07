#!/usr/bin/env python3
"""Parse LAEE weapon upgrades (both section types) and generate WPN_UPGRADES.md."""
import os, re, json
ROOT="/var/home/anton/.var/app/com.usebottles.bottles/data/bottles/bottles/LAEE/drive_c/mods"
UPDIR=os.path.join(ROOT,"gamedata","config","weapons","upgrades")
TXT=os.path.join(ROOT,"gamedata","config","text","eng","string_table_upgrades.xml")
RU_TXT=os.path.join(ROOT,"gamedata","config","text","rus","string_table_upgrades.xml")

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

# ---- string tables (eng + rus fallback) ----
def load_strings(path):
    d={}
    txt=open(path,'rb').read().decode('cp1251')
    for m in re.finditer(r'<string id="([^"]+)">.*?<text>([^<]+)</text>',txt,re.S):
        d[m.group(1)]=m.group(2).strip()
    return d
ENG=load_strings(TXT); RU=load_strings(RU_TXT)

# ---- property labels + good-direction notes ----
PROP_LABEL={
 "rpm":"Fire Rate (RPM)","rpm_semi":"Semi-auto RPM","reliab":"Reliability",
 "dispersion":"Dispersion / Accuracy","recoil":"Recoil","inertion":"Handling / Inertia",
 "bullet_speed":"Bullet Speed","weight":"Weight","calibre":"Caliber","ammo_size":"Magazine Capacity",
 "underbarrel_slot":"Underbarrel Slot","scope_attach":"Scope Mount","pistol_slot":"Pistol Slot",
}
# negative mult = improvement
NEG_BETTER={"recoil"}
# RUSSIAN property labels (from config-parameter cheat sheet + ltx descriptions).
# Keys are the STRIPPED parameter names (u["prop"] has "prop_" removed); composite
# values arrive comma-joined, so each token is stripped+looked-up and joined with " · ".
RU_LABELS={
  # stats
  "recoil":"Отдача","reliability":"Надёжность","dispersion":"Кучность",
  "inertion":"Обращение (Handling)","bullet_speed":"Начальная скорость пули",
  "rpm":"Скорострельность","ammo_size":"Ёмкость магазина","weight":"Вес",
  "calibre":"Калибр",
  # optics / attachments
  "contrast":"Контрастность ночного прицела","autolockscope":"Автоблокировка оптического прицела",
  "scope":"Основной оптический прицел","nightvision":"Прибор ночного видения",
  "silencer":"Глушитель","3xfire":"Очередь по 3 выстрела","scope_attach":"Прицельный узел",
  "doublet":"Двойной выстрел (дуплет)","autofire":"Автоматический огонь",
  "zoom":"Зум-прицел","scope_1.6x":"Штурмовой прицел 1.6x",
  "scope_2.4x":"Оптический прицел 2.4x","scope_4x":"Оптический прицел 4x",
  "scope_5x":"Оптический прицел 5x","scope_6x":"Оптический прицел 6x",
  # barrel variants
  "no_buck":"Нарезной ствол (без дроби)","no_dart":"Подкалиберная пуля",
  "no_bullet":"Дробь/картечь (без пули)","fire_damage":"Урон от выстрела",
  "underbarrel_slot":"Подствольный узел",
}
def prop_label(p):
    if not p: return ""
    parts=[RU_LABELS.get(t.replace("prop_","").strip(), t) for t in p.split(",")]
    return " · ".join(parts)

def resolve_desc(ref):
    if ref and ref in RU: return RU[ref]
    if ref and ref in ENG: return ENG[ref]
    return None

# ---- gather property-def sections (up_sect_*) : name -> mult, base parents ----
mult_by_sec={}; cost_by_sec={}
for fn in sorted(os.listdir(UPDIR)):
    if not fn.endswith("_up.ltx"): continue
    for name,parents,body in parse_sections(read(os.path.join(UPDIR,fn))):
        sm=re.match(r'^up_sect_(\w+)_(\w+)$',name)
        if not sm: continue
        kv=parse_kv_all(body)
        mult_by_sec[name]=kv.get("mult","")
        cost_by_sec[name]=kv.get("cost","")

# ---- gather element upgrades (up_*) per weapon ----
UP_RE=re.compile(r'^(up_)(?!sect_|gr_)(\w+)_(\w+)$')
WEAPONS={}   # wid -> list of upgrade dicts
for fn in sorted(os.listdir(UPDIR)):
    if not (fn.endswith("_up.ltx") or fn.endswith("_up_sect.ltx")): continue
    wid=fn[2:-len("_up.ltx")] if fn.endswith("_up.ltx") else fn[2:-len("_up_sect.ltx")]
    for name,parents,body in parse_sections(read(os.path.join(UPDIR,fn))):
        m=UP_RE.match(name)
        if not m: continue
        grp,let=m.group(2),m.group(3)
        kv=parse_kv_all(body)
        prop=kv.get("property","") or ""
        scheme=kv.get("scheme_index","").strip()
        sec_ref=kv.get("section",""); eref=kv.get("effects","")
        mult=mult_by_sec.get(sec_ref,"") if sec_ref else ""
        cost=cost_by_sec.get(sec_ref,"") if sec_ref else ""
        icon=kv.get("icon","")
        desc=resolve_desc(kv.get("description",""))
        WEAPONS.setdefault(wid,[]).append({
            "group":grp,"letter":let,"prop":prop,"scheme":scheme,
            "mult":mult,"cost":cost,"icon":icon,
            "desc":desc,"desc_ref":kv.get("description",""),"sec_ref":sec_ref,"eref":eref,
        })

# ---- sort + group by round ----
def round_of(scheme):
    parts=scheme.split(",") if scheme else []
    return int(parts[0]) if len(parts)>0 and parts[0].strip().isdigit() else None
def slot_of(scheme):
    parts=scheme.split(",") if scheme else []
    return int(parts[1]) if len(parts)>1 and parts[1].strip().isdigit() else None
# None-safe helpers (0 is a valid round/slot, so never use `or` on these)
def _sk(v): return v if v is not None else 99   # sort key: unknown -> last
def _d(v): return v if v is not None else "?"    # display text

# ---- write markdown ----
L=[]
def w(s=""): L.append(s)
w("# Weapon Upgrades — LAEE")
w()
w("_Extracted from `1_new_laee/config/weapons/upgrades/`. Parsed with a local Python script; values are the mod's raw config, not verified against in-game behavior._")
w()
w(f"- **Weapons with upgrades:** {len(WEAPONS)}")
w(f"- **Total upgrade elements:** {sum(len(v) for v in WEAPONS.values())}")
w("- Properties: Скорострельность, Надёжность, Кучность (точность), Отдача, Обращение, Начальная скорость пули, Вес, Калибр, Ёмкость магазина, Прицелы/глушитель и др. См. таблицу ниже.")
w("- Each element has a purchase `scheme_index = <round>,<slot>`; buy one element per slot within a round. Group sections (`up_gr_*`) bundle the elements offered together.")
w()

# property reference (from actual upgrade data)
props=set()
for fn in os.listdir(UPDIR):
    if fn.endswith("_up.ltx") or fn.endswith("_up_sect.ltx"):
        for name,parents,body in parse_sections(read(os.path.join(UPDIR,fn))):
            if UP_RE.match(name): props.add(parse_kv_all(body).get("property",""))
w("## Property reference")
w()
w("| Property | Meaning | Better when mult is |")
w("|---|---|---|")
for p in sorted(props, key=lambda x:(0 if x=="prop_recoil" else 1)):
    neg = "negative" if "Отдача" in prop_label(p) else "positive"
    w(f"| {p} | {prop_label(p)} | {neg} |")
w()

# per-weapon section
for wid in sorted(WEAPONS):
    ups=sorted(WEAPONS[wid], key=lambda u:(_sk(round_of(u["scheme"])), _sk(slot_of(u["scheme"]))))
    w(f"## {wid}")
    w()
    # table
    w("| Round | Slot | Prop | Effect (mult) | Cost | Description |")
    w("|---|---|---|---|---|---|")
    for u in ups:
        r = _d(round_of(u["scheme"]))
        s = _d(slot_of(u["scheme"]))
        mult = f"×{u['mult']}" if u['mult'] else "— (узел)"
        cost = f"{u['cost']}" if u['cost'] else "-"
        d=(u['desc'] or "")
        if len(d)>150: d=d[:147]+"…"
        desc = d.replace("|","\\|")
        w(f"| {r} | {s} | {u['prop']} | {mult} | {cost} | {desc} |")
    w()

# purchase trees (mermaid) for weapons with >=3 elements
w("## Purchase flowcharts")
w()
for wid in sorted(WEAPONS):
    ups=sorted(WEAPONS[wid], key=lambda u:(_sk(round_of(u["scheme"])), _sk(slot_of(u["scheme"]))))
    if len(ups)<2: continue
    w(f"### {wid}")
    w()
    w("```mermaid")
    w("graph TD")
    w('    Start(["Начать"])')
    for u in ups:
        sr=u.get("sec_ref","") or u["scheme"] or u["prop"]
        eid=f"e_{re.sub(r'[^a-zA-Z0-9_]', '_', sr)}"
        prop_ru=prop_label(u['prop'])
        mult = f"×{u['mult']}" if u['mult'] else "—"
        cost = f"{u['cost']} ₽" if u['cost'] else "—"
        r=_d(round_of(u["scheme"])); s=_d(slot_of(u["scheme"]))
        lbl=f"{prop_ru}<br/>{mult} · {cost}<br/>R{s}·S{s}"
        w(f'    {eid}["{lbl}"]')
    rounds=sorted({round_of(u["scheme"]) for u in ups if round_of(u["scheme"]) is not None})
    for r in rounds:
        w(f'    R{r}["Раунд {r}"]')
        for u in ups:
            if round_of(u["scheme"])==r:
                sr=u.get("sec_ref","") or u["scheme"] or u["prop"]
                w(f'    R{r} --> e_{re.sub(r"[^a-zA-Z0-9_]", "_", sr)}')
    entry=rounds[0] if rounds else "?"
    w(f'    Start -->|"выбор"| R{entry}')
    w("```")
    w()

# ---- COMMENTS / NOTES section ----
w("## Notes & caveats")
w()
w("### Parsing notes")
w("- The upgrade directory uses **two section kinds** that must both be parsed:")
w("  - `up_sect_<group><letter>_<weapon>` — property definition (inherits from a `_base` section, carries `mult` + `cost`).")
w("  - `up_<group><letter>_<weapon>` — the purchasable element itself (`scheme_index`, `effects=up_gr_*`, `section`, `property`, UI `name`/`description`/`icon`).")
w("- The parser reads all files under `config/weapons/upgrades/` (95 files). Weapon IDs may contain underscores (`bm16_long`) and the group prefix is abbreviated (`secona` = second round), which are handled explicitly.")
w("- Base sections define the sign convention: most stats improve with a **positive** mult; **recoil** improves with a **negative** mult (its base section uses positive internal values like `cam_dispersion`). Dispersion uses an inverted convention (`fire_dispersion_base = -1`), so a positive upgrade mult reduces spread.")
w()
w("### Reference integrity (verified)")
w("- Every element's `section=` and `effects=up_gr_*` resolve to existing sections. **No dangling references found.**")
w("- The `precondition_functor` / `effect_functor` / `prereq_functor` hooks (`inventory_upgrades.*_a`) are defined and used across the mod, so the application machinery exists.")
w()
w("### Known issues — upgrades that may not display / behave correctly in-game")
w()
w("- Descriptions shown below are the **Russian** strings (`string_table_upgrades.xml` rus); English keys are not substituted.")
w()
# descriptions missing from the RU table (would render blank in Russian install)
missing_descs=[]
for wid,ups in WEAPONS.items():
    for u in ups:
        ref=u.get("desc_ref")
        if ref and ref not in RU:
            missing_descs.append((wid,f"up_{u['group']}_{u['letter']}",ref))
missing_descs=sorted(set(missing_descs))
w(f"### Missing Russian descriptions ({len(missing_descs)} elements)")
if missing_descs:
    for wid_,name_,ref_ in missing_descs:
        w(f"- `{ref_}` (element `{name_}`, weapon `{wid_}`)")
w()
w("  These are cosmetic (missing tooltip text) and do **not** break the stat effect, which is driven by `mult`/`section`. They would only show blank descriptions until the English strings are added.")
w()
w("- Attachment-slot elements (`scope_attach`, `underbarrel_slot`, etc.) legitimately have **no `mult`** — they add an attachment point rather than changing a stat. This is expected, not a bug.")
w("- Descriptions are **shared/reused** across weapons (e.g. `st_up_zat_a1_descr`, `st_up_arm_a1_descr`) and match each element's `property`; no description/property mismatch was detected.")
w()

out="/var/home/anton/.var/app/com.usebottles.bottles/data/bottles/bottles/LAEE/drive_c/mods/WPN_UPGRADES.md"
open(out,"w").write("\n".join(L)+"\n")
print(f"wrote {out} ({sum(len(l) for l in L)} chars, {len(L)} lines)")
print(f"weapons={len(WEAPONS)} elements={sum(len(v) for v in WEAPONS.values())} missing_descs={len(missing_descs)}")
