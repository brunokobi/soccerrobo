# -*- coding: utf-8 -*-
"""Dados da campanha: Missoes secundarias. Modulo PURO (so dados, sem imports).

C13: as 14 missoes da spec (secao 6). Cada uma e uma partida unica contra Forca atual - 14 (Campaign.
side_ovr), liberada pela recompensa de um capitulo; cena "pre" e "win", recompensa unica (fx: peca,
skill, sucata, XP, flag ou cosmetico). As 4 "Fitas do Vo" contam para o final secreto (story.ENDINGS).

story.py junta estes dicts/listas nos seus (story._extend) e e o unico ponto de import para o resto
do jogo. Mesmas regras e formatos de story.py (ver o docstring de la); ids nao podem repetir os de
outros modulos. Capitulos aqui levam "act" e entram depois dos do Ato 1, na ordem da lista.
"""

CHARACTERS = {}
TOURNAMENTS = {}
REWARDS = {}
CHAPTERS = []

_CH5 = ["Goleiro", "Tanque", "Disco", "Orbital", "Velocista"]


def _team(name, color, names, paint=None):
    """Time de missao: o ovr real vem de Campaign.side_ovr (Forca atual - delta); este e so referencia."""
    return {"name": name, "color": color, "ovr": 50, "names": names, "chassis": list(_CH5),
            "paint": paint or color, "perfect": False}


TEAMS = {
    "merenda": _team("Clube da Merenda", (240, 200, 120), ["Concha", "Panela", "Colher", "Tampa", "Fogão"]),
    "xadrez2": _team("Xadrez Mk II", (230, 230, 230), ["Rei II", "Rainha II", "Torre II", "Bispo II", "Peão II"],
                     (40, 40, 45)),
    "cantina": _team("Turma da Cantina", (230, 120, 60), ["Coxinha", "Esfiha", "Pastel", "Quibe", "Suco"]),
    "sucateiros_fita": _team("Sucateiros", (150, 120, 90), ["Ferrugem", "Lata", "Prego", "Arame", "Mola"]),
    "taxi2": _team("Cooperativa Mk II", (240, 200, 40), ["Bandeirada", "Taxímetro", "Atalho", "Buzina II",
                                                        "Corrida"]),
    "oficina_sul": _team("Oficina do Sul", (120, 160, 200), ["Chave 10", "Macaco", "Graxa", "Calota", "Estepe"]),
    "dupla_trovao": _team("Dupla Trovão", (60, 140, 255), ["Raio", "Trovão", "Nuvem", "Chuva", "Granizo"],
                          (250, 210, 40)),
    "garagem_rival": _team("Garagem Rival", (180, 90, 90), ["Gambi", "Remendo", "Puxadinho", "Bico", "Jeitinho"]),
    "dojo_escondido": _team("Dojo Escondido", (90, 140, 110), ["Sombra", "Bambu", "Névoa", "Pedra", "Lua"],
                            (60, 70, 90)),
    "fiscais": _team("Fiscais da Federação", (190, 130, 255), ["Carimbo", "Lacre", "Protocolo", "Ofício",
                                                                "Selo"]),
    "prototipo_ze": _team("Protótipo Zé", (235, 245, 252), ["ZP-02", "ZP-03", "ZP-04", "ZP-05", "ZP-06"]),
    "colecao_nestor": _team("Coleção Nestor", (230, 170, 90), ["Modelo 1", "Modelo 2", "Modelo 3", "Modelo 4",
                                                               "Modelo 5"]),
    "time_chat": _team("Time do Chat", (80, 230, 120), ["Kkkk", "Primeiro", "Hype", "Like", "Inscrito"]),
    "odete_dream": _team("Odete Dream Team", (255, 200, 120), ["Fubá", "Cenoura", "Chocolate", "Laranja",
                                                               "Milho"]),
}

# --- missoes secundarias (spec secao 6): unlock = recompensa de capitulo ja aplicada ----------------
def _side(title, local, bg, team, unlock, pre, win, reward):
    return {"title": title, "local": local, "bg": bg, "team": team, "delta": 14, "unlock": unlock,
            "scenes": {"pre": pre, "win": win}, "reward": reward, "repeat": False}


SIDES = {
    "s_odete": _side("O Bolo Desaparecido", "Cantina do Santa Faísca", "cantina", "merenda",
                     ("done", "reward:rw_P"), "s_odete_pre", "s_odete_win",
                     {"piece": {"model": "Escova Dupla", "rar": 1}, "xp_team": 30}),
    "s_xadrez2": _side("Revanche do Xadrez", "Quadra do Colégio", "quadra", "xadrez2",
                       ("done", "reward:rw_1"), "s_xadrez2_pre", "s_xadrez2_win",
                       {"skill": {"robot": "hero", "id": "leitura", "rank": 1}}),
    "s_cantina": _side("Copa da Cantina", "Cantina do Ginásio", "cantina", "cantina",
                       ("done", "reward:rw_2"), "s_cantina_pre", "s_cantina_win",
                       {"piece": {"model": "Escova Dupla", "rar": 2}}),
    "s_fita1": _side("Fita do Vô 1", "Ferro-velho da Vila", "oficina", "sucateiros_fita",
                     ("done", "reward:rw_2"), "s_fita1_pre", "s_fita1_win",
                     {"flag": "fita_1", "piece": {"model": "Turbina", "rar": 1}}),
    "s_taxi": _side("Corrida de Táxi", "Ponto de Táxi", "praca", "taxi2",
                    ("done", "reward:rw_4"), "s_taxi_pre", "s_taxi_win", {"scrap": 300}),
    "s_fita2": _side("Fita do Vô 2", "Oficina do Sul", "oficina", "oficina_sul",
                     ("done", "reward:rw_5"), "s_fita2_pre", "s_fita2_win",
                     {"flag": "fita_2", "scrap": 200}),
    "s_gabi1": _side("Treino com o Gabi", "Quadra do Bairro", "quadra", "dupla_trovao",
                     ("done", "reward:rw_6"), "s_gabi1_pre", "s_gabi1_win", {"cosmetic": "raio"}),
    "s_fita3": _side("Fita do Vô 3", "Garagem Rival", "garagem", "garagem_rival",
                     ("done", "reward:rw_7"), "s_fita3_pre", "s_fita3_win",
                     {"flag": "fita_3", "piece": {"model": "Fita Crepe Reforçada", "rar": 3}}),
    "s_ogawa": _side("Provérbio do Ogawa", "Dojo Escondido", "dojo", "dojo_escondido",
                     ("done", "reward:rw_8"), "s_ogawa_pre", "s_ogawa_win",
                     {"skill": {"robot": "hero", "id": "muralha", "rank": 1}}),
    "s_helena": _side("Vistoria Surpresa", "Sede da Federação", "federacao", "fiscais",
                      ("done", "reward:rw_8"), "s_helena_pre", "s_helena_win",
                      {"piece": {"model": "Radar LiDAR", "rar": 2}, "xp_team": 40}),
    "s_clone": _side("O Outro Zé", "Laboratório da Limpex", "laboratorio", "prototipo_ze",
                     ("done", "reward:rw_9"), "s_clone_pre", "s_clone_win",
                     {"piece": {"model": "Módulo Sucção", "rar": 1}}),
    "s_fita4": _side("Fita do Vô 4", "Sótão da Garagem", "garagem", "colecao_nestor",
                     ("done", "reward:rw_10"), "s_fita4_pre", "s_fita4_win",
                     {"flag": "fita_4", "piece": {"model": "Rodinha Esquerda do Zé", "rar": 3}}),
    "s_torre1": _side("Aposta do Dudu", "Estúdio do Dudu", "lanchonete", "time_chat",
                      ("done", "reward:rw_12"), "s_torre1_pre", "s_torre1_win", {"cosmetic": "neon"}),
    "s_final": _side("Último Bolo", "Cantina do Santa Faísca", "cantina", "odete_dream",
                     ("done", "c12_end"), "s_final_pre", "s_final_win", {"cosmetic": "bolo"}),
}

SCENES = {
    # ---- s_odete (depois do Prologo)
    "s_odete_pre": {"bg": "cantina", "cast": ["odete", "teo", "dudu", "bia", "ze"], "lines": [
        ("narrador", "neutro", "Cantina do Colégio Santa Faísca, depois da aula. A Dona Odete está parada na frente de uma forma vazia, com a mão no peito."),
        ("odete", "chorando", "Meu bolo de fubá sumiu! Eu deixei esfriando na janela. Voltei, e só ficou a forma. E um rastro de migalha."),
        ("teo", "pensando", "Um rastro de migalha? Indo para onde?"),
        ("bia", "pensando", "Para a despensa. E tem marca de rodinha no chão. Rodinha pequena. De robô de cozinha."),
        ("dudu", "euforico", "Chat, é um mistério! O Caso do Bolo Desaparecido! Eu vou narrar como detetive. Com voz grave."),
        ("narrador", "neutro", "Na despensa, cinco robôs de cozinha cercam uma fatia de bolo. Eles se viram ao mesmo tempo. Têm migalha na tampa."),
        ("odete", "bravo", "O Clube da Merenda! Os robôs que eu mesma programei para lavar panela! Traidores de avental!"),
        ("ze", "robo", "Bip. (o Zé avança, decidido. Ninguém rouba bolo da Dona Odete na frente dele.)"),
    ]},
    "s_odete_win": {"bg": "cantina", "cast": ["odete", "teo", "dudu", "bia", "ze"], "lines": [
        ("narrador", "neutro", "Fim da partida improvisada na cantina. O Clube da Merenda devolve o que sobrou do bolo. Sobrou meio. Com marca de colher."),
        ("odete", "feliz", "Meio bolo é melhor que bolo nenhum. E agora eu sei quem come escondido. Eles vão lavar panela por um mês."),
        ("teo", "feliz", "Mistério resolvido, Dona Odete!"),
        ("dudu", "feliz", "Chat, o detetive Dudu resolveu o caso. Com ajuda do Zé. Com muita ajuda do Zé. O Zé resolveu sozinho."),
        ("odete", "piscando", "Para agradecer, pega essa escova que eu usava na cozinha. É boa de sucção. Limpa até farinha de fubá."),
        ("bia", "maravilhado", "Uma Escova Dupla! Dona Odete, isso é peça de verdade! Onde a senhora arrumou?"),
        ("odete", "convencida", "Merendeira tem contatos, querida. Trinta anos de recreio."),
        ("ze", "robo", "Bip. (o Zé fica perto da forma de bolo vazia, de guarda. Por via das dúvidas.)"),
    ]},

    # ---- s_xadrez2 (depois do Cap. 1)
    "s_xadrez2_pre": {"bg": "quadra", "cast": ["teo", "vivi", "ambrosio", "ze"], "lines": [
        ("narrador", "neutro", "Quadra do colégio, sábado. O Clube do Xadrez voltou. Os robôs agora têm coroas de papelão e uma estratégia escrita num caderno de cem folhas."),
        ("narrador", "neutro", "O capitão do Xadrez, de óculos e gravata borboleta, aponta para o Zé: \"Revanche. Xeque-mate em quarenta e dois lances.\""),
        ("teo", "pensando", "Futebol não tem xeque-mate."),
        ("vivi", "pensando", "Eles acham que tem. Eles planejaram a partida inteira lance por lance. Se a gente fizer qualquer coisa fora do caderno, eles travam."),
        ("ambrosio", "feliz", "O Xadrez Mk II. Eu admiro. Cem folhas de planejamento contra um aspirador de chinelo. É a luta eterna da teoria contra a prática."),
        ("teo", "determinado", "Então a gente joga fora do caderno. Zé, improvisa."),
        ("vivi", "corada", "E eu vou ler o caderno deles depois. Só por curiosidade. Profissional."),
        ("ze", "robo", "Bip. (o Zé gira duas vezes no lugar, sem motivo nenhum. O capitão do Xadrez anota, preocupado.)"),
    ]},
    "s_xadrez2_win": {"bg": "quadra", "cast": ["teo", "vivi", "ambrosio", "ze"], "lines": [
        ("narrador", "neutro", "Fim de jogo. O Xadrez Mk II perdeu no lance vinte e três, segundo o caderno. O caderno não previa uma rodinha caindo no meio do campo."),
        ("narrador", "neutro", "O capitão do Xadrez, emocionado, entrega o caderno para a Vivi: \"Leia o capítulo sobre leitura de jogo. É o melhor que eu já escrevi.\""),
        ("vivi", "maravilhado", "Leitura de jogo... Téo, isso é ouro. Ele mapeou como prever o passe do adversário. O Zé pode aprender."),
        ("teo", "feliz", "O Zé aprendendo a ler jogo? Ele não sabe nem ler placa."),
        ("ambrosio", "pensando", "Ele não precisa ler a placa, Téo. Só o adversário. É outra alfabetização."),
        ("vivi", "determinado", "Eu passo para o chip dele hoje à noite. Com o caderno e uma lanterna."),
        ("teo", "feliz", "Obrigado, Xadrez! Revanche da revanche quando quiserem!"),
        ("ze", "robo", "Bip. (o Zé aspira uma folha solta do caderno. Era o capítulo de aberturas. Agora ele sabe abrir. Mais ou menos.)"),
    ]},

    # ---- s_cantina (depois do Cap. 2)
    "s_cantina_pre": {"bg": "cantina", "cast": ["teo", "dudu", "bia", "odete", "ze"], "lines": [
        ("narrador", "neutro", "Cantina do Ginásio Municipal. Os funcionários da cantina montaram um time de robôs para a tradicional Copa da Cantina. O prêmio é uma escova profissional."),
        ("dudu", "feliz", "Chat, a Copa da Cantina! O campeonato mais saboroso do bairro! O juiz é um pastel. Mentira. Mas devia ser."),
        ("odete", "convencida", "Esse time da cantina é rival histórico da merenda. Eles acham que coxinha é melhor que bolo. Téo, você tem uma missão."),
        ("teo", "determinado", "Defender a honra do bolo. Entendido."),
        ("bia", "pensando", "Os robôs deles cheiram a fritura. O sensor do Zé vai ficar confuso. Eu vou colocar um prendedor de roupa na antena dele."),
        ("teo", "pensando", "Robô não tem nariz, Bia."),
        ("bia", "convencida", "O Zé tem tudo que precisar. Com fita."),
        ("ze", "robo", "Bip. (o Zé usa o prendedor de roupa na antena com dignidade.)"),
    ]},
    "s_cantina_win": {"bg": "cantina", "cast": ["teo", "dudu", "bia", "odete", "ze"], "lines": [
        ("narrador", "neutro", "Vitória do Zé na Copa da Cantina. O time da coxinha aceita a derrota com elegância e entrega o prêmio: uma escova dupla de sucção, profissional."),
        ("odete", "euforico", "O bolo venceu a coxinha! Isso vai para o mural da merenda! Com moldura!"),
        ("dudu", "feliz", "Chat, a honra do bolo está salva. O chat está dividido entre bolo e coxinha. Eu sou neutro. Eu como os dois."),
        ("bia", "maravilhado", "Escova Dupla Épica! Com cerda dupla e motor reforçado. O Zé vai sugar até pensamento."),
        ("teo", "feliz", "Obrigado, pessoal da cantina! Na próxima, a gente traz bolo para vocês."),
        ("odete", "piscando", "Traz mesmo. A melhor forma de vencer um rival é dar comida para ele. Ele fica sem argumento."),
        ("bia", "feliz", "E eu tiro o prendedor da antena do Zé. Missão cumprida."),
        ("ze", "robo", "Bip. (o Zé não deixa a Bia tirar o prendedor. Ele gostou. Agora é estilo.)"),
    ]},

    # ---- s_fita1 (depois do Cap. 2)
    "s_fita1_pre": {"bg": "oficina", "cast": ["teo", "nestor", "bia", "ambrosio", "ze"], "lines": [
        ("narrador", "neutro", "Ferro-velho da vila. O Vô Nestor ligou do cruzeiro: \"Téo, eu escondi umas fitas cassete pela cidade, faz trinta anos. A primeira está no ferro-velho.\""),
        ("teo", "pensando", "Fitas cassete? O que tem nelas, Vô?"),
        ("narrador", "neutro", "Vô Nestor, no telefone: \"Música de bingo. E umas coisas no fim que só quem ouve até o fim entende. Ninguém ouve até o fim. Bingo é muito longo.\""),
        ("bia", "pensando", "A fita está numa caixa no meio da sucata. E a sucata tem dono. Os Sucateiros. Com robôs feitos de lata de óleo."),
        ("ambrosio", "feliz", "Os Sucateiros só negociam de um jeito: partida. Quem ganha leva o que quiser do ferro-velho."),
        ("teo", "determinado", "Então a gente joga pela fita do Vô."),
        ("bia", "feliz", "E se sobrar tempo, eu levo uma turbina enferrujada. Ela está me chamando."),
        ("ze", "robo", "Bip. (o Zé fareja a sucata. Ele se sente em casa.)"),
    ]},
    "s_fita1_win": {"bg": "oficina", "cast": ["teo", "nestor", "bia", "ambrosio", "ze"], "lines": [
        ("narrador", "neutro", "Vitória contra os Sucateiros. O chefe deles entrega uma caixa de sapato com uma fita cassete escrita a caneta: \"Bingo 1 - não pular o fim\"."),
        ("teo", "feliz", "A primeira fita do Vô! E ainda tem a turbina que a Bia queria!"),
        ("bia", "euforico", "Ela está enferrujada, mas o coração dela é bom. Eu limpo. Com fita, é claro."),
        ("ambrosio", "pensando", "Música de bingo e uma mensagem no fim. O Nestor sempre foi dramático. Vamos ouvir na garagem, com um rádio velho."),
        ("narrador", "neutro", "Na garagem, a fita toca quarenta minutos de música de bingo. No fim, depois de um chiado, a voz do Vô Nestor jovem: \"Parte um de quatro. Guarde bem.\""),
        ("teo", "pensando", "Parte um de quatro? De quê?"),
        ("ambrosio", "pensando", "Não sei. Mas o Nestor nunca escondeu nada à toa. Nem chinelo."),
        ("ze", "robo", "Bip. (o Zé encosta a antena no rádio e fica quieto, ouvindo o chiado do fim da fita.)"),
    ]},

    # ---- s_taxi (depois do Cap. 4)
    "s_taxi_pre": {"bg": "praca", "cast": ["teo", "dudu", "vivi", "ze"], "lines": [
        ("narrador", "neutro", "Ponto de táxi da praça central. A Cooperativa dos Taxistas voltou com robôs novos, pintados de amarelo, e um desafio: corrida de bola até o outro lado da praça."),
        ("narrador", "neutro", "O líder da Cooperativa, de boné e bigode: \"Aposto trezentos de sucata que o meu Taxímetro chega primeiro. E cobra bandeirada.\""),
        ("vivi", "pensando", "Trezentos de sucata. É uma aposta alta. E eles conhecem cada atalho da praça."),
        ("dudu", "euforico", "Chat, aposta de taxista! Isso é patrimônio cultural! Eu vou narrar como corrida de Fórmula 1!"),
        ("teo", "determinado", "A gente aceita. Mas o Zé não cobra bandeirada."),
        ("vivi", "convencida", "O Zé também não conhece atalho. Ele faz o caminho dele. Que geralmente é reto até alguma coisa cair."),
        ("dudu", "feliz", "E foi dada a largada! Quer dizer, ainda não. Mas eu já estou emocionado."),
        ("ze", "robo", "Bip. (o Zé alinha na linha de partida e acende o LED como farol.)"),
    ]},
    "s_taxi_win": {"bg": "praca", "cast": ["teo", "dudu", "vivi", "ze"], "lines": [
        ("narrador", "neutro", "Fim da partida. A Cooperativa paga a aposta em notas de sucata amassadas, contadas duas vezes, com o taxímetro ligado só por tradição."),
        ("dudu", "euforico", "Chat, trezentos de sucata! O Zé ganhou dos taxistas na casa deles! Na praça deles! Com o atalho deles!"),
        ("vivi", "pensando", "Trezentos de sucata dá para três upgrades. Ou um upgrade e muita fita. Depende de quem decide."),
        ("teo", "feliz", "Valeu, pessoal! Boa corrida!"),
        ("narrador", "neutro", "O líder da Cooperativa, coçando o bigode: \"Esse aspirador corre como quem esqueceu o freio em casa. Gostei. Volta sempre.\""),
        ("vivi", "corada", "Eu vou guardar o recibo. Ele cobrou bandeirada da gente mesmo assim. Cinquenta centavos. Por princípio."),
        ("dudu", "feliz", "Chat, o Zé virou lenda dos taxistas. Agora toda corrida na cidade vai ter uma história dele."),
        ("ze", "robo", "Bip. (o Zé estaciona no ponto de táxi, como se esperasse passageiro.)"),
    ]},

    # ---- s_fita2 (depois do Cap. 5)
    "s_fita2_pre": {"bg": "oficina", "cast": ["teo", "ambrosio", "bia", "nestor", "ze"], "lines": [
        ("narrador", "neutro", "Oficina do Sul, uma garagem antiga do outro lado da cidade. A segunda fita do Vô está pendurada na parede, dentro de uma moldura, como troféu."),
        ("nestor", "feliz", "A Oficina do Sul é do meu amigo Ademar. A gente disputava tudo nos anos oitenta. Ele ficou com a fita numa aposta de pão de queijo."),
        ("teo", "pensando", "O senhor apostou uma fita secreta por pão de queijo?"),
        ("nestor", "convencido", "Era um pão de queijo muito bom, Téo. Você não entende a época."),
        ("ambrosio", "feliz", "O Ademar só devolve a fita se a gente ganhar a revanche. Os robôs dele têm trinta anos e não perdem desde mil novecentos e noventa e dois."),
        ("bia", "maravilhado", "Trinta anos sem perder! Eles devem ter muita fita."),
        ("nestor", "determinado", "Eles têm teimosia. É mais forte que fita. Quase."),
        ("ze", "robo", "Bip. (o Zé olha para os robôs da Oficina do Sul. Eles parecem os avós dele. Ele acena com a antena.)"),
    ]},
    "s_fita2_win": {"bg": "oficina", "cast": ["teo", "ambrosio", "bia", "nestor", "ze"], "lines": [
        ("narrador", "neutro", "Vitória contra a Oficina do Sul. Pela primeira vez desde 1992, os robôs do Ademar perdem. O Ademar tira a fita da moldura, devagar, e entrega ao Vô Nestor."),
        ("nestor", "chorando", "Ademar, seu velho teimoso. Ainda guardou a moldura. Eu ainda devo o pão de queijo, não devo?"),
        ("narrador", "neutro", "O Ademar ri e entrega também um saco de sucata: \"Leva. O meu pão de queijo vale mais que isso. Mas eu sou generoso.\""),
        ("teo", "feliz", "Segunda fita! Faltam duas, Vô!"),
        ("ambrosio", "pensando", "A fita dois termina igual: \"Parte dois de quatro\". E um som de chinelo batendo no chão. Ritmado. Como um código."),
        ("bia", "pensando", "Um código de chinelo? Professor, isso é a coisa mais Vô Nestor que eu já ouvi."),
        ("nestor", "piscando", "Guardem bem. Um dia vocês vão entender. Ou não. Mas guardem."),
        ("ze", "robo", "Bip. (o Zé bate o chinelo no chão, no mesmo ritmo da fita. O Vô Nestor fica pálido. E depois sorri.)"),
    ]},

    # ---- s_gabi1 (depois do Cap. 6)
    "s_gabi1_pre": {"bg": "quadra", "cast": ["gabi", "teo", "dudu", "ze"], "lines": [
        ("narrador", "neutro", "Quadra do bairro, fim de tarde. O Gabi Trovão aparece com dois robôs e um desafio: treino de dupla, sem câmera, sem patrocinador."),
        ("gabi", "convencido", "Treino. Só treino. Sem contrato, sem live, sem nada. Quero ver se o chinelo aguenta um dois contra dois de verdade."),
        ("teo", "feliz", "Topo! Sem live, Dudu."),
        ("dudu", "suor", "Sem live? Nem um storyzinho? Nem um áudio? Tá bom. Eu sofro em silêncio."),
        ("gabi", "pensando", "A Dupla Trovão é o meu time de treino. Eles são rápidos e meio malcriados. Igual a mim, segundo a minha mãe."),
        ("teo", "pensando", "Por que você quer treinar com a gente, Gabi?"),
        ("gabi", "neutro", "Porque todo mundo que eu treino tem medo de mim. Vocês não têm. Isso é útil. E um pouco irritante."),
        ("ze", "robo", "Bip. (o Zé encosta no robô do Gabi. É um cumprimento. O robô do Gabi não sabe o que fazer e encosta de volta.)"),
    ]},
    "s_gabi1_win": {"bg": "quadra", "cast": ["gabi", "teo", "dudu", "ze"], "lines": [
        ("narrador", "neutro", "Fim do treino. O Zé venceu, mas foi apertado. O Gabi senta no chão da quadra, suado, e ri pela primeira vez sem câmera por perto."),
        ("gabi", "feliz", "Tá bom, chinelo. Você é bom. Não conta para ninguém que eu disse isso."),
        ("teo", "feliz", "Você também é bom, Gabi. E quando não está fazendo pose, é ainda melhor."),
        ("gabi", "pensando", "Toma. Um adesivo de raio. Era da minha primeira equipe, quando eu tinha nove anos. Combina com o Zé. Ele é rápido quando quer."),
        ("dudu", "maravilhado", "O Gabi deu um adesivo! Chat... desculpa, eu estou sem live. Eu estou contando para a parede."),
        ("teo", "feliz", "Obrigado, Gabi. Ele vai usar com orgulho."),
        ("gabi", "piscando", "Usa no lado esquerdo. É o lado da rodinha. Dá sorte."),
        ("ze", "robo", "Bip. (o Zé exibe o adesivo de raio. Ele gira devagar, para todo mundo ver.)"),
    ]},

    # ---- s_fita3 (depois do Cap. 7)
    "s_fita3_pre": {"bg": "garagem", "cast": ["teo", "nestor", "bia", "vivi", "ze"], "lines": [
        ("narrador", "neutro", "A terceira fita está na Garagem Rival, do outro lado da rua. O dono é o Seu Lúcio, que inventa coisas desde a mesma época do Vô Nestor. E nunca perdoou o Vô por nada."),
        ("nestor", "bravo", "O Lúcio! Na minha época, ele copiava tudo que eu fazia. Eu fazia uma gambiarra, ele fazia uma gambiarra igual, só que pior."),
        ("teo", "pensando", "E por que a fita está com ele, Vô?"),
        ("nestor", "suor", "Eu perdi uma aposta. Sobre quem tinha a gambiarra mais bonita. Ele ganhou. Por um voto. O voto da mãe dele."),
        ("vivi", "pensando", "Os robôs dele se chamam Gambi, Remendo, Puxadinho, Bico e Jeitinho. Isso é uma provocação direta."),
        ("bia", "determinado", "Gambiarra contra gambiarra. Fita contra fita. Hoje se decide quem é o rei da rua."),
        ("nestor", "determinado", "Ganha essa, Téo. Pela fita. E pelo voto da mãe do Lúcio, que foi injusto."),
        ("ze", "robo", "Bip. (o Zé olha para o robô Jeitinho. Os dois têm fita no mesmo lugar. Eles se reconhecem.)"),
    ]},
    "s_fita3_win": {"bg": "garagem", "cast": ["teo", "nestor", "bia", "vivi", "ze"], "lines": [
        ("narrador", "neutro", "Vitória contra a Garagem Rival. O Seu Lúcio entrega a terceira fita e, junto, um rolo de fita crepe antigo, grosso, amarelado. Reforçado."),
        ("bia", "maravilhado", "Isso é... isso é fita crepe dos anos oitenta! Reforçada com tecido! Não fabricam mais! É uma relíquia!"),
        ("nestor", "feliz", "O Lúcio guardou a fita boa esse tempo todo. Ele sempre teve bom gosto para fita. Só para fita."),
        ("narrador", "neutro", "Na garagem, a terceira fita toca. No fim: \"Parte três de quatro. Se você chegou até aqui, a música de bingo não é música. É uma chave.\""),
        ("vivi", "pensando", "Uma chave. As fitas juntas abrem alguma coisa. Ou desligam."),
        ("teo", "pensando", "Desligam o quê, Vô?"),
        ("nestor", "pensando", "Uma coisa que eu e o Ambrósio fizemos e não devíamos. Quando faltar uma fita, eu conto. Prometo."),
        ("ze", "robo", "Bip. (o Zé passa a fita crepe antiga na antena. Ela gruda para sempre. Ele aprova.)"),
    ]},

    # ---- s_ogawa (depois do Cap. 8)
    "s_ogawa_pre": {"bg": "dojo", "cast": ["ogawa", "teo", "kenji", "ze"], "lines": [
        ("narrador", "neutro", "Um dojo escondido atrás do estádio. O Mestre Ogawa espera sentado, de olhos fechados. Na frente dele, cinco robôs cobertos com panos escuros."),
        ("ogawa", "calmo", "Um provérbio para hoje: o muro que não cai não protege. O muro que sabe cair protege duas vezes."),
        ("teo", "pensando", "Isso... é sobre defesa?"),
        ("kenji", "suor", "É sobre tudo e sobre nada, Téo-san. Eu levei cinco anos para entender o primeiro provérbio. Era sobre arroz."),
        ("ogawa", "neutro", "O Dojo Escondido são meus robôs mais antigos. Eles não atacam. Eles só defendem. Quem fizer um gol neles aprende a Muralha."),
        ("teo", "determinado", "Um gol só?"),
        ("ogawa", "piscando", "Um gol só. Ninguém fez em trinta anos. Mas ninguém tinha chinelo."),
        ("ze", "robo", "Bip. (o Zé se curva diante dos robôs cobertos. Os panos balançam, como se eles se curvassem de volta.)"),
    ]},
    "s_ogawa_win": {"bg": "dojo", "cast": ["ogawa", "teo", "kenji", "ze"], "lines": [
        ("narrador", "neutro", "Gol do Zé. Depois de trinta anos, a defesa do Dojo Escondido foi vazada. Os panos escuros caem dos robôs. Por baixo, eles sorriem. Têm sorrisos pintados."),
        ("ogawa", "feliz", "O chinelo entrou onde a técnica não entra. A Muralha agora é dele."),
        ("kenji", "maravilhado", "Sensei, o senhor está chorando?"),
        ("ogawa", "calmo", "É o vento, Kenji. O vento do dojo é muito emotivo."),
        ("teo", "feliz", "Obrigado, Mestre. O Zé vai defender como um muro. Um muro que sabe cair."),
        ("ogawa", "piscando", "Lembre: o muro protege o que está atrás dele. Escolha bem o que vai ficar atrás do seu."),
        ("kenji", "feliz", "Téo-san, você entendeu? Eu não entendi. Mas eu sinto que é importante."),
        ("ze", "robo", "Bzzzt. (o Zé para na frente do Téo, de lado, como um pequeno muro. O Mestre Ogawa assente.)"),
    ]},

    # ---- s_helena (depois do Cap. 8)
    "s_helena_pre": {"bg": "federacao", "cast": ["helena", "teo", "ambrosio", "vivi", "ze"], "lines": [
        ("narrador", "neutro", "Sede da Federação. A Dra. Helena chamou o time para uma vistoria surpresa. Desta vez, quem vai ser vistoriada é a equipe de fiscais da própria Federação."),
        ("helena", "neutro", "Os Fiscais da Federação precisam treinar. Eles vistoriam robôs há anos, mas nunca jogaram contra um. Hoje jogam contra o de vocês."),
        ("ambrosio", "maravilhado", "Fiscais jogando! Helena, isso é revolucionário. É como um juiz entrar em campo para aprender o que é falta."),
        ("helena", "calmo", "É exatamente isso. A samambaia vai arbitrar. Ela está muito animada. Dá para ver pelas folhas."),
        ("vivi", "pensando", "Os robôs deles se chamam Carimbo, Lacre, Protocolo, Ofício e Selo. Eles vão demorar para se mexer. Tudo deles precisa de autorização."),
        ("teo", "feliz", "Então a gente joga rápido. Sem papelada."),
        ("helena", "piscando", "Ganhe, e a Federação doa uma peça apreendida em vistoria. Épica. Legalizada. Com nota fiscal."),
        ("ze", "robo", "Bip. (o Zé passa no scanner da Federação. Aprovado. Ele exibe o carimbo do chinelo para os fiscais.)"),
    ]},
    "s_helena_win": {"bg": "federacao", "cast": ["helena", "teo", "ambrosio", "vivi", "ze"], "lines": [
        ("narrador", "neutro", "Vitória do Zé. Os Fiscais da Federação aprenderam muito. Principalmente que bola não espera protocolo."),
        ("helena", "neutro", "Registro da vistoria: a equipe de fiscais foi aprovada com ressalvas. A ressalva é: eles são muito lentos. Assinado, a samambaia."),
        ("vivi", "maravilhado", "A samambaia assinou? Como?"),
        ("helena", "calmo", "Com uma folha. Ela pisa no carimbo e depois no papel. Temos um protocolo para isso."),
        ("ambrosio", "feliz", "Helena, a Federação nunca foi tão divertida. E tão eficiente."),
        ("helena", "piscando", "Aqui está a peça prometida. Um Radar LiDAR Épico, apreendido de um time que tentou entrar com dois radares. Agora é de vocês. Legalmente."),
        ("teo", "feliz", "Obrigado, doutora! E obrigado, samambaia!"),
        ("ze", "robo", "Bip. (o Zé se aproxima da samambaia e espera. Ela se inclina um pouquinho. É o jeito dela de dizer de nada.)"),
    ]},

    # ---- s_clone (depois do Cap. 9)
    "s_clone_pre": {"bg": "laboratorio", "cast": ["teo", "bia", "nestor", "ze"], "lines": [
        ("narrador", "neutro", "Laboratório da Limpex, abandonado depois da série contra o Zé Perfeito. Num canto, cinco protótipos antigos, com defeito de fábrica, ainda ligados."),
        ("bia", "pensando", "Esses são os primeiros clones. Os que deram errado. Um gira para a esquerda sem parar. Outro só anda de ré."),
        ("nestor", "triste", "Protótipos com defeito. Igual ao Zé quando eu fiz. Na minha época, defeito era só o começo da personalidade."),
        ("teo", "pensando", "Eles parecem... perdidos. Ninguém vai cuidar deles?"),
        ("narrador", "neutro", "Os protótipos se juntam e rolam até o Zé. Não para atacar. Para jogar. Eles empurram uma bola velha na direção dele."),
        ("bia", "maravilhado", "Eles querem jogar! Eles nunca jogaram! A Limpex só testava eles em esteira!"),
        ("teo", "feliz", "Então a gente joga com eles. Com carinho."),
        ("ze", "robo", "Bip. (o Zé devolve a bola com um toque leve. O protótipo que só anda de ré dá um apito de alegria.)"),
    ]},
    "s_clone_win": {"bg": "laboratorio", "cast": ["teo", "bia", "nestor", "ze"], "lines": [
        ("narrador", "neutro", "Fim da partida no laboratório. Os protótipos perderam, mas giram de felicidade. O que só anda de ré dá uma volta inteira de ré pelo campo."),
        ("bia", "feliz", "Eles adoraram! Olha, o da esquerda até parou de girar. Ele estava só ansioso!"),
        ("nestor", "feliz", "Vou levar todos para a garagem. Tem espaço. Eu tiro a panela do bingo do chão."),
        ("teo", "feliz", "O senhor vai adotar cinco protótipos, Vô?"),
        ("nestor", "piscando", "Na minha época, quem tinha um robô tinha cinco. Eles vêm em família."),
        ("bia", "maravilhado", "E um deles deixou cair isso: um módulo de sucção magnética. Original da Limpex. Ainda na caixa."),
        ("nestor", "feliz", "Presente dos primos. Coloca no Zé. Ele merece um pouco de magnetismo."),
        ("ze", "robo", "Bip. (o Zé apita para cada protótipo, um por um. Eles apitam de volta, desafinados. É uma família.)"),
    ]},

    # ---- s_fita4 (depois do Cap. 10)
    "s_fita4_pre": {"bg": "garagem", "cast": ["teo", "nestor", "ambrosio", "vivi", "ze"], "lines": [
        ("narrador", "neutro", "Sótão da garagem do Vô Nestor. A quarta fita estava aqui o tempo todo, dentro de uma caixa trancada, protegida pela Coleção Nestor: os cinco primeiros robôs que o Vô construiu."),
        ("nestor", "neutro", "Eu deixei a última fita com eles. Eles foram programados para entregar só para quem vencesse uma partida. Nem eu consigo pegar. Eu tentei. Perdi de sete."),
        ("ambrosio", "pensando", "A Coleção Nestor. O Modelo 1 ao Modelo 5. Os avós do Zé. Nestor, o Modelo 3 ainda tem o pára-choque de lata de goiabada?"),
        ("nestor", "feliz", "Tem. E ainda cheira a goiabada."),
        ("vivi", "determinado", "São os projetos originais do senhor Nestor. Eles devem jogar como o Zé, só que com trinta anos de prática."),
        ("teo", "determinado", "Então é o Zé contra a família dele. Pela última fita."),
        ("nestor", "piscando", "Ganha, Téo. E quando eles perderem, não fica com pena. Eles gostam de perder. Eu ensinei."),
        ("ze", "robo", "Bip. (o Zé encara o Modelo 1. Os dois têm a mesma antena torta. O Modelo 1 pisca devagar, como quem reconhece um neto.)"),
    ]},
    "s_fita4_win": {"bg": "garagem", "cast": ["teo", "nestor", "ambrosio", "vivi", "ze"], "lines": [
        ("narrador", "neutro", "Vitória do Zé contra a Coleção Nestor. O Modelo 1 abre a caixa trancada. Dentro, a quarta fita e uma rodinha esquerda, velha e gasta."),
        ("nestor", "chorando", "A rodinha original do Zé. A primeira que caiu, trinta anos atrás. Eu guardei. Não tive coragem de jogar fora."),
        ("teo", "maravilhado", "A primeira rodinha... Vô, ela ainda gira!"),
        ("narrador", "neutro", "A quarta fita toca. No fim: \"Parte quatro de quatro. As quatro juntas, tocadas no chip do Ômega, reiniciam o projeto. Só use se ele acordar. Assinado, Nestor e Ambrósio.\""),
        ("ambrosio", "susto", "O projeto Ômega! Nestor, a gente escondeu o desligamento do Ômega em música de bingo?"),
        ("nestor", "convencido", "Ninguém ouve música de bingo até o fim, Ambrósio. Era o esconderijo perfeito."),
        ("vivi", "determinado", "Então agora a gente tem as quatro partes. Se o X-Ômega acordar, a gente tem como reiniciar ele."),
        ("ze", "robo", "Bip. (o Zé encosta na rodinha antiga. As duas rodinhas giram juntas, por um segundo, no mesmo ritmo.)"),
    ]},

    # ---- s_torre1 (depois do Cap. 12)
    "s_torre1_pre": {"bg": "lanchonete", "cast": ["dudu", "teo", "bia", "ze"], "lines": [
        ("narrador", "neutro", "Estúdio improvisado do Dudu, nos fundos de uma lanchonete. Ele fez uma aposta ao vivo com o chat: se o Zé perder para o Time do Chat, ele pinta o cabelo de verde."),
        ("dudu", "suor", "Chat, eu apostei o meu cabelo. O meu cabelo! O chat montou um time de robôs com os nomes que vocês mais escrevem nos comentários."),
        ("teo", "pensando", "Kkkk, Primeiro, Hype, Like e Inscrito. Dudu, esses nomes são estranhos."),
        ("dudu", "feliz", "São os nomes mais escritos do meu chat. O Primeiro joga sempre na frente. O Kkkk ri de tudo e se distrai."),
        ("bia", "feliz", "Se a gente ganhar, o chat dá alguma coisa?"),
        ("dudu", "euforico", "Um rastro neon para o Zé! Eles fizeram uma vaquinha. O Zé vai deixar uma luz por onde passa!"),
        ("teo", "determinado", "Pelo cabelo do Dudu, então."),
        ("ze", "robo", "Bip. (o Zé olha para o cabelo do Dudu. Depois para o pote de tinta verde. Ele entende a gravidade da situação.)"),
    ]},
    "s_torre1_win": {"bg": "lanchonete", "cast": ["dudu", "teo", "bia", "ze"], "lines": [
        ("narrador", "neutro", "Vitória do Zé contra o Time do Chat. O cabelo do Dudu está salvo. O chat, derrotado, cumpre a promessa e manda o rastro neon."),
        ("dudu", "chorando", "O meu cabelo! Ele está salvo! Chat, obrigado por perder! É a primeira vez que eu agradeço uma derrota de vocês!"),
        ("bia", "maravilhado", "O rastro neon! Liga, Zé, liga!"),
        ("narrador", "neutro", "O Zé dá uma volta pela lanchonete. Atrás dele, um rastro de luz verde-água fica no ar por um segundo, como um cometa pequeno."),
        ("teo", "feliz", "Ficou incrível! O Zé virou um cometa!"),
        ("dudu", "feliz", "Chat, o cometa Zé! Alguém faz um meme! Já fizeram. Já tem doze memes. Um deles é muito bom."),
        ("bia", "pensando", "A tinta verde ficou sobrando. Eu vou usar na fita. Fita verde. Por que não?"),
        ("ze", "robo", "Bip. (o Zé dá mais uma volta só para ver o rastro. Ele é um pouquinho vaidoso.)"),
    ]},

    # ---- s_final (no Cap. 13)
    "s_final_pre": {"bg": "cantina", "cast": ["odete", "teo", "gervasio", "dudu", "ze"], "lines": [
        ("narrador", "neutro", "Cantina do Santa Faísca, numa tarde calma antes da grande final. A Dona Odete juntou os robôs da merenda e montou o Odete Dream Team."),
        ("odete", "determinado", "Último bolo, Téo. Antes da batalha de vocês, uma partida só nossa. Se vocês ganharem, o bolo é de vocês. Se perderem, o bolo também é. Mas aí eu fico triste."),
        ("gervasio", "chorando", "Dona Odete, isso é a coisa mais bonita que já aconteceu nesta cantina. Depois do pudim de 1998."),
        ("teo", "feliz", "Dona Odete, a senhora vai jogar contra a gente?"),
        ("odete", "convencida", "Eu vou TÉCNICA contra vocês. Os robôs se chamam Fubá, Cenoura, Chocolate, Laranja e Milho. Todos os sabores que eu já fiz."),
        ("dudu", "euforico", "Chat, a final da merenda! O jogo mais delicioso da temporada! Eu estou com fome e com emoção!"),
        ("gervasio", "feliz", "Eu apito! Eu sempre quis apitar! Mesmo que seja na cantina!"),
        ("ze", "robo", "Bip. (o Zé cumprimenta o robô Fubá. Ele tem cheiro de forno. O Zé fica feliz por motivos que não sabe explicar.)"),
    ]},
    "s_final_win": {"bg": "cantina", "cast": ["odete", "teo", "gervasio", "dudu", "ze"], "lines": [
        ("narrador", "neutro", "Vitória do Zé. O Odete Dream Team aplaude com as conchas. A Dona Odete tira do forno um bolo enorme, de cinco sabores, um por andar."),
        ("odete", "chorando", "O último bolo da temporada. Para dar força para a final. Comam devagar. Não, comam rápido. Bolo quente é melhor."),
        ("gervasio", "chorando", "Cinco andares! Dona Odete, a senhora fez um prédio de bolo!"),
        ("teo", "feliz", "Obrigado, Dona Odete. Por todo bolo, de todos os jogos."),
        ("odete", "feliz", "E para o Zé, uma comemoração nova. Quando ele fizer gol, ele vai soltar um bolinho de confete. De papel, que ele não come. Mas vai que um dia."),
        ("dudu", "euforico", "Chat, a comemoração do bolo! O Zé vai comemorar gol com bolo! Isso é o futuro do futebol!"),
        ("gervasio", "feliz", "Fim de jogo! Eu apitei! Com o apito da Limpex! Brincadeira, com um apito de bambu que a Dra. Helena me deu."),
        ("ze", "robo", "Bip. (o Zé testa a comemoração nova. Um bolinho de papel voa da antena. Todo mundo aplaude. Até as conchas.)"),
    ]},
}
