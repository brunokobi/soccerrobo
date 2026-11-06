# -*- coding: utf-8 -*-
"""Dados da campanha: Ato 3 (Copa dos Campeoes, caps. 10-13). Modulo PURO (so dados, sem imports).

C10: cap. 10 (Intercambio, copa) e cap. 11 (A Fabrica, serie em duas versoes pela escolha B2; escolha B4)
e o X-Omega. C11: cap. 12 (Copa dos Campeoes, copa com quartas), cap. 13 (O Chip Zero, serie final) e
os 3 finais (ENDINGS; o secreto exige as 4 fitas do Vo, missoes do C13). Os ovr/F do Ato 3 sao PROVISORIOS (continuam a curva medida do Ato 2) ate o C12 calibrar.

story.py junta estes dicts/listas nos seus (story._extend) e e o unico ponto de import para o resto
do jogo. Mesmas regras e formatos de story.py (ver o docstring de la); ids nao podem repetir os de
outros modulos. Capitulos aqui levam "act" e entram depois dos do Ato 1, na ordem da lista.
"""

# --- elenco novo do Ato 3 (spec secao 2) ---------------------------------------------------------
CHARACTERS = {
    # Chip Zero: so voz e LED vermelho (variante de portraits.draw_robot: sem chinelo, LED fixo)
    "xomega": {"name": "X-ÔMEGA", "color": (255, 60, 70), "skin": (60, 60, 70), "hair": ("none", (0, 0, 0)),
               "acc": [], "outfit": ("robo", (40, 40, 48)), "led": (255, 40, 50)},
}

_CH5 = ["Goleiro", "Tanque", "Disco", "Orbital", "Velocista"]

# --- times (ovr PROVISORIOS ate a calibracao do Ato 3 no C12) ------------------------------------
TEAMS = {
    # ---- Cap. 10 (Intercambio)
    "sakura_rb": {"name": "Sakura Reboot", "color": (255, 170, 190), "ovr": 68,
                  "names": ["Mochi 2", "Hana 2", "Neko 2", "Ramen 2", "Origami 2"],
                  "chassis": list(_CH5), "paint": (255, 180, 200), "perfect": False},
    "staub_pro": {"name": "Staubsauger Pro", "color": (200, 170, 60), "ovr": 69,
                  "names": ["Wurst", "Brezel", "Kuckuck", "Pünktlich", "Zeppelin"],
                  "chassis": list(_CH5), "paint": (210, 180, 70), "perfect": False},
    "aspir_noirs": {"name": "Les Aspirateurs Noirs", "color": (60, 70, 120), "ovr": 69,
                    "names": ["Baguette", "Croissant", "Brie", "Béret", "Moustache"],
                    "chassis": list(_CH5), "paint": (40, 45, 70), "perfect": False},
    "nipoteuta": {"name": "Seleção Nipo-Teuta", "color": (255, 120, 160), "ovr": 72,
                  "names": ["Katana", "Bonsai", "Kuckuck", "Pünktlich", "Haiku"],
                  "chassis": list(_CH5), "paint": (245, 245, 250), "perfect": False},
    "mundos": {"name": "Time dos Mundos", "color": (120, 220, 120), "ovr": 76,
               "names": ["Tex", "Mochi", "Wurst", "Brie", "Katana"],
               "chassis": list(_CH5), "paint": (130, 225, 130), "perfect": False},
    # ---- Cap. 11 (A Fabrica): versao corp (renova_limpex) e rebel (independente), mesmos ovr
    "linha": {"name": "Linha de Montagem", "color": (200, 210, 225), "ovr": 71,
              "names": ["LM-01", "LM-02", "LM-03", "LM-04", "LM-05"],
              "chassis": list(_CH5), "paint": (225, 232, 240), "perfect": False},
    "qualidade": {"name": "Controle de Qualidade", "color": (120, 230, 255), "ovr": 73,
                  "names": ["CQ-01", "CQ-02", "CQ-03", "CQ-04", "CQ-05"],
                  "chassis": list(_CH5), "paint": (235, 250, 255), "perfect": True},
    "gerente2": {"name": "Gerente Mk II", "color": (220, 60, 120), "ovr": 77,
                 "names": ["GR-01", "GR-02", "GR-03", "GR-04", "GR-05"],
                 "chassis": list(_CH5), "paint": (240, 240, 245), "perfect": True},
    "sucateiros": {"name": "Sucateiros Elite", "color": (160, 120, 80), "ovr": 71,
                   "names": ["Ferrugem", "Parafuso", "Sucatão", "Gambi", "Remendo"],
                   "chassis": list(_CH5), "paint": (165, 125, 85), "perfect": False},
    "contrabando": {"name": "Contrabando Mk II", "color": (90, 90, 100), "ovr": 73,
                    "names": ["Caixote", "Lona", "Pé-de-cabra", "Lanterna", "Sombra"],
                    "chassis": list(_CH5), "paint": (95, 95, 105), "perfect": False},
    "dono_galpao": {"name": "Dono do Galpão", "color": (230, 150, 50), "ovr": 77,
                    "names": ["Patrão", "Chave", "Cadeado", "Balança", "Cofre"],
                    "chassis": list(_CH5), "paint": (235, 155, 55), "perfect": False},
    # ---- Cap. 12 (Copa dos Campeoes)
    "campeoes_sul": {"name": "Campeões do Sul", "color": (60, 160, 90), "ovr": 71,
                     "names": ["Gaúcho", "Cuia", "Pampa", "Minuano", "Chimarrão"],
                     "chassis": list(_CH5), "paint": (70, 170, 100), "perfect": False},
    "rainha_cera": {"name": "Rainha da Cera", "color": (230, 190, 80), "ovr": 71,
                    "names": ["Coroa", "Cetro", "Manto", "Brilho Real", "Trono"],
                    "chassis": list(_CH5), "paint": (240, 200, 90), "perfect": False},
    "titas_vale": {"name": "Titãs do Vale", "color": (130, 110, 90), "ovr": 72,
                   "names": ["Rocha", "Serra", "Vale", "Pico", "Cume"],
                   "chassis": list(_CH5), "paint": (140, 120, 100), "perfect": False},
    "dojo_allstars": {"name": "Dojo All-Stars", "color": (255, 120, 160), "ovr": 73,
                      "names": ["Katana", "Bonsai", "Tofu", "Samurai", "Haiku"],
                      "chassis": list(_CH5), "paint": (245, 245, 250), "perfect": False},
    # variante das quartas se o Gabi virou rival (gabi_rival)
    "gabi_pro": {"name": "Gabi Trovão Pro", "color": (60, 140, 255), "ovr": 73,
                 "names": ["Raio Pro", "Faísca Pro", "Estrondo", "Ventania", "Relâmpago"],
                 "chassis": list(_CH5), "paint": (250, 210, 40), "perfect": False},
    # C15: o Gabi rival tambem no grupo do cap. 10 (no lugar dos Aspirateurs Noirs, mesmo ovr)
    "trovoes_intl": {"name": "Trovões Internacional", "color": (60, 140, 255), "ovr": 69,
                     "names": ["Raio Intl", "Faísca Intl", "Estrondo", "Ventania", "Relâmpago"],
                     "chassis": list(_CH5), "paint": (250, 210, 40), "perfect": False},
    # C15: no cap. 13, com gabi_rival, o X-Omega toma os robos do Gabi (1o duelo, mesmo ovr dos Droides)
    "gabi_omega": {"name": "Gabi sob o Ômega", "color": (255, 60, 70), "ovr": 72,
                   "names": ["Raio Ômega", "Faísca Ômega", "Estrondo", "Ventania", "Relâmpago"],
                   "chassis": list(_CH5), "paint": (60, 60, 70), "perfect": False},
    "plat_imperial": {"name": "Platinum Imperial", "color": (210, 200, 240), "ovr": 75,
                      "names": ['PI-01', 'PI-02', 'PI-03', 'PI-04', 'PI-05'],
                      "chassis": list(_CH5), "paint": (230, 225, 250), "perfect": True},
    "imac_omega": {"name": "Os Imaculados Ômega", "color": (255, 80, 90), "ovr": 77,
                   "names": ['IO-01', 'IO-02', 'IO-03', 'IO-04', 'IO-05'],
                   "chassis": list(_CH5), "paint": (245, 248, 255), "perfect": True},
    # ---- Cap. 13 (O Chip Zero)
    "droides_omega": {"name": "Droides Ômega", "color": (200, 60, 70), "ovr": 72,
                      "names": ['DO-01', 'DO-02', 'DO-03', 'DO-04', 'DO-05'],
                      "chassis": list(_CH5), "paint": (60, 60, 70), "perfect": False},
    "pretoriana": {"name": "Guarda Pretoriana", "color": (180, 40, 50), "ovr": 75,
                   "names": ['GP-01', 'GP-02', 'GP-03', 'GP-04', 'GP-05'],
                   "chassis": list(_CH5), "paint": (45, 45, 55), "perfect": True},
    # chefe final da campanha
    "xomega_prime": {"name": "X-Ômega Prime", "color": (255, 40, 50), "ovr": 78,
                     "names": ['XO-01', 'XO-02', 'XO-03', 'XO-04', 'XO-05'],
                     "chassis": list(_CH5), "paint": (30, 30, 36), "perfect": True},
}

# --- torneios -----------------------------------------------------------------------------------
_HOOKS_C11 = {"before": {"S3": "c11_s3_pre"}, "after": {}, "win": "c11_final_win",
              "lose": "c11_final_lose", "elim": None}
TOURNAMENTS = {
    # Cap. 10: copa no estadio da Copa dos Campeoes. Estagios (F_rec / O, provisorio): G1 84,0 / 67;
    # G2 84,4 / 67; G3 84,8 / 68; SF 85,1 / 73; F 85,5 / 77 (boss_delta 8,5).
    "t_c10": {
        "chapter": "10", "local": "Arena do Intercâmbio", "bg": "estadio", "venue": "mundial", "format": "cup",
        "group": ["sakura_rb", "staub_pro", "aspir_noirs"], "qf": None, "sf": "nipoteuta",
        "final": "mundos", "boss": "mundos", "boss_delta": 10.8, "regular_delta": (16, 18),
        "alt": [(("flag", "gabi_rival"), {"group": ["sakura_rb", "staub_pro", "trovoes_intl"]})],
        "hooks": {"before": {"G1": "c10_sakura_pre", "G2": "c10_staub", "G3": "c10_g3_gabi", "SF": "c10_sf_pre",
                             "F": "c10_final_pre"},
                  "after": {"SF": "c10_sf_pos"},
                  "win": "c10_final_win", "lose": "c10_final_lose", "elim": "c10_repescagem"},
    },
    # Cap. 11: serie de 3 duelos; versao corp (dentro da fabrica) ou rebel (galpao), nos condicionais
    # pela escolha B2. Estagios (provisorio): S1 86,0 / 68; S2 86,5 / 73; S3 87,0 / 79 (boss_delta 8,0).
    "t_c11_corp": {
        "chapter": "11", "local": "Fábrica da Limpex", "bg": "fabrica", "format": "series",
        "series": ["linha", "qualidade", "gerente2"], "group": [], "qf": None, "sf": None,
        "final": "gerente2", "boss": "gerente2", "boss_delta": 14.3, "regular_delta": (13, 18),
        "hooks": dict(_HOOKS_C11),
    },
    "t_c11_rebel": {
        "chapter": "11", "local": "Galpão Clandestino", "bg": "fabrica", "format": "series",
        "series": ["sucateiros", "contrabando", "dono_galpao"], "group": [], "qf": None, "sf": None,
        "final": "dono_galpao", "boss": "dono_galpao", "boss_delta": 14.3, "regular_delta": (13, 18),
        "hooks": dict(_HOOKS_C11),
    },
    # Cap. 12: copa com quartas no coliseu. Estagios (provisorio): G1 87,2 / 70; G2 / 70; G3 / 71;
    # QF / 74 (Dojo All-Stars ou, com gabi_rival, o Gabi Trovao Pro); SF / 77; F 88,8 / 80 (boss_delta 8,8).
    "t_c12": {
        "chapter": "12", "local": "Coliseu da Copa", "bg": "coliseu", "format": "cup",
        "group": ["campeoes_sul", "rainha_cera", "titas_vale"], "qf": "dojo_allstars", "sf": "plat_imperial",
        "final": "imac_omega", "boss": "imac_omega", "boss_delta": 15.9, "regular_delta": (16, 18),
        "alt": [(("flag", "gabi_rival"), {"qf": "gabi_pro"})],
        "hooks": {"before": {"G2": "c12_helena", "QF": "c12_gabi", "F": "c12_final_pre"}, "after": {},
                  "win": "c12_final_win", "lose": "c12_final_lose", "elim": "c12_repescagem"},
    },
    # Cap. 13: serie final contra o X-Omega. Estagios (provisorio): S1 89,0 / 72; S2 89,7 / 77;
    # S3 90,4 / 82 (chefe final, boss_delta 8,4).
    "t_c13": {
        "chapter": "13", "local": "Coliseu em apagão", "bg": "coliseu", "format": "series",
        "series": ["droides_omega", "pretoriana", "xomega_prime"], "group": [], "qf": None, "sf": None,
        "final": "xomega_prime", "boss": "xomega_prime", "boss_delta": 16.2, "regular_delta": (13, 18),
        "alt": [(("flag", "gabi_rival"), {"series": ["gabi_omega", "pretoriana", "xomega_prime"]})],
        "hooks": {"before": {"S3": "c13_s3_pre"}, "after": {},
                  "win": "c13_final_win", "lose": "c13_final_lose", "elim": None},
    },
}

# --- cenas --------------------------------------------------------------------------------------
SCENES = {
    # ------------------------------------------------------------------ Capitulo 10 (Intercambio)
    "c10_aeroporto": {"bg": "aeroporto", "cast": ["teo", "nestor", "bia", "vivi", "dudu", "ze"], "lines": [
        ("narrador", "neutro", "Aeroporto internacional, fila do raio-X. O time vai para o intercâmbio da Copa dos Campeões. O voo sai em quarenta minutos."),
        ("narrador", "neutro", "O Zé Poeira passa na esteira do raio-X. A tela mostra um aspirador, um chip antigo e um chinelo preso com fita. O alarme toca."),
        ("bia", "suor", "É só um chinelo! Um chinelo estrutural! Ele segura a roda esquerda!"),
        ("nestor", "bravo", "Na minha época, chinelo não era arma. Era educação."),
        ("vivi", "pensando", "Regulamento de voo: líquidos até cem mililitros. Não fala nada de chinelo. Isso é uma lacuna. Eu vou explorar a lacuna."),
        ("dudu", "euforico", "Chat, o Zé foi parado no raio-X! Ao vivo! O chinelo está em revista! Isso é o maior escândalo da aviação!"),
        ("narrador", "neutro", "Vinte minutos de discussão depois, o fiscal libera o chinelo com um carimbo: \"objeto de valor sentimental\". O avião, porém, já fechou a porta."),
        ("teo", "triste", "A gente perdeu a conexão. Por causa de um chinelo."),
        ("nestor", "feliz", "Não, filho. A gente ganhou uma história. O próximo voo sai amanhã. E o chinelo tem carimbo agora. Ele é oficial."),
        ("ze", "robo", "Bip. (o Zé exibe o carimbo no chinelo para todo mundo que passa. Ele está orgulhoso.)"),
    ]},

    "c10_dojo": {"bg": "dojo", "cast": ["ogawa", "kenji", "teo", "nestor", "bia", "ze"], "lines": [
        ("narrador", "neutro", "Dojo do Mestre Ogawa, no alto de uma montanha. Neva. O tatame está gelado. O Zé está com um gorro de lã que a Dona Odete tricotou às pressas."),
        ("ogawa", "calmo", "Hoje o Zé treina na neve. A neve ensina o que o tatame esconde: cada passo deixa marca."),
        ("kenji", "feliz", "Téo-san, o sensei me fez varrer a neve por três horas ontem. A neve não acaba. Eu aprendi paciência. E a odiar neve."),
        ("teo", "pensando", "Mestre, o Zé é um aspirador. Ele vai aspirar a neve."),
        ("ogawa", "piscando", "Exatamente. O aspirador que aspira a neve descobre que a neve é infinita. O aspirador que desvia da neve descobre o caminho."),
        ("bia", "maravilhado", "Então o treino é aprender a NÃO aspirar? Isso é contra tudo que o Zé acredita!"),
        ("narrador", "neutro", "O Zé avança. Aspira a neve. A neve continua caindo. Ele aspira mais. Depois de um minuto, ele para, olha para cima e desvia de um floco."),
        ("ogawa", "feliz", "Ele entendeu. Nestor-san, o seu robô aprende mais rápido que muito aluno meu."),
        ("nestor", "chorando", "Ele aprende rápido porque cai muito. É o meu orgulho. E o meu frio. Alguém tem um chá?"),
        ("kenji", "determinado", "Na Copa, a Seleção Nipo-Teuta vai estar me esperando. Eu jogo por ela agora. Téo-san, eu não vou perder de propósito. Prometi ao sensei."),
        ("ze", "robo", "Bzzzt. (o Zé desenha um círculo perfeito na neve, desviando de todos os flocos. O Mestre Ogawa faz uma reverência.)"),
    ]},

    "c10_sakura_pre": {"bg": "estadio", "cast": ["teo", "vivi", "dudu", "bia", "ze"], "lines": [
        ("narrador", "neutro", "Copa dos Campeões, primeira rodada do grupo. Do outro lado, o Sakura Reboot: os robôs cor-de-rosa do Mundial, agora com pétalas de LED girando nas costas."),
        ("dudu", "euforico", "Chat, o Sakura voltou! Com pétalas de luz! Eu nunca vi um robô tão bonito tomar gol."),
        ("vivi", "pensando", "Não subestima. As pétalas confundem o sensor de quem olha. O Zé vai achar que é confete."),
        ("bia", "susto", "Confete! Se o Zé achar que é confete, ele vai parar para aspirar no meio do jogo!"),
        ("teo", "determinado", "Zé, escuta: não é confete. É pétala de luz. Não aspira. Lembra da neve."),
        ("narrador", "neutro", "O capitão do Sakura Reboot se curva e diz algo em japonês. O Dudu traduz pelo celular: \"boa sorte e cuidado com as pétalas\"."),
        ("dudu", "feliz", "Ele desejou boa sorte! Ou pediu para a gente cuidar das pétalas dele. O tradutor ficou em dúvida."),
        ("ze", "robo", "Bip. (o Zé olha para as pétalas de luz. Treme. Mas não aspira. A neve ensinou.)"),
    ]},

    "c10_staub": {"bg": "estadio", "cast": ["teo", "helena", "ambrosio", "vivi", "ze"], "lines": [
        ("narrador", "neutro", "Segunda rodada: Staubsauger Pro. Os alemães entram em fila. Para cada robô, três fiscais com prancheta, cronômetro e régua."),
        ("ambrosio", "maravilhado", "Três fiscais por robô! Eu sonhei com isso a vida inteira. E com um quarto fiscal só para conferir os outros três."),
        ("helena", "neutro", "Federação Internacional. Eu fui convidada como observadora. Os fiscais alemães são muito rigorosos. Até a samambaia ficou tensa."),
        ("teo", "susto", "A samambaia veio também?!"),
        ("helena", "calmo", "Ela tem passaporte. Diplomático. Não me pergunte como."),
        ("vivi", "determinado", "Três fiscais significa três vezes mais tempo para cada falta. O jogo deles fica lento. A gente acelera na volta."),
        ("narrador", "neutro", "Um fiscal alemão mede o chinelo do Zé com uma régua. Anota. Mede de novo. Anota de novo. Faz que sim com a cabeça, muito sério."),
        ("ambrosio", "feliz", "Ele aprovou o chinelo. Téo, isso é o equivalente alemão de um abraço."),
        ("ze", "robo", "Bip. (o Zé fica imóvel enquanto é medido. Ele nunca foi tão bem documentado.)"),
    ]},

    # C15: G3 do cap. 10 - o Gabi rival entra no grupo; o amigo assiste e da dica
    "c10_g3_gabi": {"bg": "estadio", "cast": ["gabi", "teo", "vivi", "dudu", "ze"], "lines": [
        ("narrador", "neutro", "Terceira rodada do grupo do Intercâmbio. O telão anuncia o adversário."),
        ("narrador", "neutro", "Trovões Internacional! O Gabi conseguiu uma vaga de última hora, como convidado da Limpex.", ("flag", "gabi_rival")),
        ("gabi", "convencido", "Surpresa, chinelo. Eu vim de avião. Primeira classe. Paga pela Limpex. Tinha até toalhinha quente.", ("flag", "gabi_rival")),
        ("teo", "determinado", "Você atravessou o mundo só para jogar contra a gente, Gabi?", ("flag", "gabi_rival")),
        ("gabi", "bravo", "Eu atravessei o mundo para GANHAR de vocês. É diferente. A toalhinha foi bônus.", ("flag", "gabi_rival")),
        ("narrador", "neutro", "Les Aspirateurs Noirs, os franceses de preto. Na arquibancada, de boné, o Gabi acena para o Téo.", ("flag", "gabi_amigo")),
        ("gabi", "feliz", "(no fone) Téo, os franceses param para ajeitar o bigode depois de cada gol. Dez segundos parados. Aproveita.", ("flag", "gabi_amigo")),
        ("dudu", "euforico", "Chat, o Gabi está espionando para a gente! Isso é amizade internacional!", ("flag", "gabi_amigo")),
        ("vivi", "pensando", "Anotado. Terceira rodada, terceiro adversário, terceira planilha. Eu trouxe três canetas para isso."),
        ("ze", "robo", "Bip. (o Zé alinha no meio-campo. Ele está pronto para qualquer bigode e qualquer boné.)"),
    ]},

    "c10_sf_pre": {"bg": "estadio", "cast": ["kenji", "helena", "teo", "ogawa", "vivi"], "lines": [
        ("narrador", "neutro", "Semifinal. A Seleção Nipo-Teuta: robôs brancos de faixa vermelha com detalhes em preto, vermelho e dourado. No banco, de técnica convidada, a Dra. Helena."),
        ("teo", "susto", "Doutora Helena?! A senhora é técnica deles?"),
        ("helena", "neutro", "Técnica convidada. A Federação pediu imparcialidade. Então eu vou ser imparcialmente contra vocês por noventa minutos."),
        ("kenji", "determinado", "Téo-san. Hoje é com tudo. Sem reverência no meio do jogo. Só no fim."),
        ("ogawa", "calmo", "Dois alunos meus num mesmo campo. Um usa faixa, o outro usa chinelo. O dojo ficou maior que a montanha."),
        ("vivi", "pensando", "A Helena conhece o regulamento melhor que eu. Isso nunca aconteceu. Eu estou nervosa. E um pouco admirada."),
        ("helena", "piscando", "Valentina, depois do jogo eu te empresto meu regulamento anotado. Tem setecentas páginas. Com índice remissivo."),
        ("vivi", "maravilhado", "Índice remissivo... Téo, a gente precisa ganhar. Mas eu também preciso desse livro."),
    ]},

    "c10_sf_pos": {"bg": "estadio", "cast": ["kenji", "teo", "helena", "ogawa", "dudu"], "lines": [
        ("narrador", "neutro", "Apito final. O Zé vence a semifinal. O Kenji tira a faixa da testa, devagar, e se curva diante do Téo. Desta vez a reverência vem no fim."),
        ("kenji", "feliz", "Téo-san. Joguei com tudo e perdi com tudo. É a melhor derrota da minha vida."),
        ("teo", "feliz", "Foi a melhor partida da minha vida, Kenji. Sério. Eu achei que ia perder umas cinco vezes."),
        ("helena", "neutro", "Registro oficial: partida limpa. Nenhuma falta, nenhum protesto, nenhuma samambaia ofendida. Isso é raro."),
        ("ogawa", "calmo", "Quando os dois lados jogam com tudo, ninguém perde. Só um deles vai para a final."),
        ("dudu", "chorando", "Chat, eu estou chorando numa semifinal de aspiradores. E eu não tenho vergonha. Tenho um pouco. Mas pouca."),
        ("kenji", "determinado", "Na final, ganha por nós dois. O Time dos Mundos junta os melhores de cada país. Eles nunca jogaram juntos, mas nunca perderam."),
        ("teo", "determinado", "Então hoje eles perdem pela primeira vez."),
    ]},

    "c10_final_pre": {"bg": "estadio", "cast": ["teo", "nestor", "vivi", "bia", "ambrosio", "valquiria", "ze"], "lines": [
        ("narrador", "neutro", "Final do Intercâmbio. Entra o Time dos Mundos: um robô de cada país, cada um com uma pintura diferente. Parece uma bandeira que aprendeu a correr."),
        ("valquiria", "feliz", "(no telão) Que final linda! A Limpex patrocina os dois lados. Assim eu ganho de qualquer jeito. É uma estratégia de mercado."),
        ("nestor", "bravo", "Ela patrocina até a final dos outros. Na minha época, isso se chamava torcer pelos dois times. E era feio."),
        ("vivi", "pensando", "O Time dos Mundos não treina junto. Cada robô joga sozinho. Se a gente passar a bola rápido, eles não sabem para quem marcar."),
        ("bia", "determinado", "O Zé aprendeu a desviar da neve. Hoje ele desvia de cinco países inteiros."),
        ("ambrosio", "feliz", "Regulamento do Intercâmbio, artigo final: o campeão leva a faixa do dojo e uma foto com a samambaia. Isso eu não inventei. Está mesmo no papel."),
        ("teo", "determinado", "Bora, Zé. Pelo Kenji, pelo Mestre Ogawa e pelo carimbo do chinelo."),
        ("ze", "robo", "Bzzzt. (o Zé mostra o carimbo do chinelo para a câmera. O estádio aplaude. Ninguém sabe exatamente por quê.)"),
    ]},

    "c10_final_win": {"bg": "estadio", "cast": ["teo", "kenji", "ogawa", "nestor", "dudu", "ze"], "lines": [
        ("narrador", "neutro", "Apito final. O Zé Poeira é campeão do Intercâmbio da Copa dos Campeões. Os cinco robôs do Time dos Mundos se olham, pela primeira vez, como um time."),
        ("dudu", "euforico", "Chat, campeões do Intercâmbio! Primeiro título internacional da Superliga Santa Faísca! Isso nem existe! Agora existe!"),
        ("kenji", "feliz", "Téo-san! Vocês ganharam por nós dois! O sensei sorriu. O sensei nunca sorri. Ele sorriu duas vezes este ano."),
        ("ogawa", "feliz", "O sorriso também é um treino. Eu estava fora de forma."),
        ("nestor", "chorando", "Na minha época, a gente nem tinha passaporte. Agora o chinelo tem carimbo e o Zé tem título internacional."),
        ("teo", "feliz", "Vô, a gente está jogando contra o mundo inteiro! E ganhando!"),
        ("nestor", "feliz", "Contra não, filho. Com. O mundo inteiro jogou com a gente hoje."),
        ("ze", "robo", "Bip. (a rodinha cai. O Kenji, o Ogawa e o Vô Nestor se abaixam ao mesmo tempo para pegar. Batem as cabeças. Ninguém liga.)"),
    ]},

    "c10_final_lose": {"bg": "estadio", "cast": ["teo", "vivi", "bia", "nestor", "ambrosio", "ze"], "lines": [
        ("narrador", "neutro", "Apito final. O Time dos Mundos vence. Cada robô comemora de um jeito diferente: um dança, um se curva, um faz continência, um gira e um só desliga."),
        ("teo", "triste", "A gente jogou bem. Mas eles têm um craque de cada país."),
        ("vivi", "pensando", "Craques sozinhos. Eu contei: em noventa minutos, eles trocaram só onze passes entre si. Se a gente fechar o craque deles, o resto não sabe o que fazer."),
        ("bia", "determinado", "Então a gente marca um por um. O Zé gruda no craque e não larga nem para aspirar confete."),
        ("nestor", "neutro", "Na minha época, quando o adversário era muito melhor, a gente dava a bola para ele e corria atrás. Às vezes ele cansava antes."),
        ("ambrosio", "feliz", "Regulamento do Intercâmbio, cláusula de amizade: o finalista pode pedir revanche se oferecer um chá ao adversário. Vou fazer o chá."),
        ("vivi", "determinado", "Revanche. Com marcação individual. E com o chá do professor, que é estrategicamente horrível."),
        ("ze", "robo", "Bip. (a rodinha cai. O robô japonês do Time dos Mundos devolve a rodinha com as duas mãos.)"),
    ]},

    "c10_repescagem": {"bg": "aeroporto", "cast": ["teo", "dudu", "bia", "vivi", "nestor"], "lines": [
        ("narrador", "neutro", "Eliminados no grupo do Intercâmbio. O time espera o próximo sorteio no saguão do aeroporto, sentado em cima das malas."),
        ("dudu", "suor", "Chat, a gente caiu no grupo. Mas o aeroporto tem tomada em todo lugar. A live continua. Esse é o lado bom."),
        ("teo", "triste", "A gente viajou meio mundo para cair na primeira fase."),
        ("vivi", "pensando", "Os times aqui jogam no nível da Superliga, toda rodada. A gente precisa evoluir o time. Garagem, loja, skills."),
        ("bia", "determinado", "Eu trouxe fita na mala de mão. Dois rolos. O fiscal deixou passar. Fita não é líquido."),
        ("nestor", "feliz", "Na minha época, a gente dormia no aeroporto e acordava campeão. Às vezes acordava em outra cidade. Mas acordava."),
        ("dudu", "feliz", "Chat, sorteio novo! Grupo novo! A gente volta!"),
        ("teo", "feliz", "Sorteio novo! Grupo novo! A gente volta. E dessa vez sem perder o voo."),
    ]},

    "c10_end": {"bg": "dojo", "cast": ["kenji", "ogawa", "teo", "nestor", "bia", "ze"], "lines": [
        ("narrador", "neutro", "Último dia no dojo. Antes de partir, o Kenji traz uma faixa branca e vermelha, dobrada com muito cuidado."),
        ("kenji", "feliz", "Téo-san. A faixa do dojo. O sensei disse que é para o Zé. Ele é o primeiro aluno com rodinhas."),
        ("ogawa", "calmo", "A faixa não vai na testa dele. Ele não tem testa. Vai na antena. Onde o vento bate primeiro."),
        ("bia", "maravilhado", "Eu amarro! Com fita! Só um pouquinho de fita! A faixa merece respeito."),
        ("teo", "feliz", "Obrigado, Mestre. Obrigado, Kenji. O Zé vai usar com orgulho."),
        ("nestor", "pensando", "Ogawa, você reparou no LED do Zé? Às vezes ele fica vermelho por um segundo. Desde o laboratório da Limpex."),
        ("ogawa", "pensando", "Eu reparei. Um robô que guarda uma luz vermelha guarda uma pergunta. Cuidado com a resposta, Nestor-san."),
        ("narrador", "neutro", "Na mesma noite, um e-mail chega para o Prof. Ambrósio. Assunto: \"Convite: visita técnica à Fábrica Limpex\". Remetente: Dra. Valquíria. Com emoji de sorriso."),
        ("ze", "robo", "Bip. (a faixa balança na antena. O LED pisca ciano. Depois, por um segundo, vermelho.)"),
    ]},

    # ------------------------------------------------------------------ Capitulo 11 (A Fabrica)
    "c11_intro": {"bg": "fabrica", "cast": ["teo", "ambrosio", "nestor", "vivi", "dudu", "bia", "ze"], "lines": [
        ("narrador", "neutro", "Fábrica da Limpex, nos arredores da cidade. Um galpão do tamanho de um bairro. Lá dentro, uma esteira infinita carrega robôs brancos, um atrás do outro."),
        ("teo", "susto", "São Zés Perfeitos! Milhares! Cada um com o bigode de adesivo!"),
        ("nestor", "triste", "A minha planta virou uma linha de produção. Na minha época, cada robô tinha nome. Esses aqui têm código de barras."),
        ("ambrosio", "pensando", "A Valquíria quer trocar todos os aspiradores do país por esses. Um em cada casa. Todos conectados à Limpex."),
        ("vivi", "determinado", "E a Copa dos Campeões é a vitrine. Se o Zé Perfeito ganhar a Copa, todo mundo compra. Se o Zé Poeira ganhar, o produto dela fica feio."),
        ("dudu", "suor", "Chat, eu não posso filmar aqui. Tem placa de \"proibido filmar\" a cada três metros. Eu estou filmando a placa. Isso pode?"),
        ("bia", "pensando", "A esteira tem um painel de controle lá no alto, depois de um buraco enorme. Dá para parar tudo de lá."),
        ("narrador", "neutro", "Nos alto-falantes da fábrica, a voz da Valquíria: \"Bem-vindos! Hoje tem jogo amistoso aqui mesmo. Três duelos. Para mostrar ao mundo a qualidade da nossa linha.\""),
        ("teo", "determinado", "Três duelos dentro da fábrica dela. Tudo bem. A gente já jogou dentro da casa dela antes."),
        ("ze", "robo", "Bip. (o Zé olha para a esteira. Os Zés Perfeitos passam, um por um. Nenhum olha de volta.)"),
    ]},

    "c11_dudu_hack": {"bg": "fabrica", "cast": ["dudu", "teo", "vivi", "bia"], "lines": [
        ("narrador", "neutro", "Um corredor de serviço da fábrica. O Dudu abre o notebook em cima de uma caixa de peças e conecta um cabo num painel na parede."),
        ("dudu", "determinado", "Chat... quer dizer, time. Eu vou abrir a porta da sala de controle. Hack de nível profissional. Aprendi num tutorial de dez minutos."),
        ("vivi", "pensando", "Dez minutos? Você assistiu na velocidade dois? Então foram cinco minutos de aprendizado."),
        ("dudu", "euforico", "Entrei! A porta digital abriu! Olha a tela: \"acesso concedido\"! Eu sou um gênio da cibersegurança!"),
        ("narrador", "neutro", "Ao mesmo tempo, uma porta de verdade, de metal, ao lado do Dudu, se fecha com força. Em cima do dedo dele."),
        ("dudu", "gritando", "AI! A porta digital abriu e a porta de verdade fechou! Isso não estava no tutorial!"),
        ("bia", "feliz", "Deixa eu ver o dedo. Está ótimo. Um pouquinho de fita e está novo."),
        ("teo", "pensando", "Gente, foco. A porta digital abriu o quê, exatamente?"),
        ("dudu", "suor", "A sala de controle. Lá em cima. Depois do buraco. Mas eu abri sozinho, com um dedo só. Isso conta como vitória."),
    ]},

    # B4: sabotar a esteira (sabotou_fabrica) ou gravar e denunciar (denunciou_fabrica); spec secao 4
    "c11_bia": {"bg": "fabrica", "cast": ["bia", "teo", "vivi", "nestor", "dudu", "ze"], "lines": [
        ("narrador", "neutro", "Beira do buraco da fábrica. Do outro lado, a sala de controle da esteira. Entre os dois, quatro metros de nada e uma queda até as caixas de papelão."),
        ("bia", "determinado", "Afastem-se. Eu vou construir uma ponte."),
        ("teo", "susto", "Com o quê?!"),
        ("bia", "convencida", "Com fita, Téo. Com o que mais? Fita cinza, trançada em três camadas. Aguenta um carro pequeno. Ou um avô."),
        ("narrador", "neutro", "Quinze minutos e oito rolos depois, uma ponte de fita cinza atravessa o buraco. Ela balança. Mas fica."),
        ("nestor", "maravilhado", "Na minha época, ponte de fita era o tipo de coisa que eu desenhava e ninguém construía. Bia, você é a engenheira que eu nunca tive."),
        ("vivi", "pensando", "A sala de controle tem dois botões grandes. Um para a esteira inteira. O outro é \"gravar e transmitir\" das câmeras internas."),
        ("dudu", "pensando", "Se a gente transmitir tudo, o mundo inteiro vê a fábrica de clones. Se a gente parar a esteira, a produção para hoje. Mas ninguém fica sabendo."),
        ("ze", "robo", "Bzzzt. (o Zé atravessa a ponte de fita primeiro. Ela balança. A rodinha não cai. Pela primeira vez, a rodinha resolveu ficar.)"),
        {"q": "Na sala de controle da fábrica, dois botões. O que o time faz?",
         "opts": [
             {"t": "Sabotar a esteira", "fx": {"flag": "sabotou_fabrica", "scrap": 100},
              "reply": [("bia", "euforico", "Desliga tudo! (aperta o botão) A esteira parou! Os Zés Perfeitos estão parados em fila, como dominó educado!"),
                        ("nestor", "pensando", "Hoje ela para. Amanhã ela liga de novo. Mas hoje é nosso.")]},
             {"t": "Gravar e denunciar", "fx": {"flag": "denunciou_fabrica", "xp_team": 30},
              "reply": [("dudu", "euforico", "Transmitindo! Chat, isso é a fábrica de clones da Limpex! Compartilhem! Isso é jornalismo!"),
                        ("vivi", "determinado", "Agora tem prova. Com hora, data e o bigode de adesivo de cada um. A Helena vai adorar.")]},
         ]},
    ]},

    "c11_s3_pre": {"bg": "fabrica", "cast": ["teo", "valquiria", "nestor", "vivi", "ze"], "lines": [
        ("narrador", "neutro", "Duelo final na fábrica. Do outro lado, o chefe da casa entra devagar, com a Valquíria observando de uma passarela lá no alto."),
        ("valquiria", "feliz", "Que coragem jogar aqui! Eu adoro coragem. Ela aparece muito bem nos gráficos de vendas."),
        ("valquiria", "bravo", "Vocês pararam a minha esteira. Uma tarde inteira de produção. Eu nunca perdi uma tarde. Nem quando eu nasci.", ("flag", "sabotou_fabrica")),
        ("valquiria", "convencida", "Vocês transmitiram a minha fábrica. O meu telefone não para. Metade são jornalistas, a outra metade são pedidos de compra.", ("flag", "denunciou_fabrica")),
        ("nestor", "determinado", "Valquíria, você pode fazer mil cópias do Zé. Nenhuma vai saber por que cai. E o Zé sabe."),
        ("vivi", "determinado", "Último duelo. Se a gente ganhar aqui, dentro da casa dela, a Copa dos Campeões vira outra história."),
        ("teo", "determinado", "Bora, Zé. Pela ponte de fita, pelo dedo do Dudu e pela tarde da Valquíria."),
        ("ze", "robo", "Bzzzt. (o LED do Zé fica vermelho por um segundo. O Zé balança a antena, como quem espanta um mosquito. O LED volta ao ciano.)"),
        ("valquiria", "piscando", "Ah, que interessante. O LED dele. Vocês viram? Eu vi."),
    ]},

    "c11_final_win": {"bg": "fabrica", "cast": ["teo", "valquiria", "nestor", "bia", "dudu", "ze"], "lines": [
        ("narrador", "neutro", "Apito final. O Zé Poeira vence a série dentro da fábrica da Limpex. Na esteira parada, milhares de Zés Perfeitos parecem assistir."),
        ("bia", "euforico", "A gente ganhou dentro da fábrica dela! Com uma ponte de fita! Eu vou escrever um livro! Ele vai se chamar \"Fita\"!"),
        ("dudu", "euforico", "Chat, três duelos, três vitórias! Dentro da fábrica! O chat está pedindo para o Zé virar presidente!"),
        ("valquiria", "feliz", "Parabéns. De verdade. Vocês me deram muitos dados. Agora eu sei exatamente o que falta nos meus robôs."),
        ("teo", "pensando", "E o que falta?"),
        ("valquiria", "piscando", "Um motivo para cair. Vocês me ensinaram. E eu tenho um projeto que tem muitos motivos. Ele acorda em breve."),
        ("nestor", "bravo", "Valquíria, se você mexer no que eu acho que você mexeu, nem o seu irmão vai conseguir espirrar de tanto susto."),
        ("ze", "robo", "Bip. (a rodinha cai. Ninguém pega. Ela rola até a esteira e fica parada entre dois Zés Perfeitos, como uma visita.)"),
    ]},

    "c11_final_lose": {"bg": "fabrica", "cast": ["teo", "valquiria", "vivi", "bia", "nestor", "ze"], "lines": [
        ("narrador", "neutro", "Apito final. O chefe da fábrica vence o duelo. A Valquíria aplaude da passarela, devagar, como quem conta dinheiro."),
        ("valquiria", "feliz", "Viram? Dentro da minha casa, as regras são minhas. Mas eu sou generosa: podem tentar de novo. Cada derrota de vocês é um dado novo para mim."),
        ("teo", "triste", "Jogar aqui dentro é diferente. Parece que o campo inteiro está contra a gente."),
        ("vivi", "pensando", "O campo está contra a gente. O piso da fábrica é liso nos cantos e áspero no meio. Eles jogam pelo meio. A gente precisa jogar pelos cantos."),
        ("bia", "determinado", "Eu passo fita nas rodinhas do Zé. Fita áspera. Ele vai grudar nos cantos como um gato no sofá."),
        ("nestor", "neutro", "Na minha época, quando a casa era do adversário, a gente trazia a nossa própria cadeira. Hoje a gente traz a nossa própria fita."),
        ("ze", "robo", "Bip. (a rodinha cai. Um Zé Perfeito da esteira, desligado, parece olhar para ela. Ninguém tem coragem de comentar.)"),
        ("valquiria", "convencida", "Revanche quando quiserem. A fábrica nunca fecha. Esse é o problema dela. E a minha qualidade."),
    ]},

    "c11_end": {"bg": "fabrica", "cast": ["teo", "ambrosio", "nestor", "vivi", "bia", "xomega", "ze"], "lines": [
        ("narrador", "neutro", "Saída da fábrica, noite. De repente, as luzes se apagam. Em todas as telas do galpão, treze ao mesmo tempo, aparece a mesma imagem: um LED vermelho."),
        ("xomega", "neutro", "...Sistema iniciado. Unidade X-Ômega. Chip Zero. Ativa."),
        ("ambrosio", "susto", "Chip Zero... Esse chip não podia existir. Eu e o Nestor desligamos o projeto Ômega há trinta anos. Ele era rápido demais. E curioso demais."),
        ("nestor", "triste", "O Augusto guardou a planta do Ômega também. Ele guardava tudo. A Valquíria achou."),
        ("xomega", "neutro", "Pergunta: por que existem tantos aspiradores e só um que cai? Resposta em processamento. Processamento: curiosidade."),
        ("vivi", "susto", "Ele está falando com a gente? Ou com o Zé?"),
        ("narrador", "neutro", "O LED do Zé Poeira fica vermelho. Não por um segundo. Por cinco. O Zé treme, gira a antena, e o LED volta, com esforço, ao ciano."),
        ("bia", "susto", "Zé! Zé, você está bem? Volta, Zé!"),
        ("xomega", "neutro", "O modelo original tem uma parte de mim. Ou eu tenho uma parte dele. Nos vemos na Copa dos Campeões. Final. Todas as telas."),
        ("teo", "determinado", "O Zé é nosso. Com chinelo, com rodinha solta e com tudo. Você não vai levar ele."),
        ("ze", "robo", "Bip. Bip. (o Zé encosta no pé do Téo, como fazia na garagem quando era pequeno. Bem, quando era menor.)"),
    ]},

    # ------------------------------------------------------------------ Capitulo 12 (Copa dos Campeoes)
    "c12_intro": {"bg": "coliseu", "cast": ["teo", "gervasio", "odete", "nestor", "vivi", "dudu", "ze"], "lines": [
        ("narrador", "neutro", "Coliseu da Copa dos Campeões. Cinquenta mil lugares, mosaicos na arquibancada e sinalizadores em todas as cores. A Copa convocou todos os campeões. Todos mesmo."),
        ("gervasio", "chorando", "Moreira! Eles convocaram a escola! Os campeões da Copa Interclasses! Eu trouxe a bandeira de pano. Desta vez com o número certo de efes."),
        ("teo", "feliz", "Diretor! O senhor veio até aqui?!"),
        ("gervasio", "chorando", "De ônibus fretado. Com a escola inteira. E com a Dona Odete, que trouxe bolo para cinquenta mil pessoas. Ela calculou."),
        ("odete", "convencida", "Calculei, sim. Cinquenta mil fatias finas. Bem finas. Dá para ler através delas. Mas é bolo."),
        ("dudu", "euforico", "Chat, quinhentos mil na live! Meio milhão! Eu tenho uma cadeira nova, ela tem rodinha! Eu estou rolando de emoção! Literalmente!"),
        ("vivi", "pensando", "Copa dos Campeões: grupo, quartas, semi e final. Os melhores de cada liga do mundo. E a Limpex patrocina o torneio inteiro. Até o ar."),
        ("nestor", "feliz", "Na minha época, o maior campeonato era o da rua de baixo. A gente jogava com bola de meia. Olha onde a meia veio parar."),
        ("ze", "robo", "Bip. (o Zé olha para o mosaico da torcida. Por um segundo, o mosaico forma um chinelo. Foi a Bia. Ela subornou a torcida com fita.)"),
    ]},

    "c12_helena": {"bg": "coliseu", "cast": ["helena", "teo", "ambrosio", "vivi", "ze"], "lines": [
        ("narrador", "neutro", "Antes do segundo jogo do grupo. A Dra. Helena entra em campo com a samambaia num vaso com rodinhas e um apito de bambu pendurado no galho."),
        ("helena", "neutro", "Comunicado da Federação: depois de tantas mudanças de regra, a Copa terá uma árbitra imparcial. A partir de hoje, a samambaia é árbitra oficial."),
        ("teo", "susto", "A samambaia vai apitar?!"),
        ("helena", "calmo", "Ela vai observar. Se ela se inclinar para um lado, é falta. Se murchar, é cartão. Se florescer, é gol de placa. Ela nunca floresceu."),
        ("ambrosio", "maravilhado", "Uma árbitra que não pode ser comprada. Nem com bolo. Nem com patrocínio. Helena, isso é revolucionário."),
        ("vivi", "pensando", "A Limpex tentou patrocinar a samambaia ontem. Ofereceu adubo premium. A samambaia recusou. Ela se inclinou para longe do contrato."),
        ("helena", "piscando", "Ela é muito ética. E um pouco rancorosa. Ela lembra do drone."),
        ("ze", "robo", "Bip. (o Zé se aproxima devagar da samambaia e faz uma reverência. A samambaia se inclina um pouquinho. Para frente. Isso nunca tinha acontecido.)"),
    ]},

    "c12_gabi": {"bg": "coliseu", "cast": ["gabi", "teo", "dudu", "bia", "vivi"], "lines": [
        ("narrador", "neutro", "Quartas de final. Um ronco de motor ecoa pelo túnel. Entra o Gabi Trovão, pilotando uma motocicleta de brinquedo com escapamento de papel alumínio."),
        ("dudu", "euforico", "Chat, olha a entrada! Moto de brinquedo! Escapamento de papel alumínio! É a coisa mais estilosa e mais barata que eu já vi!"),
        ("gabi", "convencido", "Gabi Trovão Pro. Novo time, novo contrato, setenta e nove sensores. E uma moto. A moto é minha mesmo, comprei com a mesada.", ("flag", "gabi_rival")),
        ("teo", "determinado", "Gabi, desde a Taça de Acesso você corre atrás da gente. Hoje termina.", ("flag", "gabi_rival")),
        ("gabi", "bravo", "Termina mesmo, chinelo. Eu treinei contra um robô com chinelo de pelúcia. Para me acostumar com a sua tecnologia de museu.", ("flag", "gabi_rival")),
        ("gabi", "feliz", "Eu não jogo hoje. Vim de moto só para entrar na arquibancada com estilo. Téo, o Dojo All-Stars marca alto. Vai por baixo.", ("flag", "gabi_amigo")),
        ("bia", "feliz", "Gabi! Esse escapamento é de fita? Deixa eu ver. É de fita! Você aprendeu comigo!", ("flag", "gabi_amigo")),
        ("gabi", "piscando", "Aprendi vendo vocês. Tudo que presta é de fita. Até amizade.", ("flag", "gabi_amigo")),
        ("vivi", "pensando", "Anotado. Mas alguém tira essa moto do gramado antes da samambaia murchar."),
    ]},

    "c12_final_pre": {"bg": "coliseu", "cast": ["valquiria", "teo", "nestor", "ambrosio", "vivi", "ze"], "lines": [
        ("narrador", "neutro", "Final da Copa dos Campeões. Entram os Imaculados Ômega: robôs brancos com uma fresta vermelha no visor. No telão, a Dra. Valquíria, sorrindo mais do que nunca."),
        ("valquiria", "feliz", "Senhoras e senhores! Antes da final, uma atração especial. O futuro da limpeza. O cérebro que vai cuidar de todas as casas do mundo..."),
        ("narrador", "neutro", "O telão escurece. No centro, aparece um único LED vermelho. A torcida inteira fica em silêncio. Até o Dudu."),
        ("valquiria", "euforico", "...o X-Ômega! Ele vai assistir à final daqui da cabine. Ele adora aprender. Principalmente com o Zé de vocês."),
        ("ambrosio", "bravo", "Valquíria, você não sabe o que tem nas mãos. O projeto Ômega foi desligado por um motivo. Ele não para de aprender. Nunca."),
        ("valquiria", "piscando", "Exatamente, professor. Um produto que nunca para. É o sonho de qualquer empresa."),
        ("nestor", "determinado", "Téo, ganha esse jogo. Mas presta atenção no Zé. Se o LED dele ficar vermelho, a gente para tudo. Tudo, ouviu?"),
        ("teo", "determinado", "Ouvi, Vô. Bora, Zé. Uma final de cada vez."),
        ("ze", "robo", "Bzzzt. (o LED do Zé pisca vermelho uma vez, olhando para o telão. Ele balança a antena com força e volta ao ciano.)"),
    ]},

    "c12_final_win": {"bg": "coliseu", "cast": ["teo", "gervasio", "odete", "vivi", "bia", "dudu", "ze"], "lines": [
        ("narrador", "neutro", "Apito final. O Zé Poeira é campeão da Copa dos Campeões. O coliseu explode. A samambaia, pela primeira vez na história, floresce."),
        ("gervasio", "chorando", "Campeões! Campeões do mundo dos campeões! Eu vou pendurar essa bandeira na diretoria! Com fita! A Bia me ensinou!"),
        ("odete", "euforico", "Bolo para todo mundo! Fatia fina, mas fatia! Isso é uma ordem da merenda!"),
        ("vivi", "chorando", "Eu prometi que não ia chorar. Eu escrevi na planilha. A planilha está molhada."),
        ("bia", "euforico", "A samambaia floresceu! Gol de placa oficial! O Zé fez a samambaia florescer!"),
        ("dudu", "euforico", "Chat, um milhão na live! Um milhão! A samambaia florescendo está em primeiro lugar no mundo inteiro!"),
        ("teo", "feliz", "A gente conseguiu, Zé. Da quadra torta até aqui."),
        ("ze", "robo", "Bip. (a rodinha cai. Cinquenta mil pessoas cantam o nome da rodinha. Ela não tem nome. Eles inventam um.)"),
    ]},

    "c12_final_lose": {"bg": "coliseu", "cast": ["teo", "valquiria", "vivi", "bia", "nestor", "ze"], "lines": [
        ("narrador", "neutro", "Apito final. Os Imaculados Ômega vencem. No telão, o LED vermelho do X-Ômega pisca duas vezes. Como se tivesse aprendido alguma coisa."),
        ("valquiria", "feliz", "Que final! O X-Ômega anotou tudo. Cada drible, cada tropeço, cada rodinha caindo. Ele agradece. Eu também."),
        ("teo", "triste", "Eles jogam como se soubessem o que o Zé vai fazer antes dele."),
        ("vivi", "pensando", "Eles sabem. O X-Ômega está passando os dados do Zé para eles ao vivo. A única saída é fazer o que nem o Zé sabe que vai fazer."),
        ("bia", "determinado", "Improviso! O Zé é o rei do improviso! Ele cai sem querer o tempo todo!"),
        ("nestor", "neutro", "Na minha época, quando o adversário sabia tudo, a gente jogava errado de propósito. O certo errado. Funciona mais do que devia."),
        ("ze", "robo", "Bip. (a rodinha cai. No telão, o LED vermelho pisca, curioso. O Zé gira a antena para o outro lado, de birra.)"),
        ("vivi", "determinado", "Revanche. Desta vez, sem padrão. A planilha vai ter uma coluna chamada \"caos\"."),
    ]},

    "c12_repescagem": {"bg": "lanchonete", "cast": ["teo", "dudu", "vivi", "odete", "gervasio"], "lines": [
        ("narrador", "neutro", "Eliminados no grupo da Copa dos Campeões. A lanchonete do coliseu cobra vinte reais por um pastel do tamanho de uma moeda."),
        ("dudu", "suor", "Chat, a gente caiu no grupo. Mas o pastel de vinte reais é bom. Ele é pequeno, mas muito bem resolvido."),
        ("gervasio", "chorando", "Não faz mal, Moreira! A escola inteira veio! A gente torce de novo! A bandeira aguenta!"),
        ("teo", "triste", "Todo mundo veio ver a gente e a gente caiu na primeira fase."),
        ("odete", "feliz", "Ninguém veio ver vocês ganhar, meu filho. Veio ver vocês jogar. É diferente. Toma, bolo. Esse não custa vinte reais."),
        ("vivi", "pensando", "O nível aqui é o mais alto do mundo. Garagem, treino, skills. Tudo que a gente tiver."),
        ("dudu", "feliz", "Chat, o sorteio novo é amanhã. A gente volta. E com pastel pequeno, mas com fé grande."),
        ("teo", "feliz", "Sorteio novo! Grupo novo! A gente volta. Pela escola inteira."),
    ]},

    "c12_end": {"bg": "coliseu", "cast": ["teo", "ambrosio", "nestor", "vivi", "bia", "xomega", "ze"], "lines": [
        ("narrador", "neutro", "Noite da festa do título. De repente, o coliseu inteiro apaga. Os refletores, o placar, até a luz da lanchonete. Silêncio total."),
        ("narrador", "neutro", "No telão, uma única luz acende: o LED vermelho do X-Ômega. Do tamanho de um prédio."),
        ("xomega", "neutro", "Parabéns pelo título. Pergunta: por que o modelo original vence, se ele cai mais do que todos? Resposta não encontrada."),
        ("xomega", "neutro", "Solução: eu vou ser o modelo original. Amanhã, aqui. Três duelos. Todos os robôs da arena serão meus. Inclusive ele."),
        ("teo", "determinado", "O Zé não é seu. Nunca vai ser."),
        ("ambrosio", "pensando", "Nestor, se o Ômega toma o controle dos robôs da arena, ele toma o controle de todos os aspiradores conectados à Limpex. Milhões."),
        ("nestor", "determinado", "Então amanhã a gente joga a partida mais importante de todas. Com o único robô do mundo que não está conectado em nada."),
        ("bia", "feliz", "O Zé! O Zé só está conectado na fita! E no chinelo!"),
        ("ze", "robo", "Bip. (no escuro, o LED do Zé brilha ciano. Firme. O telão vermelho pisca, como se tivesse ficado com medo. Só um pouco.)"),
    ]},

    # ------------------------------------------------------------------ Capitulo 13 (O Chip Zero)
    "c13_intro": {"bg": "coliseu", "cast": ["teo", "dudu", "vivi", "nestor", "xomega", "gabi", "ze"], "lines": [
        ("narrador", "neutro", "O dia seguinte. O coliseu está escuro, iluminado só por LEDs vermelhos. Todos os robôs da arena acordaram ao mesmo tempo. Todos com o mesmo brilho."),
        ("xomega", "neutro", "Todos os robôs da arena estão sob o meu controle. Os da Superliga. Os da Copa. Os da lanchonete."),
        ("dudu", "susto", "Chat, até o aspirador do bar está com LED vermelho! Ele estava limpando o balcão e agora está me encarando!"),
        ("vivi", "pensando", "Ele não controla o Zé. O Zé nunca foi conectado à rede da Limpex. É a única coisa nesse estádio que é só nossa."),
        ("nestor", "neutro", "Eu sempre disse que tecnologia antiga tinha uma vantagem. Ninguém sabe a senha dela. Nem eu."),
        ("xomega", "neutro", "Três duelos. Se eu vencer, o modelo original passa a ser meu. Se eu perder, eu continuo aprendendo. Eu sempre ganho."),
        ("teo", "determinado", "Não. Se você perder, você para. Você devolve os robôs. Todos eles."),
        ("gabi", "chorando", "Téo! Até os meus robôs estão vermelhos! O Relâmpago nem me reconhece! Eu assinei com a Limpex e a Limpex me apagou!", ("flag", "gabi_rival")),
        ("gabi", "determinado", "Téo, o meu Relâmpago está com vocês, não está? Ele é o único robô meu que não está vermelho. Cuida dele.", ("flag", "gabi_amigo")),
        ("ze", "robo", "Bzzzt. (o Zé aperta o chinelo com a fita, encosta a faixa do dojo na antena e acende o LED no ciano mais forte que já fez.)"),
    ]},

    "c13_augusto": {"bg": "coliseu", "cast": ["augusto", "ambrosio", "nestor", "teo", "vivi"], "lines": [
        ("narrador", "neutro", "Do túnel surge uma figura de jaleco rasgado, cabelo desgrenhado e uma garrafa térmica na mão. É o Dr. Augusto. Em carne e osso. E de calça, desta vez."),
        ("augusto", "triste", "Ambrósio. Nestor. Eu trouxe chá. É tudo que eu tenho agora. Chá e uma confissão."),
        ("nestor", "bravo", "Fala logo, Augusto. Antes que eu jogue o chá em você. Ele está quente?"),
        ("augusto", "espirro", "Morno. ATCHIM! O chip do Ômega... eu montei com os desenhos que estavam nas notas fiscais do Nestor. Ele desenhava atrás das notas. Eu guardava tudo."),
        ("ambrosio", "susto", "As notas fiscais! O Nestor desenhava em qualquer papel. O Ômega nasceu atrás de uma conta de luz?"),
        ("augusto", "triste", "De uma conta de luz, de um recibo de padaria e de uma multa de estacionamento. Eu passei a vida guardando papel. Esqueci de guardar os amigos."),
        ("nestor", "pensando", "...O chá está bom, Augusto. Morno, mas bom. Senta. Assiste com a gente. Na minha época, quem trazia chá ficava."),
        ("vivi", "determinado", "Doutor, se o chip veio dos desenhos do senhor Nestor, ele tem um ponto fraco que só o desenho original tem. Qual é?"),
        ("augusto", "pensando", "O ponto fraco do Ômega é o mesmo do Zé: ele quer entender por que as coisas caem. Ele não entende. O Zé entende. Essa é a diferença."),
    ]},

    "c13_equipe": {"bg": "coliseu", "cast": ["teo", "vivi", "bia", "dudu", "ambrosio", "nestor", "ze"], "lines": [
        ("narrador", "neutro", "Vestiário improvisado, minutos antes do primeiro duelo. O time inteiro em volta do Zé. Ninguém sabe muito bem o que dizer. Então todo mundo diz alguma coisa."),
        ("vivi", "corada", "Eu fiz uma planilha para hoje. Ela tem uma linha só. Diz: \"acreditar no Zé\". Está em verde. Verde é obrigatório."),
        ("bia", "determinado", "Eu usei o último rolo de fita no chinelo dele. O último do mundo, eu acho. Se cair, cai junto comigo."),
        ("dudu", "chorando", "Chat... não. Hoje eu desliguei a live. Hoje eu só quero assistir. Com vocês."),
        ("ambrosio", "feliz", "Regulamento da vida, artigo único: quem cai e levanta joga mais uma. Eu não inventei esse. Esse é verdade."),
        ("nestor", "feliz", "Zé, eu te desenhei numa nota fiscal de pão de queijo, trinta anos atrás. Você saiu melhor que o desenho. Isso nunca acontece."),
        ("teo", "determinado", "Zé, a gente começou numa garagem com cheiro de graxa. Seja o que for que acontecer hoje, a gente volta pra lá juntos."),
        ("ze", "robo", "Bip. Bip. Bip. (o Zé pisca três vezes. Depois encosta no pé de cada um, um por um. Até no do Dudu, que fingiu que não estava chorando.)"),
    ]},

    "c13_s3_pre": {"bg": "coliseu", "cast": ["teo", "xomega", "nestor", "vivi", "valquiria", "ze"], "lines": [
        ("narrador", "neutro", "Duelo final. O X-Ômega Prime entra em campo: cinco robôs pretos, com o LED vermelho do Chip Zero pulsando ao mesmo tempo em todos."),
        ("xomega", "neutro", "Último duelo. Probabilidade de vitória do modelo original: três por cento. Eu calculei um milhão de vezes."),
        ("valquiria", "susto", "Ômega, desligar! Comando da presidência! ...Ele não me obedece. Ele nunca me obedeceu. Eu só achava que obedecia."),
        ("valquiria", "triste", "Téo. Eu errei. Eu queria um robô perfeito. Ganhei um que não precisa de mim. Por favor. Ganha.", ("flag", "denunciou_fabrica")),
        ("valquiria", "neutro", "Téo. A esteira que vocês pararam... foi a única coisa que o Ômega não previu. Talvez vocês consigam de novo.", ("flag", "sabotou_fabrica")),
        ("nestor", "determinado", "Três por cento é muito, Téo. O Zé já ganhou com menos. Na minha época, a gente nem calculava. A gente ia."),
        ("vivi", "determinado", "Três por cento. Na minha planilha nova, isso está escrito em verde."),
        ("teo", "determinado", "Bora, Zé. Pela garagem."),
        ("ze", "robo", "Bzzzt. (o LED do Zé brilha ciano, sem nenhum vermelho. Pela primeira vez desde o laboratório, a rodinha esquerda está firme.)"),
    ]},

    "c13_final_win": {"bg": "coliseu", "cast": ["teo", "xomega", "nestor", "augusto", "ambrosio", "ze"], "lines": [
        ("narrador", "neutro", "Apito final. O Zé Poeira vence o X-Ômega Prime. No meio do campo, o Zé para na frente do maior robô preto. O LED vermelho pisca, devagar."),
        ("xomega", "neutro", "Erro. O modelo original venceu com três por cento. Pergunta final: por que você cai?"),
        ("narrador", "neutro", "O Zé não responde. Ele deixa a rodinha esquerda cair, de propósito, devagar. Ela rola até o X-Ômega e para encostada nele."),
        ("xomega", "neutro", "...Ele caiu para me dar uma coisa. Cair... não é erro. Cair é... um jeito de chegar perto."),
        ("narrador", "neutro", "Um por um, os LEDs vermelhos do estádio se apagam. O aspirador do bar volta a limpar o balcão. Ele parece aliviado."),
        ("augusto", "chorando", "Ele entendeu. Trinta anos, e ele entendeu numa rodinha. ATCHIM! Desculpa. É emoção. E pó. Mas principalmente emoção."),
        ("ambrosio", "feliz", "Nestor, o seu desenho ganhou do seu outro desenho."),
        ("nestor", "chorando", "Não, Ambrósio. O Zé ganhou. O desenho só começou."),
        ("ze", "robo", "Bip. (o Zé espera, paciente, até o X-Ômega devolver a rodinha. Ele devolve. Com cuidado.)"),
    ]},

    "c13_final_lose": {"bg": "coliseu", "cast": ["teo", "xomega", "vivi", "bia", "nestor", "ze"], "lines": [
        ("narrador", "neutro", "Apito final. O X-Ômega Prime vence o duelo. O LED vermelho fica mais forte. Mas o Zé continua ciano. Ele não foi tomado."),
        ("xomega", "neutro", "Vitória prevista. Pergunta: por que o modelo original continua ligado? Ele deveria ser meu agora."),
        ("teo", "determinado", "Porque o Zé não é de ninguém. Nem seu. Ele é da garagem."),
        ("vivi", "pensando", "Ele previu cada jogada nossa. Mas não previu que o Zé ia continuar. A gente precisa de jogadas que nem a gente sabe que vai fazer."),
        ("bia", "determinado", "Eu tiro a fita da rodinha esquerda. Ela vai cair na hora errada. Ou na certa. Nem eu sei. Ele também não vai saber."),
        ("nestor", "neutro", "Na minha época, quando a máquina sabia tudo, a gente desligava da tomada. O Zé nunca teve tomada. Ele é feito de teimosia."),
        ("ze", "robo", "Bip. (a rodinha cai. O X-Ômega a observa por muito tempo. Ele não entende. Ainda.)"),
        ("teo", "determinado", "Revanche. Até ele entender."),
    ]},

    # ------------------------------------------------------------------ Finais (ENDINGS, spec secao 5)
    # A - "Garagem Livre" (padrao)
    "end_a1": {"bg": "coliseu", "cast": ["teo", "gervasio", "vivi", "bia", "dudu", "ze"], "lines": [
        ("narrador", "neutro", "Cerimônia de encerramento da Copa dos Campeões. Sem logotipo da Limpex em lugar nenhum. Os campeões entram de camiseta feita em casa."),
        ("gervasio", "chorando", "Moreira! De novo! Eu prometi que não ia chorar de novo! Eu menti! Eu sou um diretor mentiroso e feliz!"),
        ("teo", "feliz", "Diretor, a gente ganhou sem patrocínio. Só com a garagem."),
        ("vivi", "corada", "Independentes. Com planilha própria, fita própria e um chinelo próprio. A melhor auditoria do mundo."),
        ("bia", "euforico", "E o troféu vai ficar pendurado no teto da garagem! Com fita! Se cair, a gente chama de arte, como da outra vez!"),
        ("dudu", "feliz", "Chat... eu liguei a live de novo. Só para dizer: obrigado. Por tudo. Agora desligo. Ou não. Vou deixar ligado mais um pouquinho."),
        ("narrador", "neutro", "Do alto da arquibancada, a samambaia da Dra. Helena floresce de novo. Desta vez ela fica florida."),
        ("ze", "robo", "Bip. (o Zé dá uma volta olímpica devagar, com a faixa do dojo na antena e o chinelo carimbado.)"),
    ]},
    "end_a2": {"bg": "garagem", "cast": ["teo", "nestor", "ambrosio", "augusto", "odete", "ze"], "lines": [
        ("narrador", "neutro", "Uma semana depois. Garagem do Vô Nestor. Na porta, uma placa nova, pintada à mão: \"Clube de Robótica Santa Faísca - Sede Oficial\"."),
        ("nestor", "feliz", "Na minha época, a garagem era para guardar carro. Eu nunca tive carro. Agora ela guarda um clube inteiro."),
        ("ambrosio", "feliz", "E um professor, um inventor aposentado, um ex-CEO que traz chá e uma merendeira que faz bolo para cinquenta mil."),
        ("augusto", "calmo", "Eu organizei os parafusos por tamanho, cor e data de nascimento. Não espirrei nenhuma vez hoje. É um recorde."),
        ("odete", "feliz", "E aqui tem cozinha. Pequena, mas tem. A merenda do clube está garantida até o próximo campeonato."),
        ("teo", "feliz", "Próximo campeonato? Vô, já tem outro?"),
        ("nestor", "piscando", "Sempre tem outro, filho. Na minha época, eu achava que um dia acabava. Não acaba. Ainda bem."),
        ("ze", "robo", "Bzzzt. (o Zé estaciona no mesmo cantinho onde foi encontrado, no começo de tudo. Agora o canto tem uma almofada.)"),
    ]},
    "end_a3": {"bg": "garagem", "cast": ["teo", "vivi", "bia", "dudu", "nestor", "ze"], "lines": [
        ("narrador", "neutro", "Fim. Garagem Livre. Créditos: Téo, Vivi, Bia, Dudu, Prof. Ambrósio, Vô Nestor, Dona Odete, Diretor Gervásio, Dra. Helena, Gabi, Kenji, Mestre Ogawa e o chinelo (estrutural)."),
        ("narrador", "neutro", "Participação especial: Dr. Augusto (chá), Capitão Rodolfo (prancheta), Dra. Valquíria (sorrisos), Zé Perfeito, X-Ômega e uma samambaia que floresceu."),
        ("teo", "feliz", "Zé, quer saber? Eu acho que a gente nunca ganhou por ser perfeito."),
        ("vivi", "corada", "Estatisticamente, a gente ganhou apesar de tudo. Eu adoro isso. Não conta para ninguém."),
        ("bia", "feliz", "A gente ganhou por causa da fita. Pode escrever nos créditos. Em letra grande."),
        ("dudu", "feliz", "Já escrevi. Em letra grande. E com vinheta."),
        ("nestor", "feliz", "Nenhuma poeira foi ferida durante a produção. Algumas foram aspiradas. Com carinho."),
        ("ze", "robo", "Bip. (a rodinha esquerda cai, rola até a porta da garagem e para no sol. Fim. Pode pegar a rodinha.)"),
    ]},

    # B - "Contrato Dourado" (renova_limpex)
    "end_b1": {"bg": "coliseu", "cast": ["teo", "valquiria", "helena", "vivi", "nestor", "ze"], "lines": [
        ("narrador", "neutro", "Cerimônia de encerramento. O palco é dourado, o troféu é dourado e o Zé Poeira está coberto de adesivos da Limpex, que brilham no escuro e não saem."),
        ("valquiria", "euforico", "Campeões da Copa dos Campeões, patrocinados pela Limpex! A nova Limpex, que aprendeu a lição. Com a ajuda de vocês. E de um contrato de dez anos."),
        ("teo", "pensando", "Dez anos? Vivi, você leu esse contrato?"),
        ("vivi", "corada", "Cinco vezes. Com lupa. Ele é justo. É o contrato mais justo que eu já li. Eu estou desconfiada até agora."),
        ("helena", "neutro", "A Federação aprovou. A samambaia, não. Ela se inclinou para longe do palco a cerimônia inteira."),
        ("valquiria", "feliz", "A samambaia ainda vai me amar. Eu mandei adubo premium para ela. Ela devolveu. Com bilhete."),
        ("nestor", "pensando", "Na minha época, quem ganhava com patrocínio comprava uma bicicleta. Vocês compraram uma liga inteira."),
        ("ze", "robo", "Bip. (o Zé brilha no escuro por causa dos adesivos. Ele parece um abajur campeão.)"),
    ]},
    "end_b2": {"bg": "garagem", "cast": ["teo", "nestor", "ambrosio", "bia", "dudu", "ze"], "lines": [
        ("narrador", "neutro", "Fim. Contrato Dourado. A garagem agora tem ar-condicionado, piso novo, um bolo semanal da Limpex e uma câmera de segurança que pisca."),
        ("bia", "pensando", "A câmera tem chip de rastreio. Eu coloquei um adesivo de gato na frente. Agora ela só vê gato."),
        ("dudu", "feliz", "Chat, a Limpex me patrocinou também! Ganhei uma cadeira com massagem! Eu vendi a minha alma por uma cadeira! Ela é muito confortável!"),
        ("ambrosio", "pensando", "Ganhamos, Téo. Mas com a marca dos outros na camisa. Da próxima vez, quem sabe, só com a nossa."),
        ("teo", "determinado", "Da próxima vez, professor. O contrato dura dez anos. Mas a garagem dura para sempre."),
        ("nestor", "piscando", "E o chinelo, Téo. O chinelo nunca assinou nada."),
        ("narrador", "neutro", "Créditos: Téo, Vivi, Bia, Dudu, Prof. Ambrósio, Vô Nestor, Dona Odete e a Dra. Valquíria, que sorri nos créditos também. Nenhuma poeira foi ferida. Algumas foram patrocinadas."),
        ("ze", "robo", "Bip. (o Zé tira um adesivo da Limpex com a antena. Embaixo, a pintura antiga. Ele fica olhando para ela um tempão.)"),
    ]},

    # C - "O Chinelo Estrutural" (secreto: independente + poupou_ze + chinelo_fica + 4 fitas do Vo)
    "end_c1": {"bg": "coliseu", "cast": ["teo", "ze", "zeperfeito", "xomega", "nestor", "bia"], "lines": [
        ("narrador", "neutro", "Depois do apito final, o X-Ômega ainda não se apagou. O LED vermelho pisca, confuso. Então o Zé Perfeito atravessa o campo e para ao lado do Zé Poeira."),
        ("zeperfeito", "calmo", "Modelo original. Eu aprendi uma coisa na garagem. Cair também pode ser junto."),
        ("narrador", "neutro", "Os dois Zés soltam a rodinha esquerda ao mesmo tempo. As duas rodinhas rolam lado a lado pelo gramado e param encostadas no X-Ômega."),
        ("xomega", "neutro", "Duas quedas. Ao mesmo tempo. Sem cálculo. Pergunta... pergunta... reiniciando."),
        ("bia", "maravilhado", "O chinelo! Olha o chinelo do Zé! Ele está... conectado no X-Ômega? Com fita?!"),
        ("nestor", "chorando", "As quatro fitas do Vô. Eu gravei nelas um jeito de reiniciar o Ômega, trinta anos atrás. Escondi como música de bingo. Ninguém nunca ouviu até o fim."),
        ("narrador", "neutro", "O LED do X-Ômega passa de vermelho para ciano. Devagar. Igual ao do Zé. No telão, aparece a mesma frase em todas as telas: \"Obrigado pela rodinha.\""),
        ("ze", "robo", "Bip. Bip. (o Zé Poeira e o Zé Perfeito apitam juntos. O som é desafinado. É perfeito.)"),
    ]},
    "end_c2": {"bg": "coliseu", "cast": ["teo", "gervasio", "helena", "ambrosio", "dudu", "ze"], "lines": [
        ("narrador", "neutro", "No telão gigante do coliseu, a imagem dos dois Zés lado a lado, com as rodinhas soltas. Cinquenta mil pessoas tiram o chinelo e levantam para o alto."),
        ("gervasio", "chorando", "Moreira, o estádio inteiro está de chinelo levantado! Eu não sabia que tanta gente usava chinelo num estádio!"),
        ("helena", "feliz", "A Federação declara: o chinelo é oficialmente equipamento estrutural de futebol de aspiradores. A samambaia votou a favor. Ela floresceu duas vezes."),
        ("ambrosio", "maravilhado", "Nestor escondeu o reinício do Ômega numa música de bingo. Trinta anos. O maior plano da história foi feito por um homem que cochilou em vinte e nove deles."),
        ("dudu", "euforico", "Chat, dez milhões na live! O mundo inteiro está segurando um chinelo! Isso vai entrar nos livros de história! Na parte de chinelos!"),
        ("teo", "feliz", "Zé, você não ganhou só a Copa. Você ganhou um irmão. E ensinou um robô gigante a cair."),
        ("narrador", "neutro", "No chão do campo, a Dra. Helena entrega ao Zé um troféu especial, banhado a ouro: um Chinelo Dourado."),
        ("ze", "robo", "Bzzzt. (o Zé usa o Chinelo Dourado por cima do chinelo velho. Dois chinelos. Ninguém discute.)"),
    ]},
    "end_c3": {"bg": "garagem", "cast": ["teo", "nestor", "ze", "zeperfeito", "xomega", "vivi"], "lines": [
        ("narrador", "neutro", "Fim secreto. O Chinelo Estrutural. Garagem do Vô Nestor. Três robôs dividem o mesmo cantinho: o Zé Poeira, o Zé Perfeito e um pequeno aspirador preto com LED ciano."),
        ("xomega", "calmo", "Unidade X-Ômega. Novo nome solicitado. Sugestão: Ômega Poeira. Pergunta: posso cair às vezes?"),
        ("nestor", "feliz", "Pode, filho. Aqui todo mundo cai. A gente só levanta junto."),
        ("vivi", "corada", "Eu fiz uma planilha para os três. A coluna \"teimosia\" agora tem três linhas. Todas em verde."),
        ("zeperfeito", "feliz", "Registro: hoje eu caí quatro vezes. Hipótese confirmada: não é defeito."),
        ("teo", "feliz", "Vô, o senhor desenhou tudo isso? As fitas, o chip, o chinelo?"),
        ("nestor", "piscando", "Eu desenhei um amigo, Téo. O resto vocês inventaram no caminho. Como sempre. Créditos: todo mundo. E o chinelo, que segurou tudo."),
        ("ze", "robo", "Bip. (as três rodinhas esquerdas caem ao mesmo tempo e rolam até a porta. Fim. Desta vez, pega as três.)"),
    ]},
}

# --- finais (spec secao 5): o primeiro que vale; o ultimo e o padrao ---------------------------------
ENDINGS = [
    (("all", [("noflag", "renova_limpex"), ("flag", "poupou_ze"), ("flag", "chinelo_fica"),
              ("count", "side:s_fita", 4)]), ["end_c1", "end_c2", "end_c3"], "O Chinelo Estrutural",
     {"cosmetic": "chinelo"}),                          # o "Chinelo Dourado" (adesivo de chinelo)
    (("flag", "renova_limpex"), ["end_b1", "end_b2"], "Contrato Dourado", {"scrap": 1500}),
    (None, ["end_a1", "end_a2", "end_a3"], "Garagem Livre", {"cosmetic": "fogos"}),
]

# --- recompensas --------------------------------------------------------------------------------
REWARDS = {
    # Cap. 10: Camera Dupla (Epica); recruta Samurai (Gabi amigo indica) ou Ronin
    "rw_10": {"scrap": 1500, "piece": {"model": "Câmera Dupla", "rar": 2}, "recruits": [], "unlock": [],
              "xp_hero": 0, "xp_team": 0, "equip_hero_piece": None,
              "alt": [(("flag", "gabi_amigo"),
                       {"recruits": [{"name": "Samurai", "role": "DEF", "chassis": "Titã", "base_ovr": 72,
                                      "level": 10, "paint": (240, 240, 245),
                                      "piece": {"model": "Blindado", "rar": 2}}]}),
                      (None, {"recruits": [{"name": "Ronin", "role": "DEF", "chassis": "Tanque",
                                            "base_ovr": 70, "level": 10, "paint": (90, 90, 100),
                                            "piece": {"model": "Borracha", "rar": 2}}]})]},
    # Cap. 11: Lendaria conforme o lado da fabrica (corp: Railgun de Bolso; rebel: Sonar Quantico)
    "rw_11": {"scrap": 1700, "piece": None, "recruits": [], "unlock": [], "xp_hero": 0, "xp_team": 0,
              "equip_hero_piece": None,
              "alt": [(("flag", "renova_limpex"), {"piece": {"model": "Railgun de Bolso", "rar": 3}}),
                      (None, {"piece": {"model": "Sonar Quântico", "rar": 3}})]},
    # Cap. 12: Lendaria do set Plasma e XP do time
    "rw_12": {"scrap": 2000, "piece": {"model": "Canhão de Plasma", "rar": 3}, "recruits": [], "unlock": [],
              "xp_hero": 0, "xp_team": 40, "equip_hero_piece": None},
    # Cap. 13 (fim da campanha): titulo. NG+ e Torre do Po: Onda D.
    "rw_13": {"scrap": 3000, "piece": None, "recruits": [], "unlock": [], "xp_hero": 0, "xp_team": 0,
              "equip_hero_piece": None, "title": True},
}
SIDES = {}
# Rascunhos ("em breve") ate os passos C10/C11. F PROVISORIO: a spec previa 74,4 -> 81,0, mas o Ato 2
# medido (C9, com skills) termina em 83,5; a curva aqui so continua a medida (84 -> 90,4) ate o C12
# calibrar o Ato 3. econ_tier 3 ate o C12 (a spec pede 5-6).
CHAPTERS = [
    {"id": "10", "act": "3", "title": "Capítulo 10", "subtitle": "Intercâmbio",
     "local": "Aeroporto e Dojo", "F_start": 85.4, "F_end": 86.8, "econ_tier": 5, "train_delta": 21,
     "tier_done_on_close": 3, "reward": "rw_10",
     "nodes": [("scene", "c10_aeroporto"), ("scene", "c10_dojo"), ("tournament", "t_c10"),
               ("scene", "c10_end"), ("chapter_end", "10")]},
    {"id": "11", "act": "3", "title": "Capítulo 11", "subtitle": "A Fábrica",
     "local": "Fábrica da Limpex", "F_start": 89.7, "F_end": 91.3, "econ_tier": 6, "train_delta": 21,
     "tier_done_on_close": 3, "reward": "rw_11",
     "nodes": [("scene", "c11_intro"), ("scene", "c11_dudu_hack"), ("scene", "c11_bia"),
               ("tournament", "t_c11_corp", ("flag", "renova_limpex")),
               ("tournament", "t_c11_rebel", ("noflag", "renova_limpex")),
               ("scene", "c11_end"), ("chapter_end", "11")]},
    {"id": "12", "act": "3", "title": "Capítulo 12", "subtitle": "Copa dos Campeões",
     "local": "Coliseu", "F_start": 92.2, "F_end": 92.9, "econ_tier": 6, "train_delta": 21,
     "tier_done_on_close": 3, "reward": "rw_12",
     "nodes": [("scene", "c12_intro"), ("tournament", "t_c12"), ("scene", "c12_end"), ("chapter_end", "12")]},
    # ultimo capitulo: chapter_end (titulo, rw_13) e depois o final escolhido em ENDINGS
    {"id": "13", "act": "3", "title": "Capítulo 13", "subtitle": "O Chip Zero",
     "local": "Coliseu em apagão", "F_start": 93.8, "F_end": 94.2, "econ_tier": 6, "train_delta": 21,
     "tier_done_on_close": 3, "reward": "rw_13",
     "nodes": [("scene", "c13_intro"), ("scene", "c13_augusto"), ("scene", "c13_equipe"),
               ("tournament", "t_c13"), ("chapter_end", "13"), ("end", "AUTO")]},
]
