# -*- coding: utf-8 -*-
"""Calibragem da campanha contra o MOTOR REAL (lento, opcional): mede o aproveitamento V+E/2 do jogador
e confere o SIMULAR (campaign.sim_bias(O)) e as metas de dificuldade (passo 16).

Uso (da raiz; ~12 min com n=300, 4 processos; nao grava nada em disco):
  .venv/bin/python tests/calib_campaign.py [--n 300] [--procs 4] [--chapters 1,3] [--json out.json]
  .venv/bin/python tests/calib_campaign.py --grid --n 200 --json grade.json     (grade F x O, regressao)
  .venv/bin/python tests/calib_campaign.py --skills --chapters 3,5 --n 200       (B9: garage COM skills)
Para cada checkpoint (treino e cada estagio do torneio de cada capitulo: G1..G3, [QF], SF, final) monta um
Garage de Forca F = F_rec do estagio (F_start + (F_end - F_start) * i/(n-1), como Campaign._match_action;
F_start/F_end sao a Forca da politica gulosa) pela API do garage (nivel + pecas, ver build_garage_for) e
joga o MOTOR (Game.start_robot_match, TUNING_ROBOTS, bateria ligada, 90 s, usuario sempre mandante como na
campanha, seeds 0..n-1, 10 variantes de adversario) contra o time gerado como em Campaign._opp_team
(story.TEAMS: names/chassis/jitter=not perfect/paint, ovr efetivo com pity 0). Imprime V/E/D, V+E/2 do
motor, o Poisson com o vies atual (SIM) e o Poisson(F-2) antigo.

REGRESSAO do vies (campaign.sim_bias): grade F 44..65 x O 36..64 (n=200, com e sem jitter) + os checkpoints;
o motor e aproximadamente linear, V+E/2 ~ 34 + 1.8*F - 1.8*O (rmse ~4 pts, ~ ruido do motor), mais plano
em F do que o Poisson; ajuste L1 de F - bias(O): bias = clamp(5 + 1.5*(O-40), -2, 8). A "perfeicao" (sem
jitter) nao muda o aproveitamento de forma mensuravel (|dif| < ruido).

METAS do passo 16 (motor): treino 60-75; regulares 58-66; SF 52-58; chefes 45-52; chefe final do Mundial
42-50. O motor e MUITO mais duro que o Poisson contra adversarios fortes: para dar V+E/2 ~60% o adversario
regular precisa estar ~11-13 pontos de ovr abaixo da Forca (F-O ~ 7 so da 46%).

TABELA FINAL (n=300, seeds 0..299, 03/10/2026). ANTES = story do passo 15 (ovr e F do plano);
DEPOIS = story calibrada. F = Forca real do garage de teste; motor = V+E/2 %; Pois(F-2) = Poisson antigo
(SIM_BIAS=2); SIM(O) = simulador novo; dif = SIM - motor.
  checkpoint                 | ANTES: F    O  motor Pois(F-2) | DEPOIS: F    O  motor  SIM(O)  dif
  P treino Clube do Xadrez   |        43.7  36   73.2   62.8   |         43.7  36   73.2   69.2  -4.0
  1 treino                   |        44.7  38   66.7   60.6   |         44.7  36   66.8   71.2  +4.4
  1 G1 Turma 3ºB             |        44.7  38   58.2   60.6   |         44.7  38   58.2   60.6  +2.4
  1 G2 Fundão FC             |        45.7  39   56.3   60.6   |         45.7  39   56.3   57.2  +0.9
  1 G3 Grêmio                |        45.7  40   54.5   58.4   |         46.7  39   63.2   59.5  -3.7
  1 SF Clube de Teatro       |        46.7  42   43.7   56.1   |         47.7  40   56.0   56.1  +0.1
  1 F Os Impecáveis          |        47.7  46   34.8   49.3   |         47.7  41   53.8   50.4  -3.4
  2 treino                   |        49.5  43   50.3   60.1   |         51.4  39   71.2   69.7  -1.4
  2 G1 Padaria Pão Quen      |        49.5  43   46.5   60.1   |         51.4  40   70.5   64.5  -6.0
  2 G2 Tios do Churrasc      |        49.9  43   55.7   61.1   |         51.4  40   64.7   64.5  -0.2
  2 G3 Academia Sem Esf      |        51.4  45   48.3   60.1   |         51.7  41   60.3   59.5  -0.8
  2 SF Impecáveis Mk II      |        51.4  46   43.7   57.9   |         52.7  43   54.5   53.8  -0.7
  2 F Esquadrão Faxina       |        51.4  50   43.7   48.7   |         53.7  47   48.2   47.0  -1.2
  3 treino                   |        53.7  47   44.5   60.6   |         55.7  43   65.0   60.6  -4.4
  3 G1 Bombeiros Volunt      |        53.7  46   48.2   62.8   |         55.7  43   64.2   60.6  -3.6
  3 G2 Coral Desafinado      |        53.7  48   45.8   58.4   |         56.2  43   65.7   61.7  -4.0
  3 G3 Detetives do Qua      |        54.7  48   45.2   60.6   |         56.2  44   58.3   59.5  +1.2
  3 SF Sindicato dos Ze      |        54.7  51   47.2   53.8   |         57.2  46   55.0   57.2  +2.2
  3 F Imaculados L-9         |        55.7  54   41.8   49.3   |         58.2  51   46.2   48.1  +1.9
  4 treino                   |        56.2  49   44.5   61.7   |         58.2  47   58.3   57.2  -1.1
  4 G1 Escoteiros Eletr      |        56.2  50   45.2   59.5   |         58.2  44   67.7   63.9  -3.8
  4 G2 Cartório Veloz        |        56.2  50   47.0   59.5   |         59.2  45   67.2   63.9  -3.3
  4 G3 Cooperativa dos       |        56.2  51   45.7   57.2   |         60.2  46   62.2   63.9  +1.7
  4 SF Platinum Reserva      |        56.2  53   36.7   52.7   |         60.7  50   57.8   56.1  -1.7
  4 F Divisão Platinum       |        57.2  56   36.5   48.1   |         60.7  54   46.2   47.0  +0.8
  5 treino                   |        60.7  54   52.3   60.6   |         63.6  52   59.5   58.1  -1.4
  5 G1 Sakura Vacuum Cl      |        60.7  55   46.8   58.4   |         63.6  47   66.8   68.9  +2.1
  5 G2 Staubsauger Spor      |        61.7  57   41.8   56.1   |         64.5  48   63.0   68.9  +5.9
  5 G3 Les Aspirateurs       |        61.7  57   41.8   56.1   |         64.5  49   62.7   66.8  +4.2
  5 QF Dust Bunnies USA      |        62.7  58   45.0   56.1   |         64.9  50   64.5   65.5  +1.0
  5 SF Dojo do Kenji         |        62.7  59   44.2   53.8   |         64.9  53   56.2   58.9  +2.8
  5 F Hiperlimpos X-9        |        62.7  63   29.7   44.7   |         65.9  58   45.0   49.8  +4.8
  motor (DEPOIS): treino media 64.2 (58-71) | regulares 63.5 (56-71) | SF 55.9 (54-58) | chefes 47.9 (45-54;
  chefe final do Mundial 45.0). |SIM - motor|: media 2.5, max 6.0 (duas celulas >5: 6.0 e 5.9, dentro do
  ruido de +-4.6 do motor com n=300).
  motor (ANTES): treino 51.7 | regulares 48.2 | SF 43.1 | chefes 37.3 (final do Mundial 29.7).
Valores medidos antes (n=400, passo 6): treino F43.7 O36 72.8% | Cap1 grupo F44.7 O38 65.0% | Cap1 chefe
F47.7 O46 36.1% (o motor nao e funcao so de F-O).
Opcao antiga --roles (chassis de papel) removida: o motor usa os atributos, nao o chassis.

B9 (02/11/2026, n=200, caps. 3 e 5): garage COM skills (--skills: mod_on + SKILL_KIT rank 1; F = rating
com skills.team_skill_force, aqui no teto 4,0) contra a mesma garage SEM skills (Ato 1 real):
  checkpoint             F    O | COM skills: motor  SIM  dif | SEM skills: motor  SIM  dif
  3 treino             55.7  43 |            63.0  60.6 -2.4 |            66.5  60.6 -5.9
  3 G1 Bombeiros       55.7  43 |            66.5  60.6 -5.9 |            64.5  60.6 -3.9
  3 G2 Coral           55.7  43 |            65.0  60.6 -4.4 |            61.8  60.6 -1.1
  3 G3 Detetives       56.7  44 |            66.5  60.6 -5.9 |            64.0  60.6 -3.4
  3 SF Sindicato       56.7  46 |            62.0  56.1 -5.9 |            54.0  56.1 +2.1
  3 F Imaculados L-9   57.7  51 |            47.0  47.0 -0.0 |            43.8  47.0 +3.2
  5 treino             63.1  52 |            59.0  57.0 -2.0 |            56.8  57.0 +0.2
  5 G1 Sakura          63.1  47 |            68.8  67.9 -0.9 |            66.0  67.9 +1.9
  5 G2 Staubsauger     64.1  48 |            71.8  67.9 -3.9 |            67.0  67.9 +0.9
  5 G3 Aspirateurs     65.1  49 |            67.0  67.9 +0.9 |            64.0  67.9 +3.9
  5 QF Dust Bunnies    65.1  50 |            67.0  65.8 -1.2 |            68.8  65.8 -3.0
  5 SF Dojo do Kenji   65.4  53 |            63.5  60.0 -3.5 |            54.5  60.0 +5.5
  5 F Hiperlimpos X-9  65.4  58 |            48.5  48.7 +0.2 |            43.8  48.7 +4.9
  |SIM - motor|: COM skills media 2,8 (max 5,9; dif media com sinal -2,7) | SEM skills 3,1 (max 5,9; +0,4).
  COM <= 3 pontos: sim_bias NAO foi ajustado. O vies negativo com skills vem do teto SK_CAP: o kit soma
  ~6,5 F por robo e so 4,0 entram no F (o SIMULAR fica um pouco pessimista, a favor do jogador).
  Ato 1 nao tem skills (mod_on so liga em rw_5): a coluna SEM e o mesmo caminho de antes (ruido n=200).

C9 - ATO 2 (05/11/2026, --skills, caps. 6-8 n=200, cap. 9 n=300). F_start/F_end medidos com a politica
gulosa do test_campaign_balance (que no Ato 2 compra nos da arvore e equipa skills): 74,1->75,6 | 76,5->78,1 |
79,8->81,7 | 83,1->83,5. A spec previa 66,6 -> 73,8 (teto de skills 4,0); com SK_CAP 9,0 a Forca do
Ato 2 fica ~8 pontos acima, entao os ovr foram refeitos (regulares F-O ~16-17, SF ~11-12, chefes ~7-8) e o
treino do Ato 2 usa train_delta 18 (o 12 do Ato 1 dava ~55%).
  checkpoint                 F    O  motor  SIM(O)  dif
  6 treino                 74.0   56   70.0   71.8  +1.8
  6 G1 Brigada da Pia      74.0   57   65.2   69.8  +4.5
  6 G2 Esquadrão do Rodo   74.0   58   63.0   67.7  +4.7
  6 G3 Faxineiros Mk III   75.0   58   65.2   69.8  +4.5
  6 SF Gabi e os Trovões   75.0   64   52.8   56.8  +4.0
  6 F Brigada Higiene      75.5   68   51.8   48.8  -3.0
  7 treino                 76.5   58   74.8   72.8  -2.0
  7 R1 Real Esfregão       76.5   60   62.5   68.8  +6.3
  7 R2 Atlético Micro-on   76.5   60   62.5   68.8  +6.3
  7 R3 Dínamo Pó de Arro   77.5   61   67.5   68.8  +1.3
  7 R4 Sporting Ventilad   77.5   62   63.5   66.7  +3.2
  7 R5 Clube da Cera Líq   77.5   62   63.5   66.7  +3.2
  7 SF Impecáveis Mk III   77.5   65   54.2   60.1  +5.9
  7 F Platinum Elite       77.5   71   46.0   46.5  +0.5
  8 treino                 79.5   62   72.5   70.8  -1.7
  8 G1 Coletivo do Pano    79.5   63   64.8   68.8  +4.0
  8 G2 Os Sem-Poeira       80.4   64   66.8   68.7  +1.9
  8 G3 Lavanderia FC       80.4   64   66.8   68.7  +1.9
  8 QF Dust Bunnies Pro    81.4   66   59.8   66.5  +6.8
  8 SF Dojo do Kenji 2.0   81.4   69   52.8   60.0  +7.2
  8 F Guarda Zero          81.4   74   50.8   48.6  -2.1
  9 treino                 83.3   65   68.7   72.4  +3.8
  9 S1 Droides de Plantão  83.3   67   65.2   68.4  +3.2
  9 S2 Reserva da Valquír  83.3   69   54.3   64.2  +9.8   (duelo do meio da serie: meta de SF)
  9 S3 Zé Perfeito e a G   83.3   76   49.7   48.4  -1.3
  motor: treino 60-75 (68,7-74,8) | regulares 59,8-67,5 | SF/duelo do meio 52,8-54,3 | chefes 46,0-51,8.
  |SIM - motor| media ~4; o SIMULAR fica otimista (+6 a +10) contra adversarios de O 66-69 fora do chefe
  (sim_bias satura em 8 a partir de O 42). Nao foi mexido: mudar sim_bias desloca o Ato 1 calibrado; fica
  como ponto de atencao para o C12 (um sim_bias por Ato, se o Ato 3 repetir o padrao).

C12 - ATO 3 (05/11/2026, --skills, n=200, 3 rodadas). F medido (gulosa com skills): 85,4->86,8 | 89,7->91,3 |
92,2->92,9 | 93,8->94,2. Rodada 1 com as diferencas do Ato 2 (regulares F-O ~17, chefes ~8): motor bem
abaixo das metas (regulares 52,6, chefes 38,8; X-Omega 31,2) e SIMULAR +14 em media (ate +24): acima de
F ~85 o motor ACHATA (atributos perto do teto; a Forca segue subindo por nivel/skills). Correcoes: ovr do
Ato 3 quase planos (regulares 68-72, SF/duelo do meio 72-75, chefes 76-78; o min/max de ovr nunca cai
entre capitulos), train_delta 21 e sim_bias(O, F) com +0,8 por ponto de F acima de 82 (teto 12; Ato 1 nao
muda, Ato 2 so no fim do cap. 9). Rodada 3 (final):
  checkpoint                 F    O  motor  SIM(O)  dif
  10 treino                85.3   64   66.8   73.2  +6.4
  10 G1 Sakura Reboot      85.3   68   60.0   65.0  +5.0
  10 G2 Staubsauger Pro    85.3   69   62.0   62.8  +0.8
  10 G3 Les Aspirateurs N  86.2   69   61.2   63.2  +1.9
  10 SF Seleção Nipo-Teut  86.2   72   52.2   56.5  +4.2
  10 F Time dos Mundos     87.0   76   47.2   47.7  +0.5
  11 treino                89.6   69   64.5   64.6  +0.1
  11 S1 Linha de Montagem  89.6   71   58.2   60.3  +2.0
  11 S2 Controle de Quali  90.4   73   52.0   56.1  +4.1   (duelo do meio: meta de SF)
  11 S3 Gerente Mk II      91.2   77   51.0   47.4  -3.6
  12 treino                92.1   71   64.0   61.4  -2.6
  12 G1 Campeões do Sul    92.1   71   67.0   61.4  -5.6
  12 G2 Rainha da Cera     92.1   71   67.0   61.4  -5.6
  12 G3 Titãs do Vale      92.9   72   54.8   59.5  +4.7
  12 QF Dojo All-Stars     92.9   73   60.0   57.3  -2.7
  12 SF Platinum Imperial  92.9   75   52.0   52.7  +0.7
  12 F Imaculados Ômega    92.9   77   52.5   48.1  -4.4
  13 treino                93.7   73   58.2   57.6  -0.6
  13 S1 Droides Ômega      93.7   72   59.8   59.9  +0.1
  13 S2 Guarda Pretoriana  94.5   75   52.0   53.4  +1.4   (duelo do meio: meta de SF)
  13 S3 X-Ômega Prime      94.5   78   43.5   46.6  +3.1   (chefe final: meta 42-50)
  motor: treino 58-67 | regulares 55-67 | SF/duelo do meio 52 | chefes 47-52 (final 43,5). |SIM - motor| media 2,9.

ONDA D - POS-CAMPANHA (05/11/2026, --post --n 100; garage com skills, adversario generico; Torre com o
modificador do andar). F 94,5 = Forca do fim do Ato 3 (gulosa); F 87,9 = a "potencial" da spec (~88). SIM
antes = sim_bias da campanha, sem alivio nem desconto; SIM agora = + POST_SIM_RELIEF (4) - ARENA_SIM_DF.
  celula                       F    O  V/E/D     motor | SIM antes  dif | SIM agora  dif
  NG+ F88 O60                 87.9  60  78/16/6    86.0   81.2   -4.8   87.1   +1.1
  NG+ F88 O70                 87.9  70  50/22/28   61.0   61.7   +0.7   70.2   +9.2
  NG+ F88 O78                 87.9  78  42/21/37   52.5   43.6   -8.9   52.7   +0.2
  NG+ F88 O85                 87.9  85  26/33/41   42.5   28.5  -14.0   36.9   -5.6
  NG+ F88 O90                 87.9  90  26/32/42   42.0   19.4  -22.6   26.5  -15.5
  NG+ F94 O60                 94.5  60  84/13/3    90.5   83.3   -7.2   88.7   -1.8
  NG+ F94 O70                 94.5  70  63/20/17   73.0   64.6   -8.4   72.8   -0.2
  NG+ F94 O78                 94.5  78  29/25/46   41.5   46.6   +5.1   55.7  +14.2
  NG+ F94 O85                 94.5  85  31/28/41   45.0   31.2  -13.8   39.8   -5.2
  NG+ F94 O90                 94.5  90  16/22/62   27.0   21.6   -5.4   29.1   +2.1
  Torre 10 goleiro_gigante    94.5  63  70/18/12   79.0   78.4   -0.6   76.6   -2.4
  Torre 15 bola_pesada        94.5  68  69/13/18   75.5   68.8   -6.7   74.8   -0.7
  Torre 20 bateria_curta      94.5  72  40/29/31   54.5   60.2   +5.7   61.3   +6.8
  Torre 25 goleiro_gigante    94.5  76  26/26/48   39.0   51.1  +12.1   48.9   +9.9
  Torre 30 bola_pesada        94.5  81  38/24/38   50.0   39.8  -10.2   46.6   -3.4
  Torre 35 bateria_curta      94.5  86  19/33/48   35.5   29.1   -6.4   30.2   -5.3
  Torre 39 -                  94.5  89  21/18/61   30.0   23.4   -6.6   31.2   +1.2
  Torre 40 goleiro_gigante    94.5  90  15/26/59   28.0   21.6   -6.4   19.9   -8.1
  Torre 30 sem mod            94.5  81  24/26/50   37.0   39.8   +2.8   48.9  +11.9
  Torre 40 sem mod            94.5  90  16/22/62   27.0   21.6   -5.4   29.1   +2.1
  |SIM - motor|: antes media 7,8 (com sinal -6,3); agora 5,5 (com sinal +0,4); ruido do motor ~+-9 (n=100).
  Leitura: acima de F ~88 o motor quase nao melhora (F 88 e F 94 dao ~42-45 contra O 85). O NG+ e
  alcancavel com retentativas: as voltas I-III saturam no teto 90 a partir do cap. 6 (I) ou 4-5 (II/III),
  onde cada partida vale ~27-45 de V+E/2 (= chance de passar um mata-mata com penaltis); o pity do chefe
  (-3) e as derrotas sem custo seguram. Torre: andares 1-25 acima de 39 (a maioria 55-80); 30-40 entre 28 e
  50. Modificadores (com x sem, mesma F): bateria curta e goleiro gigante pesam ate -13 contra O 85; contra
  O 90 o motor ja esta no piso e o efeito some no ruido; a bola pesada ficou neutra (o chute mais fraco,
  testado junto, fazia o time forte marcar 5-6 gols e foi retirado).
"""
import argparse
import math
import os
import random
import sys
from multiprocessing import Pool

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "game"))
os.chdir(os.path.join(ROOT, "game"))

import pygame  # noqa: E402

import campaign as cm  # noqa: E402
import career  # noqa: E402
import garage as gm  # noqa: E402
import prefs  # noqa: E402

# nunca le/grava os saves reais (stores em memoria); torcida OFF (o warm e caro e nao muda a simulacao)
gm._store_get = cm._store_get = career._store_get = lambda: None
gm._store_set = cm._store_set = career._store_set = lambda t: True
prefs._store_get = lambda: '{"v": 1, "crowd": "OFF"}'
prefs._store_set = lambda t: True
prefs.reset_cache()

import parts  # noqa: E402
import robot_league as rl  # noqa: E402
import robots  # noqa: E402
import soccer  # noqa: E402
import story  # noqa: E402

DT = 1 / 60
CHECK_CHAPTERS = ("1", "3", "5")        # chefe do Cap.1, do Cap.3 e final do Mundial (quando existirem)
_g = None
BAL = {"motor": "Motor Escovado", "bateria": "Célula Longa", "parachoque": "Borracha",
       "chutador": "Solenoide", "succao": "Escova de Sucção", "sensor": "Infravermelho",
       "chip": "Chip de CPU"}


# ---------------------------------------------------------------- Garage de Forca conhecida
def _equip_all(g, rar, lvl):
    for r in g.robots:
        r["slots"] = {s: None for s in parts.SLOTS}
    g.inventory = []
    for r in g.robots:
        for slot in parts.GEAR_SLOTS:
            pc = g.new_piece(BAL[slot], rar, lvl)
            g.inventory.append(pc)
            assert g.equip(r["id"], pc["id"])[0]


# B9: skills por papel do titular (GOL, DEF, MEI, MEI, ATA) quando build_garage_for(F, with_skills=True):
# 2 ativas + 1 passiva (carga 5 <= 6), rank 1. A Forca F do garage ja inclui a forca delas (team_rating
# com mod_on soma skills.team_skill_force), entao o SIMULAR recebe o mesmo F que o jogador veria.
SKILL_KIT = {"GK": ("elastica", "lancador", "poupanca"), "DEF": ("muralha", "blindagem", "poupanca"),
             "MID": ("succao", "pressao", "leitura"), "ATT": ("arrancada", "curva", "matador")}
SKILL_RANK = 1


def give_skills(g, rank=SKILL_RANK):
    """Liga mod_on e equipa o SKILL_KIT (aprendido direto, como uma recompensa de historia)."""
    import skills
    g.flags[gm.MOD_FLAG] = 1
    for slot, rid in zip(gm.LINEUP_SLOTS, g.lineup):
        r = g.robot(rid)
        r["skills"] = skills.new_robot_skills()
        for sid in SKILL_KIT[slot]:
            skills.learn_skill(r, sid, rank)
            ok, msg = skills.equip_skill(r, sid)
            assert ok, msg


def build_garage_for(F, with_skills=False):
    """Garage (campanha nova) com Forca ~F: escada nivel/pecas pela API do garage (a primeira
    configuracao com rating >= F-2) e ajuste fino por um deslocamento uniforme dos atributos base.
    with_skills: mod_on + SKILL_KIT nos titulares; F (rating) inclui a forca das skills."""
    g = cm.new_campaign(random.Random(7)).garage
    ladder = [(None, 0, lv) for lv in range(1, 11)]                      # so nivel
    ladder += [(rar, lvl, 10) for rar in (0, 1, 2, 3) for lvl in (0, 3, 5)]
    if with_skills:                                                       # C9 (Ato 2): nivel ate 15
        g.cap = gm.CAMPAIGN_CAP
        ladder += [(3, 5, lv) for lv in range(11, gm.CAMPAIGN_CAP + 1)]
    for rar, lvl, level in ladder:
        for r in g.robots:
            r["level"], r["xp"] = level, 0
        if rar is None:
            for r in g.robots:
                r["slots"] = {s: None for s in parts.SLOTS}
            g.inventory = []
        else:
            _equip_all(g, rar, lvl)
        if g.rating() >= F - 2.0:
            break
    g.auto_lineup()
    if with_skills:
        give_skills(g)
    for _ in range(40):                                                   # ajuste fino
        d = F - g.rating()
        if abs(d) < 0.3:
            break
        step = 1 if d > 0 else -1
        for r in g.robots:
            for a in robots.ATTRS:
                r["base"][a] = int(max(robots.ATTR_MIN, min(robots.ATTR_MAX, r["base"][a] + step)))
    return g


def story_team(tid, ovr, seed=777):
    return boss_team(tid, ovr, seed)


def boss_team(tid, ovr, seed=777):
    spec = story.TEAMS[tid]
    t = rl.opponent_team(spec["name"], spec["color"], ovr, seed, names=spec["names"],
                         chassis=spec["chassis"], jitter=not spec["perfect"])
    for e in t["squad"]:
        e["paint"] = tuple(spec["paint"])
    return t


# ---------------------------------------------------------------- motor
def _game():
    global _g
    if _g is None:
        pygame.init()
        _g = soccer.Game(pygame.display.set_mode((soccer.W, soccer.H)))
    return _g


def one(args):
    home, away, seed = args[:3]
    arena = args[3] if len(args) > 3 else None             # Onda D: modificador de arena da Torre do Po
    g = _game()
    random.seed(seed)
    old = soccer.BATTERY_ON
    soccer.BATTERY_ON = True
    try:
        g.start_robot_match(home, away, lambda s, e: None, tuning=robots.TUNING_ROBOTS, arena=arena)
        while g.state != "over":
            g.step(DT)
        return g.score[0], g.score[1]
    finally:
        soccer.BATTERY_ON = old


def pois_pmf(lam, kmax=25):
    p, out = math.exp(-lam), []
    for k in range(kmax):
        out.append(p)
        p *= lam / (k + 1)
    return out


def poisson_wdl(F, O):
    """(V, E, D) exatos de quick_sim(F, O)."""
    d = (F - O) * rl.SIM_SLOPE * rl.SIM_K / 2.0
    ph, pa = pois_pmf(rl.GOALS_AVG * math.exp(d)), pois_pmf(rl.GOALS_AVG * math.exp(-d))
    w = sum(ph[i] * pa[j] for i in range(len(ph)) for j in range(i))
    dr = sum(ph[i] * pa[i] for i in range(len(ph)))
    return w, dr, 1 - w - dr


def points(w, d):
    return 100.0 * (w + d / 2.0)


def implied_bias(F, O, eng_pts):
    best = None
    for bi in range(-10, 81):
        b = bi / 10.0
        w, d, _ = poisson_wdl(F - b, O)
        err = abs(points(w, d) - eng_pts)
        if best is None or err < best[0]:
            best = (err, b)
    return best[1]


def opp_team(tid, ovr, seed):
    """Adversario exatamente como Campaign._opp_team (names/chassis/jitter=not perfect/paint)."""
    return boss_team(tid, ovr, seed)


def table_cells(chapters=None):
    """Celulas da tabela final: por capitulo jogavel, o treino (F_start, ovr de campaign.training_ovr
    com adversario generico) e cada estagio do torneio (G1..G3, [QF], SF, F) com F = F_rec do estagio
    (F_start + (F_end - F_start) * i / (n-1), como Campaign._match_action) e o ovr efetivo (pity 0).
    Devolve [(rotulo, tipo, tid, ovr, F)], tipo em train/reg/qf/sf/boss/ptrain."""
    out = []
    for ch in story.CHAPTERS:
        if ch.get("draft") or not ch["nodes"] or (chapters and ch["id"] not in chapters):
            continue
        tid = next((n[1] for n in ch["nodes"] if n[0] == "tournament"), None)
        tr = story.TOURNAMENTS.get(tid)
        if tr is None:
            continue
        if tr["format"] == "single":
            sp = story.TEAMS[tr["final"]]
            out.append(("P treino %s" % sp["name"], "ptrain", tr["final"], sp["ovr"], ch["F_start"]))
            continue
        tov = max(cm.TRAIN_MIN_OVR, int(round(ch["F_start"])) - int(ch.get("train_delta", cm.TRAIN_DELTA)))
        out.append(("%s treino" % ch["id"], "train", None, tov, ch["F_start"]))
        stages = cm.stages_of(tr)
        for i, st in enumerate(stages):
            t = cm.stage_team(tr, st)
            frac = i / max(1, len(stages) - 1)
            F = ch["F_start"] + (ch["F_end"] - ch["F_start"]) * frac
            kind = "boss" if cm.is_boss_stage(tr, st) else ("sf" if st == "SF" else "reg")
            out.append(("%s %s %s" % (ch["id"], st, story.TEAMS[t]["name"][:16]), kind, t,
                        story.TEAMS[t]["ovr"], F))
    return out


def measure(pool, F, kind, tid, ovr, n, with_skills=False, arena=None):
    """(F real do garage, V, E, D) do motor: usuario mandante, 10 variantes de adversario. arena: modificador
    da Torre do Po (Onda D) ou None."""
    g = build_garage_for(F, with_skills)
    home = g.match_cfg()
    if kind == "train":
        spec = lambda k: rl.opponent_team(rl.TEAM_NAMES[k % len(rl.TEAM_NAMES)],  # noqa: E731
                                          rl.TEAM_COLORS[k % len(rl.TEAM_COLORS)], ovr, 31 + k)
    else:
        spec = lambda k: opp_team(tid, ovr, 777 + k)  # noqa: E731
    aways = [rl.match_cfg(spec(k)) for k in range(10)]
    res = pool.map(one, [(home, aways[s % 10], s, arena) for s in range(n)], chunksize=4)
    w = sum(x > y for x, y in res)
    l = sum(x < y for x, y in res)
    return g.rating(), w, n - w - l, l


def main_table(a):
    cells = table_cells(a.chapters.split(",") if a.chapters else None)
    print("sim_bias(O) = clamp(%.2f + %.2f*(O-%d), %.2f, %.2f)  n=%d" % (
        cm.SIM_BIAS0, cm.SIM_BIAS_SLOPE, cm.SIM_O_REF, cm.SIM_BIAS_MIN, cm.SIM_BIAS_MAX, a.n))
    print("\n%-30s %-5s %5s %4s | %-13s %6s | %-7s %5s | %s" % (
        "checkpoint", "tipo", "F", "O", "motor V/E/D", "V+E/2", "SIM(O)", "viés", "Pois(F-2) antigo"))
    rows = []
    with Pool(a.procs) as pool:
        for name, kind, tid, ovr, F in cells:
            Fr, w, d, l = measure(pool, F, kind, tid, ovr, a.n, a.skills)
            eng = 100.0 * (w + d / 2.0) / a.n
            pw, pd, _ = poisson_wdl(Fr - cm.sim_bias(ovr, Fr), ovr)
            ow, od, _ = poisson_wdl(Fr - 2.0, ovr)
            sim = points(pw, pd)
            rows.append({"name": name, "kind": kind, "F": Fr, "O": ovr, "eng": eng, "sim": sim,
                         "old": points(ow, od)})
            print("%-30s %-5s %5.1f %4s | %3d/%3d/%3d   %6.1f | %6.1f  %+5.1f | %6.1f" % (
                name, kind, Fr, ovr, w, d, l, eng, sim, sim - eng, points(ow, od)), flush=True)
    err = [abs(r["sim"] - r["eng"]) for r in rows]
    print("\n|SIM - motor|: media %.1f, max %.1f (alvo <= 5 por celula, ruido do motor +-%.1f)" % (
        sum(err) / len(err), max(err), 100 * 0.5 / math.sqrt(a.n) * 1.6))
    tg = {"train": (60, 75), "reg": (58, 66), "sf": (52, 58), "boss": (45, 52)}
    for k, (lo, hi) in tg.items():
        v = [r["eng"] for r in rows if r["kind"] == k]
        if v:
            print("%-6s motor: media %.1f  min %.1f  max %.1f   (alvo %d-%d)" % (
                k, sum(v) / len(v), min(v), max(v), lo, hi))
    if a.json:
        import json
        json.dump(rows, open(a.json, "w"), indent=1)


def main_grid(a):
    """Grade F x O (O em 36..64 passo 4, F em 44..65 passo 3), com e sem 'perfect': base da regressao
    de campaign.sim_bias (--json grava as celulas)."""
    import json
    Fs = [44, 47, 50, 53, 56, 59, 62, 65]
    Os = [36, 40, 44, 48, 52, 56, 60, 64]
    rows = []
    with Pool(a.procs) as pool:
        for perfect, tid in ((False, "gremio"), (True, "impecaveis")):
            for F in Fs:
                for O in Os:
                    if not (-4 <= F - O <= 14):
                        continue
                    Fr, w, d, l = measure(pool, F, "boss", tid, O, a.n)
                    p = 100.0 * (w + d / 2.0) / a.n
                    rows.append({"F": Fr, "O": O, "perfect": perfect, "pts": p, "n": a.n})
                    print(perfect, round(Fr, 1), O, round(p, 1), flush=True)
    if a.json:
        json.dump(rows, open(a.json, "w"))


def post_cells():
    """Onda D: (rotulo, F, O, arena). NG+: os ovr distintos que a Turne Lendaria gera (cap. 1/5 deslocados e o
    teto 90 que vale do cap. 6 em diante na volta I e antes nas II/III) com a Forca do fim do Ato 3 (~94) e a
    "potencial" da spec (~88). Torre: andares com e sem modificador, F ~94."""
    out = []
    for F in (88.0, 94.0):
        for O in (60, 70, 78, 85, 90):
            out.append(("NG+ F%.0f O%d" % (F, O), F, O, None))
    for f in (10, 15, 20, 25, 30, 35, 39, 40):
        out.append(("Torre %d %s" % (f, cm.tower_mod(f) or "-"), 94.0, cm.tower_ovr(f), cm.tower_mod(f)))
    for f in (30, 40):
        out.append(("Torre %d sem mod" % f, 94.0, cm.tower_ovr(f), None))
    return out


def main_post(a):
    """--post: NG+ e Torre do Po no motor (garage com skills, adversario generico) x SIMULAR (sim_bias e o
    alivio POST_SIM_RELIEF menos o desconto ARENA_SIM_DF). Imprime V/E/D e V+E/2 (= chance de passar uma partida de mata-mata, V + E x
    penaltis ~50%, que e o proprio V+E/2)."""
    print("%-28s %5s %3s | %-13s %6s | %6s %5s" % ("celula", "F", "O", "motor V/E/D", "V+E/2", "SIM", "dif"))
    with Pool(a.procs) as pool:
        for name, F, O, arena in post_cells():
            Fr, w, d, l = measure(pool, F, "train", None, O, a.n, True, arena)
            eng = 100.0 * (w + d / 2.0) / a.n
            pw, pd, _ = poisson_wdl(Fr - cm.sim_bias(O, Fr) + cm.POST_SIM_RELIEF - cm.ARENA_SIM_DF.get(arena, 0.0),
                                    O)
            sim = points(pw, pd)
            print("%-28s %5.1f %3d | %3d/%3d/%3d   %6.1f | %6.1f %+5.1f" % (
                name, Fr, O, w, d, l, eng, sim, sim - eng), flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--procs", type=int, default=4)
    ap.add_argument("--chapters", default="", help="ex.: 1,3 (padrao: todos os jogaveis)")
    ap.add_argument("--json", default="", help="grava as linhas em JSON")
    ap.add_argument("--grid", action="store_true", help="grade F x O (regressao do vies)")
    ap.add_argument("--skills", action="store_true", help="garage com mod_on + SKILL_KIT (B9)")
    ap.add_argument("--post", action="store_true", help="Onda D: NG+ e Torre do Po (use --n 100)")
    a = ap.parse_args()
    if a.post:
        main_post(a)
    elif a.grid:
        main_grid(a)
    else:
        main_table(a)


if __name__ == "__main__":
    main()
