# SoccerRobo (Copa Aspirador)

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![pygame](https://img.shields.io/badge/pygame-2.6-2E8B57)
![WebAssembly](https://img.shields.io/badge/roda%20no%20navegador-pygbag%20%2F%20WebAssembly-654FF0?logo=webassembly&logoColor=white)
![Status](https://img.shields.io/badge/status-em%20desenvolvimento-orange)
![Last commit](https://img.shields.io/github/last-commit/brunokobi/soccerrobo)
![Repo size](https://img.shields.io/github/repo-size/brunokobi/soccerrobo)

Futebol arcade 5x5 feito **100% em Python** (pygame), que roda no navegador via
[pygbag](https://pygame-web.github.io/) (Python -> WebAssembly). O projeto está
virando um **futebol de robôs aspiradores** com campanha em estilo RPG
(escola -> mundial), laboratório de upgrades e partidas automáticas decididas
pelas habilidades dos robôs.

## Visual
Tema tecnológico/neon: arena com grade e linhas holográficas, robôs-disco com
anel de LED e barra de bateria, bola com brilho, rastro e faíscas, e HUD e menu
novos.

## Modos
No menu (teclas 1-5): `1 - AMISTOSO`, `2 - AMISTOSO`, `3 - NOVA CARREIRA`, `4 - CONTINUAR CARREIRA` e `5 - MODO ROBÔS`.

1. **Amistoso: um jogador** contra a CPU (2 min)
2. **Amistoso: dois jogadores** no mesmo teclado
3. **Nova carreira de clubes** (estilo Elifoot): você é o técnico. 24 clubes fictícios
   em 3 divisões de 8 times (ida e volta, 14 rodadas). Elenco de 15-20 jogadores
   com overall/idade/valor, escalação dos 5 titulares (GOL, DEF, 2 MEI, ATA),
   **mercado de transferências**, vender jogadores, finanças (bilheteria,
   salários, premiação), **promoção/rebaixamento** (sobem/descem 2) e evolução
   dos jogadores entre temporadas. Suas partidas são **jogadas automaticamente
   no campo** (você assiste; velocidade 1x/2x/4x/MAX nas teclas 1-4); as dos
   outros clubes são simuladas. O progresso é salvo sozinho (`localStorage` no
   navegador; `~/.soccerpy_career.json` no desktop).
4. **Continuar carreira** (aparece quando há save)
5. **Modo Robôs**: você monta uma **equipe de robôs persistente** e disputa ligas.
   - **Equipe:** 5 titulares (GOL, DEF, 2 MEI, ATA) + reservas, até 8 robôs. Cada robô
     tem chassis, nome, cor, XP e nível (até 10).
   - **Chassis:** Disco (inicial), Tanque, Velocista, Goleiro, Orbital e Titã. Os quatro
     últimos são desbloqueados ao concluir ligas (Tanque, Velocista, Goleiro e,
     no último tier, Orbital e Titã).
   - **Peças:** 7 slots por robô (motor, bateria, para-choque, chutador, sucção, sensor,
     chip), em 4 raridades (Comum, Rara, Épica, Lendária). Cada peça pode ser
     melhorada de 0 a 5 com sucata. Os modelos "agressivos" (Turbina, Blindado,
     Canhão de Plasma etc.) dão mais bônus, mas gastam bateria.
   - **Overclock:** NORMAL, TURBO ou OVERDRIVE trocam desempenho por bateria.
   - **Progressão:** os robôs ganham XP nas partidas (os reservas ganham uma parte)
     e sobem de nível; as partidas rendem **sucata** e, às vezes, uma peça.
   - **Loja:** compra peças e modelos, vende as que sobram.
   - **Liga:** 6 times, ida e volta (10 rodadas), em 4 tiers de dificuldade. Em cada
     rodada você escolhe **assistir** (partida jogada no motor) ou **simular**
     (resultado estatístico). Terminar em 3º ou melhor libera o próximo tier, e a
     premiação em sucata depende da colocação.
   - **Save próprio**, separado da carreira de clubes: `localStorage`
     (`soccerpy_robots_v1`) no navegador; `~/.soccerpy_robots.json` no desktop. Um save
     inválido só é sobrescrito pelo NOVO JOGO após confirmação explícita; a cópia fica em `.bad`.

### Controles (modos 1 e 2)
| Ação | Modo 1 jogador | J1 | J2 |
|---|---|---|---|
| Mover | WASD / setas | WASD | setas |
| Chutar (segure = mais forte) | Espaço / Enter | Espaço | Enter |
| Passar | Shift / X / Z | Shift esq. | Shift dir. |
| Pausar | P | | |
| Voltar ao menu | Esc | | |

O jogador controlado troca sozinho (o mais perto da bola).

## Roadmap
| Fase | Conteúdo | Situação |
|---|---|---|
| 1 | Robôs com chassis e 8 atributos, bateria, arena tecnológica (neon) | pronta |
| 2 | Garagem e laboratório: peças, upgrades, XP, evolução, loja e liga (Modo Robôs) | pronta e jogável |
| 3 | **Campanha**: história do torneio de robôs (escola -> mundial), rival, capítulos | planejada |
| 4 | Editor de firmware (regras da IA em blocos) e acabamento | planejada |

**Robôs (Fase 1):** 6 chassis (Disco, Tanque, Velocista, Goleiro, Orbital, Titã) e 8 atributos
(velocidade, aceleração, chute, controle/sucção, defesa, visão, bateria, QI) que
alteram de verdade o comportamento na partida; a bateria gasta ao correr e
chutar e recarrega parado. Atributos e bateria já vêm calibrados e ligados por
padrão (`game/robots.py`; o Modo Robôs usa o ajuste próprio `TUNING_ROBOTS`); o modo legado (atributos planos, sem bateria) existe
só para o teste golden.

## Rodar
```bash
uv venv --python 3.12 .venv && . .venv/bin/activate && uv pip install pygame pygbag

# desktop (rápido, para desenvolver)
cd game && python main.py

# navegador (servidor do pygbag em http://localhost:8000)
cd game && pygbag .

# gerar build estático para publicar (itch.io, GitHub Pages...): game/build/web/
cd game && pygbag --build .
```

## Testes
```bash
export SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
.venv/bin/python tests/test_robots.py                  # modelo de robôs
.venv/bin/python tests/test_robot_mode.py              # motor no modo robôs (atributos diretos, tuning por robô)
.venv/bin/python tests/test_garage.py                  # garagem, peças, progressão e liga
.venv/bin/python tests/test_robot_save.py              # save do Modo Robôs (store, validação, save inválido)
.venv/bin/python tests/test_robots_ui.py               # telas do Modo Robôs
.venv/bin/python tests/test_visual.py                  # cores dos clubes, efeitos, pausa, save
.venv/bin/python tests/sim_harness.py golden --check   # regressão: 80 placares do modo legado
.venv/bin/python tests/sim_harness.py golden-new --check  # regressão: 80 placares do balanço novo
```
Os testes de garagem, save e UI não tocam nos saves reais (`~/.soccerpy_*.json`).
Os de partida são lentos (minutos); rode quando mexer em atributos, peças ou balanço:
```bash
.venv/bin/python tests/test_mechanics.py               # efeito dos atributos na partida
.venv/bin/python tests/test_robot_balance.py [-n 70] [--procs 4]  # balanço da equipe (peças/raridades) contra o time base
.venv/bin/python tests/calib_robots.py [--n 100] [--diffs ...] [--fit] [--procs 4]  # calibra a simulação estatística da liga contra o motor
```
Utilitários do harness (`tests/sim_harness.py`): `golden`/`golden-new` com
`--write` (regrava a baseline) ou `--check`, `run <ovrA> <ovrB> <n> [seed0] [legacy]`
(simula partidas), `draw` (tempo de desenho por quadro) e `shot <arquivo.png>`
(captura a tela).

## Estrutura
- `game/main.py`: entrada do pygbag (precisa do `import pygame` explícito)
- `game/soccer.py`: partida (física, IA), visual neon, menu e HUD
- `game/robots.py`: chassis, atributos, fatores usados pelo motor e ajustes (`TUNING`, `TUNING_ROBOTS`)
- `game/garage.py`: Modo Robôs: equipe, robôs, XP/nível, overclock, loja, recompensas e save
- `game/parts.py`: catálogo de peças (slots, modelos, raridades, upgrades)
- `game/robot_league.py`: liga de 6 times (calendário, tabela, simulação estatística, premiação)
- `game/store.py`: armazenamento de texto (`localStorage` no navegador, arquivo em `~` no desktop)
- `game/robots_ui.py`: telas do Modo Robôs (hub, garagem, banco, loja, liga)
- `game/career.py` / `game/career_ui.py`: carreira de clubes (liga, mercado, finanças, save) e suas telas
- `tests/`: testes, harness de simulação e baselines (`baseline_golden*.json`) (ficam fora de `game/` para não entrar no pacote do pygbag)

## Notas
- O pygbag exige Python >= 3.9 e só detecta dependências lendo `main.py`.
- Testando em `localhost`, use o servidor do `pygbag .` (porta 8000); um
  `http.server` comum não serve o runtime/wheel do pygame.
- Na primeira vez o navegador pede um clique na página para liberar o jogo.
