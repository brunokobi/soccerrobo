# Estatísticas da partida, MELHOR DO JOGO e artilharia

Dados individuais dos robôs (gols, assistências, chutes, passes, desarmes, dribles, defesas), o MELHOR DO
JOGO no fim de toda partida assistida e a artilharia acumulada em cada modo.

## Arquivos
- `game/match_stats.py`: módulo puro (sem pygame, sem random global). `PStat` (contadores por robô), resumo
  da partida (`from_engine`, `finish`), nota e MVP (`nota`, `pick_mvp`), estatísticas estimadas do SIMULAR
  (`simulate`, `sim_cfgs`, `seed_of`) e acumulados (`clean_cs`, `add_cs`, `top_scorers`).
- `game/soccer.py`: ganchos `st_*` do motor (só observação) e a tela de fim (faixa do MVP, TAB = painel).
- `game/stats_ui.py`: desenho do cartão MELHOR DO JOGO, da faixa compacta e do painel ESTATÍSTICAS.
- `game/narration.py`: fala `mvp` da Cleide no apito final.
- Acumulados: `garage.py` (robo `cs`, liga `ps`), `robot_league.py` (`credit_stats`, `sim_stats`,
  `sim_round_stats`, `top_scorers`), `campaign.py` (`sim_stats`, `credit_stats`, `tour["ps"]`,
  `tour_scorers`), `career.py` (`round_stats`, `credit_stats`, `scorers`).
- Testes: `tests/test_match_stats.py`.

## Coleta no motor (regra de ouro: só observar)
Os ganchos leem o estado e somam inteiros em `Player.st`; nenhuma chamada a RNG, nenhuma decisão muda.
`soccer.STATS_ON = False` desliga a coleta (o teste joga a mesma partida com e sem e compara placar, eventos,
passos, posições, bateria e o RNG global). Goldens `golden`/`golden-new` 80/80.

| Estatística | Definição |
|---|---|
| gol (G) | o último robô que dominou a bola antes de ela entrar (o mesmo do evento de gol). Gol contra conta só como `og` (e no placar do outro time) |
| assistência (A) | o último passe **certo** do mesmo time para o autor do gol, recebido até `ASSIST_WINDOW` = 10 s de jogo antes do gol, sem o rival dominar a bola no meio. Gol contra não gera assistência. O evento de gol ganha `ast`/`apid` |
| chute (CH) | chute da IA (`ai_shoot`), chute humano na direção do gol (até 650 px, mira dentro da boca + 40 px) ou gol sem chute registrado |
| no gol | virou gol ou o goleiro rival tocou (defesa) |
| passe (PAS certos/tentados) | todo chute que não é finalização (passe, lançamento do goleiro, chutão); certo se o próximo a dominar é companheiro |
| desarme (DES) | tomou a bola no corpo a corpo |
| drible | o rival tentou o desarme e falhou (1 por marcador e por posse) |
| defesa (DEF, goleiro) | segurou ou espalmou um chute do rival; se a bola entra mesmo assim, não conta |
| posse % | tempo de jogo com o último time a dominar a bola |

Médias medidas no motor (30 partidas 65x65, por time): 16,5 chutes, 6,8 no gol, 11,5 passes (5,9 certos),
20 desarmes, 21 dribles, 5,7 defesas; ~8% dos gols têm assistência (a IA conduz e chuta muito mais do que
passa).

Custo: 0,0359 → 0,0358 ms/step (padrão novo) e 0,0302 → 0,0300 (legado), dentro do ruído; o resumo é montado
uma vez no apito final (`st_finish`).

## Nota e MELHOR DO JOGO
`pontos = 30 G + 20 A + 8 DEF + 4 no gol + 3 DES + 1 drible + 1 passe certo - 20 gol contra`;
`nota = 5 + pontos/30` (0 a 10, uma casa). MVP = maior pontuação; empate → time vencedor, mais gols, mais
assistências, mais defesas, mais desarmes, time da casa, ordem no time. Determinístico.

## Onde aparece
- **Fim de toda partida assistida** (amistoso, Modo Robôs, campanha/treino/Torre/missões, carreira): faixa
  MELHOR DO JOGO (retrato do robô = o corpo já pré-renderizado da partida, nome, time, nota e números) acima
  do placar; **TAB** troca para o cartão do MVP + painel ESTATÍSTICAS (times e robô a robô). A faixa do
  narrador some no painel. A Cleide anuncia o melhor do jogo no apito final, no lugar do comentário do fim
  (uma fala, sem spam).
- **Card do resumo** (Modo Robôs, campanha, carreira): linha MELHOR DO JOGO; botão **ESTATÍSTICAS (TAB)**
  troca GOLS/RECOMPENSAS/EXPERIÊNCIA (ou o resultado da carreira) pelo cartão + painel; RESUMO (TAB) volta.
  Os gols listam a assistência ("Bolt (assist.: Turbo)").
- Telas sem `pygame.Surface` por quadro (só `pygame.draw`, textos do cache, sprites já cacheados).

## SIMULAR
Sem motor: `match_stats.simulate` gera números plausíveis a partir do placar já decidido e dos atributos/papéis
(pesos por papel e atributo; gols e assistências proporcionais), com `random.Random` **privado** de semente
derivada da partida (`seed_of`). Nunca usa o RNG da liga/campanha/carreira: placares, recompensas, loja e
calibração não mudam (teste). O painel marca "estimadas: jogo simulado".

## Acumulados e saves (campos opcionais, sem subir versão; save antigo = zeros; lixo descartado)
| Modo | Onde | Campo |
|---|---|---|
| Modo Robôs / campanha | totais do robô (ficha da garagem: "Carreira: G, A, MVP, jogos") | `robo.cs = {"g","a","mvp","j"}` (garage v2) |
| Modo Robôs | artilharia da liga em andamento (todos os times, jogos assistidos e simulados): botão ARTILHARIA no painel TABELA (top 5) e "Nesta liga" na ficha | `league.ps = [[time, chave, nome, g, a, mvp]]` (chave = id do robô no time do jogador, posição 0-4 nos outros) |
| Campanha | artilheiro do torneio atual (linha no painel do grupo/liga) | `tour.ps = [[lado, time, robô, chave, g, a]]` (save v3) |
| Carreira | gols/assistências/MVP da temporada (zeram no fim) e da carreira; ARTILHARIA na aba TABELA (top 8 da divisão), G/A no ELENCO, artilheiro da divisão no fim da temporada | jogador `sg, sa, smvp, tg, ta, tmvp` |

Um save inválido continua nunca sendo sobrescrito (as regras de `.bad` de cada modo não mudaram).

## Limitações
- Assistências são raras no motor (a IA quase não passa antes de finalizar); o SIMULAR imita isso (12%).
- Desarmes e dribles são muitos por partida (a bola troca de dono o tempo todo) e por isso pesam pouco na nota.
- Pênaltis da campanha não entram nas estatísticas (são decididos fora do motor).
