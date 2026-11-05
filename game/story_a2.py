# -*- coding: utf-8 -*-
"""Dados da campanha: Ato 2 (Superliga Limpex, caps. 6-9). Modulo PURO (so dados, sem imports).

story.py junta estes dicts/listas nos seus (story._extend) e e o unico ponto de import para o resto
do jogo. Mesmas regras e formatos de story.py (ver o docstring de la); ids nao podem repetir os de
outros modulos. Capitulos aqui levam "act" e entram depois dos do Ato 1, na ordem da lista.

C6: cap. 6 (Taca de Acesso) completo. Os ovr/F seguem os valores iniciais da spec (secao 7) e o
econ_tier fica em 3 ate o C9 estender a economia (TIER_MUL com 7 entradas) e calibrar o Ato 2.
Caps. 7-9 sao rascunhos ("em breve") ate os passos C7/C8.
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
}

# --- recompensas --------------------------------------------------------------------------------
REWARDS = {
    # Cap. 6: sucata, Servo Agil (Epica) e o modulo Arrancada equipado no heroi (o slot Modulo ja foi
    # liberado no fim do Ato 1, rw_5)
    "rw_6": {"scrap": 700, "piece": {"model": "Servo Ágil", "rar": 2}, "recruits": [], "unlock": [],
             "xp_hero": 0, "xp_team": 20, "equip_hero_piece": {"model": "Módulo Arrancada", "rar": 0}},
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
     "tier_done_on_close": 3, "reward": None, "nodes": [], "draft": True},
    {"id": "8", "act": "2", "title": "Capítulo 8", "subtitle": "Playoffs da Superliga",
     "local": "Estádio Limpex", "F_start": 70.4, "F_end": 72.0, "econ_tier": 3,
     "tier_done_on_close": 3, "reward": None, "nodes": [], "draft": True},
    {"id": "9", "act": "2", "title": "Capítulo 9", "subtitle": "O Clone",
     "local": "Laboratório da Limpex", "F_start": 72.4, "F_end": 73.8, "econ_tier": 3,
     "tier_done_on_close": 3, "reward": None, "nodes": [], "draft": True},
]
