# Roadmap - Copa Aspirador

## 1. Estado atual

Tabela original do planejamento (HEAD fd5e17b); a linha da Fase 4 está atualizada.

| Fase | Conteúdo | Situação |
|---|---|---|
| 1 | 6 chassis, 8 atributos, bateria, arena neon | pronta |
| 2 | Garagem: 14 peças (7 slots x 2 modelos, 4 raridades, upgrade 0-5), XP/nível até 10, loja, liga de 6 times (Modo Robôs) | pronta |
| 3 | Campanha "A Garagem do Vô": Prólogo + 5 capítulos + epílogo, 53 cenas / 626 falas, 27 times, 12 personagens, 6 escolhas, torneios (grupo de 4 + mata-mata), chefes com pity, treino, save próprio `soccerpy_campaign_v1` (v1, sv1) | pronta e jogável |
| 4 (nova) | **Campanha Expandida**: torcida + desenhos detalhados, itens/skills, campanha 3 atos | Ondas A (visual, torcida, câmera de estádio), B (peças, sets, módulo, 16 skills, itens, cosméticos) e C (campanha Prólogo + 13 capítulos em 3 Atos, 3 finais, 14 missões, calibrada no motor) e D (NG+ "Turnê Lendária", Torre do Pó, peças Míticas) prontas e publicadas |
| 5 | Editor de firmware (regras da IA em blocos) | planejada (era a antiga Fase 4) |

Números do código hoje:
- ~17,9 mil linhas (game ~9,5 mil, tests ~8,4 mil).
- Desenho em partida: 0,7 ms/frame.
- Motor: 0,037 ms/step.
- Goldens `golden` e `golden-new`: 80/80.
- Calibração da campanha: F 44 -> 66 em 6 unidades. Metas medidas no motor: regulares 58-66%, SF 52-58%, chefes 45-52%.

## 2. O que é a Fase 4 - "Campanha Expandida"

Quatro frentes entregues em ondas jogáveis:

1. **Onda A - Visual e torcida.** Arquibancadas, multidão pré-renderizada com reações por evento, placas de LED, telão com locutores, onomatopeias. Robôs com peças visíveis, Orbital/Titã redesenhados, animações. Retratos e cenários com mais expressões, camadas e luz.
2. **Onda B - Itens e Skills.** Catálogo de peças de 14 para ~36 modelos, sets, relíquias únicas, 8º slot "Módulo", consumáveis de partida, cosméticos, nível máximo 15 na campanha. 16 skills de robô (passivas, ativas acionadas pela IA, condicionais), com FX. Garage v2 com migração.
3. **Onda C - Campanha maior.** A campanha atual vira o **Ato 1**, sem reescrever. Entram o Ato 2 (Superliga, caps. 6-9) e o Ato 3 (Copa dos Campeões, caps. 10-13), 3 finais, missões secundárias, rivais recorrentes, formatos novos de torneio (liga e série de duelos), mapa por Ato, NG+ e Torre.
4. **Onda D (opcional) - Pós-campanha.** NG+ "Turnê Lendária" e Torre do Pó. **Pronta** (D1-D3; save v3;
   modificadores de arena atrás de `arena=None` no motor, goldens 80/80).

## 3. Objetivos mensuráveis
- Duração da campanha: de ~6 unidades (~5-6 h) para 14 unidades + 14 missões secundárias (~14-18 h).
- Conteúdo: cenas 53 -> ~175, falas 626 -> ~2000, times 27 -> ~60, personagens 12 -> 19, escolhas 6 -> ~26, finais 1 -> 3.
- Peças 14 -> ~36 modelos + 5 sets + 6 relíquias; skills 0 -> 16; consumáveis 6.
- Torcida em todas as partidas assistidas, de 12 pessoas (quadra) a ~520 (Mundial/Coliseu).
- Custo de desenho: partida em 1x <= 1,5 ms no desktop e <= 3 ms estimado no WASM; em MAX o custo extra é 0.
- Dificuldade mantida nas metas calibradas em todos os 14 capítulos, nos dois ramos de patrocínio.

## 4. Fora de escopo
- Áudio ou música (decisão adiada; ver "Decisões para o dev"). Só "som visual".
- Imagens ou fontes externas. Tudo continua desenhado por código.
- Editor de firmware (Fase 5), multiplayer online, tradução.
- Mudar o motor legado, os goldens, a carreira de clubes (`career.py`) ou os modos 1/2.
- Mudar a chave dos saves (`soccerpy_robots_v1` e `soccerpy_campaign_v1` continuam; só o campo `v` interno sobe).

## 5. Princípios (o que não pode quebrar)
1. **Goldens 80/80** (`golden` e `golden-new`) em toda onda. Todo código novo do motor fica atrás de flags (`self.sk_on`, `self.crowd`), com valor neutro quando ausente. Nenhuma chamada nova ao `random` global fora de partidas com skills.
2. **Calibração pelo motor real.** Skills e itens entram em `team_rating` como `skill_force` (pontos de F). Isso mantém `sim_bias(O)` válido; `calib_campaign.py` e o novo `calib_skills.py` confirmam.
3. **Saves**: sempre versionados, com sanitize por lista de campos, migração `MIGRATIONS`, nunca sobrescrever save inválido sem confirmação. Um build antigo lendo save novo trata como "bad" (nunca apaga).
4. **IDs estáveis**: ids de cena, personagem, time, torneio e recompensa existentes não mudam. A migração só acrescenta.
5. **Zero `pygame.Surface` por frame**. Pré-render, cache, blit de sub-áreas. Tudo novo respeita `test_60_frames_every_screen_zero_surface_and_cache`.
6. **Orçamento**: partida em MAX tem ~12 ms/frame; desenho sobe no máximo +0,8 ms (desktop). Torcida desligada em MAX. Degradação automática por LOD.
7. Só pygame + stdlib; `Font(None)`; textos Latin-1; tela 1100x700.
8. Ramificações mudam QUEM e O QUÊ (adversário, falas, recompensas, aliados), nunca a Força O além de +-1.

## 6. Tamanho estimado

| Onda | Passos | Arquivos novos | Linhas de código | Linhas de teste |
|---|---|---|---|---|
| 0 preparação | 4 | 0 | ~150 | ~100 |
| A visual/torcida | 14 | `crowd.py`, `robot_art.py`, `prefs.py` | ~1.600 | ~450 |
| B itens/skills | 18 | `skills.py` (+ extensões em `parts.py`/`garage.py`) | ~2.100 | ~1.300 |
| C campanha | 18 | `story_a2.py`, `story_a3.py`, `story_side.py` | ~1.000 código + ~2.900 dados | ~1.000 |
| D pós-campanha | 3 | - | ~400 | ~200 |
| **Total** | **~57** | **~9 de jogo + ~9 de teste** | **~5.250 + 2.900 de roteiro** | **~3.050** |

## 7. Ordem e marcos jogáveis
- **M1 (fim da Onda A)**: partida com estádio, torcida reagindo e robôs detalhados; nenhuma mudança de regra.
- **M2 (fim da Onda B)**: peças novas, módulos, skills e consumáveis jogáveis no Modo Robôs e na campanha (Ato 1 inalterado em dificuldade); garage v2.
- **M3 (Onda C parcial)**: Ato 2 jogável (caps. 6-9), mapa por Ato, missões secundárias.
- **M4**: Ato 3 + 3 finais; campanha completa.
- **M5 (opcional)**: NG+ e Torre. Atingido e publicado (Onda D).

## 8. Definição de pronto de cada onda
Suíte inteira verde, `golden` e `golden-new` 80/80, `test_*_ui` com zero Surface por frame, `draw_ms` dentro do orçamento, README e `docs/` atualizados, `calib_campaign` com as metas na tolerância.
