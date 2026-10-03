# -*- coding: utf-8 -*-
"""Dados da campanha "A Garagem do Vo" (modo robos). Modulo PURO: so dados, sem pygame e sem imports.

Regras de escrita (verificadas por tests/test_story.py): tudo em Latin-1; so aspas retas (") e tres
pontos ASCII ("..."); fala <= 260 chars e cabe em <= 4 linhas de 780 px (pygame Font(None, 28));
opcao de escolha <= 46 chars; nome de exibicao <= 14 chars; flags ASCII <= 32 chars (<= 48 no total).
Ids de cena/personagem/time/torneio sao ESTAVEIS (vao para o save): mudar um id existente exige migracao.

Como ler (resumo dos campos)
----------------------------
CHARACTERS[id] = {"name": exibicao em maiusculas (<=14), "color": RGB do nome/caixa,
    "skin": RGB, "hair": (estilo, RGB), "acc": [acessorios], "outfit": (tipo, RGB)}.
    Estilos/acessorios/roupas validos: HAIR_STYLES, ACCESSORIES, OUTFITS (o passo 9 desenha por codigo).
MOODS: expressoes validas (o retrato troca olhos/boca/suor conforme o humor).
BGS: ids de cenario (o desenho e do passo 9).
TEAMS[id] = {"name" (<=24), "color", "ovr", "names" (5 robos <=12, unicos), "chassis" (5, em
    robots.CHASSIS), "paint" (RGB dos robos), "perfect" (True = sem jitter nos atributos)}.
    Ordem dos 5 slots = garage.LINEUP_SLOTS (GK, DEF, MID, MID, ATT).
SCENES[id] = {"bg", "cast": [ids], "lines": [...]}. Item de "lines":
    (who, mood, text)  |  (who, mood, text, cond)  |  {"q", "opts": [{"t", "fx", "reply": [linhas]}]}
    who = id de personagem; cond = ("flag", nome) | ("noflag", nome) | ("done", scene_id).
    fx (so estas chaves): flag (str), scrap (int, <=100), xp_hero (int), xp_team (int),
    piece ({"model": parts.PARTS, "rar": 0..3}). Escolha: opcoes 2-3; "fx" e "reply" opcionais.
TOURNAMENTS[id]: ver o bloco proprio (formato, hooks, boss_delta/regular_delta).
CHAPTERS: lista ordenada; "nodes" em ordem: ("scene", id) | ("tournament", id) | ("chapter_end", cap_id)
    | ("end", scene_id)  [o ultimo capitulo da campanha termina com ("end", cena de epilogo)].
    "draft": True = esqueleto (nodes vazio) que o teste de alcancabilidade ignora.
REWARDS[id]: aplicado UMA vez ao fechar o capitulo (chave "reward:<id>" em `done`): scrap, piece,
    recruits [{"name","role","chassis","base_ovr","level","paint","piece"?}], unlock [chassis],
    xp_hero, xp_team, equip_hero_piece ({"model","rar"} ou None).
"""

STORY_VERSION = 1

# --- pity (derrotas seguidas no chefe) ---------------------------------------------------------
PITY_STEP = 1      # -1 de Forca do chefe por derrota seguida
PITY_MAX = 3       # ate -3; zera ao vencer

# --- personagens --------------------------------------------------------------------------------
HAIR_STYLES = ("espetado", "calvo", "longo", "curto", "ondulado", "raspado", "none")
ACCESSORIES = ("oculos_redondos", "oculos_testa", "oculos_grandes", "headset", "bandana", "bigode",
               "luvas", "canetas", "graxa", "chinelo", "fita", "capacete", "apito", "kimono")
OUTFITS = ("moletom", "blazer", "jaleco", "terno", "uniforme", "camiseta", "kimono", "robo")

CHARACTERS = {
    "teo": {"name": "TÉO", "color": (255, 90, 80), "skin": (240, 200, 160),
            "hair": ("espetado", (60, 40, 30)), "acc": [], "outfit": ("moletom", (220, 50, 50))},
    "ambrosio": {"name": "PROF. AMBRÓSIO", "color": (180, 190, 210), "skin": (235, 195, 160),
                 "hair": ("calvo", (170, 170, 175)), "acc": ["oculos_redondos", "bigode", "canetas"],
                 "outfit": ("jaleco", (230, 230, 235))},
    "vivi": {"name": "VIVI", "color": (80, 130, 255), "skin": (245, 215, 190),
             "hair": ("longo", (20, 30, 80)), "acc": [], "outfit": ("blazer", (245, 245, 250))},
    "bia": {"name": "BIA", "color": (255, 160, 40), "skin": (200, 150, 110),
            "hair": ("curto", (40, 25, 20)), "acc": ["bandana", "oculos_testa", "graxa"],
            "outfit": ("camiseta", (90, 90, 100))},
    "dudu": {"name": "DUDU", "color": (80, 230, 120), "skin": (225, 180, 140),
             "hair": ("ondulado", (30, 30, 30)), "acc": ["headset", "oculos_grandes"],
             "outfit": ("moletom", (40, 170, 90))},
    "augusto": {"name": "DR. AUGUSTO", "color": (200, 240, 255), "skin": (245, 220, 200),
                "hair": ("curto", (200, 205, 215)), "acc": ["luvas"], "outfit": ("terno", (250, 250, 255))},
    "gervasio": {"name": "DIR. GERVÁSIO", "color": (200, 170, 120), "skin": (235, 190, 150),
                 "hair": ("raspado", (90, 70, 50)), "acc": ["bigode"], "outfit": ("terno", (90, 80, 70))},
    "rodolfo": {"name": "CAP. RODOLFO", "color": (150, 160, 170), "skin": (215, 170, 135),
                "hair": ("raspado", (50, 50, 55)), "acc": [], "outfit": ("uniforme", (60, 70, 80))},
    "helena": {"name": "DRA. HELENA", "color": (190, 130, 255), "skin": (225, 185, 150),
               "hair": ("curto", (70, 50, 90)), "acc": ["oculos_redondos"],
               "outfit": ("blazer", (80, 60, 120))},
    "kenji": {"name": "KENJI", "color": (255, 120, 160), "skin": (240, 205, 170),
              "hair": ("espetado", (20, 20, 25)), "acc": ["bandana"], "outfit": ("kimono", (240, 240, 240))},
    "narrador": {"name": "NARRADOR", "color": (150, 170, 200), "skin": (200, 200, 200),
                 "hair": ("none", (0, 0, 0)), "acc": [], "outfit": ("camiseta", (60, 70, 100))},
    "ze": {"name": "ZÉ POEIRA", "color": (0, 200, 220), "skin": (170, 180, 190),
           "hair": ("none", (0, 0, 0)), "acc": ["chinelo", "fita"], "outfit": ("robo", (120, 130, 140))},
}

MOODS = ("neutro", "feliz", "susto", "triste", "bravo", "pensando", "convencida", "convencido",
         "corada", "suor", "espirro", "calmo", "cansado", "robo")

BGS = ("garagem", "oficina", "escola", "cantina", "quadra", "ginasio", "arena", "camarim",
       "federacao", "estadio", "mundial")

# --- times --------------------------------------------------------------------------------------
_CH = ["Goleiro", "Tanque", "Disco", "Disco", "Velocista"]

TEAMS = {
    "xadrez": {"name": "Clube do Xadrez", "color": (120, 120, 150), "ovr": 36,
               "names": ["Torre", "Bispo", "Cavalo", "Peão", "Rainha"], "chassis": list(_CH),
               "paint": (225, 225, 235), "perfect": False},
    "turma3b": {"name": "Turma 3ºB", "color": (240, 190, 60), "ovr": 38,
                "names": ["Zeca", "Maju", "Tato", "Pri", "Gui"], "chassis": list(_CH),
                "paint": (250, 200, 80), "perfect": False},
    "fundao": {"name": "Fundão FC", "color": (150, 110, 70), "ovr": 39,
               "names": ["Soneca", "Cochilo", "Bocejo", "Preguiça", "Ronco"], "chassis": list(_CH),
               "paint": (160, 120, 80), "perfect": False},
    "gremio": {"name": "Grêmio", "color": (60, 160, 100), "ovr": 40,
               "names": ["Ata", "Pauta", "Voto", "Moção", "Estatuto"], "chassis": list(_CH),
               "paint": (70, 170, 110), "perfect": False},
    "teatro": {"name": "Clube de Teatro", "color": (210, 70, 130), "ovr": 42,
               "names": ["Hamlet", "Julieta", "Cena", "Bis", "Ensaio"], "chassis": list(_CH),
               "paint": (220, 90, 150), "perfect": False},
    # Robos da Limpex-patrocinada de Vivi: perfeitos (sem jitter), brancos com marca ciano
    "impecaveis": {"name": "Os Impecáveis", "color": (0, 220, 255), "ovr": 46,
                   "names": ["LX-01", "LX-02", "LX-03", "LX-04", "LX-05"], "chassis": list(_CH),
                   "paint": (235, 248, 255), "perfect": True},
}

# --- torneios -----------------------------------------------------------------------------------
# format "single": 1 partida (treino; resultado nao bloqueia). format "cup": grupo de 4 (jogador + 3
#   adversarios "group", 3 jogos, top 2 avanca) + semifinal "sf" + final "final" (+ quartas "qf" no
#   Mundial). O chefe ("boss") e sempre o adversario da final. Estagios: G1 G2 G3 [QF] SF F.
# Calibragem (ver PLANO): Forca esperada do jogador F (CHAPTERS F_start>F_end). ovr do chefe =
#   F_end - boss_delta (chefe final: 0, demais: +1); regulares ficam ~regular_delta=(5..7) abaixo
#   de F_start; a semifinal e "forte" (~+4 abaixo). Eliminacao no grupo reinicia o torneio com
#   semente nova; derrota na SF/F so repete aquela partida (pity no chefe).
# hooks: cenas amarradas ao torneio (jogadas uma vez, controladas por `done`):
#   "before": {estagio: cena} antes da partida; "after": {estagio: cena} apos VENCER o estagio;
#   "win": cena ao vencer a final; "lose": cena apos perder SF/final; "elim": cena apos eliminacao
#   no grupo (o torneio recomeca em seguida).
TOURNAMENTS = {
    "t_p_treino": {
        "chapter": "P", "local": "Quadra do Colégio Santa Faísca", "bg": "quadra", "format": "single",
        "group": [], "qf": None, "sf": None, "final": "xadrez", "boss": "xadrez",
        "boss_delta": 8, "regular_delta": (8, 8),
        "hooks": {"before": {}, "after": {}, "win": None, "lose": None, "elim": None},
    },
    "t_c1": {
        "chapter": "1", "local": "Quadra do Colégio Santa Faísca", "bg": "quadra", "format": "cup",
        "group": ["turma3b", "fundao", "gremio"], "qf": None, "sf": "teatro", "final": "impecaveis",
        "boss": "impecaveis", "boss_delta": 1, "regular_delta": (5, 7),
        "hooks": {"before": {"G2": "c1_g2_fundao_pre", "F": "c1_final_pre"},
                  "after": {"SF": "c1_sf_pos"},
                  "win": "c1_final_win", "lose": "c1_final_lose", "elim": "c1_repescagem"},
    },
}

# --- cenas --------------------------------------------------------------------------------------
SCENES = {
    # ------------------------------------------------------------------ Prologo
    "p1_garagem": {"bg": "garagem", "cast": ["teo", "ambrosio", "ze"], "lines": [
        ("narrador", "neutro", "Sábado, 14h. Garagem do Vô Nestor. Cheiro de graxa, naftalina e pão de queijo de 1998."),
        ("teo", "cansado", "Vô, o senhor disse que tinha um tesouro aqui. Isso é um aspirador de pó. Com fita crepe. E um chinelo preso."),
        ("ze", "robo", "Bzzzt... cof, cof... (a rodinha esquerda cai e rola até a porta)"),
        ("teo", "susto", "Ele perdeu uma roda sozinho! Eu nem encostei!"),
        ("ambrosio", "feliz", "Esse é o Aspiradex Turbo 74, rapaz. Aposentou três campeões regionais antes de você nascer."),
        ("teo", "susto", "O senhor estava aí atrás desde quando?!"),
        ("ambrosio", "neutro", "Desde as 13h. Seu avô pediu pra eu vigiar a garagem e eu cochilei. Ambrósio Pimenta, professor de robótica do Colégio Santa Faísca. Prazer."),
        ("ambrosio", "neutro", "O clube de robótica vai fechar se não ganhar a Copa Interclasses. Faltam quatro robôs e um milagre. Você tem um robô. E um chinelo."),
        ("teo", "pensando", "O chinelo é estrutural."),
        {"q": "O que o Téo responde?", "opts": [
            {"t": "Vamos consertar o Zé Poeira hoje!", "fx": {"xp_hero": 20},
             "reply": [("ambrosio", "feliz", "Gostei da energia! Pega a chave de fenda e o pão de queijo.")]},
            {"t": "Eu vendo ele no ferro-velho e vou pra casa.", "fx": {"scrap": 25},
             "reply": [("ambrosio", "suor", "Cabeça fria. Mas olha como o Zé Poeira está olhando pra você."),
                       ("ze", "robo", "Bip."),
                       ("teo", "triste", "Tá. Eu conserto. Mas só porque ele fez bip.")]},
        ]},
    ]},

    "p2_oficina": {"bg": "oficina", "cast": ["teo", "ambrosio", "ze"], "lines": [
        ("narrador", "neutro", "Domingo, 9h. A oficina do Colégio Santa Faísca. Doze bancadas, onze com poeira e uma com um bolo."),
        ("ambrosio", "feliz", "Bem-vindo à Oficina. Regra um: robô precisa de peças. Regra dois: peça se compra com sucata. Regra três: o bolo é da Dona Odete, não encoste."),
        ("teo", "neutro", "Professor, eu só trouxe o Zé Poeira. E o chinelo."),
        ("ambrosio", "pensando", "Hum. Deixa eu olhar a caixa de achados e perdidos... (três canetas caem do bolso dele)"),
        ("ambrosio", "feliz", "Achei! Um motor, uma bateria e uma escova de sucção. Tudo meio usado, mas funciona. Quase."),
        ("teo", "susto", "\"Quase\" é a palavra mais assustadora de uma oficina."),
        ("ambrosio", "neutro", "Cada peça entra num encaixe. Motor deixa rápido, bateria deixa durar, escova ajuda a dominar a bola. É só equipar na aba Bancada."),
        ("ze", "robo", "Bip. (a escova de sucção liga sozinha e puxa uma meia do chão)"),
        ("teo", "feliz", "Ele gostou! Olha, ele já achou uma meia!"),
        ("ambrosio", "cansado", "Essa meia é minha. Está desaparecida desde 2019. Mas tudo bem."),
        ("narrador", "neutro", "Três peças instaladas depois, o Zé Poeira anda em linha reta. Quase."),
        {"q": "O que o Téo faz com o chinelo?", "opts": [
            {"t": "Deixa. O chinelo é estrutural.", "fx": {"flag": "chinelo_fica", "xp_hero": 10},
             "reply": [("ambrosio", "feliz", "Respeito. Ninguém discute com um chinelo convicto.")]},
            {"t": "Troca o chinelo por um parafuso.", "fx": {"scrap": 20},
             "reply": [("ze", "robo", "Bzzzt. (a rodinha cai de novo, de ofendida)"),
                       ("teo", "suor", "Tá bom, tá bom. Acho que o parafuso precisa de mais tempo.")]},
        ]},
    ]},

    "p3_peneira_pre": {"bg": "quadra", "cast": ["teo", "ambrosio", "gervasio", "ze"], "lines": [
        ("narrador", "neutro", "Segunda-feira, 15h. Quadra do Santa Faísca. A peneira vale uma vaga na Interclasses. O adversário é o Clube do Xadrez."),
        ("gervasio", "neutro", "Atenção, atenção. Hoje o colégio decide se o clube de robótica merece o orçamento anual de... (olha a prancheta) ...dois reais e cinquenta."),
        ("teo", "susto", "Dois e cinquenta?!"),
        ("gervasio", "pensando", "Mais um clipe, se pedirem com educação. Os clipes são caros, Sr. Moreira."),
        ("ambrosio", "suor", "Diretor Gervásio, o clube tem história! Em 1998..."),
        ("gervasio", "neutro", "Em 1998 eu era estagiário e perdi o almoço numa demonstração. Não tenho boas memórias."),
        ("teo", "neutro", "Quem a gente enfrenta hoje, professor?"),
        ("ambrosio", "pensando", "O Clube do Xadrez. Eles pensam oito jogadas à frente. Os robôs andam duas."),
        ("teo", "feliz", "Então a gente chuta antes de eles terminarem de pensar!"),
        ("ambrosio", "feliz", "Esse é o espírito. Aperte o botão, Téo. E reze pela rodinha."),
        ("ze", "robo", "Bzzzt. Bip. (a rodinha esquerda gira, firme. Por enquanto.)"),
    ]},

    "p4_peneira_pos": {"bg": "quadra", "cast": ["teo", "ambrosio", "gervasio", "ze"], "lines": [
        ("narrador", "neutro", "Fim da peneira. O placar já está no quadro. O sorriso do Téo independe dele."),
        ("gervasio", "neutro", "Sr. Moreira, vi o que precisava ver. O robô cai, o chinelo balança, e mesmo assim ele não desiste."),
        ("teo", "feliz", "Isso é um elogio?"),
        ("gervasio", "pensando", "É uma observação administrativa. O clube fica. Por enquanto."),
        ("ambrosio", "feliz", "Por enquanto! Ouviu, Téo? Por enquanto!"),
        ("gervasio", "neutro", "Em três semanas começa a Copa Interclasses. Se o clube não ganhar, fecha. A sala vira depósito de caixas de giz."),
        ("teo", "susto", "Ganhar?! Contra o colégio inteiro?!"),
        ("ambrosio", "neutro", "Contra as turmas, o Grêmio e os Impecáveis. Um bom pessoal, todos com patrocínio e nenhum com chinelo."),
        ("teo", "pensando", "Professor, quantas vezes o clube já ganhou a Interclasses?"),
        ("ambrosio", "suor", "Hm. Eu cochilei durante essa parte da história."),
        ("teo", "feliz", "Então a gente escreve a parte nova. Zé Poeira, bora?"),
        ("ze", "robo", "Bip. (a rodinha cai. Todos fingem que não viram.)"),
    ]},

    # ------------------------------------------------------------------ Cap. 1
    "c1_intro": {"bg": "quadra", "cast": ["teo", "ambrosio", "gervasio", "bia"], "lines": [
        ("narrador", "neutro", "Copa Interclasses, dia do sorteio. A urna é uma caixa de sapato com a etiqueta \"NÃO ABRIR\"."),
        ("gervasio", "neutro", "Grupo B: Turma 3ºB, Fundão FC, Grêmio e o clube de robótica. Se alguém lembrar de aplaudir, aplauda."),
        ("teo", "feliz", "Três jogos no grupo, e os dois primeiros passam! (aplaude sozinho)"),
        ("ambrosio", "pensando", "O Grêmio... Cuidado. Eles têm patrocínio. E um aspirador em cada gaveta."),
        ("teo", "neutro", "Professor, quem é aquela de bandana, colocando fita num robô alheio?"),
        ("bia", "neutro", "Esse aqui estava solto. Prendi com fita. Agora está firme. De nada."),
        ("ambrosio", "feliz", "Bia Gambiarra, a melhor mecânica do colégio! Bia, que tal entrar no clube?"),
        ("bia", "bravo", "Entrar no clube de robótica? Gambiarra não é esporte, Professor. É um estilo de vida."),
        ("teo", "feliz", "A gente tem fita crepe e um chinelo!"),
        ("bia", "pensando", "...Um chinelo estrutural?"),
        ("teo", "feliz", "Estrutural!"),
        ("bia", "corada", "Vou pensar. Não conta pra ninguém que eu pensei."),
        {"q": "O que o Téo diz pra Bia?", "opts": [
            {"t": "Você faz parte do time, Bia!", "fx": {"flag": "bia_convidada", "xp_team": 10},
             "reply": [("bia", "neutro", "Pressão emocional. Eficiente, mas não vou admitir.")]},
            {"t": "Sem pressão. A porta fica aberta.", "fx": {"flag": "bia_livre", "scrap": 15},
             "reply": [("bia", "feliz", "Gente educada é perigosa. Toma, achei isso no chão. Era seu mesmo.")]},
        ]},
    ]},

    "c1_g2_fundao_pre": {"bg": "quadra", "cast": ["teo", "ambrosio", "bia", "ze"], "lines": [
        ("narrador", "neutro", "Segundo jogo do grupo. Fundão FC, o time do fundo da sala. Eles chegam atrasados e bocejando."),
        ("teo", "neutro", "Professor, os robôs deles estão parados no meio do campo."),
        ("ambrosio", "pensando", "Estão em modo de economia de energia. Nunca vi um time tão... sereno."),
        ("bia", "neutro", "Um deles roncou. Eu ouvi. Robô de verdade ronca, Professor."),
        ("teo", "suor", "O capitão pediu pra esperar. Ele precisa de mais cinco minutos de sono."),
        ("ambrosio", "cansado", "Eu o compreendo profundamente."),
        ("teo", "pensando", "A gente aproveita pra pegar a bola ou isso é antiesportivo?"),
        ("bia", "neutro", "Antiesportivo é perder pra quem está dormindo. Vai lá."),
        ("ze", "robo", "Bzzzt. (o aspirador liga e acorda um robô adversário sem querer)"),
        ("teo", "susto", "Ops! Foi sem querer!"),
        ("narrador", "neutro", "O robô do Fundão desperta, olha em volta e volta a dormir. O capitão aplaude de olhos fechados."),
        ("bia", "corada", "E, Téo... valeu por ter me chamado. Estou só observando. Só.", ("flag", "bia_convidada")),
    ]},

    "c1_sf_pos": {"bg": "quadra", "cast": ["teo", "ambrosio", "bia"], "lines": [
        ("narrador", "neutro", "Semifinal vencida. O Clube de Teatro se despede com uma reverência de dois minutos e um desmaio dramático."),
        ("teo", "feliz", "Gente, a gente vai pra final!"),
        ("ambrosio", "neutro", "Parabéns. Mas vem aqui, Téo. Reparou nos Impecáveis jogando a outra semifinal?"),
        ("teo", "pensando", "Eles ganharam fácil. Cada robô se mexe exatamente igual ao outro."),
        ("ambrosio", "pensando", "Exatamente. Nenhum erro de passe. Nenhuma derrapada. Nem um desvio de um milímetro."),
        ("teo", "neutro", "Isso é ruim?"),
        ("ambrosio", "pensando", "Robô de verdade tem um tremorzinho, Téo. Uma hesitação. O deles parece desenhado a régua."),
        ("bia", "neutro", "Cronometrei, Professor. Trinta e seis passes, todos com a mesma duração. Até o décimo de segundo."),
        ("ambrosio", "suor", "Trinta e seis passes idênticos? Isso não é futebol. É relógio suíço."),
        ("teo", "pensando", "Vai ver eles treinam muito."),
        ("ambrosio", "triste", "Vai ver, Téo. Vai ver."),
        ("narrador", "neutro", "Do outro lado da quadra, um robô branco pisca duas luzes ciano. Ao mesmo tempo. De novo."),
    ]},

    "c1_final_pre": {"bg": "quadra", "cast": ["teo", "vivi", "ambrosio"], "lines": [
        ("narrador", "neutro", "Final da Copa Interclasses. Quadra lotada. Quatro pessoas torcendo, todas parentes."),
        ("vivi", "convencida", "Então você é o Téo Moreira, o garoto que chegou na final com um aspirador de 1974 e um chinelo."),
        ("teo", "neutro", "O chinelo é estrutural."),
        ("vivi", "convencida", "Valentina Albuquerque, presidente do Grêmio, capitã dos Impecáveis. Meus robôs são patrocinados pela Limpex. Zero defeitos, zero desvios."),
        ("ambrosio", "pensando", "Zero desvios... Robô de verdade sempre tem um defeitinho."),
        ("vivi", "bravo", "O senhor está dizendo que meus robôs são perfeitos demais?"),
        ("ambrosio", "neutro", "Estou dizendo que o meu cheira a fita crepe e o seu cheira a hospital."),
        ("teo", "feliz", "Valentina, a gente só quer jogar bola."),
        ("vivi", "corada", "Não é que eu esteja nervosa. É que você é o único obstáculo estatisticamente relevante deste torneio, e eu detesto surpresas. Prepare-se."),
    ]},

    "c1_final_win": {"bg": "quadra", "cast": ["teo", "vivi", "ambrosio", "bia"], "lines": [
        ("narrador", "neutro", "Apito final. O placar sobe. O Santa Faísca fica em silêncio por três segundos e explode."),
        ("teo", "feliz", "A gente ganhou?! O clube não fecha?!"),
        ("ambrosio", "feliz", "Não fecha! (abraça o Téo, derrubando três canetas e um pão de queijo)"),
        ("vivi", "bravo", "Isso... isso não estava nas minhas projeções. Eu tinha noventa e quatro por cento de chance."),
        ("teo", "suor", "Posso dizer que a rodinha ajudou?"),
        ("vivi", "bravo", "Não pode. Eu li o regulamento. Fita crepe não é item proibido, mas deveria ser."),
        ("teo", "feliz", "O chinelo é estrutural. E decisivo.", ("flag", "chinelo_fica")),
        ("teo", "feliz", "O parafuso foi decisivo! E o chinelo, no coração.", ("noflag", "chinelo_fica")),
        ("teo", "feliz", "Até a Dona Odete torceu. Depois de vender a última coxinha.", ("done", "c1_repescagem")),
        ("bia", "feliz", "Gente, o Zé Poeira fez o gol da vitória de costas. Eu vi."),
        ("vivi", "triste", "Vou treinar. Anotem: isso não se repete. (sai marchando e derruba o troféu de participação)"),
        ("ambrosio", "feliz", "Ela vai voltar. Gente assim sempre volta."),
    ]},

    "c1_final_lose": {"bg": "quadra", "cast": ["teo", "vivi", "ambrosio", "bia", "ze"], "lines": [
        ("narrador", "neutro", "Apito final. O placar não ajuda. O Santa Faísca aplaude com educação, como num recital de flauta."),
        ("vivi", "convencida", "Resultado: Impecáveis, um. Moreira, zero. Era o previsto, mas é sempre bom ver a matemática funcionar."),
        ("teo", "triste", "A gente chegou tão perto..."),
        ("vivi", "neutro", "Perto não é gol. Mas... (desvia o olhar) foi uma boa partida. Estatisticamente aceitável."),
        ("bia", "neutro", "Pera. Isso foi um elogio?"),
        ("vivi", "corada", "Foi uma constatação. Não repita. (sai marchando)"),
        ("ambrosio", "pensando", "Téo, olha o Zé Poeira. Continua girando. Teimoso, que nem o dono."),
        ("ze", "robo", "Bip. Bzzzt. (a rodinha cai e rola até os pés de Vivi, que finge não ter visto)"),
        ("teo", "feliz", "Professor, a gente ainda pode tentar a final de novo?"),
        ("ambrosio", "feliz", "O regulamento diz que sim. Artigo sete, escrito a lápis, ao lado de uma mancha de coxinha."),
    ]},

    "c1_repescagem": {"bg": "cantina", "cast": ["teo", "ambrosio", "gervasio", "bia"], "lines": [
        ("narrador", "neutro", "Eliminados no grupo. O silêncio na arquibancada dura até o sino do recreio."),
        ("teo", "triste", "Acabou. O clube vai fechar. Eu vou ter que vender o chinelo."),
        ("narrador", "neutro", "Dona Odete, a Tia da Cantina, surge com uma bandeja de coxinhas e um regulamento plastificado."),
        ("gervasio", "pensando", "Hum. Artigo três, Regra da Repescagem: quem perde no grupo pode tentar de novo, desde que compre uma coxinha."),
        ("teo", "suor", "Isso está mesmo no regulamento?"),
        ("gervasio", "neutro", "Está. Foi a Dona Odete quem escreveu. E é ela quem manda aqui."),
        ("ambrosio", "feliz", "A Regra da Repescagem salva o clube todo ano. Sempre foi coxinha."),
        ("bia", "neutro", "Eu pago uma. Mas a de frango. A de queijo é pra quem não tem ambição."),
        ("gervasio", "neutro", "Sorteio novo, grupo novo. Tentem não perder de novo, o orçamento de clipes é limitado."),
        ("narrador", "neutro", "A Tia da Cantina carimba o formulário com um carimbo em forma de coxinha. É oficial."),
        {"q": "Que coxinha o Téo compra?", "opts": [
            {"t": "De frango, claro.", "fx": {"flag": "coxinha_frango", "xp_team": 5},
             "reply": [("bia", "feliz", "Finalmente alguém com critério.")]},
            {"t": "De queijo, pelo clube.", "fx": {"flag": "coxinha_queijo", "xp_team": 5},
             "reply": [("bia", "bravo", "Eu avisei que ele não tinha ambição."),
                       ("teo", "feliz", "Ambição é com recheio. Queijo.")]},
        ]},
    ]},

    "c1_end": {"bg": "quadra", "cast": ["teo", "ambrosio", "bia", "vivi", "ze"], "lines": [
        ("narrador", "neutro", "Cerimônia de premiação. O troféu é de plástico, mas o brilho é de ouro de dezoito quilates. Quase."),
        ("teo", "feliz", "Professor, olha! Com o nome do clube gravado! Faltou só o \"b\" em \"robótica\"."),
        ("ambrosio", "feliz", "Detalhe. A gente manda corrigir. Ou deixa assim. Fica histórico."),
        ("vivi", "convencida", "Segunda tentativa. Você teve a sorte de uma repetição, Moreira.", ("done", "c1_final_lose")),
        ("bia", "neutro", "Você me chamou com tanta insistência que fiquei com pena. Estou dentro. Mas a fita é minha.", ("flag", "bia_convidada")),
        ("bia", "neutro", "Você deixou a porta aberta e ninguém me pressionou. Isso é raro. Estou dentro. Mas a fita é minha.", ("noflag", "bia_convidada")),
        ("teo", "feliz", "Bem-vinda ao clube, Bia!"),
        ("ze", "robo", "Bip. Bzzzt. Bip bip. (parece um aplauso. Ou um curto-circuito.)"),
        ("vivi", "neutro", "Moreira. (estende um cartão branco com um raio ciano) Cartão da Limpex. O Dr. Augusto Brilhante quer conhecer você."),
        ("teo", "susto", "A Limpex quer falar com a gente?!"),
        ("vivi", "convencida", "Patrocínio. Eles gostam de talentos. E de coisas limpas. (olha o chinelo) Trabalhe nisso."),
        ("ambrosio", "suor", "Limpex... (guarda o cartão no bolso, junto com as três canetas) Interessante."),
        ("teo", "feliz", "Professor, é a nossa chance! Nosso nome num banner!"),
        ("ambrosio", "pensando", "Hum. Chance. Ou armadilha com laço de fita."),
    ]},
}

# --- recompensas (aplicadas uma vez ao fechar o capitulo; idempotentes pela lista `done`) -------
REWARDS = {
    "rw_P": {"scrap": 30, "piece": None, "recruits": [], "unlock": [], "xp_hero": 40, "xp_team": 0,
             "equip_hero_piece": None},
    "rw_1": {"scrap": 120, "piece": {"model": "Escova de Sucção", "rar": 1},
             "recruits": [{"name": "Gambiarra", "role": "DEF", "chassis": "Tanque", "base_ovr": 50,
                           "level": 3, "paint": (255, 150, 40),
                           "piece": {"model": "Borracha", "rar": 0}}],
             "unlock": ["Tanque"], "xp_hero": 30, "xp_team": 0, "equip_hero_piece": None},
}

# --- capitulos ----------------------------------------------------------------------------------
# F_start/F_end = Forca esperada do jogador "normal" (tabela do plano). econ_tier = tier passado a
# garage.match_rewards/refresh_shop durante o capitulo (= tier_done + 1 do Garage). tier_done_on_close
# = clamp(cap-1, -1, 3) gravado em garage.tier_done ao fechar.
CHAPTERS = [
    {"id": "P", "title": "Prólogo", "subtitle": "A Garagem do Vô", "local": "Garagem e Colégio Santa Faísca",
     "F_start": 44.3, "F_end": 44.3, "econ_tier": 0, "tier_done_on_close": -1, "reward": "rw_P",
     "nodes": [("scene", "p1_garagem"), ("scene", "p2_oficina"), ("scene", "p3_peneira_pre"),
               ("tournament", "t_p_treino"), ("scene", "p4_peneira_pos"), ("chapter_end", "P")]},
    {"id": "1", "title": "Capítulo 1", "subtitle": "Copa Interclasses", "local": "Colégio Santa Faísca",
     "F_start": 44.6, "F_end": 47.0, "econ_tier": 0, "tier_done_on_close": 0, "reward": "rw_1",
     "nodes": [("scene", "c1_intro"), ("tournament", "t_c1"), ("scene", "c1_end"),
               ("chapter_end", "1")]},
    # Esqueletos (conteudo = passos 12-15, so dados)
    {"id": "2", "title": "Capítulo 2", "subtitle": "Taça Vale do Pó", "local": "Ginásio Municipal",
     "F_start": 49.7, "F_end": 51.2, "econ_tier": 1, "tier_done_on_close": 1, "reward": None,
     "draft": True, "nodes": []},
    {"id": "3", "title": "Capítulo 3", "subtitle": "Estadual Limpex Cup", "local": "Arena Estadual",
     "F_start": 53.5, "F_end": 55.0, "econ_tier": 2, "tier_done_on_close": 2, "reward": None,
     "draft": True, "nodes": []},
    {"id": "4", "title": "Capítulo 4", "subtitle": "Copa Brasil", "local": "Estádio Nacional",
     "F_start": 55.8, "F_end": 57.2, "econ_tier": 3, "tier_done_on_close": 3, "reward": None,
     "draft": True, "nodes": []},
    {"id": "5", "title": "Capítulo 5", "subtitle": "Mundial de Aspiradores", "local": "Arena Global de Neo-Tóquio",
     "F_start": 61.2, "F_end": 62.5, "econ_tier": 3, "tier_done_on_close": 3, "reward": None,
     "draft": True, "nodes": []},
]
