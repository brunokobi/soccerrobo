# Spec - Visual: desenhos mais detalhados e torcida realista

## 1. Estado atual (resumo técnico)
- Tela lógica 1100x700. `PITCH = Rect(60, 90, 980, 560)`; gols com profundidade 36 px (x 24..60 e 1040..1076, y 290..450). HUD: painel de 78 px no topo (alpha 215 -> 165). Rodapé: botões de velocidade em y 664..692 e dicas em y ~678.
- Arena: uma Surface única `pitch_surf` (gradiente, grade, linhas holográficas). `build_menu_bg` copia `pitch_surf`.
- Robôs: sprite 64x64 por `(chassis, led, gk, low)`, pré-renderizado e cacheado em `Game.sprites`; sem rotação; olho desenhado por frame na direção `p.face`; barra de bateria por frame. Sem público.
- FX: partículas em lista (teto 120) desenhadas com `pygame.draw`; RNG próprio `fx_rng`. `fx_ok()` falso em MAX.
- Retratos: `portraits.draw_character/draw_robot` desenham com `pygame.draw` direto por frame; cenários são Surfaces estáticas por `bg` (`get_background`, cache `_BG_CACHE`). Cenários `quadra`, `ginasio`, `arena`, `estadio`, `mundial` já têm `_bleachers` (arquibancada com cabeças de círculo).
- Medido: desenho em partida 0,69 ms/frame; menu 0,76 ms.

## 2. Torcida

### 2.1 Geometria
O campo ocupa quase toda a tela; só sobram faixas de margem:

| Zona | Retângulo | Uso |
|---|---|---|
| Fundo (lado da câmera) | x 0..1100, y 654..700 (46 px) | arquibancada frontal grande (3 fileiras, pessoas de 16 px) |
| Lateral esquerda | x 0..56, y 90..650 (exceto o bolsão do gol x 24..60, y 290..450 onde fica x 0..22) | arquibancada vertical, 3 colunas |
| Lateral direita | x 1044..1100, y 90..650 (idem) | idem |
| Fundo distante | x 0..1100, y 0..90 (sob o HUD) | arquibancada distante estática, pessoas de 10 px; o HUD (alpha 215/165) deixa 16-35% aparecer, efeito de profundidade sem custo |

**Visibilidade (correção pós-A8):** a UI da partida cobre o topo (placar, y 0..88) e quase toda a fileira frontal (rodapé: "P: pausa", telão, "Velocidade (1-4):" + botões; no amistoso, a linha de dicas). Os retângulos estão em `crowd.UI_HUD/UI_PAUSE/UI_TELAO/UI_SPEED/UI_HINT` (`crowd.ui_rects(assisted)`), conferidos contra o desenho real em `test_ui_rects_cover_the_drawn_ui`. A escolha de lugares (`_pick`) enche primeiro os lugares visíveis — as **laterais, que agora existem em todos os locais** (os pequenos com 2 colunas, `scols=2`) — e a frente fica só com o excedente. Estádio/superliga e mundial/coliseu apertam o passo das laterais (`spitch` 12 e 11 px) para caber mais gente visível. `test_crowd_visible_outside_the_ui_every_venue` desenha cada local e conta quem fica fora da UI (mínimo por local, crescente, e gente nos dois lados).

Placas de publicidade LED: faixa de 12 px colada ao campo, em baixo (y 652..664) e em cima (y 78..90). O rodapé de UI (botões de velocidade e dica) fica sobre uma tarja translúcida pré-renderizada (30 px, y 670..700), que cobre a fileira frontal da torcida onde a UI precisa de legibilidade. Em partidas assistidas (campanha, Modo Robôs, carreira) o centro dessa tarja vira o **telão** (ver 2.7). Os modos 1 e 2 (amistoso) mantêm o texto de dicas.

### 2.2 Técnica (sem Surface por frame)
**Camada estática por local ("arena composta")**: `stands_static(venue, home_color, away_color)` desenha uma vez e junta com `pitch_surf` em uma única Surface 1100x700 (`convert`), em cache com LRU de 3 chaves. Na partida, `draw()` faz 1 blit dessa Surface no lugar do `pitch_surf` (o menu continua com `pitch_surf` puro, sem mudança). Inclui degraus, corrimãos, placas (parte fixa), logotipo no gramado, escadas, luzes de refletor (glow estático) e a "torcida de fundo" estática (a distante e o lado oposto do campo).

**Torcida dinâmica por faixas ("strips")**: cada fileira da arquibancada é dividida em segmentos de ~128 px. Para cada segmento e cada pose é pré-renderizada uma Surface pequena (~128x18 px) com ~8 espectadores. Poses: 0 sentado, 1 de pé com braços para cima, 2 de pé pulando (a mesma imagem da 1, mas o segmento sobe 3 px), 3 decepção (mãos na cabeça), 4 bandeira (2 quadros). Em cada frame o jogo faz `blit` das faixas já prontas escolhendo a pose (e um deslocamento vertical) por segmento. Nenhuma Surface é criada por frame.

**Alocação por torcida**: cada segmento tem uma "fidelidade" `home`, `away` ou `neutral`. O time da casa (lado esquerdo do campo, onde está o gol dele) ocupa a lateral esquerda + 40% do fundo à esquerda; o visitante, o lado direito e 40% à direita; os 20% do meio são neutros (mistos). Cada segmento tem 85% de pureza de cor. Isso permite reagir por time: gol da casa levanta os segmentos `home`; gol do visitante, os `away`.

**Espectador (átomo)**: sprite de 14x18 construído com `pygame.draw` (cabeça = círculo; cabelo = 5 estilos; pele = 4 tons; corpo = camiseta com cor do time/neutra; braços variam por pose). Combinações: 4 pele x 5 cabelo x 3 camisetas ≈ 60 bases. Os atlas por segmento são montados uma vez com sementes fixas, sem RNG global (`random.Random(seed)` próprio, `seed = hash(venue, segmento)`).

### 2.3 Orçamento de desempenho

| Item | Desktop | WASM (estim. x4-6) | Observação |
|---|---|---|---|
| Espectadores desenhados | bairro 85 / quadra 110 / ginásio 140 / arena 220 / estádio 360 / mundial e coliseu 520 (visíveis fora da UI em ALTA: 85 / 100 / ~138 / ~165 / ~190 / ~210) | idem | todos pré-renderizados |
| Blits dinâmicos por frame | <= 90 (faixas) + 16 (extras) | idem | pequenas Surfaces de ~128x18 |
| Custo de desenho da torcida | <= 0,35 ms | <= 1,5 ms | meta de desenho total <= 1,5 ms desktop, <= 3 ms WASM |
| Placas LED | 0,05 ms | 0,2 ms | 2 blits com `area=` de uma tira longa |
| Extras (confete, flashes, flares) | <= 0,1 ms | <= 0,4 ms | confete = `pygame.draw.rect`, flares/flashes = sprites aditivos prontos |
| Atualização do estado (reações) | a cada 3 frames (20 Hz) | idem | ondas calculadas por função de tempo |
| Build do atlas (`warm_crowd`) | <= 60 ms | <= 300 ms | uma vez por `(local, cor casa, cor fora)` no início da partida (junto de `warm_sprites`) |
| Memória do atlas | <= 4 MB por chave, LRU de 3 chaves | idem | ~16 fileiras x poses x ~128x18x4 B |
| Em MAX | 0 (torcida e extras desligados; só 1 blit da arena composta) | 0 | `fx_ok()` já é falso em MAX |
| Degradação | `crowd_lod`: 2 completo, 1 sem ondas (poses fixas), 0 estático | idem | se a média móvel de `draw_ms` > 4 ms por 60 frames, desce um nível; volta só no próximo jogo |
| Opção do usuário | TORCIDA: ALTA / MÉDIA / OFF | idem | gravada em chave pequena `soccerpy_prefs_v1` (novo `prefs.py`, com sanitize e fallback) |

### 2.4 Reações por evento
Estado: `crowd.mood` por fidelidade (home/away/neutral) com `level` (0-1) e `timer`. Eventos recebem **hooks mínimos no motor**, chamados só se `self.crowd` existe e não em MAX; eles só escrevem em estruturas da torcida (nunca no estado da simulação nem no RNG):

| Evento | Hook | Reação |
|---|---|---|
| Gol | `goal()` | segmentos do time que marcou: pose 1/2 por 3 s com onda do campo; outros: pose 3; confete (arena+), flashes de câmera (8 por 2 s), sinalizadores (estádio+); a fala vai para a faixa do narrador (2.6) |
| Chance (chute com perigo) | `kick()` quando a bola vai ao gol a > 450 px/s e < 300 px | `level` sobe a 0,6 (murmúrio: pose 1 nos segmentos do time atacante, 0,6 s); "OOOH!" |
| Defesa do goleiro | `ball_interactions` ramo do GK com `speed >= CATCH_SPEED` | torcida do time que atacava: pose 3; do que defendeu: pose 1; "UUUH!/OLÉ!" |
| Bola na trave (`ball_bounds`, y fora da boca com impacto > 200) | `fx_wall` | "OOOH!", 0,4 s |
| Desarme forte/colisão | `fx_bump` | nada (evita ruído) |
| Fim de jogo | estado `over` | vitória: ola completa e confete; derrota: pose 3 |
| Ola | agendada a cada ~25 s de jogo se ninguém reagiu há 10 s (arena+) | onda que percorre os segmentos com defasagem de 0,12 s |
| Pré-jogo | `kickoff` | pose 1 e bandeiras balançando |

Faixas e cartazes: duas tiras de pano pré-renderizadas penduradas na vertical atrás dos gols (coluna de fora das laterais, no bolsão do gol: fora de toda a UI), uma do lado da casa e outra do visitante. Na campanha usam as frases do local (`EXTRAS[...]["banners"]`; a primeira, do lado do jogador, pode citar o Zé Poeira: "VAI, ZÉ POEIRA!", "SANTA FAÍSCA 4 EVER"...); no Modo Robôs, Amistoso e Carreira usam frases genéricas da torcida (`GENERIC_BANNERS`, sem nomes de personagens/marcas). `crowd.banner_texts(venue, casa, fora, story)`. Bandeiras: 2 quadros de uma mini-bandeira (listras) no Mundial/Coliseu, alternando a cada 0,25 s. Mosaico de torcida (cartões): imagem de ~120x40 px na arquibancada distante (estádio e acima) com 2 estados; troca no gol. Sinalizadores: 6 sprites de glow aditivo pré-renderizados (vermelho, branco, azul). Flashes de câmera: sprite de estrela 7x7 aditivo em até 8 posições aleatórias por ~0,1 s.

### 2.5 Densidade e tipo por capítulo/local

| Local (`venue`) | Capítulos | Estrutura | Pessoas | Extras |
|---|---|---|---|---|
| `bairro` | Amistoso, Modo Robôs tier 1 | fundo (2 fileiras) + 2 laterais de 2 colunas | 85 | 2 faixas |
| `quadra` | P, 1 | arquibancada de madeira, cadeiras, crianças; laterais de 2 colunas | 110 | cartazes de papel, tambor |
| `ginasio` | 2, Modo Robôs tier 2 | fundo + 2 laterais | 140 | bandeirinhas, LED simples |
| `arena` | 3, 6, Modo Robôs tier 3 | fundo + 2 laterais | 220 | LED Limpex, flashes |
| `estadio` / `superliga` | 4, 7, 8, Modo Robôs tier 4 | fundo + laterais + distante | 360 | LED, sinalizadores, mosaico, flashes, confete |
| `mundial` | 5, 10 | estádio cheio | 520 | bandeiras de 4 nações, LED completo, confete |
| `laboratorio` / `fabrica` | 9, 11 | robôs-fã (sprites de robôs pequenos, olhos LED piscando) | 80-120 | luzes de alerta, sem confete |
| `coliseu` | 12, 13 | estádio lotado + modo apagão no 13 (sem refletores, só LEDs) | 520 | mosaico "OMEGA", confete preto/dourado |
| `dojo` / `aeroporto` | 10 | tatames com aprendizes sentados / passageiros com malas; laterais de 2 colunas | 90 | faixas em japonês simulado ("GANBARE" em Latin-1) |

Campo novo `venue` na ação de partida da campanha (derivado do `bg` do torneio, com tabela em `crowd.py`) e parâmetro opcional `venue=None` em `Game.start_robot_match(...)` e `_begin_match(...)` (padrão `None` = nenhuma torcida, mantendo goldens e carreira de clubes). O Modo Robôs escolhe o local pelo tier da liga (bairro no tier 1).

**Implementado (A8)** - tabela única em `crowd.py` (`BG_VENUE`, `ROBOTS_VENUE`, `FRIENDLY_VENUE`, `CAREER_DIV_VENUE`). A ação de partida/treino da campanha traz `bg` (o do torneio; no treino, o do torneio do capítulo) e a UI converte com `crowd.venue_for_bg`. `venue=None` continua valendo `DEFAULT_VENUE` ("arena"), que é o caminho dos goldens.

| Modo / bg | Local |
|---|---|
| Campanha: `quadra`, `escola`, `cantina` | `quadra` |
| Campanha: `ginasio` | `ginasio` |
| Campanha: `arena`, `camarim` | `arena` |
| Campanha: `estadio`, `federacao`, `cabine` | `estadio` |
| Campanha: `mundial` | `mundial` |
| Campanha: `laboratorio`, `fabrica`, `dojo`, `aeroporto`, `coliseu` | o próprio |
| Campanha: `garagem`, `oficina`, `praca`, `lanchonete` | `bairro` |
| Treino da campanha | local do torneio do capítulo |
| Modo Robôs | pelo tier da liga (`crowd.venue_for_tier`, `ROBOTS_TIER_VENUE`): tier 1 `bairro`, 2 `ginasio`, 3 `arena`, 4 `estadio` (internamente `league["tier"]` 0..3) |
| Carreira de clubes | Div. 1 `estadio`, Div. 2 `arena`, Div. 3 `ginasio` |
| Amistoso (modos 1/2, pelo menu) | `bairro` leve, só se prefs TORCIDA != OFF (T na pausa alterna); sem telão |

### 2.6 Narrador e comentarista (substitui o antigo "som visual")
As onomatopeias da torcida ("GOOOL!", "NÃOOO!", "UHHH!", "OLÉ!", "CLAP CLAP"...) **saíram**. No lugar,
`game/narration.py` faz o narrador **Tonho** e a comentarista **Cleide** (os locutores que já existiam
no telão) falarem numa **faixa de TV** (860x46 px: etiqueta colorida NARRADOR/COMENTARISTA com o nome à
esquerda, texto à direita, barrinha do tempo restante embaixo, entrada deslizando 24 px).

- **Lances narrados** (`Game.narr_hook`, chamado por `crowd_event` e pelos ganchos de desarme, drible e
  skill): saída, chute (`chance`), defesa, trave, gol (normal, empate, virada, gol contra), desarme,
  drible, skill, fim (vitória/empate). Depois de lance grande a comentarista emenda análise, piada ou o
  placar ("Placar: POEIRA FC 1 x 0 RODO UNITED."). Sem lance por 8,5 s, um dos dois puxa assunto
  (estatística de finalizações, patrocinador, piada).
- **Catálogo**: `narration.LINES` (>= 6 falas do narrador e >= 4 da comentarista por lance; calmaria,
  placar e estatística à parte), com fichas `{T}` time do lance, `{O}` o outro, `{R}` robô, `{K}`
  skill, `{GT}/{GO}` gols, `{N}/{M}` estatística, `{MIN}` minuto. Nomes reais dos times e robôs da
  partida (amistoso: "VOCÊ" vira "SEU TIME" e os robôs sem nome ganham apelidos, `FALLBACK_ROBOTS`).
  Falas com estatística só a partir de 2. Sorteio em saco embaralhado com RNG privado; fala que não
  cabe na faixa (nomes longos) é pulada.
- **Fila sem spam**: uma fala por vez (2,0-4,2 s, pelo tamanho), no máximo 3 esperando; gol/fim cortam o
  que estiver passando; desarme/drible/skill/chute só entram com a faixa livre e respeitando o intervalo
  por tipo (`MINOR_COOLDOWN`). Relógio próprio que para na pausa; em MAX nada.
- **Posição**: câmera ESTADIO = logo abaixo do campo (y 610..656, sobre a arquibancada de baixo; nunca
  sobre o jogo). PERTO ou torcida desligada = dentro do campo, no alto ou embaixo, sempre do lado oposto
  ao da bola (troca de lado se a bola chegar). Desenhada depois do clarão do gol (fica legível).
- **Desempenho**: todo texto vira imagem no início da partida (trechos fixos num cache da sessão,
  nomes/números por partida, guardados na própria `Narration`); uma fala é uma tupla de imagens
  blitadas lado a lado; o fundo da faixa é criado uma vez por sessão. Zero Surface por quadro e nada
  de texto novo no `text_img` durante a partida (`tests/test_narration.py`).

### 2.7 Telão (HUD de estádio)
Caixinha pré-renderizada na tarja do rodapé (`crowd.TELAO`), só em partidas assistidas: bolinha vermelha
piscando + "AO VIVO  TONHO & CLEIDE NA TRANSMISSÃO" (`TELAO_TEXT`). As falas ficam na faixa do narrador
(2.6). Placas de LED no campo mostram a marca do local (Limpex, Santa Faísca, Superliga, Copa dos
Campeões) em uma tira longa scrollada com `blit(..., area=Rect(off, 0, 980, 10))`.

### 2.8 Câmera de estádio (ESTADIO x PERTO)
O campo ocupa quase toda a tela, então a torcida da geometria 2.1 (câmera **PERTO**) fica em faixas de ~60 px. Na câmera **ESTADIO** o "mundo" (campo, gols, robôs, bola e FX do jogo: tudo que usa coordenadas do jogo) é desenhado como sempre numa Surface fora da tela, **pré-alocada** (`Game.world`, 1100x700, criada uma vez), e reduzido para a tela; em volta sobram arquibancadas largas, desenhadas pela torcida em resolução cheia. Física, IA e coordenadas não mudam (goldens 80/80; `test_camera.test_scores_identical_estadio_perto_off`).

| Item | Valor |
|---|---|
| Recorte do mundo | `crowd.CAM_CROP` = x 16..1084, y 72..668 (campo + gols + folga para halo/barra dos robôs na borda) |
| Fator | `CAM_SCALE` = 0,80 → `CAM_SIZE` 854x477 em `CAM_RECT` = x 123..977, y 128..605 (campo na tela: `CAM_PITCH` = 158,142 784x448) |
| Arquibancada de cima (zona `T`, de frente para a câmera) | até 4 fileiras (topo das caixas y 100/89/78/67; a de y 67 fica meio sob o placar) |
| Laterais (`L`/`R`, giradas como em PERTO) | até 6 colunas (x 103/84/65/46/27/8 e o espelho), y 128..604; coluna 0 com o vão da faixa de pano atrás do gol (y 270..462) |
| Arquibancada de baixo (`F`, de costas, lado da câmera) | até 6 fileiras (y 610..670; as 4 primeiras acima do rodapé) |
| Placa de LED | colada ao muro do campo, em cima (y 118..126, largura do campo reduzido) |
| Fica fora do mundo (resolução cheia, por cima) | placar/HUD, rodapé (P: pausa, telão, velocidade), faixas GOL/PAUSADO/fim, faixa do narrador, confete, flashes, sinalizadores, bandeiras, faixas de pano, LED |

**Lotação (`crowd.VENUES_WIDE`, pessoas desenhadas incl. as distantes estáticas)**: bairro 200 < quadra 280 < ginásio 430 < arena 640 < estádio/superliga 1000 < mundial/coliseu 1180 (laboratório/fábrica 300, dojo/aeroporto 210). Os pequenos têm arquibancadas curtas (`sspan`, `top`/`bottom` com vão) e muro de tijolos no resto. Visíveis fora da UI (ALTA, `test_visible_estadio_much_more_than_perto`): bairro 176 (PERTO 85), quadra 275 (100), ginásio 423 (138), arena 634 (166), estádio 832 (190), mundial 925 (213). Casa à esquerda/visitante à direita (laterais, frente e cima pelo `x`).

**Regra da câmera**: TODA partida (amistoso 1/2, carreira, Modo Robôs, campanha, demo) começa em **ESTADIO** (`soccer.CAMERA_START`, `Game.camera_start`; os testes de geometria PERTO trocam esse atributo). Tecla **C** só na pausa (partidas com torcida): alterna ESTADIO ↔ PERTO **só na partida atual** e aplica na hora (re-warm no evento); a seguinte volta ao ESTADIO. Nada vai para as prefs: o antigo campo `camera` saiu de `prefs.FIELDS` (o sanitize descarta o valor de quem já tinha escolhido) e o C do menu não faz mais nada. Sem torcida (OFF) não há ESTADIO: o campo fica cheio (o modo continua ESTADIO e volta a valer se a torcida for ligada na pausa); decisão: respeitar o OFF de quem desligou a torcida em vez de religá-la.

**Técnica e desempenho**: por quadro, 4 blits da arena composta só FORA de `CAM_RECT` (`CAM_STRIPS`), faixas da torcida, repintura parcial do mundo (só os retângulos desenhados no quadro anterior: robôs, bola/rastro, partículas; `Game.world_restore/world_mark`; o campo inteiro só após warm/troca de câmera), escala com destino pronto `pygame.transform.scale(src, CAM_SIZE, dest)` e 1 blit. A assinatura `f(src, size, dest)` de `scale` e `smoothscale` foi conferida no pygame 2.6.1 e no pygame-ce 2.5.7. Medido (desktop): `smoothscale` 1,1-1,7 ms (ce 0,8-0,9) contra `scale` 0,25-0,3 ms (ce 0,12-0,2); com `smoothscale` o quadro passava de 3,5 ms, e o WASM não tem o caminho SIMD, então o padrão é `scale` (vizinho mais próximo, coerente com o visual pixelado; `soccer.CAM_SCALER`). `draw_ms` (gol em curso, `sim_harness.py draw --crowd ALTA ESTADIO`): 1,9-2,5 ms por local (mundial 2,4-2,5; PERTO 1,0-1,3). Build do pacote ESTADIO 16-55 ms; atlas até ~5,5 MB por chave (acima dos 4 MB do PERTO), LRU de 3 chaves (a câmera entra na chave). **MAX**: desenha o mínimo (campo cheio `pitch_surf`, sem torcida e sem escala). **Sem LOD de câmera** (removido): ele trocava para PERTO quando a média do quadro passava de 8 ms em 60 quadros, e o gol fazia exatamente isso. Medido no navegador (Chromium headless, pygbag, amistoso em ESTADIO): ~4,0-4,7 ms por quadro em jogo, **7,5 / 7,3 / 7,0 ms** nas janelas da festa do gol (clarão, GOOOOL!, fogos, confete) — colado no limite numa máquina rápida, acima dele em máquinas mais lentas — e a 1ª janela da partida (aquecimento) já derrubava a câmera. Agora a câmera nunca muda sozinha; a proteção de desempenho é o LOD da torcida (2.3), que também reduz os fogos (`Fireworks.lod`: 100/55/30% das faíscas). `test_camera.test_goal_never_changes_camera` força quadros de >= 12 ms com gols seguidos.

## 3. Robôs em campo

Hoje o robô é um disco 64x64 (chassis só muda detalhes). Plano (arquivo novo `game/robot_art.py`; `Game.build_robot_sprite` vira uma chamada para ele, mantendo o nome para os testes):

- **Corpo sem halo**: o halo hoje embutido no sprite sai e vira 4 sprites aditivos de halo por cor (4 níveis de pulso), blitados com `BLEND_RGB_ADD`; o LED "respira" sem recriar nada.
- **Peças visíveis** (overlays pequenos pré-renderizados em 8 direções, 24x24, neutros para tingir pela cor do time): `turbina` (cone traseiro com ar), `canhao` (cano na frente que cresce com a raridade), `parachoque_blindado` (arco frontal grosso), `escova_dupla` (2 escovas), `radar` (antena giratória), `modulo` (luzinha). Direção do rosto quantizada em 8 com histerese. Por robô por frame: 1 blit do corpo, 0-3 de overlays, olho e barra de bateria como hoje. O estado visual (`p.vis`: peças equipadas por slot) é copiado do `match_entry` e não participa da simulação.
- **Chassis**:
  - Disco: domo metálico (atual) + aba.
  - Tanque: placas de blindagem e anel largo (já tem) + esteiras laterais.
  - Velocista: aleta + 2 faixas de aceleração.
  - Goleiro: LEDs extras + luvas (2 pequenos círculos na frente) e antena.
  - **Orbital**: anel externo fino + 2 satélites que orbitam (2 `circle` por frame com seno/cosseno, ~0 custo).
  - **Titã**: corpo octogonal blindado, 6 rebites, aberturas de ventilação laterais (cabe no raio de 18 px; a física `PR=14` não muda).
- **Animações**: escova girando (3 quadros em sprite de 14x14, avança conforme o deslocamento do robô, `p.odo` só no desenho); rodas piscando; LED pulsando; faíscas de poeira ao correr rápido (novo `FX_KINDS["dust"]`, fora de MAX); fumaça com peças de calor (`heat > 0`) e overdrive.
- **Dano e bateria baixa**: variante `low` (já existe) ganha faíscas elétricas e meio LED apagado (quadro `low` pré-renderizado); abaixo de 0,10 de bateria, o robô perde a escova (some o overlay).
- **Pintura e cosméticos**: pintura continua `led_color`; `look.decal` (adesivo 8x8) e `look.antenna` desenhados no sprite pré-renderizado (chave de cache ganha `decal`).
- **Skills**: FX por 0,3-1,5 s (anel dourado, rastro de imagens residuais, halo vermelho) usando `pygame.draw` e sprites aditivos prontos; ver a spec de itens e habilidades.
- **Implementado (A9-A11)**: corpo sem halo por `(chassis, led, gk, low)`; halo = 5 Surfaces RGB aditivas por cor (4 pulsos + bateria baixa); atlas por `(chassis, led, gk, peças visíveis)` com as camadas "baixo"/"cima" em 8 direções recortadas no bounding rect (15-40 KB); escova = 6 quadros 14x14 compartilhados; fumaça/poeira = sprites alfa prontos. `p.vis` vem de `garage.robot_vis` via `match_entry` (aditivo; squads sem `vis` funcionam). Cache `robot_art.SpriteCache` com LRU por bytes (teto 6 MB; uma partida usa ~0,9 MB). FX novos `dust`, `smoke`, `smoke_dark`, `spark` (RNG `fx_rng`, teto `ROBOT_FX_MAX` = 36 dentro do `FX_MAX`), emitidos pelo desenho; nada em MAX, na pausa e em `over`.
- **Custo**: cache de sprites por `(chassis, led, gk, low, decal)`: ~6 chassis x ~14 cores x 2 x 2 = ~340 sprites de 64x64x4 B = ~5,5 MB no pior caso; `warm_sprites` já constrói só o que o jogo usa.

## 4. Retratos e cenários (`portraits.py`)

**Personagens**:
- Humores novos (8): `determinado`, `maravilhado`, `malicioso`, `sonolento`, `chorando`, `gritando`, `piscando`, `euforico` em `draw_face` (boca e sobrancelha novas; lágrima, estrelinhas nos olhos, "zzz" pelo `susp`).
- **Sincronia da fala**: durante a digitação (`dlg_typing`), a boca alterna 2 quadros a cada ~120 ms; ao fim volta ao humor. Pisca a cada ~3,5 s com duração de 0,12 s, determinístico por contador (sem RNG global). `bob` de respiração leve.
- **Personagens novos** (7): `nestor`, `valquiria`, `gabi`, `odete`, `ogawa`, `tonho`/`cleide` (em `cabine`, com microfone), `zeperfeito`/`xomega` (variantes de `draw_robot`: sem chinelo, LED vermelho no X-Ômega).
- Estilos novos: cabelo `trancas`, `coque`, `moicano`; acessórios `bone`, `bengala`, `avental`, `tiara`, `cachecol`; roupas `avental`, `colete`. Mantêm `R` e `k` como parâmetros.
- **Zé Poeira**: expressão por LED mais rica (LED muda de cor por humor já existe), mais 4 estados (rodinha caindo em animação de 3 quadros).

**Estilo pixel art (padrão desde a Fase 4, `game/portraits_pixel.py`)**:
- `portraits.STYLE = "pixel"` é o padrão no desktop e no navegador; `"classico"` (vetorial, por quadro) fica só para comparação: `SOCCERPY_PORTRAITS=classico` no desktop ou trocar a constante. O narrador continua com o ícone do livro.
- **Todos os personagens** têm versão pixel: os 15 humanos (Téo, Ambrósio, Gervásio, Vivi, Bia, Dudu, Dr. Augusto, Cap. Rodolfo, Dra. Helena, Kenji, Vô Nestor, Dra. Valquíria, Gabi Trovão, Dona Odete, Mestre Ogawa) e os 3 robôs (Zé Poeira, Zé Perfeito, X-Ômega: disco com LED por humor, aro da tampa na cor do LED, antena, chinelo + fita no Zé).
- **Técnica**: resolução lógica 56x102 (robô 46x30) num mapa de materiais com 4 tons por material (luz/base/sombra/sombra profunda), bevel automático, contorno de 1 px por máscara e detalhes à mão. Ordem: cabelo de trás -> roupa -> cabeça -> gola/cachecol -> cabelo da frente -> acessórios. Cabelos: espetado (Téo, Kenji), calvo (Ambrósio, Nestor com tufos fartos), social, militar, grisalho com entradas (Ogawa), penteado para trás (Augusto), liso longo com anel de brilho (Vivi), chanel (Helena), curto com tufos (Bia), cacheado em camadas (Dudu), coque com elástico (Valquíria, Odete), espetos saindo do boné (Gabi). Roupas: moletom, jaleco, terno, blazer acinturado com camisa e broche, camiseta de manga curta (engrenagem da Bia, raio da Gabi), farda (gola alta, dragonas, faixa dourada, estrela, barretas, cinto), kimono (golas cruzadas, faixa com nó, calça larga e pé descalço), camisa + colete de tweed com corrente de relógio, blusa arregaçada + avental com colher de pau. Acessórios: tiara com estrela, bandana com nó, óculos de proteção na testa, graxa, headset com LED e microfone, óculos redondos e grandes, cachecol listrado, boné de aba lateral, luvas, bengala, chinelo, brincos; bigodes social, bigodão e fino comprido.
- **Rosto por humor** (os 22 de `story.MOODS`): rosto feminino com cílios, lábio colorido e queixo mais fino; rugas para os mais velhos. `determinado` = sobrancelhas baixas, pálpebra reta e boca firme com queixo tenso (sem a boca "código de barras"); `malicioso` = olhos apertados de lado e sorriso torto com dentes de um lado; `convencido(a)` = pálpebras pesadas, sobrancelha erguida e sorrisinho com covinha.
- **Busto**: escala inteira (4x na caixa de 150x166); quando o cabelo é alto (pontas do Téo/Kenji, coque, boné) a cabeça desce até o topo caber inteiro na moldura (`BUST_MARGIN`).
- **Cache e custo**: base k=1 por (personagem, camada) - o mapa é descartado depois de pintado; grupos (personagem, humor, k) com 4 quadros (piscar x boca) em LRU de 48; esmaecido (k < 1) feito da versão k=1 com 2 fills (MULT + ADD = `P.shade`); pernas esmaecidas em LRU de 24; rascunhos de ampliação por tamanho (LRU de 6). Medido (desktop): base de um personagem 2-5 ms, grupo de humor ~0,6 ms, todos os 18 personagens em neutro x 2 k ~55 ms; quadro de diálogo com 4 personagens + busto 0,56 ms (clássico 0,71 ms); cache no teto ~4,8 MB (cena típica ~2 MB). `campaign_ui.dlg_load_line` chama `portraits.prepare` para montar o humor novo fora do `draw`; zero Surface por quadro depois disso.
- Testes: `tests/test_portraits.py` (`test_pixel_*`: matriz completa personagens x humores x quadros x k com zero Surface, humores distintos por personagem, cabelo inteiro no busto, esmaecido = `shade`, custo).

**Cenários** (`get_background` continua devolvendo uma Surface estática por `bg`; cache `_BG_CACHE`):
- **Camadas**: cada cenário passa a ter 3 camadas (fundo, meio, frente) e uma camada de luz (cones aditivos). A composição é feita uma vez no cache; a frente (grades, plantas, vasos) fica em uma segunda Surface cacheada, blitada **depois** do personagem para dar parallax de profundidade (+1 blit).
- **Animação leve** (sem Surface por frame): poeira flutuando = 14 pontos com seno (`pygame.draw.circle`), luz piscando = 2 quadros de glow aditivo (alternados), TV/telão do cenário com 2 quadros, folhas balançando (offset de 1-2 px).
- **Novos cenários (+8)**: `praca` (praça com banco e pombo robô), `laboratorio` (tubos, hologramas), `aeroporto` (esteira, painel de voos), `dojo` (tatame, biombo), `fabrica` (esteira com Zés), `coliseu` (arquibancada circular, refletores), `lanchonete` (balcão, cardápio), `cabine` (locutores).
- **Reaproveitar a torcida**: os cenários de estádio (`quadra`, `ginasio`, `arena`, `estadio`, `mundial`) hoje usam `_bleachers` com círculos; passam a usar as mesmas faixas/átomos de `crowd.py` (um espectador por vez, estático), economizando código e deixando o visual coerente com a partida.
- Custo: os retratos já são desenhados por frame com `pygame.draw` (sem Surface); manter assim. Cenário novo = 1 Surface estática de 1100x470 (~2 MB cada, cache sob demanda, LRU de 6).

## 5. Como testar (obrigatório)
- **Zero Surface por frame**: `tests/test_crowd.py` troca `pygame.Surface` por um contador (como `test_60_frames_every_screen_zero_surface_and_cache`) e confere 0 criações em 300 frames de partida com torcida em cada local; idem para robôs com todas as peças e FX de skills.
- **Tempo de desenho**: `sim_harness.py draw` ganha `--crowd` e imprime `draw_ms` por local; limite duro 25 ms (como `test_draw_time_budget`), metas 1,5 ms (desktop). Aviso informativo > 3 ms.
- **Determinismo**: duas partidas com a mesma semente e torcida ligada/desligada produzem o mesmo placar (hooks não alteram a simulação). Comparar `score` e `events` em 20 sementes.
- **Goldens**: `golden --check` e `golden-new --check` ficam em 80/80 após cada passo da Onda A e B.
- **Reações**: teste de unidade que chama `crowd.event("goal", team=0)` e confere as poses por fidelidade nos frames 0, 30, 90 e 200 (usa um relógio injetado, não `time.perf_counter`).
- **Cache**: `warm_crowd` chamado de novo com a mesma chave não reconstrói (contagem de `Surface` = 0); LRU descarta a 4ª chave.
- **LOD**: força `draw_ms` alto simulado e confere a descida 2 -> 1 -> 0 e a opção OFF.
- **Capturas**: `sim_harness.py shot` por local (revisão visual manual a cada onda); e `test_visual`/`test_portraits` ganham os novos humores/cenários (rodam sem erro, desenham algo diferente do fundo).
- **Latin-1**: nenhuma string nova com caractere fora de Latin-1 (já há `test_latin1_source`).
