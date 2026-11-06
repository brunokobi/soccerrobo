# -*- coding: utf-8 -*-
"""Dados do pos-campanha (Onda D): cenas CURTAS das revanches da Turne Lendaria (NG+). Modulo PURO.

POST_SCENES[id] = {"bg", "cast", "lines"} no mesmo formato de story.SCENES, mas com 2-4 falas e sem
escolha: e a unica cena de cada capitulo no NG+ (as cenas da historia e os ganchos dos torneios sao pulados,
spec secao 12: "cenas curtas, sem repetir dialogos longos"). Ficam FORA de story.SCENES (que exige 8-14
falas e alcancabilidade pelos nos); a chave em `done` e "<id>#<volta do NG+>" (ex.: "ngr_5#2"), entao a
mesma revanche toca uma vez por volta. NG_REVANCHE[cap] = id da cena do capitulo. Mesmas regras de texto
de story.py (Latin-1, aspas retas, fala <= 260 chars e <= 4 linhas de 780 px).
"""

NG_REVANCHE = {str(i): "ngr_%d" % i for i in range(1, 14)}


def _rev(bg, cast, lines):
    return {"bg": bg, "cast": list(cast), "lines": lines}


POST_SCENES = {
    "ngr_1": _rev("quadra", ["teo", "ze", "ambrosio"], [
        ("narrador", "neutro", "Turnê Lendária. A quadra do Santa Faísca de novo, mas os Impecáveis voltaram com robôs de competição e um técnico com prancheta dourada."),
        ("ambrosio", "pensando", "Eles treinaram o ano inteiro só para esta revanche. Isso é lisonjeiro e assustador na mesma medida."),
        ("teo", "determinado", "Então a gente joga como se fosse a primeira vez. Zé, de novo do começo."),
        ("ze", "robo", "Bip. (o Zé limpa a poeira do chinelo, devagar, como quem já viu esse filme.)"),
    ]),
    "ngr_2": _rev("ginasio", ["teo", "bia", "ze"], [
        ("narrador", "neutro", "Ginásio Municipal. O Esquadrão Faxina pintou o nome do Zé no chão. Com um X vermelho em cima."),
        ("bia", "convencida", "Eles trocaram todas as rodinhas. Eu ouvi o barulho daqui. Rodinha nova chia diferente."),
        ("teo", "feliz", "Melhor. Revanche contra time fraco não tem graça."),
    ]),
    "ngr_3": _rev("arena", ["vivi", "teo", "ze"], [
        ("narrador", "neutro", "Arena Estadual. Os Imaculados L-9 voltaram com uma faixa: \"desta vez sem tropeço\"."),
        ("vivi", "pensando", "Fiz a conta. Eles estão bem mais fortes que da primeira vez. A conta não gostou de mim."),
        ("teo", "determinado", "A conta nunca gosta da gente, Vivi. E a gente ganha mesmo assim."),
    ]),
    "ngr_4": _rev("estadio", ["teo", "dudu", "ze"], [
        ("narrador", "neutro", "Estádio Nacional. A Divisão Platinum chegou de helicóptero de brinquedo. Ele pousou torto."),
        ("dudu", "euforico", "Chat, é revanche da Copa Brasil! Quem acha que o Zé ganha manda um chinelo no chat!"),
        ("ze", "robo", "Bip. (o chat inteiro vira um mar de chinelos.)"),
    ]),
    "ngr_5": _rev("mundial", ["teo", "nestor", "ze"], [
        ("narrador", "neutro", "Arena Global de Neo-Tóquio. O Mundial abriu uma chave especial só para os campeões que voltam."),
        ("nestor", "piscando", "Na minha época, quem ganhava o Mundial ia para casa descansar. Vocês voltaram para apanhar de novo. Gosto disso."),
        ("teo", "feliz", "Ninguém vai apanhar, Vô. Só vai suar um pouco."),
    ]),
    "ngr_6": _rev("arena", ["teo", "gabi", "ze"], [
        ("narrador", "neutro", "Taça de Acesso, versão lendária. Todo time da chave já jogou contra o Zé pelo menos uma vez."),
        ("gabi", "convencido", "Eu avisei geral: o Zé tem um truque com a rodinha esquerda. Agora todo mundo marca a rodinha esquerda."),
        ("teo", "pensando", "Então ele usa a direita. Simples."),
    ]),
    "ngr_7": _rev("estadio", ["teo", "vivi", "ze"], [
        ("narrador", "neutro", "Superliga, segunda volta. Os pontos corridos agora valem uma taça de cristal que ninguém sabe limpar."),
        ("vivi", "corada", "Montei a tabela de novo. Desta vez com uma coluna \"revanche\". Está toda em amarelo."),
        ("ze", "robo", "Bip. (o Zé aspira um confete amarelo do chão, por coerência.)"),
    ]),
    "ngr_8": _rev("estadio", ["teo", "bia", "ze"], [
        ("narrador", "neutro", "Playoffs da Superliga. A Guarda Zero trocou o uniforme cinza por um cinza mais escuro. É sinal de que é sério."),
        ("bia", "determinado", "Revisei cada parafuso. Se alguma coisa soltar hoje, a culpa é minha. Nada vai soltar."),
        ("teo", "feliz", "Com você na oficina, nem o chinelo sai do lugar."),
    ]),
    "ngr_9": _rev("laboratorio", ["teo", "zeperfeito", "ze"], [
        ("narrador", "neutro", "Laboratório. O Zé Perfeito pediu para lutar de novo, \"só para medir de novo\"."),
        ("zeperfeito", "feliz", "Registro: desta vez eu não quero vencer. Quero entender por que eu perdi. Mas se eu vencer, tudo bem também."),
        ("ze", "robo", "Bip. (os dois Zés se encaram. Um deles tem chinelo. O outro está com inveja.)"),
    ]),
    "ngr_10": _rev("estadio", ["teo", "kenji", "ze"], [
        ("narrador", "neutro", "Intercâmbio, rodada lendária. O Time dos Mundos trouxe robôs de três continentes e um tradutor que só traduz ofensas."),
        ("kenji", "calmo", "Respire. O adversário é forte, mas a vassoura não sabe disso. Deixe a vassoura jogar."),
        ("teo", "pensando", "Eu não entendi nada e mesmo assim me sinto melhor."),
    ]),
    "ngr_11": _rev("fabrica", ["teo", "dudu", "ze"], [
        ("narrador", "neutro", "A Fábrica, de novo. As esteiras voltaram a rodar e alguém pendurou um cartaz: \"revanche autorizada pelo RH\"."),
        ("dudu", "euforico", "Chat, eles fizeram até crachá para os robôs! O do Zé está escrito \"visitante perigoso\"."),
        ("ze", "robo", "Bip. (o Zé usa o crachá com orgulho, meio torto, preso no chinelo.)"),
    ]),
    "ngr_12": _rev("coliseu", ["teo", "nestor", "ze"], [
        ("narrador", "neutro", "Coliseu. A Copa dos Campeões virou Copa dos Campeões das Revanches. O nome não coube no telão."),
        ("nestor", "feliz", "Todo campeão que vocês venceram está aqui. É a festa mais assustadora em que eu já fui. E eu fui num casamento de engenheiros."),
        ("teo", "determinado", "Então vamos dançar, Vô."),
    ]),
    "ngr_13": _rev("coliseu", ["teo", "xomega", "ze"], [
        ("narrador", "neutro", "O Coliseu apaga outra vez. Um LED vermelho acende no meio do campo. Depois mais quatro."),
        ("xomega", "robo", "REVANCHE REGISTRADA. PROBABILIDADE DE VITÓRIA RECALCULADA. AINDA NÃO GOSTO DO RESULTADO."),
        ("teo", "determinado", "Nem a gente gostou da primeira vez. Bora, Zé. Uma última."),
        ("ze", "robo", "Bip. (o chinelo brilha. Talvez seja só o reflexo do LED. Talvez não.)"),
    ]),
}
