#!/usr/bin/env python3
"""Extract weapon + ammo stats from merged LAEE gamedata (single tree).

Resolution via an LTX section hierarchy, NOT grep and NOT the `class` property:
  * Only files listed by `#include` in weapons.ltx are scanned (drops stale/flat duplicates).
  * Section header carries parents after `]:`, e.g. [wpn_ak74]:weapon_base,weapon_5.45x39,weapon_gp25
    A trailing `\t;description` comment is stripped before splitting.
  * Header parents are OTHER SECTIONS (not classes). Follow the full SECTION chain transitively:
    wpn_ak74_m1 -> wpn_ak74 -> weapon_5.45x39 -> ammo_class -> [ammo_5.45x39_fmj, ...].
  * Caliber bases are real sections (weapon_<caliber>) defined in gamedata/config/weapons/ammo/a_*.ltx;
    each ammo type carries its own k_hit/buck_shot. A section may also declare its own `ammo_class`
    field in the body (shotguns/grenade launchers).

Sections: ammo_ (real ammo), weapon_/wpn_ (bases + weapons) and anything else.
"""
import os, re
import math

ROOT = "/var/home/anton/.var/app/com.usebottles.bottles/data/bottles/bottles/LAEE/drive_c/mods"
GAMEDATA = os.path.join(ROOT, "gamedata")

def read(path):
    with open(path, "rb") as fh: return fh.read().replace(b"\x00", b"").decode("cp1251", "replace")

def parse_sections(txt):
    out=[]; i=0; lines=txt.split("\n")
    while i < len(lines):
        m=re.match(r"\s*\[([^\]]+)\](?::(.*))?", lines[i])
        if m:
            inh=(m.group(2) or "").strip()
            inh=re.sub(r"\s*;.*$", "", inh).split("\t")[0].strip()  # drop inline `\t;description`
            j=i+1; body=[]
            while j<len(lines) and not re.match(r"\s*\[", lines[j]):
                body.append(lines[j]); j+=1
            out.append((m.group(1), inh, "\n".join(body)))
            i=j
        else: i+=1
    return out

def parse_kv(b):
    d={}
    for line in b.split("\n"):
        line=re.sub(r"\s*;.*$", "", line)   # strip inline ltx `;comment` (also when no space precedes it)
        m=re.match(r"\s*(\w[\w\-\.]*)\s*=\s*(.*)$", line)
        if m:
            v=m.group(2).strip()
            if v != "": d[m.group(1)] = v    # skip empty-valued props (they must not swallow the next line)
    return d

# ---- class loader: parse every ltx reachable from weapons.ltx via #include (transitive closure) ----
# This follows the mod's real load graph, so caliber bases (weapon_<cal>) and ammo types
# defined in a_*.ltx (reached through ammo\ammo.ltx) are loaded, while standalone w_ files
# not referenced by any include (e.g. corrupted duplicate w_saiga êîï.ltx) are dropped.
def load_classes():
    base=os.path.join(GAMEDATA,"config","weapons")
    included=set()  # normalized paths reachable from weapons.ltx (windows includes are case-agnostic: T1\ vs t1/)
    def norm(p):
        rel=os.path.relpath(p,base).replace("\\","/").lower()   # preserve root case, fold tier/file case
        return os.path.normpath(os.path.join(base,rel))
    def walk(rel, d):
        f=norm(os.path.join(d,rel))
        if f in included: return
        included.add(f)
        try: txt=read(f)
        except FileNotFoundError: return
        for line in txt.splitlines():
            m=re.search(r'#include\s+"([^"]+)"',line)
            if m: walk(m.group(1), os.path.dirname(f))
    walk("weapons.ltx", base)
    sections={}
    def ingest(f, fn):
        for sid,inh,body in parse_sections(read(f)):
            kv=parse_kv(body)
            if not (sid.startswith("wpn_") or sid.startswith("weapon_") or sid.startswith("ammo_") or sid.endswith("_base") or sid in ("default_weapon_params","identity_immunities")): continue
            sections[sid]={"parents":[p.strip() for p in inh.split(",") if p.strip()],
                           "ammo_class":kv.get("ammo_class","") or "",
                           "inv_name":kv.get("inv_name"),"file":fn,"body":kv}
    for np in sorted(included):
        ingest(np, os.path.basename(np))
    return sections

# ---- resolve ammo ids transitively through the weapon_ inheritance chain ----
# Effective caliber = ammo_class of the SHALLOWEST section in the transitive parent chain that
# defines it: the weapon's own body first, then its header parents breadth-first (left-to-right).
# A variant's own caliber override parent (e.g. weapon_5.45x39) therefore REPLACES a deeper
# inherited one (base wpn_groza -> weapon_9x39); the winning section supplies ALL of its ammo types.
def ammo_ids(sections, sid):
    winner={}   # ammo_section_id -> source section id (shallowest definer wins entirely)
    def emit(cur):
        nonlocal done
        val=(sections.get(cur) or {}).get("body",{}).get("ammo_class")
        if val and val.strip():
            for x in val.split(","):
                x=x.strip()
                if x and not x.startswith("weapon_"): winner[x]=cur
            done=True
    queue=[sid]; i=0; done=False
    while i<len(queue) and not done:
        cur=queue[i]; i+=1
        p=sections.get(cur)
        if not p: continue
        emit(cur)
        for par in p["parents"]:
            if par not in winner: queue.append(par)
    return list(winner.keys())

def cell(x): return "" if x is None else str(x)

# ---- ergonomics / "Удобность" (GetHandling from ui_wpn_params.script): ctrlInertPart*15 + pdmPart*40 + zoomInertPart*30, then normalize to [1,100] ----
def _f(v, dflt):
    try: return float(str(v).strip().rstrip("fF"))
    except (ValueError, AttributeError): return dflt

def comf(sections, sid):
    ci = resolve(sections, sid, "control_inertion_factor") or "1.0"
    pdm = resolve(sections, sid, "PDM_disp_base") or "1"
    zf = resolve(sections, sid, "zoom_inertion_factor") or "1.5"
    ci_f=_f(ci,1.0); pdm_f=_f(pdm,1.0); zf_f=_f(zf,1.5)
    raw = (1/ci_f)*15 + ((1-pdm_f)/3+1)*40 + (1.5/zf_f)*30
    if raw > 100: raw = 100
    elif raw < 1: raw = 1
    return round(raw, 1)

# ---- Отдача (recoil) from GetRecoil in ui_wpn_params.script: normalize(35 * cam_dispersion / cam_relax_speed^0.4), clamped [1,100]; cam_dispersion = zoom_cam_dispersion when present (r_float_fallback) else cam_dispersion, both read on the resolved section; cam_relax_speed resolved through the section inheritance chain ----
def _ff(v):
    try: return float(str(v).strip().rstrip("fF"))
    except (ValueError,AttributeError): return None
def weapon_recoil(sections, sid):
    zoom=_ff(resolve(sections, sid, "zoom_cam_dispersion"))
    cd=zoom if zoom is not None else _ff(resolve(sections, sid, "cam_dispersion"))
    cr=_ff(resolve(sections, sid, "cam_relax_speed"))
    if cd is None or cr is None: return None
    val=35*cd/cr**0.4
    return max(1.0,min(100.0,val))

# ---- ammo nice name for WEAPONS.md: use the game's inv_name_short config key, fall back to full ----
def ammo_nice(sections, d, a):
    p=sections.get(a) or {}
    body=p.get("body") or {}
    ins=body.get("inv_name_short")
    if ins and ins in d: return d[ins]
    inv=p.get("inv_name") or a
    return d.get(inv, inv)

# ---- resolution (lazy, per property): check the weapon's own section first (primary then its fallbacks); only if all are absent walk up the inheritance tree; weapon_base is the ultimate default source ----
_FALLBACKS={"rpm":("rpm_semi",)}
def resolve(sections, sid, prop):
    body=(sections.get(sid) or {}).get("body",{})
    for v in (prop,*_FALLBACKS.get(prop,())):
        val=body.get(v)
        if val and str(val).strip(): return str(val).strip()
    seen=set()
    def rec(cur):
        if cur in seen: return None
        seen.add(cur)
        p=sections.get(cur)
        if not p: return None
        for v in (prop,*_FALLBACKS.get(prop,())):
            val=p["body"].get(v)
            if val and str(val).strip(): return str(val).strip()
        for par in p["parents"]:
            rv=rec(par)
            if rv is not None: return rv
        return None
    r=rec(sid)
    if r is not None: return r
    wb=(sections.get("weapon_base") or {}).get("body",{})
    for v in (prop,*_FALLBACKS.get(prop,())):
        val=wb.get(v)
        if val and str(val).strip(): return str(val).strip()
    return None

def load_xml_names(path):
    try: txt=read(path)
    except FileNotFoundError: return {}
    d={}
    for m in re.finditer(r'<string id="([^"]+)">.*?<text>([^<]+)</text>', txt, re.S):
        d[m.group(1)]=m.group(2).strip()
    return d

def parse_ammo(sections, d):
    rows=[]
    for sid,p in sections.items():
        if not (sid.startswith("ammo_") and sid!="ammo_base"): continue
        std=p["inv_name"]
        if not std: continue
        nice=d.get(std, std)
        kh=resolve(sections, sid, "k_hit"); bs=resolve(sections, sid, "buck_shot")
        try: bshot=float(bs) if (bs and float(bs)!=0) else 0.0
        except ValueError: bshot=0.0
        hp_n=float(resolve(sections, sid, "hit_power") or "1")
        kh_f=float(kh) if kh else None
        dmg=round(hp_n*kh_f*bshot*100) if kh_f is not None else ""
        k_ap=resolve(sections, sid, "k_ap"); k_pierce=resolve(sections, sid, "k_pierce")
        k_impulse=resolve(sections, sid, "k_impulse"); k_speed=resolve(sections, sid, "k_speed")
        k_disp=resolve(sections, sid, "k_disp"); k_dist=resolve(sections, sid, "k_dist")
        k_air_resistance=resolve(sections, sid, "k_air_resistance") or "0"   # non-bullet rounds (flares/grenades) have no air drag
        impair=resolve(sections, sid, "impair"); inv_weight=resolve(sections, sid, "inv_weight")
        box_size=resolve(sections, sid, "box_size")
        cost=p["body"].get("cost")
        rows.append((sid,nice,dmg,kh,k_ap,k_pierce,k_impulse,k_speed,k_disp,k_dist,k_air_resistance,bs,impair,cost,inv_weight,box_size))
    return rows

def parse_weapons(sections, d):
    seen={}
    _cnt=0
    for sid,p in sections.items():
        if not (sid.startswith("wpn_") and sid!="weapon_base"): continue
        inv=p["inv_name"]
        if not inv: continue
        ids=ammo_ids(sections, sid)
        std,all_a=(ids[0],",".join(ids)) if ids else ("","")
        kh=resolve(sections, std, "k_hit")
        hp=resolve(sections, sid, "hit_power"); bs=resolve(sections, std, "buck_shot")
        abs_dmg=""
        if ids and kh is not None:
            hp_n=float(hp) if hp else 1.0
            bs_f=float(bs) if (bs and float(bs)!=0) else 1.0
            abs_dmg=round(hp_n*float(kh)*bs_f*100)
        rn=d.get(inv,inv); m=re.search(r"(\u0422\d)",rn)
        tier=("Т"+m.group(1)[1:]) if m else None
        _cnt+=1
        if not tier: continue
        parents=" ".join(p["parents"]).replace("\r","").replace("\n"," ").replace("\t"," ")
        all_nice=";".join(ammo_nice(sections, d, a) for a in ids)
        rec=weapon_recoil(sections, sid)
        # Ресурс (durability bar): floor(shotDec / ammo_impair); shotDec = condition_queue_shot_dec for auto burst (-1 fire mode), else condition_shot_dec; guard on condition_shot_dec existing
        sd=resolve(sections, sid, "condition_shot_dec")
        resource=None
        if sd:
            fm=resolve(sections, sid, "fire_modes") or ""
            firemodes=[x.strip() for x in fm.split(",") if x.strip()]
            sd_key="condition_queue_shot_dec" if (firemodes and firemodes[-1]=="-1") else "condition_shot_dec"
            val=resolve(sections, sid, sd_key) or sd
            impair=resolve(sections, std, "impair")
            try: impair_f=float(impair) if impair else 1.0
            except ValueError: impair_f=1.0
            resource=math.floor(float(val)/impair_f)
        seen[inv]=[tier,p["file"],inv,parents,hp,resolve(sections,sid,"rpm"),resolve(sections,sid,"fire_dispersion_base"),resolve(sections,sid,"ammo_mag_size"),std,abs_dmg,all_nice,comf(sections,sid),rec,resource,resolve(sections,sid,"cost")]
    return seen

if __name__=="__main__":
    d_w=load_xml_names(os.path.join(GAMEDATA,"config","text","rus","string_table_enc_weapons.xml"))
    d_a=load_xml_names(os.path.join(GAMEDATA,"config","text","rus","string_table_enc_ammo.xml"))
    d={**d_w, **d_a}
    sections=load_classes()
    ammo_rows=parse_ammo(sections, d)
    with open(os.path.join(ROOT,"ammo.tsv"),"w",encoding="utf-8") as fh:
        header=["type_id","nice_name","damage","k_hit","k_ap","k_pierce","k_impulse","k_speed","k_disp","k_dist","k_air_resistance","buck_shot","impair","cost","weight","box"]
        for r in ammo_rows: fh.write("\t".join(cell(x) for x in r)+"\n")
    print(f"ammo types: {len(ammo_rows)}")
    weapons=parse_weapons(sections, d)
    with open(os.path.join(ROOT,"weapons.tsv"),"w",encoding="utf-8") as fh:
        header=["tier","file","name","parents","hit_power","rpm","disp","mag","std_ammo","all_ammo","all_nice","comf","recoil","resource","cost"]
        for r in sorted(weapons.values(),key=lambda x:(x[0],x[1])): fh.write("\t".join(cell(x) for x in r)+"\n")
    empties=[r for r in weapons.values() if not r[8]]
    print(f"unique weapons: {len(weapons)}  empties(no ammo): {len(empties)}")
