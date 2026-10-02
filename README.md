# SoccerPy

Futebol arcade 5x5 feito 100% em Python (pygame), rodando no navegador via
[pygbag](https://pygame-web.github.io/) (Python -> WebAssembly).

## Modos
1. **Um jogador** contra a CPU (2 min)
2. **Dois jogadores** no mesmo teclado
3. **Carreira** (estilo Elifoot): você é o técnico. 24 clubes fictícios em
   3 divisões de 8 times (ida e volta, 14 rodadas). Elenco de 15-20 jogadores
   com overall/idade/valor, escalação dos 5 titulares (GOL, DEF, 2 MEI, ATA),
   **mercado de transferências** (jogadores de outros clubes e sem clube,
   renovado a cada rodada), vender jogadores, finanças (bilheteria em casa,
   salários, premiação), **promoção/rebaixamento** (sobem/descem 2), evolução e
   aposentadoria dos jogadores entre temporadas. Suas partidas são **jogadas
   automaticamente no campo** (você assiste; velocidade 1x/2x/4x/MAX nas teclas
   1-4); as dos outros clubes são simuladas. O progresso é salvo sozinho
   (`localStorage` no navegador; `~/.soccerpy_career.json` no desktop) e há
   "Continuar carreira" no menu.
4. **Continuar carreira** (aparece quando há save)

## Controles (modos 1 e 2)
| Ação | Modo 1 jogador | J1 | J2 |
|---|---|---|---|
| Mover | WASD / setas | WASD | setas |
| Chutar (segure = mais forte) | Espaço / Enter | Espaço | Enter |
| Passar | Shift / X / Z | Shift esq. | Shift dir. |
| Pausa / menu | P / Esc | | |

Partidas de 2 minutos. O jogador controlado troca sozinho (o mais perto da bola).

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

## Notas
- O pygbag exige Python >= 3.9 e só detecta dependências lendo `main.py`
  (por isso o `import pygame` explícito lá).
- Testando em `localhost`, use o servidor do `pygbag .` (porta 8000); um
  `http.server` comum não serve o runtime/wheel do pygame.
- Arquivos: `soccer.py` (partida/menu), `career.py` (liga, mercado, finanças, save),
  `career_ui.py` (telas da carreira).
- Na primeira vez o navegador pede um clique na página para liberar o jogo.
