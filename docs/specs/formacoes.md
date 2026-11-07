# Formações

O time do jogador escolhe uma de 5 formações antes da partida, em todos os modos. A formação muda só
onde cada robô fica e para onde volta durante o jogo (posição base + avanço/recuo do bloco); papéis
(GOL/DEF/MEI/MEI/ATA), chassis e atributos não mudam.

## Arquivos
| Arquivo | Papel |
|---|---|
| `game/formations.py` | dados compartilhados (puro, sem pygame): `FORMATIONS`, `ORDER`, `DEFAULT` = `"equilibrada"`, `get`, `clean` (sanitize dos saves), `cycle`, `engine` (o que o motor recebe), `label` |
| `game/formation_ui.py` | desenho compartilhado: `draw_pitch` (mini-campo com os 5 robôs) e `draw_selector` (seletor compacto); `key_step` (teclado) |
| `game/friendly.py` / `game/friendly_ui.py` | Amistoso: reexporta os dados (`friendly.FORMATIONS`) e usa o mesmo mini-campo, maior |
| `game/garage.py`, `game/career.py` | campo `formation` no save e `set_formation` |
| `game/campaign_ui.py`, `game/robots_ui.py`, `game/career_ui.py` | o seletor em cada tela |
| `tests/calib_formations.py` | balanceamento no motor real (CPU x CPU, mesmas forças) |

## As 5 formações
| id | Seletor | Ideia |
|---|---|---|
| `equilibrada` | EQUILIBRADA 1-2-1 | a de sempre (padrão): um atrás, dois no meio |
| `retranca` | RETRANCA 2-1-1 | dois zagueiros fechando o meio |
| `ofensiva` | OFENSIVA 1-1-2 | dois atacantes abertos na frente |
| `quadrado` | QUADRADO 2-2 | duas linhas de dois, fechado |
| `pressao` | PRESSÃO 1-2-1 | linha alta, aperta a saída do rival |

Os parâmetros (`pts` e `push` de cada formação) estão em `game/formations.py`; a RETRANCA (zagueiros em
y 0,44/0,56), a OFENSIVA, o QUADRADO e a PRESSÃO foram reajustados nesta versão (o QUADRADO original, sem
ninguém no corredor central, tinha 9% de aproveitamento contra a EQUILIBRADA). A EQUILIBRADA é o
`soccer.FORMATION` de sempre.

## Balanceamento
`tests/calib_formations.py` (motor real, CPU x CPU, mesmas forças, desenho pareado). Aproveitamento
(V+E/2, %) contra a EQUILIBRADA, Modo Robôs/Campanha:

| Formação | Força 45 | 60 | 75 | 90 |
|---|---|---|---|---|
| RETRANCA | 51,7 | 42,2 | 30,4 | 11,2 |
| OFENSIVA | 54,2 | 44,6 | 29,9 | 27,8 |
| QUADRADO | 54,8 | 46,0 | 40,4 | 38,7 |
| PRESSÃO | 50,2 | 50,6 | 54,6 | 67,0 |

- Até Força ~75 (campanha) nenhuma formação passa de +5 pontos sobre a EQUILIBRADA: a campanha não fica
  mais fácil. Com robôs fortes as formações que tiram gente do corredor central perdem rendimento, e a
  PRESSÃO ganha no pós-campanha (+17 em Força 90).
- Confrontos diretos (Força 60): RETRANCA vence OFENSIVA e QUADRADO, perde da PRESSÃO; QUADRADO vence a
  PRESSÃO; o QUADRADO é o jogo mais aberto (mais gols a favor e contra).
- **SIMULAR fiel ao motor:** `formations.SIM_DF` converte o efeito medido em pontos de Força
  (dF = (aproveitamento - 50) / 1,8, interpolado pela Força do time) e `Garage.match_F()` o soma: muda a
  "Sua Força" mostrada e o SIMULAR da campanha, do treino, da Torre e do Modo Robôs. A carreira soma o mesmo
  dF ao ataque e à defesa do clube no `Career.sim_match`. A padrão não tem entrada (dF = 0): Força,
  SIMULAR e a calibração da campanha (`tests/calib_campaign.py`) ficam exatamente como antes.

## Onde aparece
| Modo | Tela | Onde |
|---|---|---|
| Amistoso (1 e 2) | tela de escolha antes da partida | formação dos dois lados, com mini-campo grande |
| Campanha | painel da partida do torneio (copa, liga, série), TREINO e Torre do Pó | acima de ASSISTIR |
| Modo Robôs | aba LIGA, painel do próximo jogo (só quando há jogo) | acima de ASSISTIR |
| Carreira | aba INÍCIO, painel da próxima partida | acima de ASSISTIR |

Seletor: `FORMAÇÃO: < EQUILIBRADA 1-2-1 >` com mini-campo. Clique na seta da esquerda volta, na da
direita ou no corpo avança. Teclado: setas esquerda/direita, **F** (próxima) e **Shift+F** (anterior).
Na Campanha e no Modo Robôs o seletor não responde com a Mochila ou o Visual abertos. Na Campanha, a troca
atualiza na hora a partida já montada (torneio, treino ou Torre).

## Motor
- `formations.engine(id)` devolve `None` para a padrão (ou id desconhecido) e o dict da formação para as
  outras; `soccer.Team(formation=...)` só troca as posições base e soma o `push` ao avanço do bloco.
- O cfg da partida (`Garage.match_cfg`, `Career.match_cfg`) só ganha `"formation"` quando ela não é a
  padrão: com a padrão o motor é exatamente o de sempre (goldens 80/80).
- O adversário controlado pela CPU usa sempre a padrão (no Amistoso, quem escolhe os dois lados é o jogador).
- O SIMULAR (resultado estatístico pela Força) soma o efeito medido da formação (ver Balanceamento).

## Saves
Campo opcional `"formation"` (id de `formations.FORMATIONS`), padrão `"equilibrada"`. Save antigo sem o
campo, ou com id inválido, carrega com a padrão (`formations.clean`).
- **Modo Robôs**: `garage.FIELDS` da garage v2, sem subir a versão (`soccerpy_robots_v1`).
- **Campanha**: vai junto da garagem dentro do save da campanha (`soccerpy_campaign_v1`, v3); a formação da
  campanha é independente da do Modo Robôs.
- **Carreira**: `Career.FIELDS` (o save da carreira não tem versão).
- **Amistoso**: prefs `fr_f0`/`fr_f1` (com os times `fr_t0`/`fr_t1`).

## Testes
- `tests/test_friendly.py`: dados, posições no motor, cfg com a padrão idêntico ao de sempre e aplicado
  com as outras, tela, prefs.
- `tests/test_campaign_ui.py`: `test_formation_selector_tourney_training_and_save` (torneio, treino, save)
  e `test_formation_old_campaign_save_loads_default`.
- `tests/test_robots_ui.py`: `test_formation_selector_robots_hub_and_save`,
  `test_formation_garage_save_migration_and_sanitize` e `test_formation_selector_career_home_and_save`.
- Com `SOCCERPY_SHOTS_DIR=<pasta>` os testes de seletor gravam `formacao_torneio.png` e
  `formacao_robos.png` (as capturas `docs/img/formacao-campanha.png` e `docs/img/modo-robos-liga.png`).
