# cond_map.py
# Infoportion (condition) names for the LAEE mod. SINGLE source of truth for the
# Russian meaning of every quest/task/artefact completion flag that appears in a
# stash drop condition or a trader supply/discount condition.
#   config/misc/treasure_manager.ltx        (stash drop conditions)
#   config/traders/*.ltx                      (supply stages + discount conditions)
# Nothing else is consulted here — add a new entry the first time a flag is found.
# Unknown flags simply return None from describe(); do not invent meanings.

INFOPORTIONS = {
    # ---- stash drop conditions (treasure_manager.ltx) ----
    'bas_switcher_off':            'Отключена установка в X-7',
    'deactivate_radar_done':       'Отключена установка в X-10',
    'has_freeplay_info':           'Фриплей',
    'yan_good_helmet_start':       'Получен настроенный пси-шлем',
    'bar_informer_info_e_2a':      'Получена наводка на Тайник веры у Осведомителя',
    'country_major_first_quest_done_af': 'Майору Грибоедову возвращены Пурпурные бусы',
    'mil_task_mad_guy_done':          'Выполнен квест сумасшедшего сталкера (Саша Голов)',
    'yan_scientist_artefact_have':     'Мегакристалл снят с трупа Бешеного Пса',

    # ---- trader supply-stage conditions (config/traders/*.ltx) ----
    'esc_rescue_fox_done':         'Лис спасён',
    'agr_gunslinger_flash_have':   'Найдена флешка Стрелка',
    'dar_barman_has_all_x18_docs': 'Все документы из X-18 доставлены Бармену',
    'yan_scientist_package_done':  'Пройдены все квесты учёных на Янтаре',
    'x16_main_power_disabled':     'Отключена установка в X-16',
    'bar_forg_rg6_given':          'Пройдены все квесты Долга',

    # ---- trader discount conditions (config/traders/*.ltx) ----
    'old_farm_bandit_hit':         'Игрок атаковал базу бандитов первым',
    'actor_in_dolg':               'Игрок стоит в "Долге"',
    'actor_in_freedom':            'Игрок состоит в "Свободе"',
    'out_lukash_task_complete':    'Выполнены квесты Лукаша',
    'forg_fuel_task_complete':     'Выполнено задание на подрыв бочек в Тёмной Лощине',
    'forg_mill_gauss_box_done':    'Выполнено задание на доставку Гаусс-бокса',
    'bar_last_job_done':           'Выполнено последнее задание для "Долга"',
    'out_barman_x7_switcher_talked': 'Бороде сообщено об отключении X-7',
}

def describe(infoportion):
    """infoportion id -> Russian meaning, or None if not yet documented.
       Single source of truth for condition names."""
    return INFOPORTIONS.get(infoportion)
