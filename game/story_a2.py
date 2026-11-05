# -*- coding: utf-8 -*-
"""Dados da campanha: Ato 2 (Superliga Limpex, caps. 6-9). Modulo PURO (so dados, sem imports).

story.py junta estes dicts/listas nos seus (story._extend) e e o unico ponto de import para o resto
do jogo. Mesmas regras e formatos de story.py (ver o docstring de la); ids nao podem repetir os de
outros modulos. Capitulos aqui levam "act" e entram depois dos do Ato 1, na ordem da lista.

C6: cap. 6 (Taca de Acesso). C7: cap. 7 (liga, escolha B2) e cap. 8 (copa com quartas). Os ovr/F
seguem os valores iniciais da spec (secao 7) e o econ_tier fica em 3 ate o C9 estender a economia
(TIER_MUL com 7 entradas) e calibrar o Ato 2. Cap. 9 e rascunho ("em breve") ate o C8.
"""

# --- elenco novo (spec secao 2) -----------------------------------------------------------------
CHARACTERS = {
    "nestor": {"name": "VÔ NESTOR", "color": (230, 170, 90), "skin": (230, 190, 155),
               "hair": ("calvo", (200, 200, 205)), "acc": ["bigode", "bengala", "chinelo"],
               "outfit": ("colete", (150, 110, 70))},
    "valquiria": {"name": "DRA. VALQUÍRIA", "color": (255, 110, 170), "skin": (245, 215, 195),
                  "hair": ("coque", (240, 240, 245)), "acc": ["tiara"], "outfit": ("blazer", (220, 60, 120))},
    "gabi": {"name": "GABI TROVÃO", "color": (60, 140, 255), "skin": (205, 160, 120),
             "hair": ("espetado", (40, 120, 255)), "acc": ["bone"], "outfit": ("camiseta", (250, 210, 40))},
    "odete": {"name": "DONA ODETE", "color": (255, 200, 120), "skin": (180, 130, 95),
              "hair": ("coque", (170, 170, 170)), "acc": ["avental"], "outfit": ("avental", (240, 240, 230))},
    "ogawa": {"name": "MESTRE OGAWA", "color": (120, 200, 160), "skin": (225, 190, 150),
              "hair": ("raspado", (60, 60, 60)), "acc": ["bigode"], "outfit": ("kimono", (60, 70, 90))},
}

# --- times (ordem dos slots = garage.LINEUP_SLOTS: GK, DEF, MID, MID, ATT) ------------------------
_CH5 = ["Goleiro", "Tanque", "Disco", "Orbital", "Velocista"]

TEAMS = {
    # ---- Cap. 6 (Taca de Acesso)
    "pia": {"name": "Brigada da Pia", "color": (110, 190, 225), "ovr": 50,
            "names": ["Torneira", "Esponja", "Detergente", "Ralo", "Bucha"],
            "chassis": list(_CH5), "paint": (120, 200, 230), "perfect": False},
    "rodo": {"name": "Esquadrão do Rodo Mestre", "color": (230, 140, 60), "ovr": 51,
             "names": ["Rodo", "Balde", "Pano", "Cera", "Vassoura"],
             "chassis": list(_CH5), "paint": (235, 145, 65), "perfect": False},
    "faxmk3": {"name": "Faxineiros Mk III", "color": (160, 120, 220), "ovr": 52,
               "names": ["Esfregão", "Lustra", "Brilho", "Polidor", "Tira-Mancha"],
               "chassis": list(_CH5), "paint": (165, 125, 225), "perfect": False},
    "trovoes": {"name": "Gabi e os Trovões", "color": (60, 140, 255), "ovr": 57,
                "names": ["Raio", "Faísca", "Estrondo", "Ventania", "Relâmpago"],
                "chassis": list(_CH5), "paint": (250, 210, 40), "perfect": False},
    # chefe do cap. 6: a nova linha da Limpex (perfeitos, chip legal)
    "higiene": {"name": "Brigada Higiene", "color": (120, 230, 255), "ovr": 61,
                "names": ["BH-01", "BH-02", "BH-03", "BH-04", "BH-05"],
                "chassis": list(_CH5), "paint": (235, 250, 255), "perfect": True},
    # ---- Cap. 7 (Superliga: pontos corridos)
    "esfregao": {"name": "Real Esfregão", "color": (200, 80, 80), "ovr": 51,
                 "names": ["Cabo", "Felpa", "Torção", "Balde", "Espuma"],
                 "chassis": list(_CH5), "paint": (210, 90, 90), "perfect": False},
    "microondas": {"name": "Atlético Micro-ondas", "color": (240, 170, 50), "ovr": 52,
                   "names": ["Pipoca", "Bandeja", "Timer", "Prato", "Bip"],
                   "chassis": list(_CH5), "paint": (245, 180, 60), "perfect": False},
    "poarroz": {"name": "Dínamo Pó de Arroz", "color": (240, 190, 210), "ovr": 52,
                "names": ["Talco", "Esponjinha", "Pluma", "Pétala", "Blush"],
                "chassis": list(_CH5), "paint": (245, 200, 215), "perfect": False},
    "ventilador": {"name": "Sporting Ventilador", "color": (90, 200, 220), "ovr": 53,
                   "names": ["Hélice", "Brisa", "Rajada", "Giro", "Turbo"],
                   "chassis": list(_CH5), "paint": (100, 205, 225), "perfect": False},
    "cera": {"name": "Clube da Cera Líquida", "color": (220, 200, 90), "ovr": 54,
             "names": ["Brilho", "Lustre", "Escorrega", "Verniz", "Espelho"],
             "chassis": list(_CH5), "paint": (230, 210, 100), "perfect": False},
    "impec3": {"name": "Os Impecáveis Mk III", "color": (0, 220, 255), "ovr": 59,
               "names": ["LX-11", "LX-12", "LX-13", "LX-14", "LX-15"],
               "chassis": list(_CH5), "paint": (235, 248, 255), "perfect": True},
    # chefe do cap. 7: Platinum Elite do Rodolfo (perfeitos)
    "plat_elite": {"name": "Platinum Elite", "color": (200, 210, 230), "ovr": 63,
                   "names": ["PE-01", "PE-02", "PE-03", "PE-04", "PE-05"],
                   "chassis": list(_CH5), "paint": (220, 228, 240), "perfect": True},
    # ---- Cap. 8 (Playoffs da Superliga)
    "pano": {"name": "Coletivo do Pano", "color": (170, 140, 110), "ovr": 53,
             "names": ["Flanela", "Microfibra", "Algodão", "Retalho", "Trapo"],
             "chassis": list(_CH5), "paint": (180, 150, 120), "perfect": False},
    "sempoeira": {"name": "Os Sem-Poeira", "color": (150, 230, 200), "ovr": 54,
                  "names": ["Vácuo", "Filtro", "HEPA", "Ciclone", "Ar Puro"],
                  "chassis": list(_CH5), "paint": (160, 235, 205), "perfect": False},
    "lavanderia": {"name": "Lavanderia FC", "color": (110, 150, 240), "ovr": 55,
                   "names": ["Amaciante", "Centrífuga", "Molho", "Varal", "Prendedor"],
                   "chassis": list(_CH5), "paint": (120, 160, 245), "perfect": False},
    "bunnies_pro": {"name": "Dust Bunnies Pro", "color": (230, 90, 90), "ovr": 57,
                    "names": ["Tex Jr.", "Donut II", "Cowboy", "Popcorn", "Jumbo Max"],
                    "chassis": list(_CH5), "paint": (235, 100, 100), "perfect": False},
    "kenji2": {"name": "Dojo do Kenji 2.0", "color": (255, 120, 160), "ovr": 60,
               "names": ["Katana", "Bonsai", "Tofu", "Samurai", "Haiku"],
               "chassis": list(_CH5), "paint": (245, 245, 250), "perfect": False},
    # chefe do cap. 8: Guarda Zero da Valquiria (perfeitos, LED vermelho)
    "guarda_zero": {"name": "Guarda Zero", "color": (230, 40, 60), "ovr": 64,
                    "names": ["GZ-01", "GZ-02", "GZ-03", "GZ-04", "GZ-05"],
                    "chassis": list(_CH5), "paint": (40, 40, 48), "perfect": True},
}

# --- torneios -----------------------------------------------------------------------------------
TOURNAMENTS = {
    # Cap. 6: copa (grupo + SF + final) no Ginasio Limpex Park. Estagios (F_rec / O): G1 66,6 / 50;
    # G2 66,9 / 51; G3 67,3 / 52; SF 67,7 / 57; F 68,0 / 61 (boss_delta 7,0). Calibragem: C9.
    "t_c6": {
        "chapter": "6", "local": "Ginásio Limpex Park", "bg": "arena", "format": "cup",
        "group": ["pia", "rodo", "faxmk3"], "qf": None, "sf": "trovoes", "final": "higiene",
        "boss": "higiene", "boss_delta": 7.0, "regular_delta": (15, 17),
        "hooks": {"before": {"G2": "c6_g2_odete", "SF": "c6_gabi_pre", "F": "c6_final_pre"},
                  "after": {"SF": "c6_sf_pos"},
                  "win": "c6_final_win", "lose": "c6_final_lose", "elim": "c6_repescagem"},
    },
    # Cap. 7: liga (R1-R5, top 4 a SF) no Estadio Limpex. Estagios (F_rec / O): R1 68,4 / 51; R2 68,7 / 52;
    # R3 69,0 / 52; R4 69,3 / 53; R5 69,6 / 54; SF 69,9 / 59; F 70,2 / 63 (boss_delta 7,2). B2 depois da R2.
    "t_c7": {
        "chapter": "7", "local": "Estádio Limpex", "bg": "estadio", "format": "league",
        "group": ["esfregao", "microondas", "poarroz", "ventilador", "cera"], "qf": None, "sf": "impec3",
        "final": "plat_elite", "boss": "plat_elite", "boss_delta": 7.2, "regular_delta": (15, 18),
        "hooks": {"before": {"R3": "c7_g3_dudu", "SF": "c7_sf_pre", "F": "c7_final_pre"},
                  "after": {"R2": "c7_contrato"},
                  "win": "c7_final_win", "lose": "c7_final_lose", "elim": "c7_repescagem"},
    },
    # Cap. 8: copa com quartas. Estagios (F_rec / O): G1 70,4 / 53; G2 70,7 / 54; G3 71,0 / 55; QF 71,4 / 57;
    # SF 71,7 / 60; F 72,0 / 64 (boss_delta 8,0). Grupo +1 sobre a spec (regulares F-O <= 18).
    "t_c8": {
        "chapter": "8", "local": "Estádio Limpex (noite)", "bg": "estadio", "format": "cup",
        "group": ["pano", "sempoeira", "lavanderia"], "qf": "bunnies_pro", "sf": "kenji2",
        "final": "guarda_zero", "boss": "guarda_zero", "boss_delta": 8.0, "regular_delta": (15, 18),
        "hooks": {"before": {"G2": "c8_helena", "QF": "c8_qf_pre", "SF": "c8_sf_kenji", "F": "c8_final_pre"},
                  "after": {},
                  "win": "c8_final_win", "lose": "c8_final_lose", "elim": "c8_repescagem"},
    },
}

# --- cenas --------------------------------------------------------------------------------------
SCENES = {
    # ------------------------------------------------------------------ Capitulo 6 (Taca de Acesso)
    # Logo depois do epilogo do Ato 1 (no 0 do cap. 6): o Vo Nestor volta do cruzeiro. Fica numa cena
    # propria para que saves migrados (epilogo ja em `done`) tambem vejam a volta dele.
    "c6_nestor": {"bg": "garagem", "cast": ["teo", "ambrosio", "vivi", "bia", "dudu", "nestor", "ze"], "lines": [
        ("narrador", "neutro", "Na mesma noite. A rodinha do Zé parou num chinelo marrom, gasto, com cheiro de protetor solar. Atrás do chinelo, uma mala de cruzeiro. Atrás da mala, um senhor."),
        ("nestor", "feliz", "Na minha época, rodinha que fugia voltava sozinha. Oi, Téo. O bingo acabou cedo. Eu ganhei uma panela."),
        ("teo", "susto", "Vô?! O senhor não estava no navio?!"),
        ("nestor", "malicioso", "O navio atracou ontem. Liguei do porto só para fazer suspense. Na minha idade, suspense é exercício."),
        ("dudu", "euforico", "Chat, é ele! O Vô Nestor! O criador do Zé Poeira! Alguém segura a câmera, eu vou desmaiar com estilo."),
        ("nestor", "neutro", "Trouxe uma coisa na mala, entre a panela e as meias. (abre um tubo de papelão) A planta original do Aspiradex."),
        ("bia", "maravilhado", "Isso é a planta do Zé? Feita à mão? Com régua? Eu vou plastificar. Depois eu choro em cima. Nessa ordem."),
        ("ambrosio", "pensando", "Nestor, metade disso está em branco. Isso não tem manual."),
        ("nestor", "piscando", "Não tem manual, Ambrósio. Tem fé. E fita. O resto a gente inventa no caminho, como sempre."),
        ("vivi", "pensando", "Com todo o respeito, senhor Nestor: \"inventar no caminho\" não é um plano. É um cronograma de risco."),
        ("nestor", "feliz", "Você deve ser a Valentina. Gostei. Na minha época, quem fazia planilha era chamado de bruxa. Era um elogio."),
        ("ze", "robo", "Bip. (o Zé rola até o Vô Nestor e encosta a cabeça na bengala dele. Ninguém diz nada por um tempo.)"),
    ]},

    "c6_convite": {"bg": "garagem", "cast": ["teo", "nestor", "ambrosio", "vivi", "bia", "valquiria"], "lines": [
        ("narrador", "neutro", "Três dias depois. Um drone branco da Limpex entra pela janela da garagem e pousa, com muita elegância, em cima da samambaia que a Dra. Helena mandou de presente."),
        ("narrador", "neutro", "O drone, numa voz educada: \"Perdão, senhora samambaia. Perdão.\" Ele solta um envelope dourado e projeta um holograma no meio da garagem."),
        ("valquiria", "feliz", "Olá, campeões! Dra. Valquíria Brilhante, nova CEO da Limpex. Irmã caçula do Augusto. Sim, aquele. Ele manda um espirro."),
        ("teo", "susto", "A Limpex de novo?! Vocês não foram desclassificados?"),
        ("valquiria", "feliz", "A antiga Limpex, sim. A nova Limpex é sorridente, transparente e cheirosa. Eu mesma escolhi o cheiro. É lavanda corporativa."),
        ("valquiria", "convencida", "E vocês aceitaram o nosso patrocínio no Estadual. Isso faz de nós quase uma família. Uma família com contrato.", ("flag", "patroc")),
        ("valquiria", "neutro", "Convite oficial: a Taça de Acesso, no Ginásio Limpex Park. O campeão entra na Superliga Limpex, a liga profissional de aspiradores."),
        ("nestor", "pensando", "Brilhante, é? Na minha época, quem sorria tanto assim estava vendendo enciclopédia. Ou aspirador."),
        ("valquiria", "piscando", "Senhor Nestor! Que honra. Meu irmão fala muito do senhor. Quase sempre espirrando."),
        ("vivi", "pensando", "Superliga é outro nível. Times profissionais, robôs patrocinados, regulamento de quarenta páginas. Eu já quero ler."),
        ("bia", "determinado", "A gente vai. Só que dessa vez eu levo fita profissional. A cinza. A que não descola nem com reza."),
        ("ambrosio", "neutro", "Aceitamos, doutora. Mas o Zé joga com o chip dele. O original. Sem nenhum ajuste de fábrica."),
        ("valquiria", "feliz", "Claro! Na nova Limpex, todo mundo é livre. Livre e monitorado com carinho. Até a Taça! (o holograma pisca e some)"),
        ("narrador", "neutro", "O drone pede desculpas à samambaia mais uma vez e sai pela janela. A samambaia, pela primeira vez, parece preocupada."),
    ]},

    "c6_g2_odete": {"bg": "arena", "cast": ["teo", "odete", "dudu", "vivi", "bia", "ze"], "lines": [
        ("narrador", "neutro", "Ginásio Limpex Park, segunda rodada. A arquibancada tem lugar para três mil pessoas. Hoje, doze. Onze trouxeram cartaz."),
        ("odete", "feliz", "Téo, meu filho! A Dona Odete veio! Trouxe bolo de fubá para a torcida inteira. Deu certinho: doze fatias."),
        ("teo", "feliz", "Dona Odete! A senhora veio da escola até aqui?"),
        ("odete", "convencida", "De ônibus, de trem e de carona num caminhão de picolé. Merendeira não falta jogo. Merendeira tem escala."),
        ("dudu", "euforico", "Chat, a Dona Odete! A lenda da merenda! O bolo dela tem mais seguidores do que eu."),
        ("narrador", "neutro", "O cheiro de bolo de fubá atravessa o ginásio. Do outro lado, os pilotos do Esquadrão do Rodo Mestre param de calibrar os robôs e olham para a arquibancada."),
        ("vivi", "pensando", "Eles estão olhando para o bolo. Estatisticamente, time com fome erra mais passe. Dona Odete, a senhora é uma estratégia."),
        ("odete", "piscando", "Eu sei, querida. Trinta anos de recreio. Eu derrubo um time só com o cheiro do forno."),
        ("bia", "feliz", "Guarda uma fatia para o Zé? Ele não come, mas gosta de ficar perto."),
        ("ze", "robo", "Bip. (o Zé estaciona ao lado do pote de bolo e fica ali, muito digno.)"),
    ]},

    "c6_gabi_pre": {"bg": "arena", "cast": ["teo", "gabi", "vivi", "dudu", "bia", "ze"], "lines": [
        ("narrador", "neutro", "Semifinal. Do túnel sai um garoto de boné azul, camiseta amarela e um tênis que pisca a cada passo. Atrás dele, cinco robôs pintados de raio."),
        ("gabi", "convencido", "E aí, campeão do mundo. Gabi Trovão. Catorze anos, três patrocinadores e um robô que faz de zero a cem em um segundo."),
        ("teo", "neutro", "Prazer, Gabi. Eu sou o Téo. E esse é o Zé Poeira."),
        ("gabi", "malicioso", "Eu sei quem vocês são. Eu sou o futuro. E você é o... (olha para o pé do Zé) ...o chinelo."),
        ("bia", "bravo", "O chinelo é estrutural! Tira o chinelo e o Zé tomba para a esquerda!"),
        ("gabi", "piscando", "Tá vendo? Tecnologia de museu. Meu robô tem setenta sensores. O seu tem uma sandália."),
        ("dudu", "suor", "Chat, ele tem dois milhões de seguidores. Eu tenho trezentos. Contando a minha mãe três vezes."),
        ("vivi", "convencida", "Setenta sensores e nenhum mede humildade. Anotado. Téo, a gente joga pelo meio. Ele é rápido, mas é ansioso."),
        ("gabi", "determinado", "Ansioso, eu? Eu sou veloz. É diferente. Bola em jogo, vovô."),
        ("ze", "robo", "Bzzzt. (a rodinha esquerda treme, mas fica no lugar. Por enquanto.)"),
    ]},

    "c6_sf_pos": {"bg": "arena", "cast": ["teo", "gabi", "dudu", "vivi", "ambrosio"], "lines": [
        ("narrador", "neutro", "Apito final da semifinal. Vitória do Zé Poeira. As doze pessoas da arquibancada fazem barulho de vinte."),
        ("teo", "feliz", "Boa partida, Gabi! O seu time é rápido demais!"),
        ("narrador", "neutro", "O Gabi não responde. Ele pega o microfone da transmissão, que nem era dele, e se vira para as câmeras."),
        ("gabi", "convencido", "Pessoal, foi um aquecimento. Meu robô estava no modo econômico. Na próxima, eu volto no modo verdade."),
        ("dudu", "bravo", "Chat, ele roubou o meu enquadramento. Eu passei vinte minutos ajeitando essa luz."),
        ("gabi", "neutro", "Ei, Téo. (dá um sorriso cheio de pena) Aproveita. Chinelo não dura muito na Superliga."),
        ("vivi", "pensando", "Ele perdeu e saiu falando como se tivesse ganhado. Isso é uma técnica. Eu deveria anotar. Não vou anotar."),
        ("ambrosio", "pensando", "Esse menino corre rápido demais para quem diz que não está com medo."),
    ]},

    "c6_final_pre": {"bg": "arena", "cast": ["teo", "valquiria", "ambrosio", "vivi", "bia", "nestor"], "lines": [
        ("narrador", "neutro", "Final da Taça de Acesso. As luzes do ginásio mudam para um azul de hospital. Entram cinco robôs brancos, idênticos, em fila perfeita."),
        ("valquiria", "feliz", "Apresento a Brigada Higiene! A nova linha da Limpex. Sem overclock, sem trapaça, sem um grão de poeira. Só eficiência e sorrisos."),
        ("bia", "pensando", "Eles são perfeitos de novo. Eu desconfio de tudo que é perfeito. Inclusive desse ginásio."),
        ("valquiria", "piscando", "Desconfiança é ótima! Combina com a nossa política de transparência. Tudo o que vocês falam é gravado. Para a sua segurança."),
        ("nestor", "bravo", "Na minha época, robô de time grande pelo menos tinha um parafuso solto. Esses aí parecem embalagem."),
        ("ambrosio", "neutro", "Mesmo desenho do X-9, só que com chip legal. A Valquíria é mais esperta do que o irmão."),
        ("vivi", "determinado", "Eles jogam em linha, muito certinhos. Se a bola sair do lugar previsto, eles demoram meio segundo para recalcular."),
        ("teo", "determinado", "Meio segundo é tudo que o Zé precisa. Bora, Zé. Só mais um."),
    ]},

    # B1: Gabi aliado (gabi_amigo) ou rival recorrente (gabi_rival); ver spec secao 4
    "c6_final_win": {"bg": "arena", "cast": ["teo", "gabi", "valquiria", "nestor", "vivi", "ze"], "lines": [
        ("narrador", "neutro", "Apito final. O placar do Ginásio Limpex Park acende: Zé Poeira, campeão da Taça de Acesso. A equipe está na Superliga."),
        ("nestor", "chorando", "Na minha época... na minha época não tinha isso. Ninguém me avisou que ia ter isso. Alguém tem um lenço? A Bia tem fita?"),
        ("valquiria", "feliz", "Parabéns! Bem-vindos à Superliga Limpex! O contrato de participação chega por drone. Por favor, não deixem ele pousar na samambaia."),
        ("vivi", "pensando", "Contrato. Ela disse contrato. Eu vou ler isso cinco vezes. Com lupa."),
        ("teo", "euforico", "Superliga, Zé! A gente vai jogar na liga profissional! Com robô de verdade! Quer dizer, você é de verdade. Desculpa, Zé."),
        ("ze", "robo", "Bip. (a rodinha esquerda cai. O Vô Nestor pega, assopra e coloca de volta, como quem faz isso há trinta anos.)"),
        ("narrador", "neutro", "Do meio da confusão surge o Gabi Trovão. Sem microfone, sem boné, com os olhos vermelhos. Ele para na frente do Téo e estende a mão, devagar."),
        ("gabi", "triste", "Vocês ganharam da Brigada. Ninguém ganha da Brigada. Eu tentei três vezes no treino. Perdi as três."),
        {"q": "O Gabi está com a mão estendida. O ginásio inteiro está olhando. O que o Téo faz?",
         "opts": [
             {"t": "Apertar a mão do Gabi", "fx": {"flag": "gabi_amigo", "xp_hero": 40},
              "reply": [("teo", "feliz", "Foi uma semifinal incrível, Gabi. Na próxima, joga no modo verdade desde o começo."),
                        ("gabi", "feliz", "Combinado. (aperta a mão) Mas não espalha que eu chorei. Fala que foi alergia. A Limpex vende o remédio.")]},
             {"t": "Provocar com o chinelo", "fx": {"flag": "gabi_rival", "scrap": 60},
              "reply": [("teo", "malicioso", "(levanta o chinelo do Zé como um troféu) Isso aqui, Gabi? Tecnologia de museu."),
                        ("gabi", "bravo", "Ri agora, chinelo. A Superliga é longa. E eu tenho memória de setenta sensores.")]},
         ]},
    ]},

    "c6_final_lose": {"bg": "arena", "cast": ["teo", "valquiria", "vivi", "bia", "ambrosio", "nestor", "ze"], "lines": [
        ("narrador", "neutro", "Apito final. A Brigada Higiene se alinha no centro do campo e faz uma reverência sincronizada. Até o suor deles parece passado a ferro."),
        ("valquiria", "feliz", "Que partida linda! Perder também é crescer. A Limpex acredita em vocês. A Limpex acredita em todo mundo que paga a inscrição."),
        ("teo", "triste", "Eles não erram nada. Nem um passe."),
        ("nestor", "pensando", "Todo robô erra, Téo. O segredo é descobrir onde o erro mora. Às vezes ele mora no regulamento.", ("done", "c6_nestor")),
        ("vivi", "pensando", "Erram, sim. No segundo tempo, o número três ficou parado meio segundo depois de cada lateral. Eu vi. Eu anotei. Duas vezes."),
        ("bia", "determinado", "Então a gente ataca pelo lado do número três. Eu ajusto a sucção do Zé para arrancar mais rápido. Me dá vinte minutos e um rolo de fita."),
        ("ambrosio", "feliz", "Regulamento da Taça, artigo um: o finalista pode pedir revanche. Artigo dois: a revanche é hoje. Artigo três: eu acabei de escrever."),
        ("ze", "robo", "Bip. (a rodinha cai. Um robô da Brigada devolve a rodinha. De luva.)"),
    ]},

    "c6_repescagem": {"bg": "lanchonete", "cast": ["teo", "bia", "dudu", "vivi", "odete"], "lines": [
        ("narrador", "neutro", "Eliminados no grupo da Taça de Acesso. A lanchonete do ginásio só vende água com gás e um sanduíche de alface chamado \"Brilho\"."),
        ("dudu", "suor", "Chat, a gente caiu. Mas o sanduíche de alface tem um sabor muito... limpo. Nota dois. Dois e meio pela embalagem."),
        ("teo", "triste", "A gente é campeão do mundo e caiu no grupo. Como isso acontece?"),
        ("vivi", "pensando", "Acontece porque aqui todo mundo joga em nível de Mundial toda semana. A gente precisa evoluir os robôs. Garagem, loja e treino."),
        ("odete", "feliz", "Ninguém fica triste de barriga vazia. Trouxe o resto do bolo. Escondi na bolsa, embaixo do guarda-chuva."),
        ("bia", "feliz", "Dona Odete, a senhora é a única coisa nesse ginásio que não tem cheiro de lavanda corporativa."),
        ("odete", "piscando", "E tem mais: o pessoal da Brigada da Pia me pediu a receita. Eu dei a errada. Merendeira também joga."),
        ("teo", "feliz", "Sorteio novo! Grupo novo! A gente volta. E com bolo."),
    ]},

    "c6_end": {"bg": "arena", "cast": ["teo", "ambrosio", "bia", "nestor", "vivi", "dudu", "ze"], "lines": [
        ("narrador", "neutro", "Fim da Taça de Acesso. Junto com o troféu, a Limpex entrega a cada jogador um apito comemorativo, branco, com o logotipo sorridente da empresa."),
        ("dudu", "feliz", "Chat, ganhei um apito! (apita) Ele faz um barulhinho de notificação. Fofo."),
        ("ambrosio", "pensando", "Dudu, me empresta esse apito. Ele pesa mais do que um apito deveria pesar. Eu conheço o peso de todos os apitos. Fui juiz de várzea."),
        ("narrador", "neutro", "O Prof. Ambrósio abre o apito com a ponta de uma das três canetas. Lá dentro, piscando, há um chip do tamanho de uma lentilha."),
        ("bia", "susto", "Isso é um chip de rastreio! Ela deu um GPS para cada um de nós. Com laço de fita!"),
        ("nestor", "bravo", "Na minha época, quem queria saber onde a gente estava perguntava. Às vezes até trazia pão."),
        ("vivi", "determinado", "Então é isso: a nova Limpex é a velha Limpex com um sorriso maior. Ninguém usa o apito. Vai tudo para uma caixa de sapato. Fechada."),
        ("teo", "neutro", "Vou mandar uma mensagem para o Gabi. Se a Limpex deu apito para a gente, deu para ele também.", ("flag", "gabi_amigo")),
        ("narrador", "neutro", "Resposta do Gabi, um minuto depois: \"O meu tinha dois chips. Desmontei no ônibus. Valeu, Téo. Superliga, aí vamos nós.\"", ("flag", "gabi_amigo")),
        ("dudu", "suor", "Chat, o Gabi postou um vídeo jogando o apito no lixo. Legenda: \"diferente de alguns, eu não preciso ser vigiado\". Era indireta.", ("flag", "gabi_rival")),
        ("ambrosio", "neutro", "Superliga Limpex. Pontos corridos, sede da empresa, câmeras em todo lugar. Vamos jogar dentro da casa deles."),
        ("nestor", "piscando", "Ótimo. Na casa dos outros, a gente sempre descobre onde fica a cozinha."),
        ("ze", "robo", "Bzzzt. (o Zé aspira o chip de rastreio. Faz um barulho de satisfação. Ninguém tem coragem de impedir.)"),
    ]},

    # ------------------------------------------------------------------ Capitulo 7 (Superliga: pontos corridos)
    "c7_intro": {"bg": "estadio", "cast": ["teo", "gervasio", "nestor", "vivi", "dudu", "bia", "ze"], "lines": [
        ("narrador", "neutro", "Estádio Limpex, abertura da Superliga. Fogos, telão de quarenta metros e um mascote: um aspirador inflável gigante chamado Limpinho, com um sorriso de dentes brancos demais."),
        ("dudu", "euforico", "Chat, olha o tamanho desse estádio! Tem mais cadeira aqui do que gente na minha cidade. Tem escada rolante para a escada rolante!"),
        ("gervasio", "feliz", "Moreira! Eu vim representar o colégio! Trouxe a faixa da escola. Pintei sozinho. Escrevi \"Santa Faísca\" com um F a mais."),
        ("narrador", "neutro", "Uma rajada de vento passa pelo estádio. O Limpinho balança, hesita, se inclina com elegância e cai inteiro em cima do Diretor Gervásio."),
        ("gervasio", "susto", "Eu estou bem! Eu estou dentro do mascote! É macio! Cheira a lavanda corporativa!"),
        ("nestor", "malicioso", "Na minha época, mascote era um senhor fantasiado de esquilo. Pelo menos ele caía sozinho."),
        ("vivi", "pensando", "Regulamento da Superliga: seis times, cinco rodadas, pontos corridos. Só os quatro primeiros vão para a semifinal. Não dá para perder ponto bobo."),
        ("bia", "determinado", "Ponto bobo é com a gente mesmo. Eu reforcei o chinelo do Zé com fita cinza. Agora ele aguenta até mascote caindo."),
        ("teo", "feliz", "Superliga, Zé! Liga de verdade! A gente começou numa quadra com uma trave torta!"),
        ("ze", "robo", "Bip. (o Zé aspira um confete. Depois outro. Depois decide que confete é o melhor dia da vida dele.)"),
    ]},

    "c7_vivi_treino": {"bg": "garagem", "cast": ["vivi", "teo", "bia", "nestor", "ambrosio", "ze"], "lines": [
        ("narrador", "neutro", "Garagem do Vô Nestor, véspera da primeira rodada. A Vivi trouxe um quadro branco, três canetas coloridas e uma planilha impressa em formato A2."),
        ("vivi", "determinado", "Pontos corridos funciona assim: vitória vale três, empate vale um, derrota vale tristeza. Ganhar em casa e empatar fora já classifica."),
        ("teo", "pensando", "Mas na Superliga a gente sempre joga em casa. Eles disseram que o mandante é sempre a gente."),
        ("vivi", "convencida", "Exato. Então a planilha manda ganhar todas. Está escrito em verde. Verde é obrigatório."),
        ("bia", "pensando", "E o apito? A gente não pode usar o da Limpex, tem chip de rastreio."),
        ("narrador", "neutro", "A Vivi pega um pano de prato, enrola na mão e sopra com força. O pano faz um \"fffffff\" murcho. Ela olha para o pano com decepção profunda."),
        ("vivi", "corada", "Apito de pano. Sem chip, sem GPS, sem som. É seguro. Não é eficiente, mas é seguro."),
        ("nestor", "feliz", "Na minha época, o técnico apitava com a boca. Às vezes saía um dente. Era mais dramático."),
        ("ambrosio", "pensando", "Valentina, você virou técnica sem perceber. Com prancheta e tudo. O Rodolfo ficaria orgulhoso. Ou com ciúme."),
        ("vivi", "bravo", "Eu não virei técnica. Eu sou capitã com responsabilidade administrativa. É diferente. Está na planilha."),
        ("ze", "robo", "Bip. (o Zé passa por cima da planilha. Agora a tabela tem um rastro de rodinha bem no meio do primeiro lugar.)"),
    ]},

    "c7_g3_dudu": {"bg": "estadio", "cast": ["dudu", "teo", "bia", "odete", "ze"], "lines": [
        ("narrador", "neutro", "Terceira rodada. No canto da arquibancada, o Dudu montou um estúdio de transmissão: um celular, uma lanterna e uma cadeira de praia."),
        ("dudu", "euforico", "Chat, quarenta mil pessoas na live! Quarenta mil! E eu tenho uma cadeira! Uma! Ninguém senta, é a cadeira da sorte!"),
        ("teo", "susto", "Quarenta mil?! Dudu, ontem eram trezentas!"),
        ("dudu", "suor", "Um vídeo do Zé aspirando confete viralizou. Agora o chat só pede confete. Eu não tenho confete. Eu tenho uma lanterna."),
        ("odete", "feliz", "Eu trouxe confete! E bolo! O confete é de papel crepom. O bolo é de cenoura. Não confunde."),
        ("bia", "pensando", "Se o Zé ver confete no meio da partida, ele vai parar para aspirar. Dona Odete, guarda o confete até o apito final."),
        ("odete", "piscando", "Guardo sim, querida. Na bolsa, embaixo do guarda-chuva, do lado do bolo. É o meu cofre."),
        ("dudu", "feliz", "Chat, se o Zé fizer gol, a Dona Odete solta o confete. É uma promessa pública. Agora é contrato."),
        ("ze", "robo", "Bip. (o Zé olha fixo para a bolsa da Dona Odete. Ele sabe. Ele sempre sabe.)"),
    ]},

    # B2: renovar o patrocinio da Limpex (renova_limpex) ou ficar independente (spec secao 4)
    "c7_contrato": {"bg": "camarim", "cast": ["valquiria", "teo", "vivi", "nestor", "ambrosio"], "lines": [
        ("narrador", "neutro", "Vestiário do Estádio Limpex, depois da segunda rodada. Em cima do banco, um bolo de três andares com o logotipo da Limpex em glacê azul. Ao lado do bolo, um contrato."),
        ("valquiria", "feliz", "Que campanha linda! Vim pessoalmente, sem holograma. Trouxe bolo e uma proposta. Assina aqui, tem bolo."),
        ("valquiria", "piscando", "E vocês já assinaram com a gente no Estadual. Eu trouxe a caneta pronta. Destampada. Para economizar tempo.", ("flag", "patroc")),
        ("vivi", "pensando", "Cláusula sete: a Limpex pode mudar o nome do time. Cláusula nove: o Zé usa adesivo da Limpex. Cláusula doze: o adesivo não sai."),
        ("valquiria", "neutro", "Em troca: vinte por cento a mais de sucata em cada partida, peças da linha profissional e um vestiário com ar-condicionado. E bolo semanal."),
        ("nestor", "bravo", "Na minha época, quem dava bolo e contrato no mesmo dia queria o terreno da sua casa."),
        ("ambrosio", "pensando", "Sem a Limpex, a gente joga com o que tem. Menos sucata, mais treino. O time aprende mais rápido quando passa aperto. Mas passa aperto."),
        ("teo", "pensando", "Vinte por cento de sucata é muita peça nova. Mas o Zé com adesivo da Limpex... ele ia ficar estranho."),
        ("valquiria", "feliz", "Sem pressão! Eu só fico aqui, sorrindo, até vocês decidirem. Eu consigo sorrir por quatro horas. É treino."),
        {"q": "O contrato está na mesa, a caneta está destampada e o bolo está derretendo. O que o time faz?",
         "opts": [
             {"t": "Renovar com a Limpex", "fx": {"flag": "renova_limpex", "scrap": 100},
              "reply": [("valquiria", "euforico", "Maravilha! Bem-vindos à família! O adesivo chega amanhã. Ele brilha no escuro. E não sai."),
                        ("nestor", "triste", "Tudo bem, Téo. Sucata é sucata. Mas, se o Zé começar a sorrir que nem ela, a gente conversa.")]},
             {"t": "Ficar independente", "fx": {"flag": "independente", "xp_team": 30},
              "reply": [("teo", "determinado", "Obrigado, doutora. Mas o Zé joga do jeito dele. Com chinelo e sem adesivo."),
                        ("valquiria", "feliz", "Que lindo! Independência! Eu respeito muito. Eu vou respeitar de pertinho. (leva o bolo embora)")]},
         ]},
    ]},

    "c7_sf_pre": {"bg": "estadio", "cast": ["vivi", "teo", "bia", "ambrosio", "dudu"], "lines": [
        ("narrador", "neutro", "Semifinal da Superliga. Do outro lado do campo, cinco robôs brancos com listra ciano e o código LX pintado no peito. Os Impecáveis Mk III."),
        ("vivi", "susto", "São os meus. Quer dizer, eram os meus. A Limpex refez o time inteiro e manteve as minhas jogadas. Eles estão usando as minhas planilhas contra mim."),
        ("teo", "pensando", "Então você sabe o que eles vão fazer antes deles?"),
        ("vivi", "determinado", "Eu sei o que eles vão fazer porque eu escrevi. Página quatro: eles sempre abrem pela direita. Página cinco: eles sempre recuam depois do gol."),
        ("bia", "feliz", "Então a gente lê a página seis antes deles! Qual é a página seis?"),
        ("vivi", "corada", "A página seis é um desenho de gato. Eu estava cansada naquele dia."),
        ("ambrosio", "feliz", "Valentina, é a primeira vez que alguém joga contra o próprio passado e leva vantagem. Normalmente o passado ganha."),
        ("dudu", "euforico", "Chat, é a revanche da Vivi! Ela contra a planilha antiga dela! É o maior clássico do esporte acadêmico!"),
        ("vivi", "determinado", "Téo, ataca pela esquerda. Eles nunca defendem a esquerda. Eu nunca gostei da esquerda. Agora eu gosto."),
    ]},

    "c7_final_pre": {"bg": "estadio", "cast": ["rodolfo", "teo", "ambrosio", "vivi", "valquiria", "nestor"], "lines": [
        ("narrador", "neutro", "Final da Superliga. Entra a Platinum Elite: cinco robôs prateados, polidos até refletir o estádio. Atrás deles, de crachá novo, um homem com uma prancheta."),
        ("teo", "susto", "Capitão Rodolfo?! O senhor não tinha pedido demissão?"),
        ("rodolfo", "convencido", "Pedi. E fui recontratado. Eu agora sou coordenador de higiene ESPORTIVA. A palavra esportiva é em maiúsculas. Está no crachá."),
        ("ambrosio", "pensando", "Rodolfo, você devolveu a prancheta no Mundial. Isso aí é outra prancheta?"),
        ("rodolfo", "neutro", "É a mesma. Ela voltou para mim. Pranchetas sempre voltam. É a natureza delas."),
        ("valquiria", "feliz", "O Rodolfo é um talento! Sabe tudo de vocês. Até a cor do chinelo. Ele fez um relatório de trinta páginas sobre a rodinha."),
        ("nestor", "bravo", "Trinta páginas sobre a minha rodinha? Na minha época, isso se chamava fofoca. Com grampeador."),
        ("vivi", "determinado", "A Platinum Elite joga igual à Platinum da Copa Brasil, só que mais rápida. Mesma formação. A gente já venceu esse desenho uma vez."),
        ("teo", "determinado", "Então a gente vence de novo. Bora, Zé. Pontos corridos acabaram. Agora é mata-mata."),
    ]},

    "c7_final_win": {"bg": "estadio", "cast": ["teo", "rodolfo", "valquiria", "vivi", "odete", "dudu", "ze"], "lines": [
        ("narrador", "neutro", "Apito final. O placar do Estádio Limpex mostra: Zé Poeira campeão da fase de pontos corridos. A Dona Odete solta o confete. Todo o confete."),
        ("odete", "euforico", "Promessa é promessa! Confete para todo mundo! Até para o pessoal da Platinum, coitados!"),
        ("dudu", "euforico", "Chat, cem mil na live! Cem mil! O chat está só escrevendo \"confete\". A gente virou um meme e um campeão no mesmo dia!"),
        ("teo", "feliz", "A gente ganhou a liga, Vivi! A sua planilha estava certa!"),
        ("vivi", "corada", "A planilha sempre está certa. O que está errado às vezes é a realidade."),
        ("rodolfo", "triste", "Eu vou ter que escrever um relatório sobre esta derrota. Com gráfico. Os gráficos de derrota são sempre os mais bonitos."),
        ("valquiria", "feliz", "Parabéns! Os playoffs começam semana que vem. Com regras novas. Que eu ainda vou inventar. Até lá!"),
        ("ze", "robo", "Bzzzt. (o Zé aspira o confete do estádio inteiro em doze segundos. A equipe de limpeza da Limpex aplaude, sem saber se deveria.)"),
    ]},

    "c7_final_lose": {"bg": "estadio", "cast": ["teo", "rodolfo", "vivi", "bia", "ambrosio", "ze"], "lines": [
        ("narrador", "neutro", "Apito final. A Platinum Elite comemora em silêncio, cada robô girando exatamente uma volta. O Rodolfo anota alguma coisa na prancheta."),
        ("rodolfo", "convencido", "Vitória da Platinum. Previsto na página dezoito do meu relatório. A página dezenove era sobre a rodinha. Valeu a pena."),
        ("teo", "triste", "Eles jogaram exatamente o que a Vivi disse, e mesmo assim ganharam."),
        ("vivi", "pensando", "Porque eles são mais rápidos na saída de bola. A gente precisa de mais aceleração. Ou de menos Rodolfo."),
        ("bia", "determinado", "Aceleração é comigo. Dá para trocar o motor do Zé por um mais leve. Ou colocar mais fita na rodinha, que deixa ela mais lisa."),
        ("ambrosio", "feliz", "Regulamento da Superliga, parágrafo único: perder a final libera a revanche. Eu li isso hoje. Na minha mão, a caneta."),
        ("rodolfo", "neutro", "Revanche aceita. A prancheta já tem uma página reservada para isso. Ela está em branco. Por enquanto."),
        ("ze", "robo", "Bip. (a rodinha cai. O Rodolfo anota: \"rodinha caiu, de novo, página vinte\".)"),
    ]},

    "c7_repescagem": {"bg": "lanchonete", "cast": ["teo", "vivi", "dudu", "bia", "nestor"], "lines": [
        ("narrador", "neutro", "Quinto lugar na Superliga. Fora da semifinal. A lanchonete do Estádio Limpex serve um suco verde chamado \"Recomeço\". Ninguém pede."),
        ("vivi", "triste", "Faltou um ponto. Um. Eu refiz a conta onze vezes. A conta não muda. Eu odeio quando a conta não muda."),
        ("dudu", "suor", "Chat, a gente ficou em quinto. Mas o chat votou: a gente é o primeiro em simpatia. Isso não vale ponto. Mas vale like."),
        ("teo", "triste", "Na Superliga todo mundo é bom. Não dá para ganhar só com coragem."),
        ("nestor", "neutro", "Coragem sozinha é chinelo sem pé, Téo. Faz barulho, mas não anda. Vamos melhorar o Zé na garagem, peça por peça."),
        ("bia", "feliz", "E treinar! Eu topo treinar até a fita acabar. A fita nunca acaba. Eu compro em atacado."),
        ("vivi", "determinado", "Regulamento: a Superliga deixa recomeçar a fase com tabela nova. Tabela nova, planilha nova, eu nova."),
        ("teo", "feliz", "Tabela nova! A gente volta. E dessa vez sem perder ponto bobo."),
    ]},

    "c7_end": {"bg": "garagem", "cast": ["teo", "vivi", "bia", "dudu", "nestor", "ze"], "lines": [
        ("narrador", "neutro", "Garagem do Vô Nestor, noite de domingo. O troféu da fase de pontos corridos está na prateleira, ao lado da panela que o Vô ganhou no bingo."),
        ("dudu", "feliz", "Chegou mensagem de áudio do Gabi! Vou colocar no viva-voz. Atenção, é um áudio de três segundos."),
        ("narrador", "neutro", "O áudio começa. O Gabi grita tão alto que, de algum jeito, dá para ouvir as letras maiúsculas: \"PARABÉNS, CHINELO.\" Fim do áudio."),
        ("teo", "feliz", "Ele mandou parabéns! O Gabi mandou parabéns pra gente!", ("flag", "gabi_amigo")),
        ("dudu", "pensando", "Ele mandou mais um áudio: \"NOS PLAYOFFS EU TÔ NA TORCIDA. COM BONÉ. SEM CHIP.\" Ele fala em caixa alta até no áudio.", ("flag", "gabi_amigo")),
        ("dudu", "suor", "Ele mandou mais um áudio: \"APROVEITA, CHINELO. NOS PLAYOFFS EU VOU ESTAR OLHANDO.\" Depois ele mandou um emoji de raio. Doze vezes.", ("flag", "gabi_rival")),
        ("bia", "pensando", "O adesivo da Limpex chegou. Brilha no escuro mesmo. O Zé fica parecendo um abajur.", ("flag", "renova_limpex")),
        ("bia", "feliz", "A Limpex mandou uma carta dizendo que respeita a nossa independência. A carta tinha um chip de rastreio. Coloquei na caixa de sapato.", ("flag", "independente")),
        ("vivi", "pensando", "Playoffs: grupo, quartas, semifinal e final. Times de todas as divisões. Inclusive gente que a gente conhece."),
        ("nestor", "pensando", "Gente que a gente conhece é sempre o pior adversário. Ela sabe onde a gente guarda o pão de queijo."),
        ("ze", "robo", "Bip. (o Zé estaciona embaixo do troféu e fica olhando para cima, como quem conta estrelas.)"),
    ]},

    # ------------------------------------------------------------------ Capitulo 8 (Playoffs da Superliga)
    "c8_intro": {"bg": "estadio", "cast": ["teo", "vivi", "ambrosio", "valquiria", "dudu", "bia", "ze"], "lines": [
        ("narrador", "neutro", "Playoffs da Superliga, rodada de abertura, à noite. O Estádio Limpex acende um telão novo. Nele, a Dra. Valquíria, sorrindo, com um anúncio."),
        ("valquiria", "feliz", "Novidade nos playoffs! Para deixar tudo mais limpo e moderno, a partir de hoje... a bola é cinza!"),
        ("teo", "susto", "Cinza?! A bola sempre foi branca!"),
        ("valquiria", "neutro", "Branco mostra sujeira. Cinza esconde. É uma bola mais feliz. A regra vale a partir de agora. Já está no regulamento. Na página que eu acabei de imprimir."),
        ("vivi", "bravo", "Mudar a regra no meio do campeonato é ilegal. É imoral. E é mal formatado. Ela imprimiu em fonte doze. Regulamento é fonte onze."),
        ("ambrosio", "pensando", "O sensor do Zé foi calibrado para bola branca. Com bola cinza, ele vai demorar para achar a bola no gramado escuro."),
        ("bia", "determinado", "Então eu recalibro. Me dá uma bola cinza, uma lanterna e o Dudu segurando a lanterna sem mexer."),
        ("dudu", "suor", "Chat, eu fui promovido a suporte de lanterna. É um cargo técnico. Eu aceito."),
        ("ze", "robo", "Bip. (o Zé encosta na bola cinza, desconfiado. Dá uma volta em torno dela. Decide que ela é amiga.)"),
    ]},

    "c8_ogawa": {"bg": "dojo", "cast": ["ogawa", "kenji", "teo", "bia", "nestor", "ze"], "lines": [
        ("narrador", "neutro", "Um dojo improvisado nos fundos do estádio, com tatame emprestado e uma lâmpada que pisca. O Kenji trouxe alguém: um senhor de kimono, olhos fechados e bigode impecável."),
        ("kenji", "feliz", "Téo! Este é o Mestre Ogawa, meu sensei. Ele veio do Japão só para ver os playoffs. E para conhecer o chinelo."),
        ("ogawa", "calmo", "O chinelo que anda sozinho conhece o caminho. O chinelo que fica parado conhece o pé."),
        ("teo", "pensando", "Isso... faz sentido?"),
        ("kenji", "suor", "Não. Nunca faz. Mas no fim sempre funciona. É o método dele."),
        ("ogawa", "neutro", "Hoje eu ensino a arte de não limpar. Um robô que limpa tudo não enxerga nada. Um robô que deixa um pouco de pó enxerga o caminho do pó."),
        ("bia", "maravilhado", "Então a sujeira é um mapa? Mestre, eu vivo suja de graxa. Eu sou um mapa ambulante!"),
        ("ogawa", "piscando", "O pó que cai duas vezes é pó interessado. Siga o pó interessado."),
        ("nestor", "feliz", "Ogawa, na minha época eu dizia a mesma coisa, só que com menos poesia: \"não varre agora, que eu ainda vou procurar o parafuso\"."),
        ("ogawa", "feliz", "Nestor-san. O senhor é um mestre sem dojo. Os melhores mestres não têm dojo. Têm garagem."),
        ("ze", "robo", "Bzzzt. (o Zé deixa de aspirar um montinho de pó, de propósito. O Mestre Ogawa faz uma reverência para ele.)"),
    ]},

    "c8_helena": {"bg": "estadio", "cast": ["helena", "teo", "bia", "ambrosio", "ze"], "lines": [
        ("narrador", "neutro", "Antes do segundo jogo do grupo. Entra no gramado a Dra. Helena Régis, juíza da Federação, com uma pasta, um scanner portátil e a samambaia num vaso com rodinhas."),
        ("helena", "neutro", "Vistoria surpresa da Federação. A Superliga mudou a bola no meio do campeonato. A Federação quer saber o que mais mudou."),
        ("teo", "feliz", "Doutora Helena! E a samambaia! Ela veio também?"),
        ("helena", "neutro", "Ela não perde uma vistoria. Ela tem um faro para irregularidades. Ou para adubo. Ainda não sei qual."),
        ("narrador", "neutro", "O scanner passa pelo Zé Poeira e apita baixinho. Tudo dentro da regra. Então a samambaia, sozinha, se inclina para longe do Zé."),
        ("helena", "pensando", "A samambaia reprovou o Zé Poeira."),
        ("bia", "susto", "Reprovou?! Por quê? Ele está limpo! Quer dizer, ele está honestamente sujo!"),
        ("helena", "neutro", "Ela não gosta de chip de rastreio. E tem um dentro do Zé. Ele aspirou na Taça de Acesso, não aspirou? Está no filtro."),
        ("ambrosio", "feliz", "O Zé engoliu o chip da Limpex! Doutora, isso conta como prova contra a Limpex ou contra o Zé?"),
        ("helena", "calmo", "Conta como prova de que o Zé come qualquer coisa. Tirem o chip do filtro e estão liberados. A samambaia vai observar."),
        ("ze", "robo", "Bip. (a Bia abre o filtro. Sai o chip, três confetes e meia fatia de bolo de cenoura. A samambaia se acalma.)"),
    ]},

    "c8_qf_pre": {"bg": "estadio", "cast": ["teo", "dudu", "vivi", "bia", "ze"], "lines": [
        ("narrador", "neutro", "Quartas de final. Entram os Dust Bunnies, os americanos do Mundial. Agora profissionais, com patrocínio novo e chapéus de cowboy ainda maiores."),
        ("dudu", "euforico", "Chat, os Dust Bunnies voltaram! Os chapéus cresceram! Eu não sabia que chapéu crescia!"),
        ("vivi", "pensando", "Os chapéus aumentaram trinta por cento. Os robôs, dez. Tem mais chapéu do que robô ali. É uma escolha estética arriscada."),
        ("bia", "feliz", "Chapéu grande atrapalha o sensor de cima. Se a bola for alta, eles não enxergam. Téo, joga pelo alto!"),
        ("teo", "pensando", "O Zé não joga pelo alto. O Zé é um aspirador. Ele joga pelo chão."),
        ("bia", "determinado", "Então joga pelo chão rápido, que eles demoram para olhar para baixo. O chapéu tem aba."),
        ("narrador", "neutro", "Do outro lado, o capitão dos Dust Bunnies tira o chapéu e acena para o Téo. O chapéu é tão grande que faz sombra no meio-campo."),
        ("dudu", "feliz", "Chat, ele acenou! Isso é respeito internacional! Ou ele estava abanando o calor do chapéu!"),
        ("ze", "robo", "Bip. (o Zé estaciona na sombra do chapéu. Está mais fresquinho ali.)"),
    ]},

    "c8_sf_kenji": {"bg": "estadio", "cast": ["kenji", "teo", "ogawa", "vivi", "ze"], "lines": [
        ("narrador", "neutro", "Semifinal dos playoffs. Do outro lado, o Dojo do Kenji 2.0, robôs brancos com faixa vermelha. O Kenji atravessa o campo e se curva na frente do Téo."),
        ("kenji", "feliz", "Téo-san. No Mundial, vocês me mostraram que perfeição sem coração é só cálculo. Eu vim agradecer. Com uma reverência e um time novo."),
        ("teo", "feliz", "Kenji! Que bom te ver! Mas... hoje a gente joga um contra o outro."),
        ("kenji", "pensando", "Eu pensei em perder de propósito. Como agradecimento. Seria uma honra."),
        ("ogawa", "calmo", "Perder de propósito é a maior falta de respeito que existe. O adversário que entrega o jogo rouba a vitória do outro."),
        ("kenji", "determinado", "O sensei tem razão. Esqueça o que eu disse, Téo-san. Hoje eu jogo com tudo. Ou não. Ou sim. Sim. Com tudo."),
        ("vivi", "pensando", "Ele disse \"ou não\" e depois \"sim\". Estatisticamente, isso quer dizer que ele vai jogar com tudo e vai se arrepender um pouco."),
        ("ogawa", "piscando", "O aluno que hesita na frente do amigo ainda tem muito a aprender. E muito coração. As duas coisas são boas."),
        ("ze", "robo", "Bzzzt. (o Zé se curva também. A rodinha cai na reverência. O Kenji pega e devolve, com as duas mãos.)"),
    ]},

    "c8_final_pre": {"bg": "estadio", "cast": ["valquiria", "teo", "ambrosio", "nestor", "vivi", "bia"], "lines": [
        ("narrador", "neutro", "Final dos playoffs, à noite. As luzes do estádio apagam. Acende um único holofote no túnel. Saem cinco robôs pretos, com uma linha de LED vermelho no peito: a Guarda Zero."),
        ("narrador", "neutro", "Um dos robôs se adianta e fala com a voz da Valquíria, gravada: \"A Valquíria mandou lembranças. E uma intimação para as lembranças.\""),
        ("teo", "susto", "Uma intimação para as lembranças? Isso nem faz sentido!"),
        ("valquiria", "feliz", "Faz, sim! Se vocês ganharem, as lembranças são intimadas a comparecer ao meu escritório. Eu coleciono lembranças. E patentes."),
        ("ambrosio", "pensando", "LED vermelho no peito. Isso não é design. Isso é um aviso. Esses robôs não são da linha de varejo."),
        ("nestor", "bravo", "Na minha época, robô de LED vermelho era o do alarme da fábrica. Quando ele acendia, alguém ia ser demitido."),
        ("vivi", "determinado", "A Guarda Zero não perdeu nenhum jogo nos playoffs. Nenhum gol sofrido. Quer dizer que ninguém tentou jogar diferente."),
        ("bia", "determinado", "Diferente é com a gente. A bola é cinza, o Zé é amarelo de fita e o chinelo é marrom. Ninguém aqui é padrão."),
        ("teo", "determinado", "Bora, Zé. Pela Superliga. E pelo pão de queijo da Dona Odete."),
    ]},

    "c8_final_win": {"bg": "estadio", "cast": ["teo", "valquiria", "vivi", "bia", "nestor", "dudu", "ze"], "lines": [
        ("narrador", "neutro", "Apito final. A Guarda Zero para no meio do campo. Os cinco LEDs vermelhos piscam uma vez, e apagam. O Zé Poeira é campeão dos playoffs da Superliga."),
        ("dudu", "euforico", "Chat, campeões da Superliga! A equipe que começou numa quadra com trave torta! Duzentos mil na live! Minha mãe está chorando! Eu também!"),
        ("bia", "euforico", "A fita! A fita aguentou a final inteira! Eu vou escrever uma carta para a fábrica de fita!"),
        ("nestor", "chorando", "Na minha época... não, esquece a minha época. Essa época é melhor. Essa época tem vocês."),
        ("valquiria", "feliz", "Parabéns! Vocês são incríveis! Incrivelmente teimosos. A Limpex adora gente teimosa. A gente aprende muito estudando gente teimosa."),
        ("vivi", "pensando", "Ela está sorrindo demais para quem perdeu a final com o time dela. Isso não está em nenhuma planilha."),
        ("valquiria", "piscando", "Ah, a Guarda Zero não era o meu melhor time. Era só um rascunho. O melhor ainda está no laboratório. Ele é a cara de vocês. Literalmente."),
        ("teo", "pensando", "A cara da gente? O que ela quis dizer com isso?"),
        ("ze", "robo", "Bip. (o Zé olha para o telão, onde por um segundo aparece a silhueta de um robô igual a ele. Sem chinelo.)"),
    ]},

    "c8_final_lose": {"bg": "estadio", "cast": ["teo", "valquiria", "vivi", "bia", "ambrosio", "nestor", "ze"], "lines": [
        ("narrador", "neutro", "Apito final. A Guarda Zero volta para o túnel em fila, sem comemorar. Os LEDs vermelhos continuam acesos, como se nada tivesse acontecido."),
        ("valquiria", "feliz", "Que final bonita! Perder para a Guarda Zero é normal. Todo mundo perde. É como perder para a gravidade."),
        ("teo", "triste", "Eles nem comemoram. É como jogar contra uma parede que faz gol."),
        ("nestor", "pensando", "Parede também tem rachadura, Téo. A gente só precisa achar onde a tinta descasca.", ("done", "c6_nestor")),
        ("vivi", "pensando", "Paredes têm padrão. A Guarda Zero marca sempre no mesmo canto, depois de três passes. Três. Sempre três. Vou contar no próximo jogo."),
        ("bia", "determinado", "E a defesa deles sobe toda junta quando a bola vai para o meio. Se o Zé ficar no canto, ele fica sozinho com o goleiro."),
        ("ambrosio", "feliz", "Regulamento dos playoffs, nota de rodapé: o finalista derrotado tem direito a revanche. Eu escrevi a nota de rodapé ontem. Em letra pequena."),
        ("ze", "robo", "Bip. (a rodinha cai. Um LED vermelho da Guarda Zero pisca na direção dela. A rodinha volta sozinha para o Zé. Ninguém explica.)"),
    ]},

    "c8_repescagem": {"bg": "lanchonete", "cast": ["teo", "dudu", "vivi", "odete", "nestor"], "lines": [
        ("narrador", "neutro", "Eliminados no grupo dos playoffs. A lanchonete agora vende a bola cinza em versão chocolate. É cinza por dentro também."),
        ("dudu", "suor", "Chat, a gente caiu no grupo. Mas o chocolate cinza é bom. Muito bom. Eu não queria admitir. Nota oito."),
        ("teo", "triste", "A bola cinza atrapalhou a gente o jogo inteiro."),
        ("vivi", "pensando", "Atrapalhou todo mundo igual. O problema é que os outros times treinaram com bola cinza a semana toda. A Limpex avisou eles antes."),
        ("odete", "bravo", "Avisou antes?! Isso é como contar a sobremesa só para metade da sala! Eu vou falar com essa moça!"),
        ("nestor", "feliz", "Calma, Odete. A gente não ganha delas reclamando. A gente ganha treinando com bola cinza até sonhar com bola cinza."),
        ("odete", "feliz", "Então eu faço bolo cinza. Para treinar os olhos. É só colocar bastante chocolate. E um pouco de fé."),
        ("teo", "feliz", "Sorteio novo! Grupo novo! A gente volta. E com bolo cinza."),
    ]},

    "c8_end": {"bg": "garagem", "cast": ["teo", "ambrosio", "nestor", "vivi", "bia", "augusto", "ze"], "lines": [
        ("narrador", "neutro", "Garagem do Vô Nestor, depois dos playoffs. O troféu da Superliga ocupa a prateleira inteira. A panela do bingo foi rebaixada para o chão."),
        ("narrador", "neutro", "De repente, o rádio velho do Vô chia e projeta um holograma tremido no meio da garagem. É o Dr. Augusto. De roupão. E de cueca por baixo do roupão."),
        ("augusto", "calmo", "Ambrósio. Nestor. Garotos. Não olhem para as minhas canelas. Eu estou no meu período de reflexão."),
        ("ambrosio", "susto", "Augusto?! Você está de cueca!"),
        ("augusto", "espirro", "É uma cueca de reflexão! É de linho! ATCHIM! Eu não tenho muito tempo. A minha irmã monitora todas as frequências. Até a do rádio do Nestor."),
        ("augusto", "neutro", "A Valquíria achou a planta do Aspiradex nos arquivos da antiga Limpex. A cópia que eu guardei. Ela fez um clone do Zé Poeira. Perfeito. Sem chinelo."),
        ("nestor", "bravo", "Um clone do Zé?! Augusto, aquela planta era minha! Você guardou uma cópia da minha planta?"),
        ("augusto", "triste", "Eu guardei tudo, Nestor. Era o meu jeito de não perder os amigos. Não funcionou. Mas a pasta ficou muito organizada."),
        ("vivi", "determinado", "Onde está o clone? No laboratório da Limpex? A gente precisa ver com os próprios olhos."),
        ("augusto", "espirro", "No subsolo. Nível menos três. O código da porta é o aniversário do Nestor. Ela é sentimental do jeito errado. ATCHIM! (o holograma some)"),
        ("bia", "pensando", "Vô Nestor... qual é o seu aniversário?"),
        ("nestor", "pensando", "Eu não lembro. Mas eu sei quem lembra. (olha para o Zé) Ele tem a data gravada no chip. Desde sempre."),
        ("ze", "robo", "Bip. Bip. Bip. (o Zé pisca o LED três vezes, devagar, como quem guarda um segredo há trinta anos.)"),
    ]},
}

# --- recompensas --------------------------------------------------------------------------------
REWARDS = {
    # Cap. 6: sucata, Servo Agil (Epica) e o modulo Arrancada equipado no heroi (o slot Modulo ja foi
    # liberado no fim do Ato 1, rw_5)
    "rw_6": {"scrap": 700, "piece": {"model": "Servo Ágil", "rar": 2}, "recruits": [], "unlock": [],
             "xp_hero": 0, "xp_team": 20, "equip_hero_piece": {"model": "Módulo Arrancada", "rar": 0}},
    # Cap. 7: se o Gabi virou amigo (B1), o Relampago dele entra no time; senao, Mola Dupla (Rara).
    # Skill Succao Magnetica nv 1 para o heroi.
    "rw_7": {"scrap": 900, "piece": None, "recruits": [], "unlock": [], "xp_hero": 0, "xp_team": 0,
             "equip_hero_piece": None, "skill": {"robot": "hero", "id": "succao", "rank": 1},
             "alt": [(("flag", "gabi_amigo"),
                      {"recruits": [{"name": "Relâmpago", "role": "ATT", "chassis": "Velocista",
                                     "base_ovr": 68, "level": 7, "paint": (60, 140, 255),
                                     "piece": {"model": "Turbina", "rar": 1}}]}),
                     (None, {"piece": {"model": "Mola Dupla", "rar": 1}})]},
    # Cap. 8: reliquia Pao de Queijo Termico (bateria unica), XP do time e Chute em Curva nv 1
    "rw_8": {"scrap": 1100, "piece": {"model": "Pão de Queijo Térmico", "rar": 3}, "recruits": [],
             "unlock": [], "xp_hero": 0, "xp_team": 30, "equip_hero_piece": None,
             "skill": {"robot": "hero", "id": "curva", "rank": 1}},
}
SIDES = {}

# --- capitulos ----------------------------------------------------------------------------------
# O no 0 do cap. 6 e o epilogo do Ato 1 (saves migrados do roteiro 1 ficam em ch "6", node 0 com o
# epilogo ja em `done` e seguem para o c6_nestor). econ_tier/tier_done_on_close = 3 ate o C9.
CHAPTERS = [
    {"id": "6", "act": "2", "title": "Capítulo 6", "subtitle": "Taça de Acesso",
     "local": "Ginásio Limpex Park", "F_start": 66.6, "F_end": 68.0, "econ_tier": 3,
     "tier_done_on_close": 3, "reward": "rw_6",
     "nodes": [("scene", "e1_epilogo"), ("scene", "c6_nestor"), ("scene", "c6_convite"),
               ("tournament", "t_c6"), ("scene", "c6_end"), ("chapter_end", "6")]},
    {"id": "7", "act": "2", "title": "Capítulo 7", "subtitle": "Superliga: Pontos Corridos",
     "local": "Estádio Limpex", "F_start": 68.4, "F_end": 70.2, "econ_tier": 3,
     "tier_done_on_close": 3, "reward": "rw_7",
     "nodes": [("scene", "c7_intro"), ("scene", "c7_vivi_treino"), ("tournament", "t_c7"),
               ("scene", "c7_end"), ("chapter_end", "7")]},
    {"id": "8", "act": "2", "title": "Capítulo 8", "subtitle": "Playoffs da Superliga",
     "local": "Estádio Limpex (noite)", "F_start": 70.4, "F_end": 72.0, "econ_tier": 3,
     "tier_done_on_close": 3, "reward": "rw_8",
     "nodes": [("scene", "c8_intro"), ("scene", "c8_ogawa"), ("tournament", "t_c8"),
               ("scene", "c8_end"), ("chapter_end", "8")]},
    {"id": "9", "act": "2", "title": "Capítulo 9", "subtitle": "O Clone",
     "local": "Laboratório da Limpex", "F_start": 72.4, "F_end": 73.8, "econ_tier": 3,
     "tier_done_on_close": 3, "reward": None, "nodes": [], "draft": True},
]
