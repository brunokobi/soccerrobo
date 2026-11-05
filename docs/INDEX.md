# Documentação - Copa Aspirador

Planejamento e especificações do jogo. O código e os comandos do dia a dia estão no
[README](../README.md).

| Documento | Conteúdo |
|---|---|
| [roadmap.md](roadmap.md) | Fases do projeto, objetivos e tamanho da Fase 4 (Campanha Expandida), princípios que não podem quebrar e marcos jogáveis (M1-M5) |
| [specs/campanha-expandida.md](specs/campanha-expandida.md) | A campanha atual vira o Ato 1; Ato 2 (Superliga Limpex, caps. 6-9) e Ato 3 (Copa dos Campeões, caps. 10-13); 7 personagens novos, formatos de torneio novos, escolhas com consequência, 3 finais, missões secundárias, migração de saves, curva de dificuldade e economia |
| [specs/itens-e-habilidades.md](specs/itens-e-habilidades.md) | Peças de 14 para ~36 modelos, 8º slot "Módulo", sets, relíquias únicas, consumíveis de partida, cosméticos e o sistema de 16 skills dos robôs (gatilhos, efeitos no motor, cooldown, custo de bateria, como se ganham), integração no motor sem quebrar os goldens, calibração e garage v2 |
| [specs/visual-desenhos-e-torcida.md](specs/visual-desenhos-e-torcida.md) | Torcida nas arquibancadas (geometria, técnica sem Surface por frame, orçamento de desempenho, reações por evento, densidade por capítulo, "som visual", telão), robôs com peças visíveis e animações, retratos e cenários mais detalhados, e como testar |
| [baseline-fase4.md](baseline-fase4.md) | Medições de referência antes da Fase 4 (commit 8a467a3): `draw_ms`, `menu_ms`, `ms_step`, goldens e resumo da calibragem da campanha |
| [img/](img/) | Capturas de tela usadas no README (menu, partida, campanha, garagem, habilidades, Mochila, cosméticos). Para regerar: rode `tests/test_robots_ui.py`, `tests/test_campaign_ui.py` e `tests/sim_harness.py camera-shots` com `SOCCERPY_SHOTS_DIR=<pasta>` e copie as imagens escolhidas |
| [specs/plano-de-implementacao.md](specs/plano-de-implementacao.md) | Ondas 0, A (visual), B (itens/skills), C (campanha), D (pós-campanha) em passos pequenos com arquivos e validação; estratégia de testes; riscos; decisões para o dev |

## Estado
- Fases 1, 2 e 3: prontas e publicadas em https://copaaspirador.brunokobi.tech
- Fase 4 (Campanha Expandida): **Onda A (torcida, robôs detalhados, retratos, cenários e câmera de
  estádio) e Onda B (peças novas, sets, relíquias, slot Módulo, 16 skills, itens de partida, Mochila e
  cosméticos) prontas**. Onda C (Atos 2 e 3) em andamento na branch `feat/fase4-onda-c-estrutura`:
  C1-C8 prontos: estrutura (fachada do `story.py`, save v2 com migração, torneios de liga e série,
  nós condicionais, finais, missões, mapa por Ato, recompensas com variante) e o **Ato 2 inteiro
  jogável** (caps. 6-9: Taça de Acesso, Superliga, Playoffs e O Clone, com as escolhas B1, B2 e B3,
  Vô Nestor, Dra. Valquíria, Gabi Trovão, Dona Odete, Mestre Ogawa e Zé Perfeito). O Ato 3 (caps.
  10-13) aparece como "em breve"; quem termina o conteúdo fica esperando no primeiro rascunho
  (posição válida de save). C9 pronto: economia do Ato 2 (tiers 4-6, loja, XP até o nível 15, bônus
  da escolha B2) e calibração no motor (tabela em `tests/calib_campaign.py`); a Força real do Ato 2 é
  74 → 83,5, ~8 pontos acima da spec, por causa das skills. **Ponto de atenção:** quem nunca evolui o
  time (não gasta sucata nem PH) trava no Ato 2; ideias em aberto: equipar sozinhas as skills de
  história ou pity maior no Ato 2. C10 pronto: caps. 10 (Intercâmbio) e 11 (A Fábrica, em duas
  versões pela escolha B2, com a escolha B4) jogáveis e o X-Ômega. C11 pronto: caps. 12 (Copa dos
  Campeões) e 13 (O Chip Zero) e os **3 finais** (Garagem Livre, Contrato Dourado e o secreto O
  Chinelo Estrutural, que depende das 4 Fitas do Vô do C13). **A campanha tem começo, meio e fim**
  (P-13, 132 cenas). C12 pronto: Ato 3 calibrado no motor (Força 85 → 94; acima de ~85 o motor
  "achata", então os adversários do Ato 3 ficam quase planos e o SIMULAR ganhou uma correção para Força
  alta; tabela em `tests/calib_campaign.py`). O ponto de atenção do Ato 2 piora no Ato 3: quem nunca
  evolui o time não termina a campanha. Próximo: C13 (14 missões secundárias). Deploy pendente: falta
  saber onde o site é hospedado.
  Onda D (pós-campanha) planejada. Passos em [specs/plano-de-implementacao.md](specs/plano-de-implementacao.md)
- Fase 5 (Editor de firmware): planejada
