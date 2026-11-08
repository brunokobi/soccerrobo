# Plano - publicar o Copa Aspirador no CrazyGames

Status: **proposta** (08/11/2026). Nada disto foi feito ainda. Os números do portal (repasse,
limites, pagamento) vêm de guias de terceiros e precisam ser conferidos nos termos oficiais
([docs.crazygames.com](https://docs.crazygames.com)) antes de assinar.

## 1. Por que o CrazyGames
- O jogo já roda no navegador (pygbag/WASM), que é o formato do portal.
- O portal aceita jogos maiores que o Poki: guias citam até 50 MB no carregamento inicial (20 MB para
  aparecer na home de celular), 250 MB no total e até 1.500 arquivos. O jogo hoje tem ~7 MB de pacote
  mais o runtime do pygbag.
- É aberto a jogos indie e paga uma parte da receita de anúncios. Um termo de 2026 citava 60% dos
  anúncios e 70% das compras no jogo para o desenvolvedor.
- O pagamento é mensal, via Tipalti, a partir de cerca de €100 acumulados (fonte não oficial).

## 2. Como funciona a publicação
1. **Cadastro** no Developer Portal (pessoa física, e-mail).
2. **Envio** do build HTML5 com capa, descrição, controles e categoria.
3. **Revisão (QA)** técnica e de qualidade feita pelo time do portal.
4. **Basic Launch:** o jogo vai ao ar para uma parte do público, ainda **sem receita**. O portal mede
   tempo de jogo, retenção e avaliação.
5. **Full Launch:** se as métricas forem boas e o SDK estiver completo, passa por um QA completo, a
   monetização é ligada e começa o repasse.

Exclusividade: o portal prefere jogos que ainda não foram publicados em outros portais. Mandar para o
CrazyGames **antes** de qualquer outro portal (Poki, GameDistribution). O site próprio
(copaaspirador.brunokobi.tech) pode continuar, mas confirmar isso nos termos.

## 3. O que precisa mudar no jogo

### 3.1 Direitos dos áudios (obrigatório, bloqueia a revisão)
Trocar por sons livres (CC0, ex. Freesound), gravações próprias ou síntese do `sfx.py`. Depois de trocar,
rodar `tools/normalizar_audio.sh` (regra: compacto e volume nivelado) e conferir `FILE_SFX`/`STREAMS`.

| Arquivo | Problema | Ação |
|---|---|---|
| `derrota1.ogg` | som do League of Legends | trocar |
| `inicio3.ogg` | vinheta do Super Star Soccer (Konami) | trocar |
| `defesa3.ogg` ("ooo that's strong"), `trave3.ogg` ("oh my god"), `lamento3.ogg` ("acorda, cara"), `lamento2.ogg` ("gol dos caras, mano") | áudios de meme, direitos incertos | trocar |
| `palmas2.ogg` (palmas Real Madrid) e demais gravações de torcida/gol de origem desconhecida | origem e licença a confirmar | confirmar a licença ou trocar |
| `menu1.ogg` ("Era do Metal"), `partida_musica.ogg` ("Into the Iron Horizon"), `menu2/3`, `copas`, `interno1/2`, `submenus` | músicas: se geradas por IA (Suno, Udio etc.), uso comercial depende do plano | guardar a prova da licença comercial ou trocar |
| `vitoria1.ogg` (ElevenLabs) | uso comercial depende do plano | guardar a prova da licença |

Criar `docs/licencas-audio.md` com origem e licença de cada arquivo de `game/audio/`.

### 3.2 Idioma inglês (muito recomendado)
O público do portal é mundial; só em português o alcance cai muito. O texto do jogo está espalhado e é
grande: a campanha tem ~2.000 falas (`story*.py`, ~2.950 linhas), mais menus, narração
(`narration.py`), peças, skills e telas.

- Fase A: módulo `game/i18n.py` com tabela de textos da interface (menus, botões, telas, narração,
  peças, skills) e escolha de idioma (pref `lang`, padrão pelo navegador; tecla/opção no menu).
- Fase B: campanha traduzida por arquivos paralelos (`story_en.py` etc.) com os mesmos ids de cena.
- Alternativa para lançar antes: Amistoso, Modo Robôs e Carreira em inglês, e a campanha marcada como
  "Portuguese only" até a Fase B.
- Fonte: `Font(None)` cobre Latin-1, então inglês não precisa de fonte nova.

### 3.3 SDK do CrazyGames (obrigatório para o Full Launch)
- Carregar o SDK no template `web/copaaspirador.tmpl` (tag `<script>` do SDK v3) e chamar do Python
  pelo `platform.window` do pygbag, num módulo `game/portal.py` que vira no-op fora do portal
  (desktop, site próprio e testes).
- Chamadas:
  - `loadingStart` / `loadingStop` no carregamento;
  - `gameplayStart` / `gameplayStop` ao entrar e sair das partidas e telas de jogo;
  - anúncio `midgame` entre partidas (ex. ao sair do card do resumo), nunca no meio da partida;
  - anúncio `rewarded` opcional (ex. "assista e ganhe +sucata"), sem desequilibrar a campanha;
  - `happytime` opcional em vitórias de chefe/final.
- Durante o anúncio: pausar o jogo e silenciar todo o som (`sfx` mudo temporário), e voltar ao estado
  anterior depois.
- Saves: hoje ficam no `localStorage` (store.py). Avaliar o módulo de dados do SDK para salvar na conta
  do jogador (cross-device); se usado, migrar sem perder saves locais.
- Testes: `tests/test_portal.py` com um SDK falso (registra as chamadas), garantindo que nada quebra sem
  o SDK e que goldens seguem 80/80.

### 3.4 Build para o portal
- **Runtime sem CDN externo:** o pygbag baixa `pythons.js`/wasm de `pygame-web.github.io`. Conferir se o
  portal aceita requisições externas; se não, empacotar o runtime junto do build (opção de CDN local do
  pygbag) e medir o tamanho total.
- **Sem links e marcas externas:** tirar do template o domínio próprio e qualquer link para fora.
- **Tela de carregamento:** manter rápida; medir o tempo até o menu numa conexão média.
- Script `tools/build_crazygames.sh`: build do pygbag com o template do portal, sem `versionar_build.sh`
  (o portal versiona), e um `.zip` pronto para upload.

### 3.5 Celular (opcional, aumenta muito o público)
- Hoje o jogo é só teclado e mouse. Controles por toque (botões virtuais de mover/chutar/passar e toque
  nos menus) liberariam o público de celular.
- Pode ficar para depois do primeiro lançamento (marcar o jogo como "desktop only").

### 3.6 Material de página
- Nome em inglês (ex. "Vacuum Cup" / "Robo Vacuum Soccer") mantendo "Copa Aspirador" como subtítulo.
- Capa e miniaturas nos tamanhos pedidos pelo formulário (pixel art dos personagens e uma partida no
  estádio).
- Descrição curta e longa, lista de controles, categoria (Sports / Soccer), tags.
- Vídeo curto (15-30 s) de gameplay: gol com a narração e a torcida.

## 4. Cadastro e pagamento (com o dev)
- Conta no CrazyGames Developer Portal (pessoa física).
- Dados de pagamento no Tipalti: conta bancária no Brasil (SWIFT/IBAN) ou PayPal.
- Formulário fiscal do pagador (normalmente W-8BEN, declarando não residente nos EUA).
- No Brasil: rendimento do exterior como pessoa física vai no carnê-leão mensal e na declaração anual.
  Confirmar com um contador.

## 5. Ordem sugerida
1. Auditoria e troca dos áudios + `docs/licencas-audio.md` (3.1).
2. `game/portal.py` + SDK no template + anúncios entre partidas + mudo/pausa no anúncio (3.3).
3. Build do portal sem CDN externo e sem links (3.4).
4. Interface em inglês (3.2 Fase A).
5. Página: nome, capa, descrição, vídeo (3.6).
6. Cadastro e envio; Basic Launch; acompanhar métricas.
7. Depois, conforme as métricas: campanha em inglês (3.2 Fase B) e controles de toque (3.5).

## 6. Invariantes do projeto (continuam valendo)
Goldens `golden` e `golden-new` 80/80; nada de `random` global; zero `pygame.Surface` por quadro;
testes nunca gravam `~/.soccerpy_*.json`; áudios compactos e nivelados; nada do portal ativo fora do
portal (desktop, site próprio e testes seguem iguais).

## 7. Expectativa de receita
A receita vem de anúncios por partida jogada e depende só do volume de jogadores. Alguns milhares de
partidas por mês rendem de poucos dólares a dezenas; valores relevantes pedem centenas de milhares de
partidas. Divulgação (vídeos curtos dos gols e da narração) é o que mais muda esse número.

## Fontes
- [CrazyGames Docs](https://docs.crazygames.com)
- [Guia CrazyGames 2026 (Cinevva)](https://app.cinevva.com/guides/publish-game-crazygames)
- [Onde publicar jogos HTML5 (Summer Engine)](https://www.summerengine.com/es/make-great-games/publish-an-html5-game)
- [Poki vs CrazyGames vs GameDistribution (Playgama)](https://playgama.com/blog/business-faqs/poki-vs-crazygames-vs-gamedistribution-revenue-share/)
