# -*- coding: utf-8 -*-
"""Formacoes dos 5 robos (modulo puro: sem pygame, sem random, sem imports do jogo).

Usadas no Amistoso (friendly.py reexporta), na Campanha, no Modo Robos e na Carreira (campo "formation" do
save de cada modo). FORMATIONS[id]: {"name", "code" (notacao: linhas de linha sem o goleiro), "desc",
"pts": 5 x (fx, fy) = posicao base (fracao x a partir do proprio gol, fracao y) na ordem do motor (indice 0 =
goleiro, 4 = quem da a saida), "push": avanco/recuo do bloco inteiro (fracao do campo)}. Os papeis
(GK/DEF/MID/MID/ATT -> chassi e atributos) NAO mudam: a formacao so muda onde cada robo fica e para onde
volta (soccer.Game.formation_pos). "equilibrada" = soccer.FORMATION de sempre com push 0.0; o motor recebe
None nesse caso (cfg(None) = exatamente o motor antigo; goldens 80/80).

Balanceamento (tests/calib_formations.py, motor real CPU x CPU, mesmas forcas; tabela no docstring daquele
script): ate Forca ~75 (campanha) nenhuma formacao passa de +5 pontos de aproveitamento sobre a EQUILIBRADA; o
efeito cresce com a Forca (as alternativas pioram, a PRESSAO melhora no pos-campanha) e por isso entra no
SIMULAR (SIM_DF abaixo).
"""

DEFAULT = "equilibrada"

FORMATIONS = {
    "equilibrada": {"name": "EQUILIBRADA", "code": "1-2-1", "desc": "a de sempre: um atrás, dois no meio",
                    "pts": ((0.05, 0.50), (0.25, 0.50), (0.45, 0.22), (0.45, 0.78), (0.66, 0.50)),
                    "push": 0.0},
    "retranca": {"name": "RETRANCA", "code": "2-1-1", "desc": "dois zagueiros fechando o meio",
                 "pts": ((0.05, 0.50), (0.22, 0.44), (0.22, 0.56), (0.42, 0.50), (0.62, 0.50)),
                 "push": 0.0},
    "ofensiva": {"name": "OFENSIVA", "code": "1-1-2", "desc": "dois atacantes abertos lá na frente",
                 "pts": ((0.05, 0.50), (0.28, 0.50), (0.47, 0.50), (0.66, 0.29), (0.66, 0.71)),
                 "push": 0.03},
    "quadrado": {"name": "QUADRADO", "code": "2-2", "desc": "duas linhas de dois, bem fechado",
                 "pts": ((0.05, 0.50), (0.23, 0.43), (0.48, 0.39), (0.23, 0.57), (0.48, 0.61)),
                 "push": 0.03},
    "pressao": {"name": "PRESSÃO", "code": "1-2-1", "desc": "linha alta: aperta a saída do rival",
                "pts": ((0.05, 0.50), (0.30, 0.50), (0.52, 0.22), (0.52, 0.78), (0.72, 0.50)),
                "push": 0.01},
}
ORDER = ("equilibrada", "retranca", "ofensiva", "quadrado", "pressao")

# SIMULAR fiel ao motor: efeito medido de cada formacao (contra a EQUILIBRADA, mesmas forcas) convertido em pontos
# de Forca (1 ponto de Forca ~ 1,8 ponto de aproveitamento no motor; ver tests/calib_campaign.py), por Forca do
# time [(F, dF), ...] com interpolacao linear e pontas fixas. Entra em Garage.match_F() (SIMULAR da Campanha,
# Torre, treino e Modo Robos; "Sua Forca" mostrada no painel) e no Career.sim_match. A padrao nao tem entrada
# (dF = 0.0: Forca e SIMULAR exatamente como antes).
SIM_DF = {
    "retranca": ((45, 1.0), (60, -4.5), (75, -11.0), (90, -21.5)),
    "ofensiva": ((45, 2.5), (60, -3.0), (75, -11.0), (90, -12.5)),
    "quadrado": ((45, 2.5), (60, -2.0), (75, -5.5), (90, -6.5)),
    "pressao": ((45, 0.0), (60, 0.5), (75, 2.5), (90, 9.5)),
}


def get(fid):
    """Formacao pelo id (desconhecido -> a padrao)."""
    return FORMATIONS.get(fid) or FORMATIONS[DEFAULT]


def clean(fid):
    """Id valido (str conhecida) ou o padrao: sanitize dos saves."""
    return fid if isinstance(fid, str) and fid in FORMATIONS else DEFAULT


def cycle(cur, step):
    """Proxima formacao da lista (step +1/-1), circular."""
    i = ORDER.index(cur) if cur in FORMATIONS else 0
    return ORDER[(i + step) % len(ORDER)]


def engine(fid):
    """O que o motor recebe (soccer.Team(formation=...)): None para a padrao/desconhecida (motor de sempre),
    senao o dict da formacao."""
    fid = clean(fid)
    return None if fid == DEFAULT else FORMATIONS[fid]


def sim_df(fid, F):
    """Pontos de Forca que a formacao `fid` vale no SIMULAR para um time de Forca F (0.0 na padrao)."""
    pts = SIM_DF.get(clean(fid))
    if not pts:
        return 0.0
    if F <= pts[0][0]:
        return float(pts[0][1])
    for (f0, d0), (f1, d1) in zip(pts, pts[1:]):
        if F <= f1:
            return float(d0 + (d1 - d0) * (F - f0) / float(f1 - f0))
    return float(pts[-1][1])


def label(fid):
    """Texto curto do seletor: "EQUILIBRADA 1-2-1"."""
    f = get(fid)
    return "%s %s" % (f["name"], f["code"])
