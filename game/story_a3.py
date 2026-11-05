# -*- coding: utf-8 -*-
"""Dados da campanha: Ato 3 (Copa dos Campeoes, caps. 10-13). Modulo PURO (so dados, sem imports).

C10: cap. 10 (Intercambio, copa) e cap. 11 (A Fabrica, serie em duas versoes pela escolha B2; escolha B4)
e o X-Omega. Os ovr/F do Ato 3 sao PROVISORIOS (continuam a curva medida do Ato 2) ate o C12 calibrar.

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
    "sakura_rb": {"name": "Sakura Reboot", "color": (255, 170, 190), "ovr": 67,
                  "names": ["Mochi 2", "Hana 2", "Neko 2", "Ramen 2", "Origami 2"],
                  "chassis": list(_CH5), "paint": (255, 180, 200), "perfect": False},
    "staub_pro": {"name": "Staubsauger Pro", "color": (200, 170, 60), "ovr": 67,
                  "names": ["Wurst", "Brezel", "Kuckuck", "Pünktlich", "Zeppelin"],
                  "chassis": list(_CH5), "paint": (210, 180, 70), "perfect": False},
    "aspir_noirs": {"name": "Les Aspirateurs Noirs", "color": (60, 70, 120), "ovr": 68,
                    "names": ["Baguette", "Croissant", "Brie", "Béret", "Moustache"],
                    "chassis": list(_CH5), "paint": (40, 45, 70), "perfect": False},
    "nipoteuta": {"name": "Seleção Nipo-Teuta", "color": (255, 120, 160), "ovr": 73,
                  "names": ["Katana", "Bonsai", "Kuckuck", "Pünktlich", "Haiku"],
                  "chassis": list(_CH5), "paint": (245, 245, 250), "perfect": False},
    "mundos": {"name": "Time dos Mundos", "color": (120, 220, 120), "ovr": 77,
               "names": ["Tex", "Mochi", "Wurst", "Brie", "Katana"],
               "chassis": list(_CH5), "paint": (130, 225, 130), "perfect": False},
    # ---- Cap. 11 (A Fabrica): versao corp (renova_limpex) e rebel (independente), mesmos ovr
    "linha": {"name": "Linha de Montagem", "color": (200, 210, 225), "ovr": 68,
              "names": ["LM-01", "LM-02", "LM-03", "LM-04", "LM-05"],
              "chassis": list(_CH5), "paint": (225, 232, 240), "perfect": False},
    "qualidade": {"name": "Controle de Qualidade", "color": (120, 230, 255), "ovr": 73,
                  "names": ["CQ-01", "CQ-02", "CQ-03", "CQ-04", "CQ-05"],
                  "chassis": list(_CH5), "paint": (235, 250, 255), "perfect": True},
    "gerente2": {"name": "Gerente Mk II", "color": (220, 60, 120), "ovr": 79,
                 "names": ["GR-01", "GR-02", "GR-03", "GR-04", "GR-05"],
                 "chassis": list(_CH5), "paint": (240, 240, 245), "perfect": True},
    "sucateiros": {"name": "Sucateiros Elite", "color": (160, 120, 80), "ovr": 68,
                   "names": ["Ferrugem", "Parafuso", "Sucatão", "Gambi", "Remendo"],
                   "chassis": list(_CH5), "paint": (165, 125, 85), "perfect": False},
    "contrabando": {"name": "Contrabando Mk II", "color": (90, 90, 100), "ovr": 73,
                    "names": ["Caixote", "Lona", "Pé-de-cabra", "Lanterna", "Sombra"],
                    "chassis": list(_CH5), "paint": (95, 95, 105), "perfect": False},
    "dono_galpao": {"name": "Dono do Galpão", "color": (230, 150, 50), "ovr": 79,
                    "names": ["Patrão", "Chave", "Cadeado", "Balança", "Cofre"],
                    "chassis": list(_CH5), "paint": (235, 155, 55), "perfect": False},
}

# --- torneios -----------------------------------------------------------------------------------
_HOOKS_C11 = {"before": {"S3": "c11_s3_pre"}, "after": {}, "win": "c11_final_win",
              "lose": "c11_final_lose", "elim": None}
TOURNAMENTS = {
    # Cap. 10: copa no estadio da Copa dos Campeoes. Estagios (F_rec / O, provisorio): G1 84,0 / 67;
    # G2 84,4 / 67; G3 84,8 / 68; SF 85,1 / 73; F 85,5 / 77 (boss_delta 8,5).
    "t_c10": {
        "chapter": "10", "local": "Arena do Intercâmbio", "bg": "estadio", "format": "cup",
        "group": ["sakura_rb", "staub_pro", "aspir_noirs"], "qf": None, "sf": "nipoteuta",
        "final": "mundos", "boss": "mundos", "boss_delta": 8.5, "regular_delta": (16, 18),
        "hooks": {"before": {"G1": "c10_sakura_pre", "G2": "c10_staub", "SF": "c10_sf_pre",
                             "F": "c10_final_pre"},
                  "after": {"SF": "c10_sf_pos"},
                  "win": "c10_final_win", "lose": "c10_final_lose", "elim": "c10_repescagem"},
    },
    # Cap. 11: serie de 3 duelos; versao corp (dentro da fabrica) ou rebel (galpao), nos condicionais
    # pela escolha B2. Estagios (provisorio): S1 86,0 / 68; S2 86,5 / 73; S3 87,0 / 79 (boss_delta 8,0).
    "t_c11_corp": {
        "chapter": "11", "local": "Fábrica da Limpex", "bg": "fabrica", "format": "series",
        "series": ["linha", "qualidade", "gerente2"], "group": [], "qf": None, "sf": None,
        "final": "gerente2", "boss": "gerente2", "boss_delta": 8.0, "regular_delta": (13, 18),
        "hooks": dict(_HOOKS_C11),
    },
    "t_c11_rebel": {
        "chapter": "11", "local": "Galpão Clandestino", "bg": "fabrica", "format": "series",
        "series": ["sucateiros", "contrabando", "dono_galpao"], "group": [], "qf": None, "sf": None,
        "final": "dono_galpao", "boss": "dono_galpao", "boss_delta": 8.0, "regular_delta": (13, 18),
        "hooks": dict(_HOOKS_C11),
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
}

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
}
SIDES = {}
# Rascunhos ("em breve") ate os passos C10/C11. F PROVISORIO: a spec previa 74,4 -> 81,0, mas o Ato 2
# medido (C9, com skills) termina em 83,5; a curva aqui so continua a medida (84 -> 90,4) ate o C12
# calibrar o Ato 3. econ_tier 3 ate o C12 (a spec pede 5-6).
CHAPTERS = [
    {"id": "10", "act": "3", "title": "Capítulo 10", "subtitle": "Intercâmbio",
     "local": "Aeroporto e Dojo", "F_start": 84.0, "F_end": 85.5, "econ_tier": 5, "train_delta": 18,
     "tier_done_on_close": 3, "reward": "rw_10",
     "nodes": [("scene", "c10_aeroporto"), ("scene", "c10_dojo"), ("tournament", "t_c10"),
               ("scene", "c10_end"), ("chapter_end", "10")]},
    {"id": "11", "act": "3", "title": "Capítulo 11", "subtitle": "A Fábrica",
     "local": "Fábrica da Limpex", "F_start": 86.0, "F_end": 87.0, "econ_tier": 6, "train_delta": 18,
     "tier_done_on_close": 3, "reward": "rw_11",
     "nodes": [("scene", "c11_intro"), ("scene", "c11_dudu_hack"), ("scene", "c11_bia"),
               ("tournament", "t_c11_corp", ("flag", "renova_limpex")),
               ("tournament", "t_c11_rebel", ("noflag", "renova_limpex")),
               ("scene", "c11_end"), ("chapter_end", "11")]},
    {"id": "12", "act": "3", "title": "Capítulo 12", "subtitle": "Copa dos Campeões",
     "local": "Coliseu", "F_start": 87.2, "F_end": 88.8, "econ_tier": 3,
     "tier_done_on_close": 3, "reward": None, "nodes": [], "draft": True},
    {"id": "13", "act": "3", "title": "Capítulo 13", "subtitle": "O Chip Zero",
     "local": "Coliseu em apagão", "F_start": 89.0, "F_end": 90.4, "econ_tier": 3,
     "tier_done_on_close": 3, "reward": None, "nodes": [], "draft": True},
]
