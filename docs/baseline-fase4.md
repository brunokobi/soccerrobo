# Baseline da Fase 4 (Onda 0, passo 0.1)

Medido em 02/11/2026 no commit `8a467a3` (antes de qualquer código da Fase 4), em desktop (WSL2, Linux 6.18),
Python 3.12.13, pygame 2.6.1 (SDL 2.28.4), `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy`, da raiz do repo.
É a referência para os limites da Onda A e B: desenho em partida no máximo +0,8 ms (meta de 1,5 ms com
torcida), `ms_step` estável e goldens 80/80 (ver `docs/roadmap.md`, seção 5).

## Desempenho

| Medição | Comando | Valor (3 execuções) | Referência |
|---|---|---|---|
| Desenho em partida (`draw_ms`) | `tests/sim_harness.py draw` | 0,584 / 0,561 / 0,566 ms (**~0,57 ms**) | spec: 0,69 ms |
| Desenho do menu (`menu_ms`) | `tests/sim_harness.py draw` | 0,642 / 0,639 / 0,653 ms (**~0,64 ms**) | spec: 0,76 ms |
| Passo do motor (`ms_step`) | `tests/sim_harness.py run 65 65 20` | **0,0326 ms/step** | plano: 0,037 ms |

`run 65 65 20` também deu `goals_per_game` 2,4 e V/D/E do time A `[8, 7, 5]`.
Os valores de referência da spec/plano (0,69 / 0,76 / 0,037) foram medidos antes; a máquina atual mede um
pouco abaixo. Compare sempre na mesma máquina e repita 3 vezes (a variação entre execuções é de ~±0,03 ms).

## Goldens

| Comando | Resultado |
|---|---|
| `tests/sim_harness.py golden --check` | `golden OK: 80/80 placares identicos` |
| `tests/sim_harness.py golden-new --check` | `golden-new OK: 80/80 placares identicos` |

## Calibragem da campanha (`tests/calib_campaign.py`)

Não foi rodada de novo (é pesada, ~12 min). Resumo da tabela final que está no cabeçalho de
`tests/calib_campaign.py` (n=300, seeds 0..299, medida em 03/10/2026; motor = V+E/2 % do jogador contra o
motor real; SIM(O) = `campaign.sim_bias`; dif = SIM - motor):

| Grupo de checkpoints | Meta (passo 16) | Motor (média, faixa) |
|---|---|---|
| Treinos | 60-75 | 64,2 (58-71) |
| Jogos regulares (G1-G3, QF) | 58-66 | 63,5 (56-71) |
| Semifinais | 52-58 | 55,9 (54-58) |
| Chefes (finais) | 45-52 | 47,9 (45-54) |
| Chefe final do Mundial (cap. 5, Hiperlimpos X-9) | 42-50 | 45,0 |

- Força do jogador (F) vai de 43,7 (treino do Prólogo) a 65,9 (final do cap. 5); ovr dos adversários (O)
  de 36 a 58.
- |SIM - motor|: média 2,5 pontos, máximo 6,0 (duas células acima de 5: 6,0 e 5,9, dentro do ruído de
  ±4,6 do motor com n=300).
- Viés do simulador: `bias = clamp(5 + 1,5*(O-40), -2, 8)`; o motor é ~linear:
  V+E/2 ≈ 34 + 1,8*F - 1,8*O (rmse ~4 pontos).
- Antes da recalibragem (story do passo 15) o motor dava: treino 51,7, regulares 48,2, SF 43,1, chefes
  37,3 (final do Mundial 29,7).

A Onda B (skills/itens) e a Onda C (campanha) devem comparar contra esta tabela (`calib_campaign.py`
e o futuro `calib_skills.py`).
