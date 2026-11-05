# -*- coding: utf-8 -*-
"""Dados da campanha: Ato 2 (Superliga Limpex, caps. 6-9). Modulo PURO (so dados, sem imports).

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
# Cap. 6 PROVISORIO (C2): so o epilogo do Ato 1 como no "end" (mesmo fim de campanha de hoje). O C6
# troca por [("scene", "e1_epilogo"), cenas/torneio do cap. 6, ("chapter_end", "6")] e define F/econ;
# o no 0 continua sendo o epilogo, entao saves migrados (ch "6", node 0) seguem validos.
CHAPTERS = [
    {"id": "6", "act": "2", "title": "Capítulo 6", "subtitle": "Taça de Acesso",
     "local": "Ginásio Limpex Park", "F_start": 65.8, "F_end": 65.8, "econ_tier": 3,
     "tier_done_on_close": 3, "reward": None,
     "nodes": [("end", "e1_epilogo")]},
]
