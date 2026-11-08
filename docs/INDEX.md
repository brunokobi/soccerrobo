# Documentação - Copa Aspirador

Planejamento e especificações do jogo. O código e os comandos do dia a dia estão no
[README](../README.md).

| Documento | Conteúdo |
|---|---|
| [roadmap.md](roadmap.md) | Fases do projeto, objetivos e tamanho da Fase 4 (Campanha Expandida), princípios que não podem quebrar e marcos jogáveis (M1-M5) |
| [specs/campanha-expandida.md](specs/campanha-expandida.md) | A campanha atual vira o Ato 1; Ato 2 (Superliga Limpex, caps. 6-9) e Ato 3 (Copa dos Campeões, caps. 10-13); 7 personagens novos, formatos de torneio novos, escolhas com consequência, 3 finais, missões secundárias, migração de saves, curva de dificuldade e economia |
| [specs/itens-e-habilidades.md](specs/itens-e-habilidades.md) | Peças de 14 para ~36 modelos, 8º slot "Módulo", sets, relíquias únicas, consumíveis de partida, cosméticos e o sistema de 16 skills dos robôs (gatilhos, efeitos no motor, cooldown, custo de bateria, como se ganham), integração no motor sem quebrar os goldens, calibração e garage v2 |
| [specs/visual-desenhos-e-torcida.md](specs/visual-desenhos-e-torcida.md) | Torcida nas arquibancadas (geometria, técnica sem Surface por frame, orçamento de desempenho, reações por evento, densidade por capítulo, narrador e comentarista na faixa de TV, telão AO VIVO, câmera ESTÁDIO em toda partida), robôs com peças visíveis e animações, retratos e cenários mais detalhados, personagens em pixel art (estilo padrão: técnica, roupas/acessórios por personagem, humores, busto, cache e custo), escudos dos times (`crests.py`: técnica, símbolos, especiais, cache fora do desenho, custo, escudo do jogador) e como testar |
| [specs/som.md](specs/som.md) | Fase 6 - Som: catálogo de efeitos e onde tocam, trilhas chiptune, síntese (stdlib, 22050 Hz), formato do mixer, prefs (M/S/N), limites de vozes e throttle, navegador (pygbag) e medições; reações da torcida (tabela única, variações derivadas, saco embaralhado), música da partida + torcida de fundo em loop tocando juntas (volumes, RAM, `tools/torcida_loop.sh`) e áudios compactos com volume nivelado (`tools/normalizar_audio.sh`) |
| [specs/formacoes.md](specs/formacoes.md) | Formações (5) em todos os modos: dados compartilhados (`formations.py`), seletor com mini-campo (`formation_ui.py`) no Amistoso, na Campanha (torneio, treino, Torre), no Modo Robôs (aba LIGA) e na Carreira (aba INÍCIO), teclas, motor (padrão = motor de sempre), campo opcional `formation` nos saves, CPU na padrão; balanceamento medido em `tests/calib_formations.py` (sem formação dominante até Força ~75; efeito no SIMULAR) |
| [specs/estatisticas.md](specs/estatisticas.md) | Estatísticas da partida (coleta passiva no motor: gols, assistências, chutes, passes, desarmes, dribles, defesas, posse), nota e MELHOR DO JOGO, onde aparecem em cada modo (fim da partida, card do resumo, TAB), SIMULAR com RNG privado, acumulados nos saves (robo `cs`, liga `ps`, torneio `ps`, jogadores da carreira) e limitações |
| [plano-crazygames.md](plano-crazygames.md) | Proposta para publicar no CrazyGames: como funciona a publicação (Basic/Full Launch, repasse), direitos dos áudios a trocar, inglês, SDK de anúncios (`game/portal.py`), build sem CDN externo, celular, página, cadastro/pagamento e ordem dos passos |
| [baseline-fase4.md](baseline-fase4.md) | Medições de referência antes da Fase 4 (commit 8a467a3): `draw_ms`, `menu_ms`, `ms_step`, goldens e resumo da calibragem da campanha |
| [img/](img/) | Capturas de tela usadas no README (menu, partida com a faixa do narrador, amistoso, formação, campanha, garagem, habilidades, Mochila, cosméticos, Torre, escudos, elenco da carreira). Para regerar, com `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy SOCCERPY_SHOTS_DIR=<pasta>`: `tests/sim_harness.py ui-shots` (menu `a7_menu.png`, gol e narração) e `camera-shots`; `tests/test_campaign_ui.py <teste>` (ex.: `test_tourney_group_table_bracket_and_labels` -> `tourney_knockout.png`, `test_tower_screen_sim_watch_marks_and_restart` -> `d2_torre_tela.png`, `test_formation_selector_tourney_training_and_save` -> `formacao_torneio.png`); `tests/test_robots_ui.py test_formation_selector_robots_hub_and_save` (`formacao_robos.png`, aba LIGA); `tests/test_friendly.py` (tela do amistoso). A partida do README é um Modo Robôs no `estadio` com a garagem `sim_harness.loaded_garage()`, capturada após ~12 s de jogo. Confira cada imagem e copie só as escolhidas |
| [specs/plano-de-implementacao.md](specs/plano-de-implementacao.md) | Ondas 0, A (visual), B (itens/skills), C (campanha), D (pós-campanha) em passos pequenos com arquivos e validação; estratégia de testes; riscos; decisões para o dev |

## Estado
- Fases 1, 2 e 3: prontas e publicadas em https://copaaspirador.brunokobi.tech
- Fase 4 (Campanha Expandida): **Ondas A (torcida, robôs detalhados, retratos, cenários, câmera de
  estádio), B (peças, sets, relíquias, slot Módulo, 16 skills, itens, Mochila, cosméticos) e C (Atos 2
  e 3) prontas e publicadas.** Onda C:
  - campanha completa: Prólogo + 13 capítulos em 3 Atos, 161 cenas, 4 escolhas grandes (B1-B4) que
    mudam adversários, falas e recompensas, **3 finais** (Garagem Livre, Contrato Dourado e o secreto
    O Chinelo Estrutural) com galeria e recompensa própria, e **14 missões secundárias** (as 4 Fitas do
    Vô levam ao final secreto);
  - estrutura: `story.py` como fachada de `story_a2/a3/side.py`, save **v2** com migração dos saves v1
    (sem rewind do Ato 1), torneios de liga e série, nós condicionais, variantes de adversário e de
    recompensa, mapa por Ato, tela de missões, torcida por torneio (`venue`);
  - economia do Ato 2/3 (tiers 4-6, loja, XP até o nível 15, bônus da escolha B2) e calibração dos 3
    Atos no motor real (tabelas em `tests/calib_campaign.py`; acima de Força ~85 o motor achata e o
    SIMULAR ganhou uma correção para Força alta);
  - **pontos de atenção (decisão do dev):** quem nunca evolui o time (não gasta sucata nem PH) trava no
    Ato 2 e não termina o Ato 3 — ideias: equipar sozinhas as skills de história ou pity maior a
    partir do Ato 2; dois testes sensíveis à carga da máquina (`test_camera`, limite de tempo do
    `test_skills_engine`).
  - **Onda D (pós-campanha) pronta e publicada:** NG+ "Turnê Lendária" (3 voltas
    de revanches com rivais +20/+26/+30, teto 90, cenas curtas, sucata, peças Míticas e cosméticos), Torre
    do Pó (40 andares, modificadores de arena opt-in no motor, marcos 10/20/30/40) e peças Míticas +
    7 cosméticos de recompensa; save da campanha **v3** com migração do v2; calibração no motor em
    `tests/calib_campaign.py --post` (detalhes e desvios em
    [specs/plano-de-implementacao.md](specs/plano-de-implementacao.md)).
- Fase 5 (Editor de firmware): planejada
- Amistoso com escolha de times (29, de todos os modos) e formações (5) antes da partida (`game/friendly.py`,
  `game/friendly_ui.py`; padrão idêntico ao motor antigo, goldens 80/80): pronto e publicado.
- Formação em todos os modos: o mesmo seletor na Campanha
  (torneio, treino, Torre), no Modo Robôs (aba LIGA) e na Carreira (aba INÍCIO), salvo como campo opcional
  `formation` (garage v2 sem subir versão; carreira idem), CPU na padrão
  ([specs/formacoes.md](specs/formacoes.md)): pronta e publicada; balanceamento medido em
  `tests/calib_formations.py` (sem formação dominante até Força ~75; acima disso a PRESSÃO rende mais,
  aceito pelo dono; o efeito por Força entra no SIMULAR).
- Fase 6 (Som): **pronta** — efeitos e música sintetizados por código (`game/sfx.py`, `game/music.py`),
  sons gravados em `game/audio/` (músicas de menu/robôs/copas, torcida com variações em saco embaralhado,
  gol, apito, "acabou!", caixa registradora no card do resumo, trave, motor e desligar dos robôs), música
  "Into the Iron Horizon" (`partida_musica.ogg`) nas partidas junto da torcida de fundo em loop
  (`tools/torcida_loop.sh`), áudios nivelados (`tools/normalizar_audio.sh`), mudo (M) e volumes (S/N) nas
  prefs, testado no desktop e no navegador (pygbag); publicada.
- Partida e campanha: câmera ESTÁDIO em toda partida, sem troca automática (C só na pausa, só naquela
  partida), faixa do narrador Tonho e da comentarista Cleide (`game/narration.py`), personagens e
  cenários da campanha em pixel art (`game/portraits_pixel.py`, `game/scenes_pixel.py`).
- Estatísticas e MELHOR DO JOGO em todos os modos (fim da partida, card do resumo com TAB, narradora anuncia o
  MVP), estatísticas estimadas no SIMULAR e artilharia/assistências acumuladas (liga do Modo Robôs, ficha do
  robô, torneio da campanha, carreira), campos opcionais nos saves; goldens 80/80
  ([specs/estatisticas.md](specs/estatisticas.md)): pronto e publicado.
- Escudos dos times em pixel art (`game/crests.py`): os 128 times de todos os modos + o do jogador (clique no escudo
  do topo troca símbolo/formato, campo opcional `crest` na garagem), em todas as telas com times; goldens 80/80
  ([specs/visual-desenhos-e-torcida.md](specs/visual-desenhos-e-torcida.md)): pronto e publicado.
- Carreira com robôs: todos os jogadores da carreira são robôs aspiradores com nome de robô (`game/robot_names.py`:
  ~4,7 mil nomes, tirados do id do robô, sem RNG e sem repetir no clube; carreira nova só com nomes-base como
  "Zumbido" e "Faísca", os que chegam depois ganham modelos/códigos como "Turbo Mk2", "Vassoura-7", "RX-07") e
  **elenco de 5 a 10** (5 titulares + até 5 reservas; a CPU nasce com 7-10 tirados de uma peneira de 15, mantendo
  a força dos titulares da geração antiga; o mercado não compra acima de 10 nem vende abaixo de 5). O save da
  carreira ganhou `ver` = 2: save antigo é migrado ao carregar (nomes de robô pelo id; elencos acima de 10 ficam
  com os titulares + melhores reservas, garantindo um goleiro; excedentes do clube do jogador vendidos pelo valor
  de mercado; estatísticas seguem no id), save inválido não carrega nem é sobrescrito; testes em
  `tests/test_career.py` (fixture real do save antigo em `tests/fixtures/career_v1_mid_season.json`); goldens 80/80.
- Deploy: build do pygbag + `tools/versionar_build.sh` (cache busting do `game.apk`); ver o README.
- Publicação em portais: proposta para o CrazyGames em [plano-crazygames.md](plano-crazygames.md) (ainda não iniciada).
- Código: ~52,7 mil linhas (game ~31,7 mil, tests ~21,0 mil); 572 testes (`def test_` em `tests/test_*.py`).
