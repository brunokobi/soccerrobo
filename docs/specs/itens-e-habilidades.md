# Spec - Itens e Skills

## 1. Catálogo de peças (`parts.py`)

**Estado atual**: 7 slots (`motor, bateria, parachoque, chutador, succao, sensor, chip`) x 2 modelos (um "equilibrado" `heat 0` e um "agressivo" com `heat` > 0). Somatório de pesos: equilibrado ~1,3-1,4; agressivo ~1,6-1,9 com calor 0,25-0,35.

**Regra de design dos modelos novos**: sidegrade, nunca estritamente melhor. Equilibrado: Σw 1,3-1,5, `heat` 0. Agressivo: Σw 1,6-1,9 e `heat` 0,25-0,50. Especialista (pesos em 3 atributos): Σw 1,5.

**Modelos novos (+16, total 30 modelos em 7 slots)**:

| Slot | Modelo | Pesos | heat | Tipo | Set |
|---|---|---|---|---|---|
| motor | Servo Ágil | ace 1,0, vel 0,4 | 0 | equilibrado | Faxineiro |
| motor | Ímã Linear | vel 1,5, ace 0,5 | 0,45 | agressivo | Plasma |
| bateria | Célula Solar | bat 1,2, vel 0,1 | 0 | equilibrado | Faxineiro |
| bateria | Célula Fusão | bat 1,1, ace 0,8 | 0,5 | agressivo (pico) | Plasma |
| parachoque | Espuma Viscoelástica | def 0,7, ctr 0,7 | 0 | especialista | Faxineiro |
| parachoque | Placa Reativa | def 1,5, ctr 0,3 | 0,4 | agressivo | Titã |
| chutador | Mola Dupla | chu 0,8, vis 0,4, ctr 0,2 | 0 | especialista | Dojo |
| chutador | Railgun de Bolso | chu 1,6, ctr 0,3 | 0,45 | agressivo | Plasma |
| succao | Escova Dupla | ctr 0,8, vel 0,3, def 0,3 | 0 | especialista | Faxineiro |
| succao | Vórtice | ctr 1,5, def 0,3 | 0,35 | agressivo | Titã |
| sensor | Câmera Dupla | vis 0,7, qi 0,5, ctr 0,2 | 0 | especialista | Dojo |
| sensor | Sonar Quântico | vis 1,5, qi 0,3 | 0,35 | agressivo | Plasma |
| chip | Chip Tático | qi 0,8, ctr 0,5 | 0 | equilibrado | Dojo |
| chip | Chip Zero | qi 1,6, vis 0,4 | 0,4 | agressivo (só loja Lendária/história) | Limpex |
| motor | Motor Torque | vel 0,6, ace 0,6, def 0,3 | 0 | especialista | Titã |
| chutador | Solenoide Duplo | chu 1,1, ctr 0,3 | 0,15 | meio-termo | Limpex |

**Decisão do dev (B6-B9): Célula Fusão é sidegrade.** Com os pesos originais (bat 1,5, ace 0,4, def 0,2, heat 0,5) ela empatava em BAT líquido e dominava a Célula Longa/Rápida em todas as raridades. Agora é uma bateria de **pico**: muita ACE (arranque), com calor alto que deixa a BAT líquida abaixo de todas as baterias (drena mais). O teste de sidegrade (`test_parts_v2`) vale para todos os modelos, sem exceção.

**Cuidado com a loja determinística**: `garage.refresh_shop` e `match_rewards` usam `r.choice(parts.MODELS)` e tests dependem do fluxo do RNG. Manter `parts.MODELS` (14 modelos originais) como `CORE_MODELS`; criar `ALL_MODELS` com os novos. A loja usa `CORE_MODELS` no tier < 4 e `ALL_MODELS` a partir do tier 4; assim, o stream do RNG dos testes antigos não muda.

## 2. 8º slot: Módulo (`modulo`)
`parts.SLOTS` ganha `"modulo"`. Um módulo é uma peça com `PARTS[m]["skill"] = id` e `w = {}`; ele concede 1 skill; a raridade define o rank (Comum 1, Rara 1, Épica 2, Lendária 3) e o `up` do upgrade incrementa o efeito (não o rank). Cada skill tem 1 módulo. Dá 12 módulos (ver tabela de skills).

Impacto de UI: `robots_ui.draw_bench` desenha 7 slots a y = 182 + i·50 (altura 46), terminando em 528; as ações começam em 548. Com 8 slots, o espaçamento passa a 42 px (altura 38), terminando em 180 + 7·42 + 38 = 512; ajuste de `PIECE_ROWS` não é necessário. Teste de layout em `test_robots_ui`.

Modo Robôs: o slot Módulo só aparece/equipa com `flags["mod_on"]` (liberado ao completar o tier 1) para não desbalancear a liga; na campanha, o flag liga no capítulo 6 (derivado de `reward:rw_5`).

## 3. Sets (bônus de conjunto)
Cada modelo tem `set` opcional. `effective_attrs` conta peças equipadas por set (qualquer raridade) e aplica bônus de atributo. Cálculo antes do multiplicador de overclock e dentro de `raw[a]`.

**Decisão do dev (B6-B9): faixas 2/3/4 peças** (com uma peça por slot as faixas 4/6 eram inalcançáveis). As magnitudes da coluna "4 peças" abaixo valem para **3 peças**, e as da coluna "6 peças" (a de 4 + passiva) valem para **4 peças** (`parts.SET_TIERS = (2, 3, 4)`). Titã e Dojo só têm peças em 3 slots: a passiva deles (faixa 4) continua inalcançável num robô.

| Set | Peças | 2 peças | 4 peças (agora 3) | 6 peças (agora 4) |
|---|---|---|---|---|
| Faxineiro | Servo Ágil, Célula Solar, Espuma Viscoelástica, Escova Dupla, Escova de Sucção, Borracha | CTR +2 | CTR +3, BAT +3 | + passiva "Faxina Total" (`tackle` x1,1 e `reach` +3) |
| Plasma | Ímã Linear, Célula Fusão, Railgun de Bolso, Sonar Quântico, Canhão de Plasma, Turbina | CHU +2 | CHU +3, VEL +3 | + passiva "Sobrecarga" (`kick_pow` x1,06; `bat_drain_mul` x1,08) |
| Titã | Placa Reativa, Vórtice, Motor Torque, Blindado, Vácuo Turbo | DEF +3 | DEF +4, CTR +3 | + passiva "Muralha de Aço" (`shield` x0,92) |
| Dojo | Mola Dupla, Câmera Dupla, Chip Tático, Chip de CPU, Infravermelho | QI +2 | QI +3, VIS +3 | + passiva "Mente Zen" (`dec_err` x0,6) |
| Limpex | Chip Zero, Solenoide Duplo, Radar LiDAR, Célula Rápida | VEL +2 | VEL +3, ACE +3 | + passiva "Impecável" (`speed` x1,02, `gk_save` +0,03) |

Efeito estimado: um set completo (6 peças) em um robô vale ~+1 F de equipe por robô-set se os 5 titulares usarem; com 2-3 peças por robô fica em ~+0,4 F. O bônus de atributo já entra em `effective_attrs`, portanto em F automaticamente; só as passivas dos 6 peças precisam de `skill_force` (0,2-0,3 cada).

## 4. Relíquias (peças únicas, `unique: true`)
Lendárias de potência fixa 22 (acima da Lendária comum 19), não compráveis; vêm de recompensas de capítulo e missões. Cada uma tem uma passiva própria (usa o mesmo motor de skills).

| Relíquia | Slot | Efeito base | Passiva |
|---|---|---|---|
| Rodinha Esquerda do Zé | motor | vel 1,2, ace 0,6 (heat 0) | "Rolando Sozinha": 1 vez por partida, a rodinha cai e o robô ganha `speed` x1,25 por 4 s (comédia + vantagem) |
| Chip do Vovô | chip | qi 1,3, vis 0,4 | "Instinto do Vô": `dec_err` x0,5; `think_mul` x0,92 |
| Fita Crepe Reforçada | parachoque | def 1,3, ctr 0,5 | "Remendo": após sofrer um desarme, ganha `shield` x0,7 por 2 s |
| Pão de Queijo Térmico | bateria | bat 1,6 | "Calor de Forno": `bat_regen_mul` x1,3 |
| Chinelo Estrutural | sucção | ctr 1,2, def 0,5 | "Chinelada de Honra": 1 chute por partida com `kick_pow` x1,35 e `shot_err` x0,3 |
| Meia do Prof. Ambrósio | sensor | vis 1,3, qi 0,5 | "Faro de Meia": `gk_lead` +0,15 e `pass_range` x1,1 |

## 5. Consumáveis de partida
Campo novo `Garage.items = {id: qtd}` (máx 9 de cada). Antes de uma partida da campanha ou do Modo Robôs, o jogador pode carregar até 2 na "Mochila" (tela do torneio e da liga). São consumidos ao assistir ou simular. Efeitos usam a mesma máquina de skills (aura de time); cada um tem `force` (pontos de F) que entra em `user_F` ao simular, para o SIMULAR continuar válido.

| Item | Preço | Efeito (duração = partida toda, salvo nota) | force (F) |
|---|---|---|---|
| Bateria Extra | 90 | `bat_drain_mul` x0,85 no time | +0,6 |
| Cera Turbo | 120 | `speed` x1,05 e `accel` x1,08 no time | +0,9 |
| Café do Prof. | 100 | `think_mul` x0,9 no time | +0,5 |
| Fita Isolante | 110 | `gk_save` +0,10 no goleiro | +0,6 |
| Pilha Reserva | 140 | 1 vez: restaura a bateria do robô a 1,0 quando < 0,2 (automático, só 1 robô) | +0,5 |
| Spray Anti-Poeira | 150 | `shield` x0,92 no time | +0,7 |

Itens do chefe e da missão: 1 de cada tipo de recompensa. Venda não permitida.

## 6. Cosméticos
Campo por robô: `look = {"decal": id, "trail": id, "antenna": id}`, mais `Garage.cosmetics = [ids]` (desbloqueados). Só visual (sem efeito no motor):
- **Adesivos** (`decal`): estrela, raio, pão de queijo, chinelo, caveira, coração (6).
- **Rastro da bola** (`trail`): neon, fogo, arco-íris, estrelas (4).
- **Comemoração de gol** (por time): confete padrão, bolo, chinelo voando, fogos (4).
- **Faixas de torcida** (texto até 16 chars, Latin-1): texto do jogador, mostrado na arquibancada.
- Desbloqueio: recompensas de side e de final, conquistas (12): "Primeiro gol", "5 vitórias seguidas", "Campeão sem perder", "Todas as fitas", etc. Guardadas em `flags` (`ach_*`) ou em `cosmetics`.

## 7. Sistema de Skills (habilidades dos robôs)

### 7.1 Conceito
Cada robô pode ter até **3 skills equipadas** (limite de "carga" 6: passiva custa 1, ativa 2, lendária 3). As ativas são acionadas pela IA do próprio motor quando o gatilho vale (o jogador não controla; ver decisão). Tipos:
- **P (passiva)**: modifica os fatores do robô durante toda a partida (aplicada em `Player.__init__`).
- **A (ativa)**: gatilho + duração + recarga + custo de bateria; troca os fatores por uma variante enquanto dura.
- **C (condicional)**: passiva que liga só quando uma condição vale (ex.: perto do gol).

### 7.2 Catálogo (16 skills)
`mods` usam os nomes de `robots.Factors` mais `spd`. `mul` multiplica, `add` soma. Rank 1/2/3 escala a magnitude por (1, 1,25, 1,5) e a recarga por (1, 0,9, 0,8). `dur` e `cd` em segundos de partida; custo `bat` é fração de bateria (0-1).

| id | Nome | Tipo | Papéis | Gatilho (avaliado a ~10 Hz) | Efeito (rank 1) | dur | cd | bat | FX |
|---|---|---|---|---|---|---|---|---|---|
| `arrancada` | Arrancada | A | ATT/MID/DEF | tem a bola, sem adversário a menos de 80 px à frente, bat > 0,35 | `spd` x1,35, `accel` x1,6 | 1,2 | 9 | 0,10 | rastro de imagens residuais + faíscas, letreiro "ZOOM" |
| `succao` | Sucção Magnética | A | MID/DEF/ATT | bola solta a < 90 px, velocidade da bola < 280, é o perseguidor | `reach` +10, `catch_speed` x1,4, `fumble` x0,3; puxa a bola 120 px/s² | 1,5 | 12 | 0,08 | arcos concêntricos azuis |
| `curva` | Chute em Curva | A | ATT/MID | ao chutar a < `shoot_range`, goleiro fora da linha | bola ganha curva ±70°/s por 0,8 s; `shot_err` x0,6; `kick_pow` x1,05 | 0,8 | 10 | 0,06 | rastro curvo magenta |
| `muralha` | Muralha | A | DEF/GK | bola vindo para o gol a < 220 px com adversário com a bola na zona | `tackle` x1,5, `spd` x0,85, raio de desarme +6 px | 2,0 | 11 | 0,08 | anel de escudo |
| `leitura` | Leitura de Jogo | P | MID/ATT/GK | sempre | `pass_range` x1,15, `lane_margin` x0,85, `gk_lead` +0,1, `think_mul` x0,9, `dec_err` x0,7 | - | - | 0 | ícone discreto |
| `poupanca` | Poupança | P | qualquer | sempre | `bat_regen_mul` x1,25, `bat_drain_mul` x0,92 | - | - | 0 | nenhum |
| `recarga` | Recarga Rápida | A | qualquer | bat < 0,25 e velocidade < 25% | `bat_regen_mul` x3 | 1,5 | 20 | 0 | cruz verde |
| `overclock` | Overclock Controlado | A | qualquer | placar <= empate e minuto >= 60, ou bat > 0,7 com bola no terço de ataque | `spd` x1,15, `accel` x1,15, `kick_pow` x1,10, `bat_drain_mul` x1,5; depois 3 s de cansaço (`spd` x0,9) | 6,0 | 25 | 0 | halo vermelho |
| `blindagem` | Blindagem Inercial | A | DEF/MID | tem a bola e adversário a < 55 px | `shield` x0,6, `spd` x0,9 | 1,5 | 10 | 0,05 | anel dourado |
| `drible` | Drible Giratório | A | ATT/MID | pressionado por >= 1 adversário a < 45 px com a bola | `shield` x0 (não perde a bola) | 0,5 | 8 | 0,07 | anel girando |
| `elastica` | Defesa Elástica | A | GK | chute vindo a > 450 px/s, a < 260 px, na direção do gol | `gk_save` +0,25 (máx 0,95), `gk_speed` x1,3 | 1,0 | 6 | 0 | luvas piscando "!!" |
| `pressao` | Pressão Alta | A | MID/ATT | adversário com a bola no próprio terço defensivo | `spd` x1,2, `tackle` x1,3 | 3,0 | 15 | 0,10 | faíscas laranja |
| `choque` | Choque Elétrico | A | DEF | após ganhar a bola com sucesso | o adversário desarmado fica 0,5 s a mais sem poder dominar | 0 (efeito imediato) | 12 | 0,05 | raio curto |
| `matador` | Instinto Matador | C | ATT | a < 180 px do gol adversário | `shot_err` x0,8, `kick_pow` x1,05 | enquanto vale | 0 | 0 | brilho no sensor |
| `lancador` | Lançador | P | GK | sempre | `pass_range` x1,4 | - | - | 0 | nenhum |
| `lider` | Líder | P (aura) | qualquer (só 1 por time) | sempre | para os titulares: `speed` x1,02, `think_mul` x0,97 | - | - | 0 | faixa de capitão |

Skills de relíquia e de set (da seção 3 e 4) usam o mesmo motor: "Rolando Sozinha", "Chinelada de Honra", "Instinto do Vô", "Remendo", "Calor de Forno", "Faro de Meia" (relíquias) e "Faxina Total", "Sobrecarga", "Muralha de Aço", "Mente Zen", "Impecável" (sets).

### 7.3 Como se ganham
1. **Módulo (slot 8)**: cada skill tem um módulo; rank pela raridade. Fonte principal em loja, drops e recompensas.
2. **Árvore de habilidades**: cada nível a partir do 2 dá 1 ponto (PH); o nível máximo é 10 no Modo Robôs e 15 na campanha. A árvore tem 3 ramos por papel (Ataque, Controle, Defesa), 4 camadas por ramo; cada nó custa 1-3 PH. Nós liberam skills por rank (ex.: ramo "Defesa": `muralha` r1 (1 PH), `blindagem` r1 (2), `muralha` r2 (2), `choque` (3)). Um robô sem módulo pode equipar as skills que aprendeu.
3. **História**: `REWARDS`/`fx` ganham a chave `skill` (`{"robot": "hero", "id": "arrancada", "rank": 1}`) e `pts` (pontos de habilidade extras).
4. **Treino**: partidas de treino dão +1 PH a cada 5 jogadas (`stats["trained"]`), no máximo 5 por robô.
5. **Missões**: `s_xadrez2`, `s_ogawa`, `s_clone` entregam módulos; relíquias vêm de `s_fita3` e `s_fita4`.

**Ordem de entrega recomendada** (reduz risco): MVP = módulos + recompensas de história (10 skills: `arrancada`, `succao`, `curva`, `muralha`, `leitura`, `poupanca`, `recarga`, `elastica`, `matador`, `overclock`); árvore e as outras 6 numa segunda passada da Onda B.

### 7.4 Dados (módulo novo `game/skills.py`, puro, sem pygame)
```python
SKILLS = {
  "arrancada": {"name": "Arrancada", "kind": "A", "roles": ("ATT", "MID", "DEF"), "load": 2,
                "trigger": "carry_free_lane", "dur": 1.2, "cd": 9.0, "bat": 0.10,
                "mods": {"spd": ("mul", 1.35), "accel": ("mul", 1.6)},
                "ranks": (1.0, 1.25, 1.5), "fx": "dash",
                "text": "Acelera com a bola quando ha espaco livre.", "force": (0.5, 0.7, 0.9)},
  ...
}
TRIGGERS = {"carry_free_lane": fn(game, p) -> bool, ...}   # funcoes puras sobre o estado do Game
SET_BONUS = {...}      # tabela da secao 3
ITEMS = {...}          # consumaveis da secao 5
TREE = {"ATT": [...], "MID": [...], "DEF": [...]}  # nos: {"id","skill","rank","cost","needs":[ids]}
def compile_factors(base_factors, skill_ids_with_rank) -> dict[id, Factors]: ...
def skill_force(robot_skills) -> float: ...   # soma de force por skill/rank, cap por robo
LOAD_MAX = 6
```
`SKILL_FORCE` por skill/rank é gerado por `tests/calib_skills.py` (seção 9) e colado em `skills.py`, como a tabela de `SIM_BIAS` em `campaign.py`.

Texto: Latin-1, nomes <= 18 chars, descrição <= 60 chars.

## 8. Integração no motor (sem quebrar goldens)

**Princípio**: nada muda na trilha de partida legado/carreira/amistoso. O motor só liga skills se alguma entrada de elenco trouxer `skills`.

Mudanças em `soccer.py` (todas guardadas por flag):
- `Player.__init__`: `self.skills = tuple(e.get("skills", ()))`, `self.f_base = self.f`, `self.f_var = {}`, `self.sk_state = {}`, `self.spd_base = self.spd`. Para cada skill passiva, `self.f` já nasce modificado (compilado uma vez). Para cada ativa, `f_var[id]` é uma cópia pré-calculada de `Factors` (22 floats por variante, ~15 variantes por time, desprezível).
- `Team.__init__`: passa `skills` do dict de entrada (`e.get("skills")`) junto com `attrs`, `pid`, `paint`.
- `Game._begin_match`: `self.sk_on = any(p.skills for t in teams for p in t.players)`; `self.sk_rng = random.Random(20261)` (RNG próprio, como `fx_rng`); `self.sk_tick = 0`; `self.consumables = home.get("items")` aplicado como aura de time na criação.
- `update_play(dt)`: `if self.sk_on: self.tick_skills(dt)` logo após `tick_timers` (antes da IA, para o efeito valer no mesmo step).
- `tick_skills`: a cada step decrementa `cd` e `dur`; a cada 6 steps (escalonado por jogador) avalia o gatilho dos skills ativos prontos (`cd <= 0`, `bat >= custo + 0,05`, GCD de 1,5 s entre skills do mesmo robô). `start_skill`: `p.f = p.f_var[id]; p.spd = p.f.speed; p.bat -= custo`; `end_skill`: restaura `p.f = p.f_base; p.spd = p.spd_base`. Um skill ativo por robô por vez.
- `kick()`: `if self.sk_on and p.skills: self.sk_on_kick(p, d)` para `curva` e `Chinelada` (altera `b.curve` e usa `shot_err`). `Ball.curve = 0.0` por padrão; `update_ball` ganha `if b.curve: b.vel = b.vel.rotate(b.curve * dt); b.curve *= 0.0 if t > 0.8`. Quando `curve == 0.0` o `if` é falso e a bola nem passa por `rotate`.
- Raio de desarme: `PR*2+4` vira `PR*2+4+q.tk_ext` (`tk_ext = 0.0` por padrão: o valor `x + 0.0` é exato em ponto flutuante e não muda nenhum resultado).
- `ball_interactions` (desarme com sucesso): `if self.sk_on: self.on_steal(q, o)` para `choque`.
- Nenhum `random.random()` global novo: o RNG novo é `sk_rng`, e as skills são determinísticas; só `Instinto Matador`/`curva` usam `sk_rng` para a direção da curva.
- `fx_ok()` continua falso em MAX, mas as skills **continuam funcionando em MAX** (afetam a simulação); só os FX visuais dependem de `fx_ok()`.

**Goldens**: `golden` e `golden-new` usam `start_career_match` com tuplas `(nome, ovr)`: `skills` ausente, `sk_on` False, nenhum RNG novo, `tk_ext = 0.0`, `curve = 0.0`. Teste obrigatório `tests/test_skills_engine.py::test_golden_unchanged_flags_off`: roda `golden --check` e confere 80/80. Mais um teste que roda 20 partidas com `skills=()` explícito e compara o placar com um time sem a chave.

**Custo**: `tick_skills` só roda se `sk_on`. Meta: <= +0,006 ms/step (+16% sobre 0,037) com 10 robôs e 3 skills cada. Medir com o harness (`run` com skills) e documentar.

## 9. Calibração
1. **`skill_force`**: novo `tests/calib_skills.py`. Para cada skill (e rank), joga N = 200 partidas no motor com TUNING_ROBOTS (time A com a skill nos 5 titulares versus time A sem), em F = 55, 65 e 75, contra o mesmo adversário calibrado. `delta = V+E/2 com skill - sem skill`. `force = delta / 1,8` (pontos de F por robô); média por papel. Meta por skill: |delta| entre 1,5 e 4,0 pontos de V+E/2 por robô (relíquias e Lendárias até 6). O script imprime a tabela e um `--write` gera o dicionário `SKILL_FORCE`.
2. **`team_rating`**: `team_rating(robot_list, pieces_by_id)` passa a somar `min(SK_CAP, mean(skill_force(robô)))` (cap `SK_CAP` = 4,0) ao F. Os itens consumíveis entram em `user_F` da partida (somados em `Campaign._match_action`, não em `rating()` global). O SIMULAR continua com `sim_match(user_F, O, rng)`: nada muda em `sim_bias`.
3. **Regressão**: `calib_campaign.py --grid` (F 66..82 x O 48..74, n = 200) e a tabela por checkpoint com garages que incluem skills (`build_garage_for` ganha skills em F alto). Meta: |SIM - motor| médio <= 3 pontos, máximo <= 6,5 (hoje 2,5/6,0).
4. **Modo Robôs**: `calib_robots.py --fit` roda de novo (a liga usa `team_rating` com skills) e confere que a simulação continua dentro da tolerância; se o desvio passar de 3, `ROBOT_SLOPE`/`SIM_K` ajustam, mas o motor não.
5. **Ramos e atos**: um autoplay "guloso" por semente (3 sementes) em cada ramo (`renova_limpex` sim/não), medindo F ao fim de cada capítulo contra a tabela da spec de campanha.

**Estado (B6-B9, 02/11/2026).** Motor: `Game.sk_setup/tick_skills/sk_eval/sk_start/sk_stop/sk_pre_shot/sk_on_kick/on_steal/ball_curve` em `soccer.py`, atrás de `sk_on` (só liga com `skills`, aura ou `items` no elenco: Modo Robôs com `mod_on` e campanha a partir de `rw_5`); goldens 80/80. Custo medido: ~0,0023 ms/step (10 robôs x 3 skills; meta 0,006). Diferenças da spec: o gatilho de chute (Curva/Chinelada) é avaliado em `ai_shoot` antes do erro de mira (para `shot_err` valer) e interrompe a ativa atual; a saída do Chute em Curva é pré-girada pela corda do arco (integrada com a física da bola) para a curva terminar no alvo. `SKILL_FORCE` calibrada por `tests/calib_skills.py` (tabela no docstring); `ROBOT_SK_CAP` = 20 (o teto que vale é o do time, 4,0). `calib_campaign --skills` (caps. 3 e 5): |SIM - motor| 2,8 pontos, `sim_bias` mantido. Skills sem efeito mensurável no motor atual: Lançador (nenhum), Curva, Muralha r1, Drible, Choque, Instinto Matador, Recarga, Calor de Forno, Mente Zen, Sobrecarga, Chinelada (candidatas a rebalanceamento na B14).

**Estado B14/B15/B16 (02/11/2026).** Segunda passada: todas as skills mudam o lance (teste
`test_every_skill_changes_the_play`). Mudanças de dados/motor (sempre atrás de `sk_on`, RNG `sk_rng`): Lançador
(lança por cima o mais adiantado, chance 0,12/reposição, bola `air`), Choque (paralisa 0,15 s, cd 20), Drible
(0,8 s, marcador fica `evade` 0,5 s sem desarmar), Matador (220 px, mira `aim` +0,02), Curva (`kick_pow` x1,2,
`aim` +0,15), Muralha (GK ganha `gk_save` +0,08), Recarga (bat < 0,6 parado: +0,10 e arranque), Elástica
(+0,07/x1,08), Líder (x1,014/x0,98), Sucção (ímã move bola parada), Pressão (bat 0,05, `tk_ext` 4), e as
especiais Calor de Forno, Faro de Meia, Mente Zen, Instinto do Vô, Sobrecarga (passiva de velocidade) e
Chinelada (mira). FX de evento: "DRIBLE!", "LANÇOU!", "ZZT!", bola alta, faixa de capitão. SKILL_FORCE nova no
docstring de `tests/calib_skills.py`. B16: com `mod_on` a loja traz 1 Módulo e 25% dos drops viram Módulo
(RNG derivado: sem `mod_on` nada muda).

## 10. Garage v2 (save)
- `garage.VERSION` 1 -> 2. `MIGRATIONS[1] = fn(dict) -> dict`: para cada robô, `slots["modulo"] = None`, `skills = {"learned": {}, "equipped": [], "pts": 0}`, `look = {}`; no topo, `items = {}`, `cosmetics = []`, `cap = 10`; `v = 2`. `FIELDS` ganha `items`, `cosmetics`, `cap`. A chave de armazenamento continua `soccerpy_robots_v1`.
- `_robot()` (sanitize): `skills.learned` é dict `{id: rank}` só com ids conhecidos e rank 1-3; `equipped` é subconjunto de `learned` (e de módulos equipados), sem duplicatas, com soma de `load` <= `LOAD_MAX`; `pts` int 0..99; `look` só com ids conhecidos; `level` 1..15 (e <= `cap`). `slots` aceita `modulo` (peça existente do slot certo).
- `_piece()`: aceita modelos novos e `unique` + `uid` (relíquias, máx 1 de cada), `lvl` 0..5.
- `MAX_FLAGS` 64 -> 128 e `MAX_INVENTORY` fica 200.
- `Garage.save()`: continua só gravando um estado que passa no sanitize sem perder nada.
- `effective_attrs` ganha o cálculo de sets e o `ocm` aplicado antes; uma função `effective_skills(robot, pieces_by_id)` junta: skills aprendidas equipadas + skill do módulo + passivas de relíquia e de set.
- `match_entry()` passa `"skills": effective_skills(...)` (lista de `(id, rank)`) ao motor.
- `add_xp(robot, amount, cap=MAX_LEVEL)`: `Campaign` passa `cap = garage.cap` (15 a partir do Ato 2); Modo Robôs usa 10.
- `match_rewards`: pontos de habilidade (PH) por nível ganho; `drop` usa `CORE_MODELS` (ver seção 1).
- Risco: build antigo (cache do navegador) lendo save v2 devolve "bad"; o texto cru vai para `.bad`, nunca é apagado. Documentar no README.

## 11. UI necessária
- **Bancada** (`robots_ui.draw_bench`): 8 slots com espaçamento 42 px; aba "HABILIDADES" à direita (a `draw_bench_right` já tem espaço sob o overclock) com a árvore em 3 colunas, nós clicáveis (PH disponível no cabeçalho), skills equipadas em 3 caixas com a carga (x/6). Reuso: `self.btn`, `self.hit`, `self.panel`, `self.fit`.
- **Tooltips**: ao passar o mouse (ou tocar) em um nó, caixa pré-desenhada com nome, tipo, gatilho, efeito em linguagem natural, recarga e custo; texto vem de `SKILLS[id]["text"]` (já cacheado por `text_img`).
- **Comparar**: `draw_compare` hoje mostra ANTES/DEPOIS de atributos; ganha uma linha "Força: 63,2 -> 64,0 (skills +0,8)" usando `skill_force`.
- **Mochila** (consumáveis): 2 caixas na tela de torneio (`draw_match_panel`) e na liga, com os 6 itens e a quantidade; botão limpar.
- **Loja**: filtros por slot com 8 abas, aba "CONSUMÍVEIS" e "COSMÉTICOS".
- **Sets**: ícone com contagem "Faxineiro 3/6" na lista de slots e bônus ativos listados abaixo.
- **Galeria de cosméticos**: tela nova simples (grade de adesivos/rastros), só leitura + equipar.
- Todos os textos Latin-1, `Font(None)`, tamanhos <= 24 nas listas, e testes de layout no estilo de `test_robots_ui` e `test_campaign_ui`.
