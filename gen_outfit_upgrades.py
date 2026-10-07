# -*- coding: utf-8 -*-
import os, re
import xml.etree.ElementTree as ET
from collections import defaultdict

D = "gamedata/config/items/equipments/outfit_upgrades"
STR = "gamedata/config/text/rus/string_table_upgrades.xml"

PROPTITLE = {
    "prop_psy":         "\u041f\u0441\u0438\u0445\u0438\u043a\u0430",
    "prop_head":        "\u0413\u043e\u043b\u043e\u0432\u0430",
    "prop_hand":        "\u0420\u0443\u043a\u0438",
    "prop_legs":        "\u041d\u043e\u0433\u0438",
    "prop_belt":        "\u041f\u043e\u044f\u0441",
    "prop_back":        "\u0420\u0443\u043a\u0430\u043a",
    "prop_neck":        "\u0428\u0435\u044f",
    "prop_gloves":      "\u0420\u0430\u0437\u0433\u0440\u0443\u0437\u043a\u0430",
    "prop_boots":       "\u0411\u043e\u0442\u0438\u043d\u0433",
    "prop_mask":        "\u041c\u0430\u0441\u043a\u0430",
    "prop_headgear":    "\u0428\u0435\u043b\u043c",
    "prop_coat":        "\u041f\u043e\u043b\u043e",
    "prop_pants":       "\u0411\u0440\u0443\u043a\u0438",
    "prop_gasmask":     "\u0413\u0430\u0437\u043e\u043f\u0435\u0440\u0435\u0447\u044c",
    "prop_armor_1":     "\u0411\u0440\u043e\u043d\u044f \u0438 \u0443\u0434\u0430\u0440 (\u0431\u0430\u0437)",
    "prop_armor_2":     "\u0411\u0440\u043e\u043d\u044f \u0438 \u0443\u0434\u0430\u0440 (\u0441\u0440\u0435\u0434)",
    "prop_armor_3":     "\u0411\u0440\u043e\u043d\u044f \u0438 \u0443\u0434\u0430\u0440 (\u0442\u044fжёлая)",
    "prop_tonnage":     "\u0420\u0430\u0441\u043f\u0440\u0435\u0434\u0435\u043b\u0438\u0442\u0435\u043b\u044c\u043d\u044b\u0439 \u0436\u0438\u043b\u0435\u0442",
    "prop_electro":     "\u042d\u043b\u0435\u043a\u0442\u0440\u043e\u0441\u0442\u0430\u0442\u0438\u0447. \u043f\u0440\u043e\u0442\u0438\u0432\u043e\u0434. (\u0421\u043a\u0430\u0442)",
    "prop_chem":        "\u041c\u0438\u0445\u0438\u0447\u0435\u0441\u043a\u0430\u044f \u0437\u0430\u0449\u0438\u0442\u0430",
    "prop_damage":      "\u0417\u0430\u0449\u0438\u0442\u0430 \u043e\u0442 \u0443\u0434\u0430\u0440\u0430",
    "prop_durability":  "\u0423\u0441\u0442\u043e\u0439\u0447\u0438\u0432\u043e\u0441\u0442\u044c \u043a \u0438\u0437\u043d\u043e\u0441\u0443",
    "prop_explo":       "\u0412\u0437\u0440\u044b\u0432\u043e\u0443\u0441\u0442\u043e\u0439\u0447\u0438\u0432\u043e\u0441\u0442\u044c",
    "prop_power":       "\u0421\u043e\u043f\u0440\u043e\u0442\u0438\u0432\u043b. \u043f\u043e\u0442\u0435\u0440\u0435 \u044d\u043d\u0435\u0440\u0433\u0438\u0438",
    "prop_radio":       "\u0420\u0430\u0434\u0438\u0430\u0446\u0438\u043e\u043d\u043d\u0430\u044f \u0437\u0430\u0449\u0438\u0442\u0430",
    "prop_thermo":      "\u0422\u0435\u0440\u043c\u0438\u0447. \u0437\u0430\u0449\u0438\u0442\u0430 (\u043e\u0433\u043e\u043d\u044c)",
    "prop_wound":       "\u0423\u0441\u0442\u043e\u0439\u0447\u0438\u0432\u043e\u0441\u0442\u044c \u043a \u0440\u0430\u043d\u0430\u043c",
    "prop_restore_health": "\u0420\u0435\u0433\u0435\u043d\u0435\u0440\u0430\u0446\u0438\u044f \u0437\u0434\u043e\u0440\u043e\u0432\u044c\u044f",
    "prop_restore_bleeding": "\u0417\u0430\u0449\u0438\u0442\u0430 \u043e\u0442 \u043a\u0440\u043e\u0432\u043e\u0442\u0435\u0447\u0435\u043d\u0438\u044f",
    "prop_weightoutfit": "\u0412\u0435\u0441 \u043a\u043e\u043c\u043f\u043b\u0435\u043a\u0442\u0430",
}

def prop_title(p): return PROPTITLE.get(p, p)

def load_strings():
    raw = open(STR, "rb").read()
    root = ET.fromstring(raw.decode("cp1251"))
    s = {}
    for st in root.findall(".//string"):
        sid = st.get("id")
        te = st.find("text")
        if sid and te is not None:
            s[sid] = te.text or ""
    return s

def parse_elements():
    els = {}
    for fn in sorted(os.listdir(D)):
        if not (fn.startswith("o_") and fn.endswith("_up.ltx")):
            continue
        txt = open(os.path.join(D, fn), "rb").read().replace(b"\x00", b"").decode("utf-8", "replace")
        cur = None; parent = None; kv = {}
        for line in txt.splitlines():
            s = line.strip()
            m = re.match(r'\[([^\]]+)\](?::([^,]*))?$', s)
            if m:
                cur = m.group(1).strip()
                parent = (m.group(2) or "").strip().lstrip(",")
                kv = {}
                continue
            if "=" in s and cur:
                k, _, v = s.partition("=")
                v = v.split(";")[0].strip()
                kv[k.strip()] = v
            if cur and ELEM.match(cur) and parent == "up_base_outfit":
                els[cur] = kv
    return els

ROUND = {"first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5}

ELEM = re.compile(r'^up_(first|second|third|fourth|fifth)([a-z]+)_(.+)_outfit$')

def round_of(cur):
    m = ELEM.match(cur)
    return ROUND[m.group(1)] if m else 9

def scheme_round(v):
    return int(v["scheme_index"].split(",")[0])

SM = re.compile(r'^(up_)(\w+)(\w+)_outfit$')

def build():
    strings = load_strings()
    els = parse_elements()
    # outfit -> list of dicts, sorted by round then letter
    grouped = {}
    for cur, kv in els.items():
        m = ELEM.match(cur)
        grp, letter, outfit = m.group(1), m.group(2), m.group(3)
        sr = scheme_round(kv)
        props = [p.strip() for p in kv.get("property", "").split(",") if p.strip()]
        title = " + ".join(prop_title(p) for p in props)
        rows = []
        name_ref = kv.get("name", "")
        desc_ref = kv.get("description", "")
        nm = strings.get(name_ref, name_ref) if name_ref else "\u2014"
        dr = strings.get(desc_ref, desc_ref) if desc_ref else ""
        rows.append({
            "round": sr,
            "sr": sr,
            "grp": grp,
            "letter": letter,
            "key": grp + letter,
            "property": kv.get("property", ""),
            "title": title,
            "name": nm,
            "desc": dr,
            "effects": kv.get("effects", ""),
        })
        rows.sort(key=lambda r: (r["sr"], r["letter"]))
        grouped.setdefault(outfit, []).extend(rows)
    return strings, grouped

def mermaid(outfit, rows):
    out = [f"flowchart TD\n"]
    key_to_id = {r["key"]: f"u{r['round']}{r['key']}" for r in rows}
    for r in rows:
        idn = key_to_id[r["key"]]
        lbl = f"{r['title']}\\n{r['name']}"
        out.append(f'  {idn}[ "{lbl} " ]')
    grp_re = re.compile(r'(first|second|third|fourth|fifth)([a-z]+)')
    seen = set()
    for r in rows:
        eff = r["effects"].replace("up_gr_", "")
        gm = grp_re.match(eff)
        if gm and (r["grp"], r["letter"]) not in seen:
            tid = key_to_id.get(gm.group(1) + gm.group(2)[0])
            if tid is not None:
                out.append(f"  {key_to_id[r['key']]} --> {tid}")
                seen.add((r["grp"], r["letter"]))
    return "\n".join(out) + "\n"

def main():
    strings, grouped = build()
    lines = []
    lines.append("# \U0001F3C6 Комплекты брони: схемы улучшений (Outfit Upgrades)")
    lines.append("")
    lines.append("Элементы улучшения комплекта. Порядок применения задаётся `scheme_index` (круг/слот); ")
    lines.append("`effects` связывает элемент с следующим кругом. Умножитель и стоимость заданы в шаблонах ")
    lines.append("`up_sect_*` и могут отличаться от значений по умолчанию.")
    lines.append("")
    lines.append("| Комплект | Круг | Слот | Свойство | Название улучшения |")
    lines.append("|----------|------|------|----------|--------------------|")
    for outfit in sorted(grouped):
        for r in grouped[outfit]:
            lines.append(f"| {outfit} | {r['round']} | {r['letter']} | {r['title']} | {r['name']} |")
    lines.append("")
    lines.append("## Детальные схемы улучшений")
    lines.append("")
    for outfit in sorted(grouped):
        rows = grouped[outfit]
        lines.append(f"### {outfit}")
        lines.append("")
        lines.append(mermaid(outfit, rows))
        lines.append("")
    open("OUTFIT_UPGRADES.md", "w").write("\n".join(lines) + "\n")
    print(f"OUTFIT_UPGRADES.md: {len(grouped)} outfits, {sum(len(v) for v in grouped.values())} elements")

if __name__ == "__main__":
    main()
