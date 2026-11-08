# Fase 6 - Som

Efeitos sonoros e música sintetizados por código (stdlib: `math`, `array`, `random.Random` privado)
**somados a gravações** em `game/audio/` (OGG; ver "Reações da torcida" e "Arquivos de áudio" no fim).
A síntese é o plano B de cada som gravado (arquivo faltando ou que não abre). Ligado por padrão,
volume médio.

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
| `reward` / `buy` / `upgrade` / `error` | arpejo / moeda / power-up / recusa | recompensa / compras / upgrade / ação recusada |
| `draw` | "plim-plom" | resultado empatado |
| `ole` | palmas ritmadas | catálogo (reserva para festas) |

`crowd_event` toca o som **antes** de repassar à torcida, então há som mesmo com a torcida desligada
(os antigos `if self.crowd is not None` em volta dos hooks saíram; o `crowd_event` checa sozinho).
Em **MAX** (`speed_idx == 3`) nenhum som de lance toca.

## Música (`music.TRACKS`)
| Trilha | Uso | Tempo / tamanho |
|---|---|---|
| `menu` | menu, carreira, Modo Robôs, campanha (loop) | 128 bpm, 8 compassos, ~15 s |
| `match` | partida, inclusive pausa e fim (loop, ganho 0,55 sob os efeitos); só toca se `partida_musica.ogg` faltar | 150 bpm, 8 compassos, ~12,8 s |
| `win` / `lose` | jingles sintetizados (não tocam mais no resultado: o card usa a caixa registradora) | ~3,4 s / ~5 s |

Lead em pulso (duty 25/50%), baixo em triângulo, bateria com bumbo (seno descendo), caixa, chimbal e
prato (ruído). A trilha vem de `Game.music_track()`; `sfx.tick` troca com fade de 400 ms no canal
reservado 0 (`Sound` em loop, `loops=-1`; `pygame.mixer.music` não é usado). O jingle toca no mesmo
canal e, ao terminar, a trilha pedida volta sozinha. Resultado: Modo Robôs `finish_round`, campanha
`finish_result` (pênaltis decidem empate), carreira `make_round_info`, amistoso no fim da partida
(modo 1 = visão do humano).

## Música e torcida na partida (juntas)
Toda partida (amistoso, carreira, Modo Robôs, campanha; inclusive pausa e fim) toca **duas camadas** de
fundo ao mesmo tempo, por baixo dos efeitos, dos gritos e das reações da torcida:

| Camada | Arquivo | Como toca | Volume |
|---|---|---|---|
| música | `partida_musica.ogg` ("Into the Iron Horizon", 179 s; mono 22,05 kHz q2, -20 LUFS, 857 KB) | `STREAMS["match"]` em `pygame.mixer.music` (o único stream), `play(loops=-1)` (faixa única: loop no próprio stream, sem recarregar) | `music_vol` x `MATCH_MUSIC_GAIN` 0,5 (tecla **N**) |
| torcida de fundo | `torcida_loop.ogg` (24 s, mono 44,1 kHz q2, -20 LUFS, 172 KB) | `Sound` em loop (`loops=-1`) no canal reservado 2 (`sfx.bed_tick`), fade de 600 ms ao entrar/sair | `sfx_vol` x `BED_VOL` 0,85 (tecla **S**) |

- Antes a torcida era a trilha `match` do stream (3 gravações de 42-156 s alternando), e o stream é um só:
  com a música nele, a torcida virou um `Sound` curto em loop. `tools/torcida_loop.sh` mistura os trechos
  mais estáveis das 3 gravações (`torcida` e `torcida_estadio` a 0,75, o canto `torcida_boca` a 0,30),
  faz o loop com **crossfade de 3 s** (potência constante) do fim sobre o começo e aplica um **ganho
  estático** para -20 LUFS (o `loudnorm` dinâmico mudaria o ganho ao longo do arquivo e a emenda
  apareceria). O loop tem 517 x 2048 quadros: o libvorbis do ffmpeg completa o último bloco com
  silêncio, e com 24 s exatos o arquivo decodificava com 32 quadros a mais (clique na emenda). Medido:
  salto na emenda do tamanho da mediana do sinal; RMS das pontas -20,6 / -19,0 dB. As 3 gravações
  originais saíram de `game/audio/` (estão no histórico do repositório, commit 3d6d029) e o script as lê
  de qualquer pasta.
- **Volumes (padrão, MÉDIO = 0,65):** música 0,65 x 0,5 = **0,33**; torcida 0,65 x 0,85 = **0,55** (o
  mesmo nível da antiga trilha `match`); efeitos/reações 0,6-1,0 x 0,65 sobre arquivos a -16 LUFS. A
  música fica ~4-5 dB abaixo da torcida e bem abaixo dos efeitos. **N** desliga só a música, **S**
  desliga efeitos e a torcida (a música segue), **M** corta tudo. Fora da partida (`track != "match"`)
  a torcida para com fade; a demo do menu continua só com a música do menu.
- **Canais:** 17 (0 = música sintetizada/jingle, 1 = motor dos robôs, 2 = torcida; 14 vozes de efeito,
  as mesmas de antes).
- **RAM (áudio decodificado, mixer 44,1 kHz estéreo 16-bit = ~10,6 MB/min):** a torcida em loop ocupa
  **4,2 MB**; o total de `Sound` na memória foi de ~49,9 MB para **~54,1 MB** (efeitos em arquivo 39,6 MB,
  motor 7,7 MB, torcida 4,2 MB, síntese 2,5 MB). A música não é decodificada inteira (stream).
- Sem `torcida_loop.ogg`: partida só com a música; sem `partida_musica.ogg`: a trilha sintetizada `match`.
- **Navegador (verificado com Playwright no servidor do pygbag, AnalyserNode na saída do SDL):**
  AudioContext `running` a 44100 Hz; console `[som] partida: torcida de fundo (canal 2) + musica match`
  ao começar o amistoso; RMS na pausa da partida com as duas = 0,064; só a torcida (N = DESL.) = 0,060;
  só a música (S = DESL.) = 0,042; com **M** = 0. Ou seja, as duas tocam juntas e cada uma responde à
  sua tecla.

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
- `main()`: `sfx.pre_init()` (pede `MIXER_RATE` = 44100 Hz estéreo; buffer 512, 2048 no navegador) -> `pygame.init()`
  -> `Game(...)` -> `sfx.init()` (depois do `Game`, para o `new_match` do construtor não apitar) e, por
  quadro, `sfx.tick(game.music_track())`.
- A geração roda **aos poucos** dentro de `tick` (orçamento de 5 ms por quadro; cada pedaço é um
  efeito ou parte de um compasso). Ordem: sons de menu, trilha do menu, efeitos, trilha da partida,
  jingles. Um `play` de algo ainda não gerado gera na hora.
- Limites: 17 canais (3 reservados: música sintetizada/jingle, motor, torcida), intervalo mínimo por id (ex.: `kick` 60 ms, `goal`
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

## Reações da torcida (tabela única `sfx.FILE_SFX`)
Cada id de efeito gravado aponta para uma lista de variações: um arquivo de `game/audio/` ou uma
variação **derivada em runtime** dele, `("x.ogg", velocidade, início, fim[, máx_s])` — reamostra
(velocidade != 1 muda tom e andamento), recorta o trecho `[início, fim)` (frações da duração), limita a
`máx_s` (padrão `DERIVE_MAX_S` = 3 s) e suaviza as pontas (30 ms). As derivadas não viram arquivo (o
`game.apk` não cresce): o `_builder` gera em pedaços de `DERIVE_CHUNK` quadros (no navegador a geração
inteira levou ~0,35 s de CPU em ~3 s de relógio, ainda no menu). Para trocar um som, mexa só na
tabela.

**Sorteio:** "saco embaralhado" por id com RNG privado (`S.vrng`): cada volta toca todas as variações,
nunca a mesma duas vezes seguidas. **Vozes faladas** (`SPOKEN`: `inicio2` 60 s, `lamento3` 45 s,
`defesa3`, `trave3` e `derrota2` 35 s) só voltam depois do seu intervalo.

| Reação (id) | Quando | Variações |
|---|---|---|
| `goal` | gol do jogador (2P: qualquer gol) | 9: `gol`, `gol_grito`, `gol_e_gol`, `gol_olha_o_gol`, `gol_brasil`, `gol_we` + `gol_grito`@0,92, `gol_e_gol`@1,08, `gol`@0,94 |
| `goal_opp` | gol do adversário | 7: `gol_adv1..4`, `gol_adv_nao` ("não!", voz, 20 s) + `gol_adv1`@0,93, `gol_adv3`@1,07 |
| `end_voice` | apito final | `acabou` ("acabou!") |
| `cash` | card do resumo da partida (qualquer placar; `sfx.result`) | `caixa_registradora` |
| `lament` | gol sofrido: lamento da torcida da casa | 4: `lamento1`, `lamento2`, `lamento3` (voz) + `lamento1`@0,9 |
| `boo` | gol contra do nosso time; derrota | 3: `vaias`, `vaia2` + `vaias`@0,9 (1º terço) |
| `ooh` | chance (chute forte perto do gol) | 6: `uhhh_torcida`, `quase_uh`, `defesa3` ("ooo that's strong"), `derrota2` + derivadas |
| `near` / `near_opp` | defesa/trave: quase gol do jogador / contra o jogador | 6: `quase_uh`, `defesa1`, `defesa3`, `derrota2` + 2 derivadas / 3: `quase_nao` + @0,88 e @1,12 |
| `save` | defesa (soma à luva sintetizada) | 4: `defesa1`, `defesa3` (voz) + trecho de `palmas` + `defesa1`@0,92 |
| `post` | trave (soma ao CLANG) | 4: `trave_torcida`, `trave2`, `trave3` (voz) + `trave_torcida`@0,9 |
| `ole` | drible e defesa do jogador | 4: `ole` + 2 trechos de ~5 s do coro `ole2` (14 s) + `ole`@0,92 |
| `kickoff_voice` | 1º pontapé | 3: `comecou`, `inicio2` (voz), `inicio3` |
| `crowd_cheer` | 1º pontapé e gol do jogador | 3: `palmas3`, `palmas` + trecho de `palmas2` |
| `applause` / `crowd_chant` | fim sem derrota / cântico e ola | 4: `palmas`, `palmas2`, `palmas3` + derivada / 3 |
| `win_crowd` | vitória do jogador | 3: `vitoria1` + @0,94 e @1,06 |
| `lose_crowd` | derrota do jogador (com a vaia) | 3: `derrota1`, `derrota2` + `derrota2`@0,93 |

Em MAX nenhum som de lance toca. Gravações reais que ainda deixariam as reações mais variadas (hoje
completadas por derivadas): mais 2 tomadas de "olé" curto (2-3 s), 2 de "uuuh" de chance (1-2 s), 1-2
de "nãããão" (quase leva gol, 1 s), 1-2 de vaia curta (2-4 s) e 1-2 de festa de vitória (2-4 s).

**Mixer a 44,1 kHz:** `pre_init`/`init` pedem `MIXER_RATE` = 44100 (a mesma taxa do navegador). Com o
mixer a 22050 Hz o SDL_mixer do pygame 2.6.1 (desktop) devolvia `Sound` vazio (`get_length() == 0`)
para algumas gravações de 44,1 kHz (`vaias`, `gol`, `inicio3`, `palmas3`...), que então não tocavam.
`_load_file` também descarta Sound vazio (fica a síntese). A síntese continua em 22050 e o `fit`
converte (44100 = 2 x 22050).

## Arquivos de áudio: compactos e com o mesmo volume
Regra: todo áudio novo passa por `tools/normalizar_audio.sh <pasta_de_entrada> [game/audio]`
(ffmpeg + libvorbis, reprodutível):

| Tipo | Formato | Corte | Volume |
|---|---|---|---|
| efeitos e reações (o resto) | vorbis mono 44,1 kHz, q3 | silêncio do início (`silenceremove`, -50 dB) | `loudnorm` I=-16 LUFS, TP=-1,5 dBTP |
| músicas (stream: `menu1-3` (`menu1` = "Era do Metal", a primeira do menu), `copas`, `interno1/2`, `submenus`, `partida_musica`; e as fontes `torcida*` do loop) | vorbis mono 22,05 kHz, q2 | nenhum | I=-20 LUFS (fundo: não briga com os efeitos) |
| motor dos robôs (`robo_motor`, Sound em loop) | vorbis mono 44,1 kHz, q2 | nenhum | I=-20 LUFS |
| torcida de fundo (`torcida_loop`, Sound em loop; `tools/torcida_loop.sh`) | vorbis mono 44,1 kHz, q2 | trecho de ~27 s de cada gravação | ganho estático para -20 LUFS (loop sem emenda) |

Medido: fontes em `game/audio/` 14,4 MB -> 7,5 MB (48 arquivos, já com as 16 gravações novas);
`game.apk` 10.267.824 -> 7.169.990 bytes.

**Cópias `*-pygbag.ogg`:** o build do pygbag converte cada áudio com ffmpeg para `<nome>-pygbag.ogg`
ao lado do original e empacota a cópia no lugar dele; elas ficam fora do git (`.gitignore`). O pygbag só
reconverte quando a cópia NÃO existe, então quem troca um `.ogg` precisa apagar a cópia (o script já
apaga) ou o `game.apk` leva o som antigo.
