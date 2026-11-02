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

Placas de publicidade LED: faixa de 12 px colada ao campo, em baixo (y 652..664) e em cima (y 78..90). O rodapé de UI (botões de velocidade e dica) fica sobre uma tarja translúcida pré-renderizada (30 px, y 670..700), que cobre a fileira frontal da torcida onde a UI precisa de legibilidade. Em partidas assistidas (campanha, Modo Robôs, carreira) o centro dessa tarja vira o **telão** (ver 2.7). Os modos 1 e 2 (amistoso) mantêm o texto de dicas.

### 2.2 Técnica (sem Surface por frame)
**Camada estática por local ("arena composta")**: `stands_static(venue, home_color, away_color)` desenha uma vez e junta com `pitch_surf` em uma única Surface 1100x700 (`convert`), em cache com LRU de 3 chaves. Na partida, `draw()` faz 1 blit dessa Surface no lugar do `pitch_surf` (o menu continua com `pitch_surf` puro, sem mudança). Inclui degraus, corrimãos, placas (parte fixa), logotipo no gramado, escadas, luzes de refletor (glow estático) e a "torcida de fundo" estática (a distante e o lado oposto do campo).

**Torcida dinâmica por faixas ("strips")**: cada fileira da arquibancada é dividida em segmentos de ~128 px. Para cada segmento e cada pose é pré-renderizada uma Surface pequena (~128x18 px) com ~8 espectadores. Poses: 0 sentado, 1 de pé com braços para cima, 2 de pé pulando (a mesma imagem da 1, mas o segmento sobe 3 px), 3 decepção (mãos na cabeça), 4 bandeira (2 quadros). Em cada frame o jogo faz `blit` das faixas já prontas escolhendo a pose (e um deslocamento vertical) por segmento. Nenhuma Surface é criada por frame.

**Alocação por torcida**: cada segmento tem uma "fidelidade" `home`, `away` ou `neutral`. O time da casa (lado esquerdo do campo, onde está o gol dele) ocupa a lateral esquerda + 40% do fundo à esquerda; o visitante, o lado direito e 40% à direita; os 20% do meio são neutros (mistos). Cada segmento tem 85% de pureza de cor. Isso permite reagir por time: gol da casa levanta os segmentos `home`; gol do visitante, os `away`.

**Espectador (átomo)**: sprite de 14x18 construído com `pygame.draw` (cabeça = círculo; cabelo = 5 estilos; pele = 4 tons; corpo = camiseta com cor do time/neutra; braços variam por pose). Combinações: 4 pele x 5 cabelo x 3 camisetas ≈ 60 bases. Os atlas por segmento são montados uma vez com sementes fixas, sem RNG global (`random.Random(seed)` próprio, `seed = hash(venue, segmento)`).

### 2.3 Orçamento de desempenho

| Item | Desktop | WASM (estim. x4-6) | Observação |
|---|---|---|---|
| Espectadores visíveis | quadra 30 / ginásio 90 / arena 220 / estádio 360 / mundial e coliseu 520 | idem | todos pré-renderizados |
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
| Gol | `goal()` | segmentos do time que marcou: pose 1/2 por 3 s com onda do campo; outros: pose 3; confete (arena+), flashes de câmera (8 por 2 s), sinalizadores (estádio+), onomatopeia "GOOOL!" |
| Chance (chute com perigo) | `kick()` quando a bola vai ao gol a > 450 px/s e < 300 px | `level` sobe a 0,6 (murmúrio: pose 1 nos segmentos do time atacante, 0,6 s); "OOOH!" |
| Defesa do goleiro | `ball_interactions` ramo do GK com `speed >= CATCH_SPEED` | torcida do time que atacava: pose 3; do que defendeu: pose 1; "UUUH!/OLÉ!" |
| Bola na trave (`ball_bounds`, y fora da boca com impacto > 200) | `fx_wall` | "OOOH!", 0,4 s |
| Desarme forte/colisão | `fx_bump` | nada (evita ruído) |
| Fim de jogo | estado `over` | vitória: ola completa e confete; derrota: pose 3 |
| Ola | agendada a cada ~25 s de jogo se ninguém reagiu há 10 s (arena+) | onda que percorre os segmentos com defasagem de 0,12 s |
| Pré-jogo | `kickoff` | pose 1 e bandeiras balançando |

Faixas e cartazes: tiras de pano pré-renderizadas pendem da fileira frontal ("VAI, ZÉ POEIRA!", "SANTA FAÍSCA 4 EVER", "LIMPEX: LIMPA, MAS NÃO GANHA"), com texto por capítulo e a faixa personalizada do jogador. Bandeiras: 2 quadros de uma mini-bandeira (listras) no Mundial/Coliseu, alternando a cada 0,25 s. Mosaico de torcida (cartões): imagem de ~120x40 px na arquibancada distante (estádio e acima) com 2 estados; troca no gol. Sinalizadores: 6 sprites de glow aditivo pré-renderizados (vermelho, branco, azul). Flashes de câmera: sprite de estrela 7x7 aditivo em até 8 posições aleatórias por ~0,1 s.

### 2.5 Densidade e tipo por capítulo/local

| Local (`venue`) | Capítulos | Estrutura | Pessoas | Extras |
|---|---|---|---|---|
| `bairro` | Amistoso, Modo Robôs (padrão) | só fundo, 2 fileiras | 30 | 2 faixas |
| `quadra` | P, 1 | arquibancada de madeira, cadeiras, crianças | 30 | cartazes de papel, tambor |
| `ginasio` | 2 | fundo + 1 lateral | 90 | bandeirinhas, LED simples |
| `arena` | 3, 6 | fundo + 2 laterais | 220 | LED Limpex, flashes |
| `estadio` / `superliga` | 4, 7, 8 | fundo + laterais + distante | 360 | LED, sinalizadores, mosaico, flashes, confete |
| `mundial` | 5, 10 | estádio cheio | 520 | bandeiras de 4 nações, LED completo, confete |
| `laboratorio` / `fabrica` | 9, 11 | robôs-fã (sprites de robôs pequenos, olhos LED piscando) | 80-120 | luzes de alerta, sem confete |
| `coliseu` | 12, 13 | estádio lotado + modo apagão no 13 (sem refletores, só LEDs) | 520 | mosaico "OMEGA", confete preto/dourado |
| `dojo` / `aeroporto` | 10 | tatames com aprendizes sentados / passageiros com malas | 40 | faixas em japonês simulado ("GANBARE" em Latin-1) |

Campo novo `venue` na ação de partida da campanha (derivado do `bg` do torneio, com tabela em `crowd.py`) e parâmetro opcional `venue=None` em `Game.start_robot_match(...)` e `_begin_match(...)` (padrão `None` = nenhuma torcida, mantendo goldens e carreira de clubes). O Modo Robôs usa `venue="bairro"` por padrão.

### 2.6 "Som visual"
Onomatopeias e letreiros no lugar de áudio, sempre via `text_img` (cache) em tamanhos fixos {26, 36, 52}: "GOOOL!", "OOOH!", "UUUH!", "OLÉ!", "CLAP CLAP", "BUZZ!" (skill), "ZOOM" (arrancada), "CLANG!" (trave). Surgem acima da arquibancada da fidelidade que reage, sobem 30 px em 0,8 s e desaparecem por troca de cor em 4 passos (sem `set_alpha` em Surfaces compartilhadas: o fade usa `scale_color` no `text_img` com os 4 degraus pré-cacheados). No máximo 2 onomatopeias ao mesmo tempo.

### 2.7 Telão (HUD de estádio)
Mostrador pré-renderizado de ~450x34 px na tarja do rodapé (x 270..720, y 658..692), só em partidas assistidas (`career_match`). Conteúdo: linha 1 placar compacto + minuto; linha 2 legenda do locutor (Tonho/Cleide) por evento ("Que lance, Cleide!", "O chinelo ainda está no lugar, Tonho."), até 3 variações por tipo escolhidas por `event_index % n`. Textos pré-renderizados via `text_img`. Placas de LED no campo mostram a marca do local (Limpex, Santa Faísca, Superliga, Copa dos Campeões) em uma tira longa scrollada com `blit(..., area=Rect(off, 0, 980, 10))`.

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
- **Custo**: cache de sprites por `(chassis, led, gk, low, decal)`: ~6 chassis x ~14 cores x 2 x 2 = ~340 sprites de 64x64x4 B = ~5,5 MB no pior caso; `warm_sprites` já constrói só o que o jogo usa.

## 4. Retratos e cenários (`portraits.py`)

**Personagens**:
- Humores novos (8): `determinado`, `maravilhado`, `malicioso`, `sonolento`, `chorando`, `gritando`, `piscando`, `euforico` em `draw_face` (boca e sobrancelha novas; lágrima, estrelinhas nos olhos, "zzz" pelo `susp`).
- **Sincronia da fala**: durante a digitação (`dlg_typing`), a boca alterna 2 quadros a cada ~120 ms; ao fim volta ao humor. Pisca a cada ~3,5 s com duração de 0,12 s, determinístico por contador (sem RNG global). `bob` de respiração leve.
- **Personagens novos** (7): `nestor`, `valquiria`, `gabi`, `odete`, `ogawa`, `tonho`/`cleide` (em `cabine`, com microfone), `zeperfeito`/`xomega` (variantes de `draw_robot`: sem chinelo, LED vermelho no X-Ômega).
- Estilos novos: cabelo `trancas`, `coque`, `moicano`; acessórios `bone`, `bengala`, `avental`, `tiara`, `cachecol`; roupas `avental`, `colete`. Mantêm `R` e `k` como parâmetros.
- **Zé Poeira**: expressão por LED mais rica (LED muda de cor por humor já existe), mais 4 estados (rodinha caindo em animação de 3 quadros).

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
