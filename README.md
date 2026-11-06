# SoccerRobo (Copa Aspirador)

![Python](https://img.shields.io/badge/Python-3.12-3776AB?logo=python&logoColor=white)
![pygame](https://img.shields.io/badge/pygame-2.6-2E8B57)
![WebAssembly](https://img.shields.io/badge/roda%20no%20navegador-pygbag%20%2F%20WebAssembly-654FF0?logo=webassembly&logoColor=white)
![Status](https://img.shields.io/badge/status-em%20desenvolvimento-orange)
![Last commit](https://img.shields.io/github/last-commit/brunokobi/soccerrobo)
![Repo size](https://img.shields.io/github/repo-size/brunokobi/soccerrobo)
[![Jogar online](https://img.shields.io/badge/jogar%20online-copaaspirador.brunokobi.tech-00b4d8?logo=googlechrome&logoColor=white)](https://copaaspirador.brunokobi.tech)

**Jogue agora no navegador: https://copaaspirador.brunokobi.tech**

Futebol arcade 5x5 feito **100% em Python** (pygame), que roda no navegador via
[pygbag](https://pygame-web.github.io/) (Python -> WebAssembly). O projeto está
virando um **futebol de robôs aspiradores** com campanha em estilo RPG
(escola -> mundial), laboratório de upgrades e partidas automáticas decididas
pelas habilidades dos robôs.

## Telas

| | |
|---|---|
| ![Menu principal](docs/img/menu.png) | ![Partida com câmera de estádio e torcida no gol](docs/img/partida-estadio-gol.png) |
| **Menu** - amistosos, carreira de clubes, Modo Robôs e campanha | **Partida assistida** - câmera de estádio, torcida reagindo ao gol, LED e telão |
| ![Campanha: diálogo](docs/img/campanha-dialogo.png) | ![Campanha: mapa dos capítulos](docs/img/campanha-mapa.png) |
| **Campanha** - diálogos com retratos animados e cenários desenhados por código | **Mapa da campanha** - da escola ao Mundial de Aspiradores |
| ![Campanha: torneio](docs/img/campanha-torneio.png) | ![Modo Robôs: liga](docs/img/modo-robos-liga.png) |
| **Torneio** - grupo, chaveamento e final contra o chefe (ASSISTIR ou SIMULAR) | **Modo Robôs** - liga de 6 times em 4 tiers |
| ![Garagem: bancada com 8 slots](docs/img/garagem-bancada.png) | ![Árvore de habilidades](docs/img/habilidades.png) |
| **Garagem** - 8 slots (com Módulo), sets, relíquias e o antes/depois de cada peça | **Habilidades** - árvore Ataque/Controle/Defesa, skills equipadas e tática do time |
| ![Mochila de itens](docs/img/mochila.png) | ![Galeria de cosméticos](docs/img/visual-cosmeticos.png) |
| **Mochila** - até 2 itens de partida, gastos ao jogar | **Visual** - adesivo, antena, rastro e comemoração por robô |

| ![Mapa do Ato 2](docs/img/campanha-mapa-ato2.png) | ![Superliga em pontos corridos](docs/img/campanha-superliga.png) |
| **Ato 2** - mapa por Ato (Ato 1 escola ao Mundial, Ato 2 Superliga Limpex, Ato 3 Copa dos Campeões) | **Superliga** - liga em pontos corridos, os 4 primeiros vão à semifinal |

![Missões secundárias](docs/img/campanha-missoes.png)

**Missões secundárias** - 14 missões avulsas com prêmio próprio; as 4 "Fitas do Vô" levam ao final secreto.

**Pós-campanha (Onda D):**

| | |
|---|---|
| ![Fim da campanha com Turnê Lendária e Torre do Pó](docs/img/pos-campanha-fim.png) | ![Torre do Pó](docs/img/torre-do-po.png) |
| **Fim da campanha** - galeria de finais e as portas do pós-jogo: Turnê Lendária (NG+) e Torre do Pó | **Torre do Pó** - 40 andares, modificador de arena a cada 5 e prêmios nos marcos 10/20/30/40 |
| ![Andar com goleiro gigante](docs/img/torre-goleiro-gigante.png) | ![Peça Mítica na garagem](docs/img/peca-mitica.png) |
| **Modificador de arena** - goleiro gigante (também bateria curta e bola pesada) | **Peça Mítica** - raridade acima da Lendária, só como prêmio do NG+ e da Torre |

Robôs em campo com cosméticos (câmera PERTO):

![Partida com robôs personalizados](docs/img/partida-perto.png)

## Visual
Tema tecnológico/neon: arena com grade e linhas holográficas, robôs-disco com
anel de LED e barra de bateria, bola com brilho, rastro e faíscas, e HUD e menu
novos.

**Torcida:** arquibancadas ao redor do campo com espectadores nas cores dos times,
de uma quadra de escola ao Mundial lotado (o local muda com o capítulo e o modo; no
Modo Robôs, com o tier da liga: bairro, ginásio, arena e estádio). A torcida ocupa
primeiro as arquibancadas laterais, que a interface não cobre.
Ela reage a gol, chance, defesa e trave (pula, levanta os braços, faz ola e
mosaico), com confete, flashes, sinalizadores, bandeiras, placas de LED,
onomatopeias e um telão com os locutores Tonho Vassoura e Cleide. Tecla **T**
(no menu ou na pausa) alterna a torcida entre ALTA, MÉDIA e DESLIGADA; ela some
no modo MAX. **Câmera de estádio:** nas partidas assistidas (campanha, Modo Robôs,
carreira) o campo aparece reduzido (80%) com arquibancadas largas em volta, em cima,
nas laterais e embaixo; no Amistoso com humano a câmera fica PERTO (campo em tela
cheia). Tecla **C** no menu gira AUTO / ESTÁDIO / PERTO e na pausa troca a câmera da
partida (fica gravado). **F11** abre a tela cheia.

## Som
Efeitos sonoros e música **sintetizados por código** (nenhum arquivo de áudio: `game/sfx.py` e
`game/music.py` geram tudo com `math`/`array` no início do jogo, aos poucos, em ~0,4 s no desktop).
Ligados por padrão em volume médio.

- **Efeitos:** chute e toque na bola, roubo e drible, trave (CLANG), apito de início e de fim, gol
  (explosão da torcida + buzina), "uuuh" da chance, defesa, palmas, skill (BUZZ), arrancada (ZOOM),
  cliques de menu, avanço de diálogo, vitória/derrota/empate, recompensa, compra e upgrade na loja.
- **Música** chiptune em loop: uma trilha para menus/campanha e outra, mais animada e mais baixa,
  para a partida; jingles de vitória e de derrota na tela de resultado.
- **Teclas:** **M** liga/desliga o mudo geral (em qualquer tela); **S** gira o volume dos efeitos e
  **N** o da música (DESL. / BAIXO / MÉDIO / ALTO), no menu ou na pausa. Tudo fica gravado nas
  preferências. No modo MAX a partida fica sem efeitos.
- No navegador o áudio só começa depois do primeiro clique (a página já pede esse clique); se o
  áudio falhar, o jogo segue sem som. Detalhes em [docs/specs/som.md](docs/specs/som.md).

**Robôs e cenas:** cada chassi tem desenho próprio (o Orbital com satélites, o
Titã octogonal), as peças equipadas aparecem no robô (turbina, canhão, para-choque
blindado, radar...), as escovas giram e a bateria baixa solta faíscas e fumaça.
Na campanha, os personagens piscam e mexem a boca ao falar, e os cenários têm
camadas, luz e animação.

## Modos
No menu (teclas 1-6): `1 - AMISTOSO`, `2 - AMISTOSO`, `3 - NOVA CARREIRA`, `4 - CONTINUAR CARREIRA`, `5 - MODO ROBÔS` e `6 - CAMPANHA`.

1. **Amistoso: um jogador** contra a CPU (2 min)
2. **Amistoso: dois jogadores** no mesmo teclado
3. **Nova carreira de clubes** (estilo Elifoot): você é o técnico. 24 clubes fictícios
   em 3 divisões de 8 times (ida e volta, 14 rodadas). Elenco de 15-20 jogadores
   com overall/idade/valor, escalação dos 5 titulares (GOL, DEF, 2 MEI, ATA),
   **mercado de transferências**, vender jogadores, finanças (bilheteria,
   salários, premiação), **promoção/rebaixamento** (sobem/descem 2) e evolução
   dos jogadores entre temporadas. Suas partidas são **jogadas automaticamente
   no campo** (você assiste; velocidade 1x/2x/4x/MAX nas teclas 1-4); as dos
   outros clubes são simuladas. O progresso é salvo sozinho (`localStorage` no
   navegador; `~/.soccerpy_career.json` no desktop).
4. **Continuar carreira** (aparece quando há save)
5. **Modo Robôs**: você monta uma **equipe de robôs persistente** e disputa ligas.
   - **Equipe:** 5 titulares (GOL, DEF, 2 MEI, ATA) + reservas, até 8 robôs. Cada robô
     tem chassis, nome, cor, XP e nível (até 10).
   - **Chassis:** Disco (inicial), Tanque, Velocista, Goleiro, Orbital e Titã. Os quatro
     últimos são desbloqueados ao concluir ligas (Tanque, Velocista, Goleiro e,
     no último tier, Orbital e Titã).
   - **Peças:** 7 slots por robô (motor, bateria, para-choque, chutador, sucção, sensor,
     chip), em 4 raridades (Comum, Rara, Épica, Lendária). Cada peça pode ser
     melhorada de 0 a 5 com sucata. Os modelos "agressivos" (Turbina, Blindado,
     Canhão de Plasma etc.) dão mais bônus, mas gastam bateria.
   - **Overclock:** NORMAL, TURBO ou OVERDRIVE trocam desempenho por bateria.
   - **Progressão:** os robôs ganham XP nas partidas (os reservas ganham uma parte)
     e sobem de nível; as partidas rendem **sucata** e, às vezes, uma peça.
   - **Loja:** compra peças e modelos, vende as que sobram.
   - **Liga:** 6 times, ida e volta (10 rodadas), em 4 tiers de dificuldade. Em cada
     rodada você escolhe **assistir** (partida jogada no motor) ou **simular**
     (resultado estatístico). Terminar em 3º ou melhor libera o próximo tier, e a
     premiação em sucata depende da colocação.
   - **Habilidades, itens e visual (Fase 4, Onda B)** - liberados ao concluir o tier 1 do
     Modo Robôs ou o Ato 1 da campanha (antes disso tudo joga exatamente como antes):
     - **8º slot "Módulo"**, 30 modelos de peça, 6 relíquias únicas e 5 sets (Faxineiro,
       Plasma, Titã, Dojo, Limpex) com bônus ao juntar 2, 3 e 4 peças do mesmo set.
     - **16 skills** (+11 especiais da campanha) que a IA usa sozinha durante a partida
       (Arrancada, Sucção Magnética, Chute em Curva, Muralha, Defesa Elástica, Choque
       Elétrico, Instinto Matador, Líder...): cada robô equipa até 3, aprendidas com
       pontos de habilidade (1 por nível) numa árvore Ataque/Controle/Defesa, com ranks
       1-3. Aba **HABILIDADES** na garagem e tática do time (Ofensivo / Equilibrado /
       Defensivo). Cada skill foi calibrada no próprio motor e soma Força ao time (até +9).
     - **Itens de partida** (Bateria Extra, Cera Turbo, Café do Prof., Fita Isolante, Pilha
       Reserva, Spray Anti-Poeira): comprados na LOJA, levados na **Mochila** (até 2 por
       partida) e gastos ao jogar.
     - **Cosméticos** (adesivo, antena, rastro e comemoração de gol): só visuais, comprados
       na aba COSMÉTICOS da loja e equipados por robô no botão **VISUAL** da bancada.
   - **Save próprio**, separado da carreira de clubes: `localStorage`
     (`soccerpy_robots_v1`) no navegador; `~/.soccerpy_robots.json` no desktop. Um save
     inválido só é sobrescrito pelo NOVO JOGO após confirmação explícita; a cópia fica em `.bad`.
6. **Campanha** "A Garagem do Vô": a história do torneio de robôs aspiradores, jogada
   sobre a mesma garagem/bancada/loja do Modo Robôs, mas com **save próprio**.
   - **Enredo:** Téo (Moreira) descobre na garagem do Vô Nestor o Zé Poeira, um
     aspirador antigo, e junta-se ao Prof. Ambrósio para salvar o clube de robótica do
     Colégio Santa Faísca. No caminho conhece Vivi (Valentina), Bia e Dudu, e passa a
     enfrentar a corporação Limpex e o chip X-9 do Dr. Augusto Brilhante, do torneio
     escolar ao mundial.
   - **Estrutura:** **Ato 1** "A Garagem do Vô": Prólogo + 5 capítulos (Copa Interclasses,
     Taça Vale do Pó, Estadual Limpex Cup, Copa Brasil e Mundial de Aspiradores) + epílogo.
     **Ato 2** "A Superliga Limpex", jogável inteiro: Capítulos 6 (Taça de Acesso), 7 (Superliga
     em pontos corridos), 8 (Playoffs) e 9 (O Clone, série de duelos contra o Zé Perfeito), com o
     Vô Nestor de volta, a Dra. Valquíria, o rival Gabi Trovão, a Dona Odete e o Mestre Ogawa, e três
     escolhas que mudam adversários, falas e recompensas. **Ato 3** "A Copa dos Campeões":
     Capítulos 10 (Intercâmbio), 11 (A Fábrica, que muda conforme o patrocínio), 12 (Copa dos
     Campeões) e 13 (O Chip Zero, contra o X-Ômega), com **3 finais** conforme as escolhas (um
     deles secreto). Mais **14 missões secundárias** no botão MISSÕES do mapa (as 4 "Fitas do Vô"
     levam ao final secreto). São ~160 cenas de diálogo. Retratos e
     cenários são **desenhados por código** (sem imagens externas). O mapa tem uma aba por Ato
     e um botão de **MISSÕES** secundárias.
   - **Escolhas:** algumas cenas oferecem 2-3 opções que mudam falas seguintes e podem dar
     recompensas (sucata, XP, peça). Esc na cena abre um mini-menu; PULAR CENA pede
     confirmação (e, se há escolha, assume a opção 1).
   - **Torneios:** grupo de 4 + mata-mata com pênaltis (o Mundial tem também quartas).
     Você é sempre o mandante. Em cada partida escolhe **ASSISTIR** (partida jogada no
     motor, velocidade 1x/2x/4x/MAX nas teclas 1-4) ou **SIMULAR** (resultado estatístico).
   - **Chefes e "ajuda":** a cada derrota seguida contra o chefe ele perde 1 de Força
     (até -3); zera ao vencer.
   - **TREINO:** partidas ilimitadas contra um adversário mais fraco, na garagem ou no
     mapa, para juntar sucata e XP sem mexer no torneio.
   - **Progressão:** cada capítulo concluído dá recompensa única (sucata, peça, XP) e
     libera chassis (Tanque, Velocista, Goleiro e Titã nos Caps. 1 a 4) e recrutas
     (os robôs Gambiarra, Pixelado e Majestade). A loja evolui com o capítulo.
   - **Save próprio**, separado da carreira de clubes e do Modo Robôs: `localStorage`
     (`soccerpy_campaign_v1`) no navegador; `~/.soccerpy_campaign.json` no desktop. Um
     save inválido só é sobrescrito pelo NOVO JOGO após confirmação; a cópia fica em
     `.bad`. Um save com pequenos defeitos é reparado automaticamente, voltando ao início
     do capítulo. Desde a Onda C o save da campanha é **v2**: saves v1 são migrados ao
     carregar (quem já estava no epílogo ou tinha terminado vai para o Capítulo 6, sem
     refazer nada do Ato 1). Desde a Onda D o save é **v3** (NG+, Torre do Pó e peças
     Míticas): saves v2 são migrados ao carregar, sem rewind (quem terminou a campanha
     continua no fim, com o NG+ e a Torre liberados). Um build antigo (em cache no navegador)
     que abra um save mais novo o trata como inválido e o preserva em `.bad`, sem apagar.
   - **Pós-campanha (Onda D)**, liberado ao terminar o Capítulo 13 (qualquer final):
     - **Turnê Lendária (NG+)**: botão TURNÊ LENDÁRIA na tela de fim. Recomeça no Capítulo 1
       com a mesma garagem (robôs, peças, níveis, escolhas); os torneios viram revanches com uma
       cena curta por capítulo (sem repetir os diálogos) e os rivais ganham +20, +26 e +30 de Força
       nas voltas I, II e III (teto 90). Cada capítulo fechado dá sucata; o fim de cada Ato dá uma
       **peça Mítica** e cada volta concluída dá um cosmético exclusivo.
     - **Torre do Pó**: botão TORRE DO PÓ no mapa. 40 andares, uma partida por andar, rival de
       Força 54 + 0,9 por andar (55 a 90); a cada 5 andares a arena muda (**bola pesada**, **bateria
       curta** ou **goleiro gigante** do rival). ASSISTIR joga com o modificador; SIMULAR desconta da sua
       Força o efeito medido no motor. Empate vai aos pênaltis; perder só repete o andar. Os andares
       10, 20, 30 e 40 dão cosméticos (e 20 e 40, uma peça Mítica); no topo dá para recomeçar a subida.
     - **Peças Míticas**: uma raridade acima da Lendária (+2 de potência, cor rosa), só como prêmio
       do NG+ e da Torre (a loja e os drops nunca sorteiam). Sete cosméticos novos (antenas Para-raios,
       Coroa do Pó e Auréola; rastros Poeira Dourada e Cometa; comemorações Troféu e Relâmpagos) aparecem
       na loja como "prêmio" e não se compram.

### Controles (modos 1 e 2)
| Ação | Modo 1 jogador | J1 | J2 |
|---|---|---|---|
| Mover | WASD / setas | WASD | setas |
| Chutar (segure = mais forte) | Espaço / Enter | Espaço | Enter |
| Passar | Shift / X / Z | Shift esq. | Shift dir. |
| Pausar | P | | |
| Voltar ao menu | Esc | | |
| Mudo / efeitos / música | M / S e N na pausa | | |

O jogador controlado troca sozinho (o mais perto da bola).

## Roadmap
| Fase | Conteúdo | Situação |
|---|---|---|
| 1 | Robôs com chassis e 8 atributos, bateria, arena tecnológica (neon) | pronta |
| 2 | Garagem e laboratório: peças, upgrades, XP, evolução, loja e liga (Modo Robôs) | pronta e jogável |
| 3 | **Campanha** "A Garagem do Vô": história, diálogos, torneios, chefes e treino (escola -> mundial) | pronta e jogável |
| 4 | **Campanha Expandida**: torcida realista, câmera de estádio e desenhos mais detalhados (Onda A), peças/sets/relíquias/itens/cosméticos e 16 skills dos robôs (Onda B), Atos 2 e 3, missões secundárias e 3 finais (Onda C), NG+ "Turnê Lendária", Torre do Pó e peças Míticas (Onda D) | Ondas A, B, C e D (pós-campanha) prontas e publicadas ([docs/roadmap.md](docs/roadmap.md)) |
| 5 | Editor de firmware (regras da IA em blocos) | planejada |
| 6 | **Som**: efeitos e música sintetizados por código, mudo (M) e volumes (S/N) | pronta |

O planejamento detalhado fica em [`docs/`](docs/INDEX.md).

**Robôs (Fase 1):** 6 chassis (Disco, Tanque, Velocista, Goleiro, Orbital, Titã) e 8 atributos
(velocidade, aceleração, chute, controle/sucção, defesa, visão, bateria, QI) que
alteram de verdade o comportamento na partida; a bateria gasta ao correr e
chutar e recarrega parado. Atributos e bateria já vêm calibrados e ligados por
padrão (`game/robots.py`; o Modo Robôs usa o ajuste próprio `TUNING_ROBOTS`); o modo legado (atributos planos, sem bateria) existe
só para o teste golden.

## Rodar
```bash
uv venv --python 3.12 .venv && . .venv/bin/activate && uv pip install pygame pygbag

# desktop (rápido, para desenvolver)
cd game && python main.py

# navegador (servidor do pygbag em http://localhost:8000)
cd game && pygbag --template ../web/copaaspirador.tmpl --width 1100 --height 700 --title "Copa Aspirador" .

# gerar build estático para publicar (itch.io, GitHub Pages...): game/build/web/
cd game && pygbag --template ../web/copaaspirador.tmpl --width 1100 --height 700 --title "Copa Aspirador" --build .
```

## Testes
```bash
export SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy
.venv/bin/python tests/test_robots.py                  # modelo de robôs
.venv/bin/python tests/test_robot_mode.py              # motor no modo robôs (atributos diretos, tuning por robô)
.venv/bin/python tests/test_garage.py                  # garagem, peças, progressão e liga
.venv/bin/python tests/test_robot_save.py              # save do Modo Robôs (store, validação, save inválido)
.venv/bin/python tests/test_garage_v2.py              # garage v2: migração do save, slot Módulo, itens, cosméticos, sanitize
.venv/bin/python tests/test_parts_v2.py               # catálogo novo: modelos, relíquias, módulos e sets
.venv/bin/python tests/test_skills.py                  # dados das skills, árvore, carga, tática e força calibrada
.venv/bin/python tests/test_skills_engine.py           # skills no motor: cada uma muda o lance, disparos, FX (~minutos)
.venv/bin/python tests/test_robots_ui.py               # telas do Modo Robôs
.venv/bin/python tests/test_visual.py                  # cores dos clubes, efeitos, pausa, save
.venv/bin/python tests/test_story.py                   # dados da campanha (cenas, textos, torneios, capítulos, recompensas)
.venv/bin/python tests/test_campaign.py                # lógica da campanha (torneios, pity, treino, recompensas)
.venv/bin/python tests/test_campaign_save.py           # save da campanha (validação, reparo, save inválido)
.venv/bin/python tests/test_campaign_migration.py      # migração v1 -> v2 -> v3 (4 saves reais do cap. 5, save terminado) e builds antigos lendo o save novo
.venv/bin/python tests/test_campaign_ui.py             # telas da campanha (menu, mapa por Ato, missões, diálogo, torneio, fim e galeria)
.venv/bin/python tests/test_portraits.py               # retratos e cenários desenhados por código
.venv/bin/python tests/test_prefs.py                   # preferências do jogador (store, valor inválido -> padrão)
.venv/bin/python tests/test_sfx.py                     # som: buffers sintetizados, formato do mixer, throttle, mudo, no-op sem mixer
.venv/bin/python tests/test_crowd.py                   # torcida: locais, reações, extras, LOD, zero Surface por quadro
.venv/bin/python tests/test_camera.py                  # câmera de estádio: prefs/tecla C, layout largo, LOD, zero Surface
.venv/bin/python tests/test_robot_art.py               # robôs: chassis, peças visíveis, cache, FX, local da torcida por modo
.venv/bin/python tests/test_arena.py                   # modificadores de arena da Torre do Pó (desligados fora dela, efeito, zero Surface)
CAMPAIGN_BAL_N=100 .venv/bin/python tests/test_campaign_balance.py   # balanço da campanha por simulação (lento, ver abaixo)
.venv/bin/python tests/sim_harness.py golden --check   # regressão: 80 placares do modo legado
.venv/bin/python tests/sim_harness.py golden-new --check  # regressão: 80 placares do balanço novo
```
O `test_campaign_balance.py` joga a campanha inteira (13 capítulos) N vezes por política: com o N
padrão (300) passa de 20 min nesta máquina; a variável `CAMPAIGN_BAL_N` reduz o N (com 100 roda em
cerca de um terço do tempo, com mais ruído nos alvos).
Os testes de garagem, save e UI não tocam nos saves reais (`~/.soccerpy_*.json`).
Os testes da campanha também não gravam nos saves reais. Os de partida são lentos
(minutos); rode quando mexer em atributos, peças ou balanço:
```bash
.venv/bin/python tests/test_mechanics.py               # efeito dos atributos na partida
.venv/bin/python tests/test_robot_balance.py [-n 70] [--procs 4]  # balanço da equipe (peças/raridades) contra o time base
.venv/bin/python tests/calib_robots.py [--n 100] [--diffs ...] [--fit] [--skills] [--procs 4]  # calibra a simulação estatística da liga contra o motor
.venv/bin/python tests/calib_campaign.py [--n 200] [--skills] [--procs 4]  # calibra a simulação da campanha (SIM_BIAS) contra o motor; pesado, opcional
.venv/bin/python tests/calib_campaign.py --post --n 100  # NG+ e Torre do Pó (com modificadores) no motor x SIMULAR (~20 min)
.venv/bin/python tests/calib_skills.py               # mede a força de cada skill no motor (tabela SKILL_FORCE); muito pesado
```
Utilitários do harness (`tests/sim_harness.py`): `golden`/`golden-new` com
`--write` (regrava a baseline) ou `--check`, `run <ovrA> <ovrB> <n> [seed0] [legacy]`
(simula partidas), `draw` (tempo de desenho por quadro) e `shot <arquivo.png>`
(captura a tela).

## Estrutura
- `game/main.py`: entrada do pygbag (precisa do `import pygame` explícito)
- `game/soccer.py`: partida (física, IA), visual neon, menu e HUD; modificadores de arena da Torre do Pó (`arena=`, desligados por padrão)
- `game/robots.py`: chassis, atributos, fatores usados pelo motor e ajustes (`TUNING`, `TUNING_ROBOTS`)
- `game/garage.py`: Modo Robôs: equipe, robôs, XP/nível, overclock, loja, recompensas e save
- `game/parts.py`: catálogo de peças (slots, modelos, raridades, upgrades, relíquias, módulos, sets) e cosméticos
- `game/skills.py`: skills dos robôs (dados, árvore, gatilhos, efeitos no motor, força calibrada), táticas e itens de partida
- `game/robot_league.py`: liga de 6 times (calendário, tabela, simulação estatística, premiação)
- `game/robot_art.py`: arte dos robôs em campo (sprites pré-renderizados e cache); `Game` delega a ele
- `game/store.py`: armazenamento de texto (`localStorage` no navegador, arquivo em `~` no desktop)
- `game/prefs.py`: preferências do jogador (`soccerpy_prefs_v1`: torcida ALTA/MEDIA/OFF, tecla T; câmera ESTADIO/PERTO, tecla C, ausente = AUTO; som `sfx_vol`/`music_vol` 0-3 e `mute`, teclas S/N/M), com sanitize e padrão
- `game/sfx.py`: efeitos sonoros sintetizados, conversão para o formato do mixer, throttle, volumes/mudo e a música no canal reservado
- `game/music.py`: trilhas chiptune (menu, partida, jingles de vitória/derrota) escritas como texto e sintetizadas compasso a compasso
- `game/crowd.py`: torcida (locais, espectadores pré-renderizados, reações, confete/LED/telão, LOD) e a geometria das câmeras PERTO/ESTÁDIO
- `game/robots_ui.py`: telas do Modo Robôs (hub, garagem, banco, loja, habilidades, mochila, visual, liga)
- `game/career.py` / `game/career_ui.py`: carreira de clubes (liga, mercado, finanças, save) e suas telas
- `game/story.py`: dados da campanha (personagens, times, cenas/diálogos, torneios, capítulos, recompensas); módulo puro, sem pygame. É a fachada da campanha: guarda o Ato 1 e junta `story_a2.py` (Ato 2), `story_a3.py` (Ato 3) e `story_side.py` (missões secundárias), com os dados de cada parte; `story_post.py` guarda as cenas curtas das revanches do NG+
- `game/campaign.py`: lógica da campanha (progresso, torneios de copa/liga/série, chefes/pity, treino, missões secundárias, finais, recompensas, NG+ e Torre do Pó, save v3 com migração do v1/v2)
- `game/campaign_ui.py`: telas da campanha (menu, mapa com abas por Ato, missões secundárias, diálogo, torneio de copa/liga/série, resultado, fim de capítulo, fim com galeria de finais e entrada do NG+, Torre do Pó), reaproveitando garagem/bancada/loja do Modo Robôs
- `game/portraits.py`: retratos e cenários da campanha, desenhados por código
- `docs/`: planejamento e especificações (`docs/INDEX.md`); `docs/img/`: capturas de tela do README
- `tests/`: testes, harness de simulação e baselines (`baseline_golden*.json`) (ficam fora de `game/` para não entrar no pacote do pygbag)

## Notas
- O pygbag exige Python >= 3.9 e só detecta dependências lendo `main.py`.
- `web/copaaspirador.tmpl` é o template da página (fundo escuro nas laterais, para o jogo parecer ocupar a tela toda; F11 abre tela cheia no navegador). Passe sempre as flags `--template/--width/--height/--title` acima ao gerar o build.
- Testando em `localhost`, use o servidor do `pygbag .` (porta 8000); um
  `http.server` comum não serve o runtime/wheel do pygame.
- Na primeira vez o navegador pede um clique na página para liberar o jogo (e o áudio).
