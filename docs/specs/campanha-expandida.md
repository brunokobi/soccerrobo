# Spec - Campanha Expandida (Ato 2 e Ato 3)

## 1. Decisão estrutural
**A campanha atual vira o Ato 1, intacta**: mesmos ids de cena, time, torneio, recompensa e capítulo (P, 1-5). Motivos:
- Os saves existentes guardam ids de cena em `done`; reescrever exige rewind e pune quem já jogou.
- A calibração do Ato 1 (F 44,3 -> 65,8, tabela em `tests/calib_campaign.py`) é cara de refazer.

O que muda no Ato 1:
- O epílogo `e1_epilogo` sai do nó `("end", ...)` e vira o primeiro nó do capítulo 6 (ponte entre atos). O texto ganha 2 falas de gancho (Vô Nestor volta do cruzeiro).
- Entram 4 missões secundárias retroativas, que só dependem de `done` (ver seção 6).
- A torcida (Onda A) e as skills (a partir do cap. 6, ver seção 8) não alteram a dificuldade já calibrada.

Estrutura nova (14 unidades jogáveis + sides):

| Ato | Título | Unidades | F | Local-tema |
|---|---|---|---|---|
| 1 | A Garagem do Vô | P, 1, 2, 3, 4, 5 | 44,3 -> 65,8 | escola -> Mundial (existente) |
| 2 | A Superliga Limpex | 6, 7, 8, 9 | 66,6 -> 73,8 | liga profissional, sede da Limpex |
| 3 | A Copa dos Campeões | 10, 11, 12, 13 | 74,4 -> 81,0 | intercâmbio, fábrica, coliseu, chip zero |

## 2. Elenco novo (CHARACTERS 12 -> 19)
Todos seguem o formato de `story.CHARACTERS` (nome <= 14 chars, Latin-1). Estilos novos em `HAIR_STYLES`, `ACCESSORIES` e `OUTFITS`: cabelo `trancas`, `coque`, `moicano`; acessório `bone`, `bengala`, `avental`, `tiara`, `cachecol`; roupa `avental`, `colete`.

| id | Nome | Papel | Visual |
|---|---|---|---|
| `nestor` | VÔ NESTOR | Inventor do Aspiradex. Volta do cruzeiro, resmungão fofo, fala "na minha época..." | calvo, bigode, bengala, chinelo; colete |
| `valquiria` | DRA. VALQUÍRIA | Nova CEO da Limpex (irmã caçula do Augusto). Sorridente demais. Vilã "educada" do Ato 2 | coque branco, tiara; blazer |
| `gabi` | GABI TROVÃO | Rival prodígio de 14 anos, "eu sou o futuro". Evolui de rival a aliado ou inimigo (escolha B1) | cabelo espetado azul, boné; camiseta amarela |
| `odete` | DONA ODETE | Merendeira do Santa Faísca, dona do bolo. Dá missões secundárias | coque grisalho; avental |
| `ogawa` | MESTRE OGAWA | Sensei do Kenji; zen, fala em provérbios que não fazem sentido | raspado, bigode; kimono |
| `galvao` / `cleide` | GALVÃO PÓ / CLEIDE MOP | Locutores. Aparecem em 2 cenas e como legendas no telão | cabine (bg `cabine`) |
| `zeperfeito` | ZÉ PERFEITO | Clone perfeito do Zé Poeira, sem chinelo (robô branco/ciano) | variante de `draw_robot` |
| `xomega` | X-ÔMEGA | Chip Zero, só voz e LED vermelho (usa o retrato de robô) | variante de `draw_robot` |

(São 8 entradas; `galvao` e `cleide` contam como 2, total 19 com os 12 atuais menos nenhum.)

Cenários novos em `story.BGS` (+7): `praca`, `laboratorio`, `aeroporto`, `dojo`, `fabrica`, `coliseu`, `lanchonete` (+ `cabine` para os locutores). Detalhe visual na spec de visual.

Humores novos (ids ASCII): `determinado`, `maravilhado`, `malicioso`, `sonolento`, `chorando`, `gritando`, `piscando`, `euforico`.

## 3. Novos formatos de torneio (`story.TOURNAMENTS[...]["format"]`)
Hoje: `single` e `cup` (grupo de 4 + [QF] + SF + F). Entram:

| Formato | Estágios | Regra |
|---|---|---|
| `league` | R1..R5, SF, F | 6 times, 5 rodadas contra os `group` (5 adversários), top 4 vai à SF; 5º-6º = eliminado (reinicia com semente nova, como o grupo). SF e F contra `sf` e `final` |
| `series` | S1, S2, S3 | sequência de 2-3 duelos obrigatórios. Perder repete aquele duelo (pity só no último = chefe) |

Mudanças em `campaign.py`:
- `stages_of(tr)`: cobre `league` e `series`.
- `STAGE_NAMES`: +`R1..R5` ("Rodada 1".."Rodada 5") e `S1..S3` ("Duelo 1".."Duelo 3").
- `_stage_team`: `R<i>` -> `group[i-1]`; `S<i>` -> `series[i-1]`.
- `_is_boss`: usa `tr["boss_stages"]`, padrão `["F"]` para `cup`, `["S<n>"]` para `series`.
- `group_league()` generalizado para n times (hoje fixo em 4): tabela com os outros jogos simulados da semente.
- Em `record_match`: `ko = stage[0] not in "GR"` (grupo e liga não vão a pênaltis); `if stage == stages[last_group_stage]` decide a classificação, com `adv_pos` por formato (`cup` 2, `league` 4).
- `_tour()` (sanitize): compara só os 2 primeiros elementos do nó e valida os estágios pelo formato novo.
- `MAX_RESULTS` 12 continua suficiente (liga = 7 resultados).

Nós condicionais: o nó vira `("tournament", id, cond)` ou `("scene", id, cond)`. `cond` é o mesmo formato de `check_cond`: `("flag", f)`, `("noflag", f)`, `("done", id)`, e novo `("count", prefixo, n)` (mínimo de chaves `done` com o prefixo). `next_action` pula o nó cuja condição é falsa (avança `node`). Isso permite capítulos com duas versões que têm a mesma estrutura de estágios.

Variantes de adversário: `TOURNAMENTS[id]["alt"] = [(cond, {"sf": "...", "final": "..."}), ...]`; `_stage_team` aplica a primeira variante cuja condição vale. A regra de design é que a variante troca o time, não o ovr (+-1).

Finais: `story.ENDINGS = [(cond, scene_id), ...]` em ordem de prioridade; o nó final é `("end", "AUTO")` e `next_action` escolhe a cena pelo primeiro `cond` verdadeiro.

## 4. Fluxo de escolhas e flags
Flags novas (todas <= 32 chars ASCII; `MAX_FLAGS` sobe de 64 para 128 no Garage v2). Já existem e são reaproveitadas: `patroc` (aceitou o patrocínio da Limpex no Ato 1), `denuncia`, `orgulho`, `chinelo_fica`, `bia_livre`, `bia_convidada`.

| Flag | Onde | Efeito |
|---|---|---|
| `gabi_amigo` / `gabi_rival` | final do cap. 6 (B1) | Gabi aliado (S1 do cap. 13 é dupla com ele, recruta "Relâmpago") ou inimigo recorrente (adversário no 10, 12 e 13) |
| `renova_limpex` | meio do cap. 7 (B2) | Renovar a Limpex (+20% de sucata no Ato 2/3, set "Linha Limpex Pro", finais B) ou ficar independente (+15% de XP, side quests de relíquias, finais A/C). Usa `patroc` como pano de fundo |
| `poupou_ze` / `desligou_ze` | cap. 9 (B3) | Poupar o Zé Perfeito (recruta ele, base 70) ou desligá-lo (ganha o Chip Zero, módulo de skill) |
| `sabotou_fabrica` / `denunciou_fabrica` | cap. 11 (B4) | Muda o time do S1/S2 do cap. 11 (fábrica da Limpex vs. galpão clandestino) e uma fala do chefe final |
| `fita_1`..`fita_4` | 4 missões secundárias "Fitas do Vô" | O final secreto exige as 4 |

## 5. Os 3 finais
Lógica de `ENDINGS` (primeira que vale):

| Final | Condição | Resumo |
|---|---|---|
| **C - "O Chinelo Estrutural"** (secreto) | `renova_limpex` ausente AND `poupou_ze` AND `chinelo_fica` AND `("count","side:fita",4)` | Zé Poeira e Zé Perfeito fazem a rodinha rolar juntos; o X-Ômega é "reiniciado" pelo chinelo. Cena final com os 2 Zés no telão; recompensa cosmética "Chinelo Dourado" |
| **B - "Contrato Dourado"** | `renova_limpex` | Campeões com a marca Limpex em tudo; Valquíria sorri (a samambaia da Helena não aprova). Final agridoce e cômico, com recompensa de +sucata |
| **A - "Garagem Livre"** | padrão | Campeões independentes; Gervásio chora de novo; a garagem vira sede oficial do clube |

Cada final é um conjunto de 2-3 cenas (`end_a1..`, `end_b1..`, `end_c1..`) e grava `c["endings"]` (lista, no máximo 3) para a tela de "galeria de finais".

## 6. Missões secundárias (eventos paralelos)
`story.SIDES[id]` = `{"title","local","bg","team","delta","unlock": cond,"scenes":{"pre","win","lose"?},"reward": {...},"repeat": False}`. São partidas únicas (formato `duel` = 1 jogo; derrota não tem penalidade e pode repetir). Aparecem na aba "MISSÕES" do mapa quando `unlock` vale. Recompensa única (peça, módulo, relíquia, cosmético, XP, sucata); ao concluir grava a chave `side:<id>` em `done`.

| id | Unlock | Nome | Adversário (ovr = F do momento - 14) | Recompensa |
|---|---|---|---|---|
| `s_odete` | P concluído | O Bolo Desaparecido | Clube da Merenda | Peça Rara + XP |
| `s_xadrez2` | cap. 1 | Revanche do Xadrez | Xadrez Mk II | módulo "Leitura de Jogo" nv 1 |
| `s_cantina` | cap. 2 | Copa da Cantina | Turma da Cantina | Escova Dupla |
| `s_fita1` | cap. 2 | Fita do Vô 1 | Sucateiros | `fita_1` + peça |
| `s_taxi` | cap. 4 | Corrida de Táxi | Cooperativa Mk II | sucata 300 |
| `s_fita2` | cap. 5 | Fita do Vô 2 | Oficina do Sul | `fita_2` |
| `s_gabi1` | cap. 6 | Treino com o Gabi | Dupla Trovão | cosmético "Faixa Azul" |
| `s_fita3` | cap. 7 | Fita do Vô 3 | Garagem Rival | `fita_3`, relíquia "Fita Crepe Reforçada" |
| `s_ogawa` | cap. 8 | Provérbio do Ogawa | Dojo Escondido | skill "Muralha" nv 1 |
| `s_helena` | cap. 8 | Vistoria Surpresa | Fiscais | Épica + XP |
| `s_clone` | cap. 9 | O Outro Zé | Protótipo Zé | módulo "Sucção Magnética" |
| `s_fita4` | cap. 10 | Fita do Vô 4 | Coleção Nestor | `fita_4` + relíquia "Rodinha Esquerda do Zé" |
| `s_torre1` | cap. 12 | Aposta do Dudu | Time do Chat | cosmético "Rastro Neon" |
| `s_final` | cap. 13 | Último Bolo | Odete Dream Team | cosmético "Comemoração Bolo" |

14 missões, ~2-3 cenas cada (~35 cenas).

Estado no save: `c["side"] = None | {"id","seed","loses"}` e chaves `side:<id>` em `done` (prefixo novo aceito por `_done_keys`). `Campaign.start_side(sid)` cria `self.side`; `next_action()` devolve a ação da side quando `self.side` está ativo (prioridade sobre os nós). Recompensas via o mesmo `apply_fx`/`_give_piece`.

## 7. Roteiro por capítulo (Ato 2 e Ato 3)

Convenções: `O` = ovr do adversário; F_rec do estágio = interpolação entre F_start e F_end (como em `Campaign._match_action`). Os `O` são valores iniciais; `calib_campaign.py` ajusta. As deltas refletem a tendência medida no Ato 1: regular F-O de 7 a 17, SF 8-12, chefe 6-8. Para o Ato 2 e 3 extrapolei +1 por capítulo nos regulares e +0,2 nos chefes, porque o motor "achata" em F alto. Locais usam o novo campo `venue` (ver spec visual).

### Ato 2 - A Superliga Limpex (F 66,6 -> 73,8)

**Cap. 6 - Taça de Acesso** | Ginásio Limpex Park (`arena`), formato `cup`, F 66,6 -> 68,0, econ_tier 4
- Estágios (F_rec / O / delta): G1 66,6 / 50 / 16,6; G2 66,9 / 51 / 15,9; G3 67,3 / 52 / 15,3; SF 67,7 / 57 / 10,7; F 68,0 / 61 / 7,0 (boss_delta 7,0).
- Times: grupo "Brigada da Pia", "Esquadrão do Rodo Mestre", "Faxineiros Mk III"; SF "Gabi e os Trovões" (Gabi, O 57); final "Brigada Higiene" (boss, O 61, perfeitos).
- Cenas: (1) `e1_epilogo` revisada + gancho: o Vô Nestor aparece em pessoa na garagem com mala de cruzeiro e entrega a planta do Aspiradex ("não tem manual, tem fé"); (2) `c6_convite`: um drone da Limpex entrega o convite da Superliga e a Dra. Valquíria sorri por holograma (humor: o drone pede desculpa por pousar na samambaia); (3) `c6_gabi_pre`: apresenta o Gabi Trovão ("eu sou o futuro, você é o... chinelo"); (4) `c6_g2_odete`: Dona Odete traz bolo para a arquibancada de 12 pessoas e distrai a Brigada; (5) `c6_sf_pos`: depois de vencer o Gabi, ele rouba o foco e dá um sorriso cheio de pena; (6) `c6_final_pre`/`win`/`lose`/`repescagem`; (7) **escolha B1** em `c6_final_win`: "Apertar a mão do Gabi" (`gabi_amigo`) ou "Provocar com o chinelo" (`gabi_rival`); (8) `c6_end`: Ambrósio descobre que o apito traz chip de rastreio.
- Recompensa `rw_6`: sucata 700, peça Épica "Servo Ágil", desbloqueia o 8º slot (Módulo) e dá 1 módulo "Arrancada" nv 1 ao herói; XP time 20.
- Side: `s_gabi1`. Torcida: `arena` (220 pessoas, LED Limpex, flashes).

**Cap. 7 - Superliga: Pontos Corridos** | Estádio Limpex (`superliga`, bg `estadio` + arquibancada neon), formato `league`, F 68,4 -> 70,2, econ_tier 4
- Estágios: R1 68,4 / 51 / 17,4; R2 68,7 / 52 / 16,7; R3 69,0 / 52 / 17,0; R4 69,3 / 53 / 16,3; R5 69,6 / 54 / 15,6; SF 69,9 / 59 / 10,9; F 70,2 / 63 / 7,2.
- Times (R1-R5): "Real Esfregão", "Atlético Micro-ondas", "Dínamo Pó de Arroz", "Sporting Ventilador", "Clube da Cera Líquida". SF "Os Impecáveis Mk III" (revanche da Vivi, agora aliada, treina contra). Final "Platinum Elite" (Rodolfo, boss, O 63).
- Cenas: (1) `c7_intro`: a Superliga tem mascote (um aspirador gigante inflável) que cai em cima do Gervásio; (2) `c7_vivi_treino`: Vivi explica a tabela com planilha e apita com um pano; (3) `c7_g3_dudu`: Dudu transmite a live da rodada com 40 mil espectadores e 1 cadeira; (4) **escolha B2** em `c7_contrato`: Valquíria oferece renovar o patrocínio ("assina aqui, tem bolo"): `renova_limpex` ou independente; se `patroc` do Ato 1 está ligado, ela já vem com a caneta pronta; (5) `c7_sf_pre`: Vivi vs. o time dela; (6) `c7_final_pre`/`win`/`lose`/`repescagem` com Rodolfo ("Eu agora sou coordenador de higiene ESPORTIVA"); (7) `c7_end`: Gabi manda uma mensagem de áudio escrita em caixa alta.
- Recompensa `rw_7`: sucata 900; se `gabi_amigo`, recruta "Relâmpago" (ATA, Velocista, base 68, nível 7); senão peça Rara "Mola Dupla". Skill "Sucção Magnética" nv 1 ao herói.
- Sides: `s_fita3`. Torcida: `superliga` (360, flashes, mosaico "SUPERLIGA").

**Cap. 8 - Playoffs da Superliga** | Estádio Limpex (`superliga` noturno), formato `cup` com QF, F 70,4 -> 72,0, econ_tier 5
- Estágios: G1 70,4 / 52 / 18,4; G2 70,7 / 53 / 17,7; G3 71,0 / 54 / 17,0; QF 71,4 / 57 / 14,4; SF 71,7 / 60 / 11,7; F 72,0 / 64 / 8,0 (boss_delta 8,0).
- Times: grupo "Coletivo do Pano", "Os Sem-Poeira", "Lavanderia FC"; QF "Dust Bunnies Pro" (rivais do Mundial evoluídos); SF "Dojo do Kenji 2.0"; final "Guarda Zero" (boss, perfeita, O 64, servos da Valquíria).
- Cenas: (1) `c8_intro`: a Superliga muda as regras no meio ("agora a bola é cinza"); (2) `c8_ogawa`: Mestre Ogawa ensina a "arte de não limpar" (provérbios sem sentido: "o pó que cai duas vezes é pó interessado"); (3) `c8_helena`: Helena faz vistoria surpresa e a samambaia reprova o Zé; (4) `c8_qf_pre`: os Dust Bunnies voltaram com chapéus maiores; (5) `c8_sf_kenji`: Kenji vem agradecer e perde de propósito, ou não; (6) `c8_final_pre`/`win`/`lose`/`repescagem` com a Guarda Zero ("a Valquíria mandou lembranças e uma intimação para as lembranças"); (7) `c8_end`: um holograma do Augusto aparece de cueca ("é o meu período de reflexão").
- Recompensa `rw_8`: sucata 1.100, relíquia "Pão de Queijo Térmico" (bateria Lendária única), XP time 30. Skill "Chute em Curva" nv 1 ao herói.
- Sides: `s_ogawa`, `s_helena`. Torcida: `superliga` com sinalizadores e confete.

**Cap. 9 - O Clone** | Laboratório da Limpex (`laboratorio`), formato `series` (3 duelos), F 72,4 -> 73,8, econ_tier 5
- Estágios: S1 72,4 / 56 / 16,4; S2 73,1 / 60 / 13,1; S3 73,8 / 66 / 7,8 (chefe: Zé Perfeito, boss).
- Times: S1 "Droides de Plantão"; S2 "Gabi Trovão" (se `gabi_rival`) ou "Time Reserva da Valquíria" (se `gabi_amigo`); S3 "Zé Perfeito + Guarda Zero" (O 66, perfeitos).
- Cenas: (1) `c9_intro`: Vô Nestor reconhece a própria planta na tela ("eu não autorizei esse clone nem esse bigode"); (2) `c9_lab`: infiltração na Limpex com Dudu e o headset, humor de espião ("estou dentro... do armário"); (3) `c9_ze_perfeito`: o clone é calmo, sem rodinha solta, sem chinelo; pergunta "por que você cai?"; (4) `c9_s2_pre`; (5) `c9_s3_pre`; (6) vitória: **escolha B3**: "Poupar o Zé Perfeito" (`poupou_ze`) ou "Desligar" (`desligou_ze`); (7) `c9_end`: Valquíria agradece, sorrindo, pela "aula gratuita".
- Recompensa `rw_9`: sucata 1.300; se `poupou_ze`, recruta "Zé Perfeito" (MEI, Orbital, base 70, nível 9); se `desligou_ze`, o módulo Chip Zero (skill "Overclock Controlado" nv 2) e sucata 400 extra. Fim do Ato 2: `a2_fim` (cena curta com Vô Nestor: "agora vem o mundo").
- Side: `s_clone`. Torcida: `laboratorio` (robôs-fã, tipo "robô"; 80 espectadores-robô).

### Ato 3 - A Copa dos Campeões (F 74,4 -> 81,0)

**Cap. 10 - Intercâmbio** | Aeroporto e Dojo (`aeroporto`/`dojo`), formato `cup`, F 74,4 -> 76,0, econ_tier 5
- Estágios: G1 74,4 / 54 / 20,4; G2 74,8 / 55 / 19,8; G3 75,2 / 56 / 19,2; SF 75,6 / 63 / 12,6; F 76,0 / 68 / 8,0.
- Times: grupo "Sakura Reboot", "Staubsauger Pro", "Les Aspirateurs Noirs"; SF "Seleção Nipo-Teuta" (Kenji + Helena como técnica convidada); final "Time dos Mundos" (boss, O 68).
- Cenas: (1) `c10_aeroporto`: o time perde a conexão por causa do chinelo na esteira de raio-X; (2) `c10_dojo`: Ogawa e o Kenji treinam o Zé na neve; (3) `c10_sakura_pre`; (4) `c10_staub`: os alemães têm 3 fiscais para cada robô; (5) `c10_sf_pre`/`pos`; (6) `c10_final_pre`/`win`/`lose`/`repescagem`; (7) `c10_end`: Kenji dá a faixa do dojo (cosmético).
- Recompensa `rw_10`: sucata 1.500; recruta de elenco "Samurai" (DEF, Titã, base 72, nível 11) se `gabi_amigo` e "Ronin" (DEF, Tanque, base 70) senão; peça Épica "Câmera Dupla". `level_cap` 15 já ativo desde o início do Ato 2.
- Side: `s_fita4`. Torcida: `mundial` parcial (sakura e staub = bandeiras, 300).

**Cap. 11 - A Fábrica** | Fábrica da Limpex (`fabrica`), formato `series` (3 duelos), F 76,4 -> 77,6, econ_tier 6
- Estágios: S1 76,4 / 58 / 18,4; S2 77,0 / 62 / 15,0; S3 77,6 / 69 / 8,6 (chefe).
- **Duas versões** (nó condicional): `t_c11_corp` se `renova_limpex` (jogam dentro da fábrica, a pedido da Limpex, contra "Linha de Montagem", "Controle de Qualidade", "Gerente Mk II") e `t_c11_rebel` se independente (jogo clandestino no galpão: "Sucateiros Elite", "Contrabando Mk II", "Dono do Galpão"). Mesmos ovr.
- Cenas: (1) `c11_intro`: a fábrica produz milhares de Zés Perfeitos em esteira; (2) `c11_dudu_hack`: o hack do Dudu abre uma porta e uma porta de verdade fecha sobre o dedo dele; (3) `c11_bia`: Bia constrói uma ponte com fita; (4) **escolha B4**: sabotar a esteira (`sabotou_fabrica`) ou gravar tudo e denunciar (`denunciou_fabrica`); (5) `c11_s3_pre`; (6) vitória/derrota; (7) `c11_end`: o X-Ômega acorda em 13 telas ao mesmo tempo.
- Recompensa `rw_11`: sucata 1.700; peça Lendária "Railgun de Bolso" (se corp) ou "Sonar Quântico" (se rebel). Sem recruta.
- Torcida: `fabrica` (robôs-fã sentados em esteiras, 120).

**Cap. 12 - Copa dos Campeões** | Coliseu (`coliseu`), formato `cup` com QF, F 77,8 -> 79,4, econ_tier 6
- Estágios: G1 77,8 / 57 / 20,8; G2 78,1 / 58 / 20,1; G3 78,4 / 59 / 19,4; QF 78,8 / 62 / 16,8; SF 79,1 / 66 / 13,1; F 79,4 / 71 / 8,4 (boss_delta 8,4).
- Times: grupo "Campeões do Sul", "Rainha da Cera", "Titãs do Vale"; QF "Gabi Trovão Pro" (se `gabi_rival`) ou "Dojo All-Stars"; SF "Platinum Imperial" (Rodolfo + Valquíria); final "Os Imaculados Ômega" (boss, O 71).
- Cenas: (1) `c12_intro`: a Copa convoca todos os campeões, incluindo os da escola; Gervásio chora na plateia, com uma bandeira de pano; (2) `c12_gabi`: Gabi (aliado ou rival) faz uma entrada de motocicleta de brinquedo; (3) `c12_helena`: Helena promove a samambaia a "árbitra"; (4) `c12_final_pre`: Valquíria mostra o X-Ômega como atração final; (5) `c12_final_win`/`lose`; (6) `c12_end`: apagão no estádio; o telão mostra só o LED vermelho.
- Recompensa `rw_12`: sucata 2.000; peça Lendária de set; XP time 40.
- Side: `s_torre1`. Torcida: `coliseu` (520, mosaico, sinalizadores, flashes, confete).

**Cap. 13 - O Chip Zero** | Coliseu em apagão (`coliseu` modo escuro), formato `series` (3 duelos), F 79,6 -> 81,0, econ_tier 6
- Estágios: S1 79,6 / 62 / 17,6; S2 80,3 / 67 / 13,3; S3 81,0 / 73 / 8,0 (chefe final).
- Times: S1 "Droides Ômega" (se `denunciou_fabrica`, entram com a polícia de fiscalização ao fundo); S2 "Guarda Pretoriana"; S3 "X-Ômega Prime" (O 73, perfeito).
- Cenas: (1) `c13_intro`: X-Ômega toma o controle de todos os robôs da arena (até o aspirador do bar); (2) `c13_augusto`: Dr. Augusto reaparece de jaleco rasgado e confessa que o chip veio das notas fiscais do Vô; redenção cômica (traz chá); (3) `c13_equipe`: todos se juntam, uma última fala por personagem; (4) `c13_s3_pre`; (5) vitória: ramifica em `ENDINGS`; (6) 3 cenas por final; (7) créditos.
- Recompensa `rw_13`: sucata 3.000, título (`stats.titles`), cosmético do final, desbloqueia NG+ e Torre.

## 8. Integração com o código atual
- `story.py` vira fachada: continua exportando `CHARACTERS`, `TEAMS`, `SCENES`, `TOURNAMENTS`, `CHAPTERS`, `REWARDS`, `MOODS`, `BGS`. Os dados novos ficam em `story_a2.py`, `story_a3.py` e `story_side.py`, que fazem `update` nos dicts do `story.py`. Todos os testes (`test_story` etc.) seguem importando `story`.
- `STORY_VERSION` sobe de 1 para 2. `CHAPTERS` ganha o campo `act` ("1".."3") e o capítulo 5 perde o nó `("end","e1_epilogo")`; esse nó vira o primeiro do capítulo 6.
- Chave do garage: `campaign._migrate` não migra o garage; quem migra é `Garage.from_dict` internamente (ver spec de itens e skills).

## 9. Migração dos saves existentes
1. `campaign.VERSION` sobe de 1 para 2: campos novos em `c` (`side` = None, `ng` = 0, `endings` = []). `MIGRATIONS[("v",1)] = fn` adiciona os padrões. Um build antigo lendo save v2 devolve "bad" (nunca apaga).
2. `MIGRATIONS[("sv",1)] = fn`: se `c.ch == "5"` e `c.node >= 4` (estava no epílogo ou depois), muda para `ch = "6"`, `node = 0`, `tour = None`, `pity = 0`. O epílogo (se já está em `done`) é pulado por `next_action`; o jogador continua exatamente onde terminou. Quem estava no meio do cap. 5 (nodes 0-3) não muda nada. Nenhum rewind do Ato 1.
3. Níveis: quem já passou do cap. 5 ganha `cap = 15` e retroativo de pontos de skill = `level - 1` (derivado de `reward:rw_5` em `done`, idempotente).
4. Se o save tem `sv` desconhecido sem migração, a regra atual vale: rewind ao início do capítulo, com aviso.
5. Sanitize: `_done_keys` aceita o prefixo `side:<id>`, `MAX_DONE` sobe de 300 para 600 e `MAX_DONE_RAW` de 1000 para 1500; `STAT_KEYS` ganha `sides`.
6. Teste novo `test_campaign_migration.py`: fixture com um save v1/sv1 real (no meio do cap. 5, no `chapter_end`, no epílogo e já terminado) deve virar um save válido sem rewind do Ato 1.

## 10. Curva de dificuldade e economia

**Dificuldade** (metas no motor real; cada capítulo recalibra com `calib_campaign.py`):
- Regulares 58-66%, SF 52-58%, chefes 45-52%, chefe final 42-50%.
- Tabela de F_rec e O por estágio na seção 7. Motor no Ato 1: V+E/2 ~ 34 + 1,8·F - 1,8·O (rmse ~4 pts), mas o desvio regular cresce de 7 (cap. 1) a 17 (cap. 5), então o Ato 2 e 3 seguem a tendência (regulares 15-21, SF 11-13, chefes 7-8,6).
- `sim_bias(O)` (clamp 5 + 1,5·(O-40), -2, 8) satura em 8 acima de O = 42; o SIMULAR continua válido se `skill_force` entra em F (ver spec de itens e skills). Revalidar com `--grid` (F 66..82 x O 48..74).

**De onde vem o F do Ato 2 e 3** (66 -> 81, estimativa a validar na Onda B/C). A sucata sozinha não basta: um upgrade Épico +1 custa 210·(lvl+1) e rende ~0,06 F, então escalar F só por upgrade é caro demais.

| Fonte | Contribuição estimada |
|---|---|
| Nível máximo 10 -> 15 (`LEVEL_STEP` 1,1) | +4 a +5,5 |
| Recrutas com base mais alta (68, 70, 72) | +4 a +6 |
| Sets (bônus de conjunto) | +1,5 a +2 |
| Skills (`skill_force`, teto 4,0) | +2,5 a +4 |
| Peças (Épicas em vez de Raras; relíquias) | +3 a +4 |
| **Total** | **~+15 a +20** |

Se a calibração mostrar déficit, o ajuste é diminuir os F_end do Ato 3 (nunca inventar poder).

**Economia**: `G.TIER_MUL` estende de 4 para 7 entradas, mantendo as 4 primeiras iguais (Modo Robôs não muda): `(1,0, 1,5, 2,2, 3,2, 4,2, 5,2, 6,4)`.
- Sucata por vitória (5 gols) no `econ_tier` 4 / 5 / 6: 315 / 390 / 480.
- `econ_tier` por capítulo: 4 (caps. 6-7), 5 (caps. 8-10), 6 (caps. 11-13).
- Recompensas de capítulo (ver seção 7): 700 -> 3.000 sucata.
- `refresh_shop`: chance de Épica 0,25 e Lendária 0,10 hoje; nos tiers 4-6 sobe para (0,35/0,18), (0,45/0,25) e (0,55/0,32).
- XP: `xp_need(l)` para `l >= 10` passa a `560 + 40·(l-10)` (níveis 10-14: 560, 600, 640, 680, 720; total ~3.200 XP). Com ~55 partidas no Ato 2 e 3 a 60-80 XP, os níveis fecham perto do fim.
- Ramos: `renova_limpex` dá +20% de sucata no Ato 2 e 3 (aplicado em `record_match`), independente dá +15% de XP. O `calib`/autoplay confere que os dois ramos terminam com F_end +-0,7.

**Pity**: `PITY_MAX` fica em 3; `PITY_STEP` em 1.

## 11. Estimativa de roteiro
- Ato 2: 4 capítulos x ~11 cenas x ~11 falas ≈ 480 falas, ~44 cenas.
- Ato 3: idem ≈ 480 falas, ~44 cenas.
- Missões secundárias: 14 x 2,5 cenas x 9 falas ≈ 315 falas, ~35 cenas.
- Finais e ponte: ~10 cenas, ~100 falas.
- **Total novo**: ~125 cenas, ~1.400 falas (a campanha atual tem 626). Resultado final: ~178 cenas / ~2.030 falas.
- Linhas de código de dados: ~2.900 (`story_a2.py` ~1.100, `story_a3.py` ~1.100, `story_side.py` ~700).
- Regras de escrita (já testadas em `test_story`): Latin-1, fala <= 260 chars e <= 4 linhas de 780 px, opção <= 46 chars, nome <= 14, flags ASCII <= 32.

## 12. Pós-campanha (Onda D opcional)
- **NG+ "Turnê Lendária"** (`c["ng"]` 1-3): mantém a garagem, reinicia os torneios como "revanches" (cenas curtas, sem repetir diálogos longos). Os adversários ganham `NG_SHIFT = (0, 20, 26, 30)` pontos de ovr, com teto 90. Recompensas: cosméticos e peças "Míticas" (Lendária com +2 de potência). O F potencial (sets completos + nível 15 + Lendárias +3) chega a ~88, suficiente.
- **Torre do Pó**: 40 andares, cada andar uma partida; O = 54 + andar·0,9 (teto 90); a cada 5 andares um modificador de arena (bola pesada, bateria curta, goleiro gigante); marcos em 10, 20, 30, 40 dão cosméticos. O progresso (`tower`) vai em `c` (campo novo na migração, v2).
