# Documentação - Copa Aspirador

Planejamento e especificações do jogo. O código e os comandos do dia a dia estão no
[README](../README.md).

| Documento | Conteúdo |
|---|---|
| [roadmap.md](roadmap.md) | Fases do projeto, objetivos e tamanho da Fase 4 (Campanha Expandida), princípios que não podem quebrar e marcos jogáveis (M1-M5) |
| [specs/campanha-expandida.md](specs/campanha-expandida.md) | A campanha atual vira o Ato 1; Ato 2 (Superliga Limpex, caps. 6-9) e Ato 3 (Copa dos Campeões, caps. 10-13); 7 personagens novos, formatos de torneio novos, escolhas com consequência, 3 finais, missões secundárias, migração de saves, curva de dificuldade e economia |
| [specs/itens-e-habilidades.md](specs/itens-e-habilidades.md) | Peças de 14 para ~36 modelos, 8º slot "Módulo", sets, relíquias únicas, consumíveis de partida, cosméticos e o sistema de 16 skills dos robôs (gatilhos, efeitos no motor, cooldown, custo de bateria, como se ganham), integração no motor sem quebrar os goldens, calibração e garage v2 |
| [specs/visual-desenhos-e-torcida.md](specs/visual-desenhos-e-torcida.md) | Torcida nas arquibancadas (geometria, técnica sem Surface por frame, orçamento de desempenho, reações por evento, densidade por capítulo, "som visual", telão), robôs com peças visíveis e animações, retratos e cenários mais detalhados, e como testar |
| [specs/som.md](specs/som.md) | Fase 6 - Som: catálogo de efeitos e onde tocam, trilhas chiptune, síntese (stdlib, 22050 Hz), formato do mixer, prefs (M/S/N), limites de vozes e throttle, navegador (pygbag) e medições |
| [baseline-fase4.md](baseline-fase4.md) | Medições de referência antes da Fase 4 (commit 8a467a3): `draw_ms`, `menu_ms`, `ms_step`, goldens e resumo da calibragem da campanha |
| [img/](img/) | Capturas de tela usadas no README (menu, partida, campanha, garagem, habilidades, Mochila, cosméticos). Para regerar: rode `tests/test_robots_ui.py`, `tests/test_campaign_ui.py` e `tests/sim_harness.py camera-shots` com `SOCCERPY_SHOTS_DIR=<pasta>` e copie as imagens escolhidas |
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
- Fase 6 (Som): **pronta** — efeitos e música sintetizados por código (`game/sfx.py`, `game/music.py`),
  sons gravados em `game/audio/` (músicas de menu/robôs/copas, torcida, gol, apito, trave, motor e desligar dos robôs), mudo (M) e volumes (S/N) nas prefs, testado no desktop e no navegador (pygbag); ainda não publicada
