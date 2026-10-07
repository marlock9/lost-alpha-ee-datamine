#!/usr/bin/env python3
"""Generate AMMO.md from ammo.tsv (source of truth for abs damage + nice names).

ammo.tsv columns: type_id, nice_name, damage, k_hit, k_ap,
k_pierce, k_impulse, k_speed, k_disp, k_dist, k_air_resistance, buck_shot, impair,
cost, weight, box.  nice_name is already resolved from inv_name via the string table by
parse_weapons.py; gen_ammo.py just renders the table.
"""
import os

ROOT="/var/home/anton/.var/app/com.usebottles.bottles/data/bottles/bottles/LAEE/drive_c/mods"
TSV=os.path.join(ROOT,"ammo.tsv")

def num(v):
    return v if v not in ("",) else "-"

def w(v):
    v = str(v).strip()
    return "-" if not v else ("0" + v if v.startswith(".") else v)   # weight: ".34" -> "0.34", leave integer-part values as-is

rows=[l.rstrip("\n").split("\t") for l in open(TSV, encoding="utf-8")]

out=["# AMMO\n\n",
     "\n",
       "All ammunition types in the mod with their crucial properties. Урон = abs damage (hit_power × k_hit × buck × 100), already including the pellet count.\n",
     "\n",
     "## Property meanings (from ammo.ltx comments)\n\n",
     "| Property | Meaning |\n",
     "|---|---|\n",
      "| Убойность | коэффициент урона, умножающий базовый урон оружия |\n",
      "| Бронебойность | пробитие костюмов и экзоскелетов |\n",
      "| Пробиваемость | пробитие стен, дверей и укрытий |\n",
      "| Импульс | физический эффект попадания (рагдолл врага) |\n",
      "| Начальная скорость пули | влияет на настильность (падение скорости с дистанцией) |\n",
      "| Кучность | коэффициент разброса; чем меньше, тем точнее |\n",
      "| Дальность | эффективная дальность полёта пули |\n",
      "| Сопротивление воздуха | торможение пули в полёте |\n",
      "| Дробь | число дробинок/картечин в выстреле (дробовые патроны) |\n",
      "| Износ оружия | множитель износа ствола при стрельбе этим патроном |\n",
      "| Цена | стоимость пачки патронов у торговцев |\n",
      "| Вес | чистый вес одной пачки патронов |\n",
      "| В пачке | число патронов в коробке |\n",
     "\n",
     "## Ammo table\n\n",
      "| Type| Name| Урон| Бронебойность| Пробиваемость| Импульс| Начальная скорость| Кучность| Дальность| Сопротивление воздуха| Дробь| Износ оружия| Цена| Вес| В пачке |\n",
     "| " + " | ".join(["----------"]*15) + " |\n",
]

for r in rows:
    tid, nice, dmg, k_hit, k_ap, k_pierce, k_impulse, k_speed, k_disp, k_dist, k_air, buck, impair, cost, weight, box = r
    out.append(
        f"| {tid}| {nice}| {num(dmg)}| {num(k_ap)}| {num(k_pierce)}| {num(k_impulse)}| "
        f"{num(k_speed)}| {num(k_disp)}| {num(k_dist)}| {num(k_air)}| {num(buck)}| {num(impair)}| {num(cost)}| {w(weight)}| {num(box)} |\n"
    )

out.append("\n")
open(os.path.join(ROOT,"AMMO.md"),"w",encoding="utf-8").write("".join(out))
print(f"wrote AMMO.md with {len(rows)} ammo types")
