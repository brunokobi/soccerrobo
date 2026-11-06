# Fase 6 - Som

Efeitos sonoros e música **100% sintetizados por código** (stdlib: `math`, `array`, `random.Random`
privado). Não existe nenhum arquivo de áudio no repositório nem no pacote do pygbag. Ligado por
padrão, volume médio.

## Arquivos
| Arquivo | Papel |
|---|---|
| `game/sfx.py` | receitas dos efeitos (osciladores, ruído filtrado, envelopes), conversão para o formato do mixer (`fit`), runtime: `init`, `tick`, `play`, `jingle`, `result`, mudo/volumes |
| `game/music.py` | trilhas escritas como texto (16 passos por compasso) e renderizadas compasso a compasso |
| `game/prefs.py` | `sfx_vol`, `music_vol` ("0".."3", padrão "2") e `mute` ("0"/"1", padrão "0") |
| `tests/test_sfx.py` | buffers, determinismo, formato, throttle, mudo, no-op sem mixer, integração com o `Game` |

## Catálogo de efeitos (`sfx.SFX`)
| id | Som | Onde toca |
|---|---|---|
| `kick` / `touch` | "tum" grave + estalo / "tic" curto | `Game.kick` (potência >= 600 / abaixo) |
| `steal` / `dribble` | "shk" descendo / "fwip" subindo | desarme certo (`ball_interactions`) / `on_evade` (Drible) |
| `whistle` / `whistle_end` | apito com trinado / curto-curto-longo | `crowd_event("kickoff")` / `("end")` |
| `goal` | explosão da torcida + buzina (acorde de dente de serra) | `crowd_event("goal")` |
| `ooh` | coro "uuuh" descendo | `crowd_event("chance")` |
| `save` | luva + "olé" curto | `crowd_event("save")` |
| `post` | CLANG (parciais inarmônicas) | `crowd_event("post")` |
| `skill` / `dash` | BUZZ / ZOOM | `sk_start` (fx `dash`/`wheel` = ZOOM) |
| `click` / `back` / `toggle` / `blip` | clique / Esc / opção alternada / avanço de diálogo (discreto) | menu, botões das telas, T/C/S/M, `dlg_advance` |
| `reward` / `buy` / `upgrade` / `error` | arpejo / moeda / power-up / recusa | subiu de nível ou recompensa no resultado / compras / upgrade / ação recusada |
| `draw` | "plim-plom" | resultado empatado |
| `ole` | palmas ritmadas | catálogo (reserva para festas) |

`crowd_event` toca o som **antes** de repassar à torcida, então há som mesmo com a torcida desligada
(os antigos `if self.crowd is not None` em volta dos hooks saíram; o `crowd_event` checa sozinho).
Em **MAX** (`speed_idx == 3`) nenhum som de lance toca.

## Música (`music.TRACKS`)
| Trilha | Uso | Tempo / tamanho |
|---|---|---|
| `menu` | menu, carreira, Modo Robôs, campanha (loop) | 128 bpm, 8 compassos, ~15 s |
| `match` | partida, inclusive pausa e fim (loop, ganho 0,55 sob os efeitos) | 150 bpm, 8 compassos, ~12,8 s |
| `win` / `lose` | jingle na tela de resultado (do ponto de vista do jogador) | ~3,4 s / ~5 s |

Lead em pulso (duty 25/50%), baixo em triângulo, bateria com bumbo (seno descendo), caixa, chimbal e
prato (ruído). A trilha vem de `Game.music_track()`; `sfx.tick` troca com fade de 400 ms no canal
reservado 0 (`Sound` em loop, `loops=-1`; `pygame.mixer.music` não é usado). O jingle toca no mesmo
canal e, ao terminar, a trilha pedida volta sozinha. Resultado: Modo Robôs `finish_round`, campanha
`finish_result` (pênaltis decidem empate), carreira `make_round_info`, amistoso no fim da partida
(modo 1 = visão do humano).

## Síntese e formato
- Tudo nasce em **22050 Hz mono 16-bit** e é convertido uma vez por `sfx.fit` para
  `pygame.mixer.get_init()`: taxa múltipla inteira (44100) por atribuição em fatias, outra taxa por
  vizinho mais próximo; mono -> estéreo por fatias; `int16` ou `float32`.
- Efeitos normalizados para 40-85% do fundo de escala (sem saturar); a música não satura por
  construção (soma dos picos lead + baixo + maior golpe < 32767).
- Música barata no WASM: tabelas de vários períodos por nota repetidas em C (`array * n`), envelope
  inteiro e mixagem em list comprehension, um compasso por pedaço.
- Determinístico: cada efeito usa `random.Random(semente)` próprio; o `random` global e o RNG do motor
  nunca são tocados (goldens 80/80; `test_simulation_identical_with_sound_on_off`).

## Runtime
- `main()`: `sfx.pre_init()` (pede 22050 Hz estéreo; buffer 512, 2048 no navegador) -> `pygame.init()`
  -> `Game(...)` -> `sfx.init()` (depois do `Game`, para o `new_match` do construtor não apitar) e, por
  quadro, `sfx.tick(game.music_track())`.
- A geração roda **aos poucos** dentro de `tick` (orçamento de 5 ms por quadro; cada pedaço é um
  efeito ou parte de um compasso). Ordem: sons de menu, trilha do menu, efeitos, trilha da partida,
  jingles. Um `play` de algo ainda não gerado gera na hora.
- Limites: 16 canais (1 reservado à música), intervalo mínimo por id (ex.: `kick` 60 ms, `goal`
  1,5 s, `ooh` 1,2 s) e vozes simultâneas por id (1-2). Custo por quadro: uma comparação de string e,
  com jingle, um `get_busy`.
- **Falha = silêncio**: qualquer erro do mixer (sem dispositivo, formato de 8 bits etc.) deixa
  `sfx.S.ok = False` e tudo vira no-op. Antes de `init` (testes, goldens, harness) também é no-op.

## Preferências e teclas
| Tecla | Onde | Efeito |
|---|---|---|
| **M** | qualquer tela (menos com campo de nome em edição) | mudo geral liga/desliga |
| **S** | menu e pausa | volume dos efeitos: DESL. -> BAIXO -> MÉDIO -> ALTO |
| **N** | menu e pausa | volume da música (idem) |

Ganhos: 0 / 0,35 / 0,65 / 1,0. Os rótulos ficam no rodapé do menu e na pausa (cache de `text_img`,
zero Surface por quadro).

## Navegador (pygbag 0.9.3 / pygame-ce 2.5.7)
- O template já espera o clique ("Pronto! Clique ou toque para jogar") antes de rodar o `main.py`,
  então o AudioContext existe e está `running` quando o mixer abre.
- Verificado com Playwright no servidor do pygbag: mixer `(44100, -16, 2)`, `Sound(buffer=...)`
  funciona, console sem exceção, `AudioContext.state == "running"` (44100 Hz) depois do clique, e a
  saída do ScriptProcessor do SDL com sinal (pico ~0,40 no menu; 0 com **M**; ~0,41 na partida).
- Geração no WASM: ~1,1-1,2 s de CPU espalhados em ~1,7-1,9 s de relógio (desktop: ~0,4 s), com o menu
  respondendo durante a geração. Os pedaços maiores (rugido do gol, coro do "uuuh") custam ~40-50 ms
  no desktop e algumas centenas de ms no WASM, uma única vez, ainda no menu.
- O `sfx` escreve `[som] ...` no console do JS (início e fim da geração) para diagnóstico.
