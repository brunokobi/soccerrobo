# Plano de implementação e testes - Fase 4

Níveis: `mecanico` (renomear, mover, ajustar texto/config, mudança local óbvia), `rotineiro` (feature/correção pequena seguindo padrão existente), `complexo` (várias camadas, regra de negócio nova, concorrência, performance, integração). (sensível: save/migração) marca save, migração de dados e sanitize (não há autenticação, tenants nem pagamentos neste repositório).

Comandos de validação padrão (rodar da raiz com `export SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy`):
- Rápidos: `.venv/bin/python tests/test_<arquivo>.py`.
- Goldens: `tests/sim_harness.py golden --check` e `golden-new --check` (80/80).
- Orçamento: `tests/sim_harness.py draw`.
- Calibração: `tests/calib_campaign.py` (pesado), `tests/calib_skills.py`, `tests/calib_robots.py`.

## Onda 0 - Preparação (1 sessão)
| # | Nível | Passo | Arquivos | Validação |
|---|---|---|---|---|
| 0.1 | mecanico | Gravar baselines: `draw_ms` (0,69), `ms_step` (0,037), `golden`/`golden-new` verdes, tabela atual de `calib_campaign`. Nota em `docs/` | `docs/baseline-fase4.md` | comandos acima |
| 0.2 | mecanico | Atualizar README (roadmap: Fase 4 Campanha Expandida, Fase 5 editor de firmware) e criar `docs/INDEX.md` | `README.md`, `docs/INDEX.md` | revisão |
| 0.3 | rotineiro | `prefs.py` com `soccerpy_prefs_v1` (torcida ALTA/MÉDIA/OFF), sanitize e fallback; sem UI ainda | `game/prefs.py`, `tests/test_prefs.py` | teste de store, valor inválido -> padrão |
| 0.4 | rotineiro | Extrair `Game.sprites`/`build_robot_sprite` para `game/robot_art.py` mantendo `Game.build_robot_sprite` como wrapper | `game/robot_art.py`, `game/soccer.py` | `test_visual`, `test_robots_ui`, goldens |

## Onda A - Torcida e visual (marco M1)
| # | Nível | Passo | Arquivos | Validação |
|---|---|---|---|---|
| A1 | complexo | `crowd.py`: átomo de espectador, segmentos, poses, atlas por `(venue, cores)`, LRU 3, `warm_crowd` no início da partida | `game/crowd.py` | `test_crowd.py` (zero Surface, build <= 60 ms, memória) |
| A2 | complexo | Arena composta por local (`stands_static`): degraus, placas, fundo distante, tarja do rodapé; `draw()` usa 1 blit; menu intacto | `game/crowd.py`, `game/soccer.py` | `test_visual`, `draw_ms` <= 1,2 ms, goldens |
| A3 | complexo | Estado de reação (`crowd.event`, humores por fidelidade, ola, calma) e hooks guardados em `goal`, `kick`, `ball_interactions`, `fx_wall`, `kickoff` e fim de jogo; relógio injetável | `game/crowd.py`, `game/soccer.py` | `test_crowd.py` (poses por frame), teste de determinismo, goldens |
| A4 | rotineiro | Extras: confete, flashes, sinalizadores, bandeiras de 2 quadros, mosaico, faixas de pano; sprites aditivos prontos | `game/crowd.py` | zero Surface, `draw_ms` |
| A5 | rotineiro | Placas de LED scrolladas e onomatopeias via `text_img` | `game/crowd.py`, `game/soccer.py` | `test_crowd.py`, captura |
| A6 | rotineiro | Telão no rodapé (`career_match`) com legendas de locutores; modos 1/2 mantêm dicas | `game/soccer.py`, `game/crowd.py` | `test_visual`, captura |
| A7 | complexo | LOD automático e opção TORCIDA ALTA/MÉDIA/OFF (pausa e menu), gravada em prefs | `game/soccer.py`, `game/prefs.py` | `test_crowd.py::test_lod`, `test_prefs` |
| A8 | mecanico | Tabela `venue` por `bg` da campanha e `venue=` em `start_robot_match`/`_begin_match` (padrão `None`); Modo Robôs usa `bairro` | `game/soccer.py`, `game/campaign_ui.py`, `game/robots_ui.py` | `test_robot_mode`, `test_campaign_ui` (zero Surface), goldens |
| A9 | complexo | Robôs: halo em 4 níveis, overlays de peças em 8 direções, `p.vis`, escova girando | `game/robot_art.py`, `game/soccer.py`, `game/garage.py` (`match_entry` adiciona `vis`) | `test_visual`, zero Surface, `draw` |
| A10 | complexo | Orbital (satélites) e Titã (octogonal), Tanque/Velocista/Goleiro com detalhes novos | `game/robot_art.py` | capturas, `draw_ms` |
| A11 | rotineiro | Dano/bateria baixa (faíscas, quadro `low` novo), poeira e fumaça (`FX_KINDS`) | `game/robot_art.py`, `game/soccer.py` | `test_visual` |
| A12 | rotineiro | `portraits.py`: 8 humores novos, piscar e fala 2 quadros, estilos novos de cabelo/acessório/roupa | `game/portraits.py`, `game/story.py` (`MOODS`, `HAIR_STYLES`...) | `test_portraits`, `test_story` |
| A13 | complexo | Cenários em camadas + luz + animação leve; `_bleachers` passa a usar átomos do `crowd.py`; 8 cenários novos | `game/portraits.py` | `test_portraits`, `draw_ms` por cena |
| A14 | rotineiro | Fechamento da Onda A: README, capturas, medições finais | `README.md`, `docs/` | suíte completa, goldens, `draw` |

## Onda B - Itens e Skills (marco M2)
| # | Nível | Passo | Arquivos | Validação |
|---|---|---|---|---|
| B1 | rotineiro | 16 modelos novos em `PARTS`, `CORE_MODELS`/`ALL_MODELS`, campo `set`, `unique`; loja usa `CORE_MODELS` até o tier 3 | `game/parts.py`, `game/garage.py` | `test_garage`, `test_parts_v2.py` (pesos, sidegrade, stream do RNG idêntico) |
| B2 | complexo | Sets: bônus em `effective_attrs` (2/4/6 peças), `set_bonus_text` | `game/parts.py`, `game/garage.py` | `test_parts_v2.py` (tabela da spec), `test_garage` |
| B3 | complexo (sensível: save/migração) | **Garage v2**: `VERSION = 2`, `MIGRATIONS[1]`, `_robot`/`_piece` com `skills`, `look`, `modulo`, `items`, `cosmetics`, `cap`; `MAX_FLAGS` 128; `add_xp(cap)`; níveis até 15 | `game/garage.py` | `test_garage_v2.py` (migrar um save v1 real, sanitize de ids inválidos), `test_robot_save`, `test_campaign_save` (garage embutido) |
| B4 | rotineiro | 8º slot `modulo` em `parts.SLOTS`, `SLOT_NAMES`, equipar/desequipar, `mod_on` | `game/parts.py`, `game/garage.py` | `test_garage` |
| B5 | complexo | `skills.py`: dados das 16 skills, `TRIGGERS`, `compile_factors`, `effective_skills`, `skill_force` (valores provisórios) | `game/skills.py` | `test_skills.py` (cada skill compila, mods válidos, rank escala) |
| B6 | complexo | Motor: `Player.skills/f_base/f_var`, `Game.sk_on`, `tick_skills`, `kick`/`steal`/curva/`tk_ext` guardados; RNG próprio `sk_rng` | `game/soccer.py` | `test_skills_engine.py` (golden idêntico com flags desligadas; efeito de cada skill; MAX funciona sem FX; `ms_step` <= +0,006 ms) |
| B7 | rotineiro | FX de skills (dash, ímã, curva, escudo, overclock, recarga) via `pygame.draw`/sprites prontos | `game/soccer.py`, `game/robot_art.py` | `test_visual`, zero Surface |
| B8 | rotineiro | `match_entry` passa `skills` e `items`; aura de time (consumáveis); `user_F` soma `item_force` | `game/garage.py`, `game/campaign.py` | `test_campaign`, `test_garage` |
| B9 | complexo | `tests/calib_skills.py` e geração de `SKILL_FORCE`; `team_rating` soma `skill_force` com cap 4,0 | `tests/calib_skills.py`, `game/skills.py`, `game/garage.py` | rodar o script; metas da spec; `calib_robots --fit` |
| B10 | complexo | UI: 8 slots no layout (42 px), aba HABILIDADES (árvore), tooltips, linha "Força" no comparar | `game/robots_ui.py` | `test_robots_ui` (layout, zero Surface, cliques) |
| B11 | rotineiro | PH por nível, retroativo na campanha, `fx.skill/pts` em `story.REWARDS`/`apply_fx` | `game/garage.py`, `game/campaign.py`, `game/story.py` | `test_campaign`, `test_story` (fx válidos) |
| B12 | rotineiro | Consumáveis: itens, loja, Mochila nas telas de torneio/liga | `game/garage.py`, `game/robots_ui.py`, `game/campaign_ui.py` | `test_garage`, `test_campaign_ui` |
| B13 | rotineiro | Cosméticos: `look`, galeria, sprites (adesivo, antena, rastro) | `game/garage.py`, `game/robot_art.py`, `game/robots_ui.py` | `test_robots_ui`, `test_visual` |
| B14 | complexo | Segunda passada: as 6 skills restantes + árvore completa + relíquias/sets passivos | `game/skills.py`, `game/soccer.py` | `test_skills_engine.py`, `calib_skills.py` |
| B15 | complexo | Recalibração: `calib_campaign.py --grid` com skills e conferência de `sim_bias` (ajuste só se passar de 3 pts) | `tests/calib_campaign.py`, `game/campaign.py` | tabela final no docstring |
| B16 | rotineiro | Modo Robôs: skills ligadas com `mod_on` ao completar o tier 1; ajuste de loja | `game/garage.py`, `game/robot_league.py` | `calib_robots.py`, `test_robot_balance` |
| B17 | mecanico | Documentação: README (skills, itens), `docs/specs/` | `README.md` | revisão |
| B18 | rotineiro | Fechamento da Onda B: suíte completa, goldens, `draw`, `ms_step`, tabela de calibração | - | tudo verde |

## Onda C - Campanha maior (marcos M3 e M4)
> **Estado (05/11/2026): C1-C18 prontos** na branch `feat/fase4-onda-c-estrutura`. Desvios do plano,
> todos documentados nos commits: o cap. 6 provisório do C2 virou rascunhos "em breve" até o conteúdo
> chegar; a Força dos Atos 2 e 3 ficou bem acima da spec (skills com teto 9,0 e o motor achatando acima
> de F ~85), então os ovr foram recalibrados no motor (C9/C12) e o SIMULAR ganhou uma correção para
> Força alta; a política passiva do balanço só cobre os Atos 1 e 2.
| # | Nível | Passo | Arquivos | Validação |
|---|---|---|---|---|
| C1 | complexo | `story.py` vira fachada; `story_a2/a3/side.py` vazios com `update()` dos dicts; `CHAPTERS` ganha `act`; `STORY_VERSION = 2`; ids existentes intocados | `game/story*.py` | `test_story` verde com `STORY_VERSION = 2` |
| C2 | complexo (sensível: save/migração) | **Campaign v2**: `VERSION = 2`; `MIGRATIONS[("v",1)]`, `MIGRATIONS[("sv",1)]` (cap. 5 node >= 4 -> cap. 6 node 0); campos `side`, `ng`, `endings`, `tower`; `_done_keys` com `side:`; limites `MAX_DONE*` e `STAT_KEYS`; epílogo vira nó do cap. 6 | `game/campaign.py`, `game/story.py` | `test_campaign_save`, `test_campaign_migration.py` (4 saves v1 reais) |
| C3 | complexo | Formatos `league` e `series`: `stages_of`, `_stage_team`, `STAGE_NAMES`, `_is_boss` por `boss_stages`, `group_league` n-times, `record_match`, `_tour` sanitize | `game/campaign.py`, `game/story.py` | `test_campaign.py` (novos testes de liga e série), `test_campaign_save` |
| C4 | complexo | Nós condicionais, `alt` de adversário, `ENDINGS`, `("count", prefixo, n)`, `Campaign.start_side`/`next_action` para sides | `game/campaign.py`, `game/story.py` | `test_campaign.py`, `test_story.py` (alcançabilidade com flags) |
| C5 | complexo | Mapa por Ato (abas Ato 1/2/3), nós por Ato, painel "MISSÕES" com unlock, telas de finais e galeria | `game/campaign_ui.py` | `test_campaign_ui` (zero Surface, 14 nós visíveis, cliques) |
| C6 | rotineiro | Dados Ato 2 parte 1: personagens/times/cenários novos (sem cenas), cap. 6 completo (cenas, torneio, recompensa) | `game/story_a2.py`, `game/story.py` | `test_story` (limites de texto), autoplay do cap. 6 |
| C7 | rotineiro | Cap. 7 (liga) e cap. 8 (playoffs): cenas, times, escolha B2 (`renova_limpex`), recompensas | `game/story_a2.py` | `test_story`, autoplay |
| C8 | rotineiro | Cap. 9 (série, clone, escolha B3) e `a2_fim` | `game/story_a2.py` | `test_story`, autoplay |
| C9 | complexo | Calibração do Ato 2: `calib_campaign.py` com os novos checkpoints (`TEAMS`/F por estágio), ajuste de `ovr` e F; economia (`TIER_MUL` 7 entradas, shop tiers 4-6, `xp_need` >= 10) | `game/story_a2.py`, `game/garage.py`, `tests/calib_campaign.py` | metas: regulares 58-66, SF 52-58, chefe 45-52 (tolerância +-4,6 do ruído do motor) |
| C10 | rotineiro | Cap. 10 e 11 (nós condicionais por `renova_limpex`, B4) | `game/story_a3.py` | `test_story`, autoplay nos 2 ramos |
| C11 | rotineiro | Cap. 12 e 13, 3 finais e créditos | `game/story_a3.py` | `test_story`, autoplay por final |
| C12 | complexo | Calibração do Ato 3 e dos 2 ramos de patrocínio (F_end do ramo A vs B dentro de +-0,7) | `game/story_a3.py`, `tests/calib_campaign.py` | tabela final |
| C13 | rotineiro | 14 missões secundárias (cenas, times, recompensas) | `game/story_side.py` | `test_story`, `test_campaign.py::test_side_*` |
| C14 | rotineiro | Recompensas de capítulo 6-13 (`rw_*`): recrutas, relíquias, módulos, `level_cap` | `game/story.py`, `game/campaign.py` | `test_campaign.py` |
| C15 | rotineiro | Rivais recorrentes: times evoluídos por capítulo, falas condicionais (`("flag", ...)`) | `game/story_a2.py`, `game/story_a3.py` | `test_story` |
| C16 | rotineiro | Venues por capítulo (tabela de torcida) e faixas de torcida por capítulo | `game/crowd.py`, `game/campaign_ui.py` | `test_campaign_ui` |
| C17 | complexo | Autoplay da campanha inteira (3 sementes, 2 ramos, 3 finais) com SIMQ e com partidas reais selecionadas | `tests/test_campaign_full.py` | alcança os 3 finais; F de cada capítulo dentro da curva |
| C18 | rotineiro | Fechamento da Onda C: README, calibração final (tabela no docstring), suíte e goldens | `README.md`, `docs/` | tudo verde |

## Onda D (opcional) - Pós-campanha
| # | Nível | Passo | Arquivos | Validação |
|---|---|---|---|---|
| D1 | complexo (sensível: save/migração) | NG+ (`c["ng"]`, `NG_SHIFT`, revanches sem diálogo longo, reset de nós preservando garage) e migração de saves terminados | `game/campaign.py`, `game/story.py` | `test_campaign.py`, `test_campaign_save` |
| D2 | complexo | Torre do Pó: 40 andares, modificadores de arena, marcos | `game/campaign.py`, `game/campaign_ui.py`, `game/soccer.py` | `test_campaign.py`, `test_campaign_ui` |
| D3 | rotineiro | Peças Míticas e cosméticos finais | `game/parts.py`, `game/story.py` | `test_garage` |

## Estratégia de testes
- **Arquivos novos**: `test_prefs.py`, `test_crowd.py`, `test_parts_v2.py`, `test_garage_v2.py`, `test_skills.py`, `test_skills_engine.py`, `test_campaign_migration.py`, `test_campaign_full.py`, `calib_skills.py`. Estendidos: `test_story`, `test_campaign`, `test_campaign_save`, `test_campaign_ui`, `test_robots_ui`, `test_portraits`, `test_visual`, `calib_campaign`.
- **Goldens**: em toda onda e a cada passo de motor (A3, B6, B14, D2): `golden --check` e `golden-new --check` devem dar 80/80.
- **Zero Surface por frame**: um helper único (contador de `pygame.Surface`) reutilizado por `test_crowd`, `test_campaign_ui`, `test_robots_ui`.
- **Autoplay da campanha**: `test_flow_full_campaign_by_clicks_reaches_ending` é ampliado; o `walk()` de `test_story` passa a enumerar ramos e finais (políticas "patroc", "independente", "secreto"), conferindo que toda cena é alcançável e todos os `ENDINGS` são atingíveis. Um autoplay guloso (`build_garage_for`) simula a campanha com semente fixa e confere F por capítulo.
- **Calibração**: `calib_campaign.py` (checkpoints novos + `--grid`), `calib_skills.py` e `calib_robots.py`; as tabelas finais são coladas nos docstrings, como já é feito.
- **Saves**: fixtures reais de saves v1 (garage e campanha) em `tests/fixtures/`; cada migração tem teste de ida e de save inválido (continua indo para `.bad` e nunca é sobrescrito sem confirmação).
- **Desempenho**: `sim_harness.py draw` com torcida, `run` com skills (`ms_step`), `test_draw_time_budget` por tela.

## Riscos e mitigação
| Risco | Mitigação |
|---|---|
| Torcida estoura o orçamento no WASM | atlas pré-renderizado, 90 blits no máximo, 3 LODs automáticos, opção OFF, desligada em MAX; medir no navegador (`pygbag`) já na A2 |
| Hooks da torcida/skills alteram a simulação e quebram os goldens | todos os hooks escrevem só em estruturas novas; RNG próprio; `tk_ext = 0.0` e `curve = 0.0` neutros; teste de determinismo com torcida ligada/desligada |
| Loja/RNG determinístico muda com modelos novos | `CORE_MODELS` preserva o stream; `ALL_MODELS` só a partir do tier 4 |
| Migração de save corrompe progresso | `MIGRATIONS` com `deepcopy`, sanitize por lista de campos, `.bad`, testes com saves reais; o Ato 1 nunca faz rewind por causa da migração |
| Build antigo em cache lê save v2 | trata como "bad" e preserva o texto; aviso no README |
| F não alcança a curva do Ato 2-3 | levers explícitos (nível 15, recrutas, sets, skills) validados na C9/C12; se faltar, reduz F_end em vez de inventar poder |
| Skills mudam a dificuldade e quebram `sim_bias` | `skill_force` em F com cap 4,0; `calib_skills`/`--grid`; limite de 3 pts no desvio SIM x motor |
| Roteiro cresce além do que o dev escreve | entregar capítulo a capítulo (cada um jogável, com C9 e C12 como portões); sides por último |
| `story.py` fica grande (>3.500 linhas) e lento no WASM | dividir em módulos de dados; o parse ocorre uma vez |
| UI de bancada/mapa lotada | layout testado por teste (`test_robots_ui`, `test_campaign_ui`) e capturas; mapa por Ato |
| Ramos duplicam o trabalho de calibração | variantes trocam identidade, não ovr (+-1); autoplay nos 2 ramos |
| Memória do atlas e dos cenários no WASM | LRU de 3 arenas e 6 cenários; tamanho medido em `test_crowd` |

## Decisões para o dev (com recomendação)
1. **Tamanho da campanha.** Opções: A) só Ato 2 (4 caps.), B) Ato 2 + 3 (14 unidades, ~125 cenas novas) como no plano, C) Ato 2 + 3 + NG+/Torre. **Recomendo B**, entregue capítulo a capítulo (M3 jogável no cap. 9), e deixar D (NG+/Torre) para depois do M4.
2. **Skills automáticas (IA) ou o jogador escolhe a tática?** **Recomendo automáticas** (a IA aciona pelos gatilhos), mais uma única preferência de time na pausa/pré-jogo ("Ofensivo / Equilibrado / Defensivo", que só muda quais gatilhos têm prioridade). O jogador não controla o robô em partidas de campanha/robôs (são automáticas), então tática manual dobraria UI e testes.
3. **Haverá som algum dia?** **Recomendo "não nesta fase"**: manter o "som visual" (onomatopeias, telão, locutores). Se vier som, que seja uma Fase 6 opcional com uma abstração `sfx.play(id)` já chamada pelos mesmos hooks da torcida (assim o custo futuro é trocar `crowd.event` por `crowd.event + sfx`).
4. **Campanha atual vira Ato 1 ou é reescrita?** **Recomendo Ato 1 intacto** (ids estáveis, calibração pronta, saves preservados). Reescrever custa calibrar de novo e quebra saves.
5. **Torcida também no Amistoso e no Modo Robôs?** **Recomendo sim, versão leve**: `bairro` (30 pessoas, 2 fileiras) no Modo Robôs e no Amistoso; carreira de clubes pode ganhar `estadio` por divisão depois. Custo desprezível e melhora a percepção do jogo todo. Amistoso (modos 1/2) só desenha a torcida se `prefs` permitir; os goldens não são afetados (`venue=None` no caminho deles).
6. **Skills e itens também no Modo Robôs?** **Recomendo sim, ligados por `mod_on` ao completar o tier 1** (uma só base de código). O custo é recalibrar `calib_robots` (já planejado em B16).
7. **Ramo "renova_limpex" muda a economia?** **Recomendo +20% de sucata vs +15% de XP**, validado por autoplay para fechar o Ato 3 com F equivalente (+-0,7). Se o jogador achar o ramo "independente" mais fraco, ajusta-se só esses dois números.
8. **Nível máximo 15 só na campanha ou também no Modo Robôs?** **Recomendo só na campanha** (`Garage.cap`), para não deslocar a liga já calibrada.
9. **Ordem das ondas.** **Recomendo A -> B -> C** (visual primeiro dá um ganho percebido imediato e é o item mais isolado do motor; B depende de A só nos FX; C precisa de B para calibrar as skills no Ato 2). Alternativa: C1-C4 (estrutura) em paralelo com B, já que não dependem uma da outra.
10. **Mundial 5 e Superliga na mesma curva de F?** Está no plano; se a Onda B mostrar que F alto fica muito caro, a opção é reduzir o Ato 3 de 4 para 3 capítulos (fundir 11 e 12), sem mexer no Ato 2.

---
Arquivos de referência lidos (todos sob /home/bruno/soccerpy): README.md; game/soccer.py, robots.py, parts.py, garage.py, robot_league.py, story.py, campaign.py, campaign_ui.py, portraits.py, robots_ui.py; tests/sim_harness.py, calib_campaign.py, test_campaign_ui.py, test_story.py, test_campaign_balance.py.
