# -*- coding: utf-8 -*-
"""Dados da campanha: Ato 3 (Copa dos Campeoes, caps. 10-13). Modulo PURO (so dados, sem imports).

story.py junta estes dicts/listas nos seus (story._extend) e e o unico ponto de import para o resto
do jogo. Mesmas regras e formatos de story.py (ver o docstring de la); ids nao podem repetir os de
outros modulos. Capitulos aqui levam "act" e entram depois dos do Ato 1, na ordem da lista.
"""

CHARACTERS = {}
TEAMS = {}
TOURNAMENTS = {}
SCENES = {}
REWARDS = {}
SIDES = {}
# Rascunhos ("em breve") ate os passos C10/C11. F PROVISORIO: a spec previa 74,4 -> 81,0, mas o Ato 2
# medido (C9, com skills) termina em 83,5; a curva aqui so continua a medida (84 -> 90,4) ate o C12
# calibrar o Ato 3. econ_tier 3 ate o C12 (a spec pede 5-6).
CHAPTERS = [
    {"id": "10", "act": "3", "title": "Capítulo 10", "subtitle": "Intercâmbio",
     "local": "Aeroporto e Dojo", "F_start": 84.0, "F_end": 85.5, "econ_tier": 3,
     "tier_done_on_close": 3, "reward": None, "nodes": [], "draft": True},
    {"id": "11", "act": "3", "title": "Capítulo 11", "subtitle": "A Fábrica",
     "local": "Fábrica da Limpex", "F_start": 86.0, "F_end": 87.0, "econ_tier": 3,
     "tier_done_on_close": 3, "reward": None, "nodes": [], "draft": True},
    {"id": "12", "act": "3", "title": "Capítulo 12", "subtitle": "Copa dos Campeões",
     "local": "Coliseu", "F_start": 87.2, "F_end": 88.8, "econ_tier": 3,
     "tier_done_on_close": 3, "reward": None, "nodes": [], "draft": True},
    {"id": "13", "act": "3", "title": "Capítulo 13", "subtitle": "O Chip Zero",
     "local": "Coliseu em apagão", "F_start": 89.0, "F_end": 90.4, "econ_tier": 3,
     "tier_done_on_close": 3, "reward": None, "nodes": [], "draft": True},
]
