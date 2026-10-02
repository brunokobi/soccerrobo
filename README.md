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

## Modos (Amistoso)
1. **Um jogador** contra a CPU (2 min)
2. **Dois jogadores** no mesmo teclado
3. **Carreira de clubes** (estilo Elifoot): você é o técnico. 24 clubes fictícios
   em 3 divisões de 8 times (ida e volta, 14 rodadas). Elenco de 15-20 jogadores
   com overall/idade/valor, escalação dos 5 titulares (GOL, DEF, 2 MEI, ATA),
   **mercado de transferências**, vender jogadores, finanças (bilheteria,
   salários, premiação), **promoção/rebaixamento** (sobem/descem 2) e evolução
   dos jogadores entre temporadas. Suas partidas são **jogadas automaticamente
   no campo** (você assiste; velocidade 1x/2x/4x/MAX nas teclas 1-4); as dos
   outros clubes são simuladas. O progresso é salvo sozinho (`localStorage` no
   navegador; `~/.soccerpy_career.json` no desktop).
4. **Continuar carreira** (aparece quando há save)

### Controles (modos 1 e 2)
| Ação | Modo 1 jogador | J1 | J2 |
|---|---|---|---|
| Mover | WASD / setas | WASD | setas |
| Chutar (segure = mais forte) | Espaço / Enter | Espaço | Enter |
| Passar | Shift / X / Z | Shift esq. | Shift dir. |
| Pausa / menu | P / Esc | | |

O jogador controlado troca sozinho (o mais perto da bola).

## Roadmap
| Fase | Conteúdo | Situação |
|---|---|---|
| 1 | Robôs com chassis e 8 atributos, bateria, arena tecnológica (neon) | em andamento |
| 2 | Garagem e laboratório: peças, upgrades, XP, evolução, mercado de peças | planejada |
| 3 | **Campanha**: história do torneio de robôs (escola -> mundial), rival, capítulos | planejada |
| 4 | Editor de firmware (regras da IA em blocos) e acabamento | planejada |

**Robôs (Fase 1):** 4 chassis (Disco, Tanque, Velocista, Goleiro) e 8 atributos
(velocidade, aceleração, chute, controle/sucção, defesa, visão, bateria, QI) que
alteram de verdade o comportamento na partida; a bateria gasta ao correr e
chutar e recarrega parado.

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
.venv/bin/python tests/sim_harness.py golden --check   # regressão: 80 placares do modo legado
.venv/bin/python tests/test_mechanics.py               # efeito dos atributos na partida
```

## Estrutura
- `game/main.py`: entrada do pygbag (precisa do `import pygame` explícito)
- `game/soccer.py`: partida (física, IA), menu e HUD
- `game/robots.py`: chassis, atributos e fatores usados pelo motor
- `game/career.py` / `game/career_ui.py`: carreira de clubes (liga, mercado, finanças, save) e suas telas
- `tests/`: testes e harness de simulação (ficam fora de `game/` para não entrar no pacote do pygbag)

## Notas
- O pygbag exige Python >= 3.9 e só detecta dependências lendo `main.py`.
- Testando em `localhost`, use o servidor do `pygbag .` (porta 8000); um
  `http.server` comum não serve o runtime/wheel do pygame.
- Na primeira vez o navegador pede um clique na página para liberar o jogo.
