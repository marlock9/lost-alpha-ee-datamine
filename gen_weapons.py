#!/usr/bin/env python3
"""Generate WEAPONS.md from weapons.tsv, grouped by tier.

Columns: nice Russian weapon name + tech .ltx filename + stats (Russian headers).
"""
import os
import math
import re

ROOT="/var/home/anton/.var/app/com.usebottles.bottles/data/bottles/bottles/LAEE/drive_c/mods"
GAMEDATA=os.path.join(ROOT,"gamedata")
TSV=os.path.join(ROOT,"weapons.tsv")
RU_WEAPONS=os.path.join(GAMEDATA,"config/text/rus/string_table_enc_weapons.xml")

def load_strings(path):
    d={}
    txt=open(path,'rb').read().decode('cp1251')
    for m in re.finditer(r'<string id="([^"]+)">.*?<text>([^<]+)</text>',txt,re.S):
        d[m.group(1)]=m.group(2).strip()
    return d

def num(v):
    return v if v not in ("",) else "-"

def ammo_list(a):
    names=[x for x in a.split(";") if x]   # all_nice stores variants joined by ;
    if not names: return "special"
    return "; ".join(names)

rows=[l.rstrip("\n").split("\t") for l in open(TSV)]
NAMES=load_strings(RU_WEAPONS)

# ammo.tsv: section_id -> (k_disp=col9, buck=col12). Used for Точность (accuracy %).
AMMO={}
for l in open(os.path.join(ROOT,"ammo.tsv")):
    p=l.rstrip("\n").split("\t")
    AMMO[p[0]]=(float(p[8]), float(p[11]))

def tochnost(fdb, sec):
    """Точность (accuracy %). coef = k_disp/(1+sqrt(buck-1)), buck clamped to >=1; normalize to [1,100]."""
    k,b=AMMO[sec]; b=max(b,1.0); coef=k/(1+math.sqrt(b-1)); v=(1.3-math.atan(fdb*coef*2))*100
    return round(max(1.0,min(100.0,v)),1)

 # Оружие | Файл | Урон (коэф.) | Абс. урон | Скорострельность | Урон в секунду | Удобность | Отдача | Разброс | Точность | Ёмкость магазина | Патрон
header=(
      "| Оружие | Файл | Множ. урона | Урон | Скорострельность | Урон в секунду | Удобность | Отдача | Точность | Ёмкость магазина | Патрон | Ресурс | Стоимость |\n"
     "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |\n"
)

tiers={"Т1": [], "Т2": [], "Т3": [], "Т4": []}
for r in rows:
    tiers[r[0].upper()].append(r)

out=["# WEAPONS.md\n\n",
     "> Статистика каждого оружия считана напрямую из файлов конфигурации игры (gamedata ltx), без слияния модов; таблица разбита по типам оружия (Т1–Т4).\n\n",
     "> **Множ. урона** = hit_power; пустое значение = дефолт 1.0.\n\n",
     "> **Урон** — `hit_power × ammo_base_damage` на выстрел; base = k_hit первого (стандартного) патрона калибра ×100.\n\n",
     "> **Разброс** — радиус рассеивания, а не процент; у точных оружий он меньше.\n\n",
     "> **Точность** (в %) = `normalize((1.3 − atan(Разброс × coef × 2)) × 100)`, clamped к [1,100]; coef = k_disp стандартного патрона / (1 + √(k−1)), k ≥1 — число картечи в патроне.\n\n",
     "> **Урон в секунду** = Урон × RPM ÷ 60; при малом магазине (<1 сек до пустых на полной скорости) ограничение — Урон × ёмкость магазина.\n\n",
     "> **Удобность** = normalize(ctrlInertPart×15 + pdmPart×40 + zoomInertPart×30), clamped к [1,100]; ctrlInertPart=1/control_inertion_factor, pdmPart=(1−PDM_disp_base)/3+1, zoomInertPart=1.5/zoom_inertion_factor (если ключа нет — берётся дефолт weapon_base).\n\n",
     "> **Отдача** = normalize(35 × cam_dispersion / cam_relax_speed^0.4), clamped к [1,100]; cam_dispersion = zoom_cam_dispersion при наличии, иначе cam_dispersion; cam_relax_speed через наследование секций.\n",
     "\n"]

for tname, items in tiers.items():
    out.append(f"## Tier {tname}\n\n")
    out.append(header)
    for r in sorted(items, key=lambda x: x[1]):
        tier, fn, key, parents, hp, rpm, disp, mag, ammo, abs_dmg, all_nice, comf, rec, resource, cost = r
        nice = NAMES.get(key, key)
        d = num("-") if not abs_dmg else num(abs_dmg)
        hp_disp = "-" if hp in ("", "1.0") else num(hp)
        rpm_disp = num("-") if not rpm else num(rpm)
        rpm_f = float(rpm) if rpm else 0.0
        mag_f = float(mag) if mag else 0.0
        try: cf=float(comf)
        except ValueError: cf=0.0
        comf_disp = str(int(cf)) if cf == int(cf) else str(cf)
        try: rec_f=float(rec)
        except ValueError: rec_f=None
        rec_disp = str(round(rec_f,1)) if rec_f is not None else "-"
        res_disp = "-" if not resource or str(resource).strip() == "0" else str(resource)
        cost_disp = "-" if not cost else str(cost).strip()
        sec = ammo.split(";")[0].strip()   # standard (first) ammo section id
        acc = tochnost(float(disp), sec) if disp not in ("", "-") else "-"
        # reload-limited: whole magazine empties in <1s at rated rpm, so a ≥1s reload caps the sustainable rate at ~mag_size rounds/sec
        # устойчивая скорострельность = min(цикл, перезагрузка); реальный магазин даёт ≥1 выстрел/сек, поэтому ДПС не ниже урона одного выстрела (ножи: магазин 0 → "-" по правилу для нулей)
        rate = min(rpm_f / 60, mag_f)
        if mag_f >= 1 and rate < 1:
            rate = 1
        dps = str(round(float(abs_dmg) * rate))
        dps = "-" if dps == "0" else dps
        mag_disp = "-" if str(mag).strip() == "0" else num(mag)
        out.append(
            f"| {nice} | `{fn}` | {hp_disp} | {d} | {rpm_disp} | {dps} | {comf_disp} | {rec_disp} | {acc} | {mag_disp} | {ammo_list(all_nice)} | {res_disp} | {cost_disp} |\n"
        )
    out.append("\n")

open("WEAPONS.md", "w", encoding="utf-8").write("".join(out))
print(f"wrote WEAPONS.md with {len(rows)} weapons")
