"""Nomes de robos aspiradores para a Carreira (dados puros, sem pygame e sem RNG).

O nome de um robo sai so do id dele (`name_for(pid)`), entao e deterministico: o mesmo save sempre gera os mesmos
nomes, a geracao nao consome o RNG da carreira e a migracao dos saves antigos renomeia por id.

Espaco de nomes (NAMES, ~3,6 mil, todos <= NAME_MAX caracteres, latin-1, sem repeticao), em blocos:
  1. os nomes-base sozinhos ("Zumbido", "Faisca", "Rodinha"...), embaralhados por uma permutacao fixa;
  2. nome-base + sufixo de modelo ("Turbo Mk2", "Vassoura-7", "Grilo Jr"...) e codigos de serie ("RX-07",
     "ZK-42"...), misturados por outra permutacao fixa.
Os ids sao sequenciais, entao uma carreira nova (ids 1..~220) so tem nomes-base; os robos que chegam depois
(juniores, mercado) pegam os blocos seguintes. Dois ids distintos so repetem nome depois de len(NAMES) ids
(dezenas de temporadas, quando o mais antigo ja se aposentou); dentro do mesmo clube `unique_name` desvia.
"""

NAME_MAX = 12

BASE = (
    # limpeza e o proprio aspirador
    "Vassoura", "Rodo", "Escova", "Esfregão", "Flanela", "Balde", "Espanador", "Poeira", "Pozinho", "Ciclone",
    "Filtro", "Sucção", "Bocal", "Sabão", "Bolha", "Espuma", "Faxina", "Brilho", "Cera", "Vapor",
    "Migalha", "Farelo", "Fiapo", "Cisco", "Tapete", "Capacho", "Rodapé", "Ralo", "Esponja", "Lustra",
    "Aspira", "Varredor", "Coletor", "Saquinho", "Pano", "Lixinho", "Tampinha", "Cantinho", "Faxineiro",
    # pecas e eletronica
    "Pistão", "Bobina", "Sensor", "Ventoinha", "Motor", "Rotor", "Turbina", "Chip", "Bit", "Byte",
    "Pixel", "Diodo", "Fusível", "Capacitor", "Resistor", "Bateria", "Pilha", "Volt", "Watt", "Ohm",
    "Ímã", "Dínamo", "Parafuso", "Porca", "Arruela", "Mola", "Eixo", "Roda", "Rodinha", "Esteira",
    "Polia", "Alavanca", "Biela", "Cabo", "Plugue", "Tomada", "Antena", "Radar", "Sonar", "Laser",
    "Led", "Neon", "Circuito", "Placa", "Solda", "Rebite", "Trava", "Gatilho", "Botão", "Chave",
    "Relé", "Servo", "Torque", "Giro", "Pulso", "Sinal", "Código", "Cursor", "Clique", "Atalho",
    "Kernel", "Cache", "Buffer", "Modem", "Ping", "Firmware", "Joystick", "Teclado", "Mouse", "Pendrive",
    "Rolimã", "Engrenagem", "Catraca", "Manivela", "Turbo", "Nitro", "Mecha", "Drone", "Sonda", "Cápsula",
    "Módulo", "Núcleo", "Vetor", "Matriz", "Prisma", "Cubo", "Esfera", "Hélice", "Bússola", "Âncora",
    # sons
    "Zumbido", "Zunido", "Ronco", "Chiado", "Estalo", "Bip", "Vrum", "Zum", "Tique", "Plim",
    "Vupt", "Tchan", "Bum", "Trec", "Clec", "Fiu", "Pof", "Zás", "Toc", "Zunzum",
    # tempo, ceu e materiais
    "Faísca", "Chispa", "Raio", "Trovão", "Relâmpago", "Tufão", "Furacão", "Brisa", "Vento", "Rajada",
    "Garoa", "Granizo", "Neblina", "Orvalho", "Tornado", "Cometa", "Meteoro", "Órbita", "Eclipse", "Quasar",
    "Pulsar", "Astro", "Fagulha", "Brasa", "Chama", "Lava", "Magma", "Geada", "Gelo", "Cristal",
    "Quartzo", "Cobalto", "Titânio", "Cromo", "Níquel", "Zinco", "Cobre", "Bronze", "Ferro", "Aço",
    "Lata", "Sucata", "Ferrugem", "Grafite", "Carbono", "Silício", "Plasma", "Fóton", "Átomo", "Próton",
    "Elétron", "Nêutron", "Quark", "Íon", "Turbilhão", "Ventania", "Redemoinho", "Nebulosa", "Vulcão", "Poente",
    # bichos pequenos
    "Grilo", "Besouro", "Vagalume", "Formiga", "Cupim", "Tatu", "Ouriço", "Pinguim", "Tucano", "Gambá",
    "Quati", "Sagui", "Lontra", "Castor", "Coruja", "Morcego", "Jabuti", "Siri", "Polvo", "Mosquito",
    "Libélula", "Cigarra", "Joaninha", "Lagarta", "Caracol", "Lesma", "Minhoca", "Camaleão", "Lagartixa", "Sapo",
    "Perereca", "Piranha", "Arraia", "Bagre", "Sardinha", "Furão", "Hamster", "Texugo", "Guaxinim", "Esquilo",
    "Morsa", "Foca", "Marreco", "Pardal", "Colibri", "Pica-pau", "Tamanduá", "Preá", "Capivara", "Calango",
    # comidinhas
    "Pipoca", "Paçoca", "Biscoito", "Bolacha", "Torrada", "Pudim", "Quindim", "Cocada", "Pamonha", "Canjica",
    "Pastel", "Coxinha", "Empada", "Jujuba", "Chiclete", "Pirulito", "Granola", "Tapioca", "Cuscuz", "Mingau",
    "Bombom", "Sequilho", "Torresmo", "Pé-de-moça", "Rapadura", "Goiabada", "Pinhão", "Amendoim", "Caju", "Açaí",
    # brinquedos, ferramentas e barulho
    "Pião", "Ioiô", "Bumerangue", "Catapulta", "Estilingue", "Foguete", "Trampolim", "Bólido", "Flecha", "Dardo",
    "Biruta", "Leme", "Bigorna", "Martelo", "Alicate", "Serrote", "Furadeira", "Broca", "Lixa", "Torno",
    "Prensa", "Grampo", "Clipe", "Tachinha", "Sirene", "Buzina", "Apito", "Sineta", "Chocalho", "Pandeiro",
    "Tambor", "Cuíca", "Agogô", "Berimbau", "Patinete", "Carrinho", "Trenó", "Tobogã", "Gangorra", "Bolinha",
    "Pingo", "Pitoco", "Xodó", "Zigue", "Zague", "Fuzuê", "Muvuca", "Treco", "Bugiganga", "Geringonça",
)

SUFFIXES = (" Mk2", "-7", " Jr", " X", " Pro", "-9", " Mk3", " Max", " Neo", " Turbo", "-3", " Zero")
CODE_PREFIXES = ("RX", "ZK", "VK", "TX", "KB", "QR")      # LX/PR/PT/X9 sao da campanha


def _permute(items, mult):
    """Permutacao fixa (sem RNG): posicao j recebe items[(j * mult) % n], mult coprimo com n."""
    n = len(items)
    if n < 2:
        return list(items)
    m = mult
    while _gcd(m, n) != 1:
        m += 1
    return [items[(j * m) % n] for j in range(n)]


def _gcd(a, b):
    while b:
        a, b = b, a % b
    return a


def _build():
    out, seen = [], set()

    def add(block, mult):
        for nm in _permute([x for x in block if len(x) <= NAME_MAX and x not in seen], mult):
            if nm not in seen:
                seen.add(nm)
                out.append(nm)

    add(BASE, 97)
    rest = [b + suf for suf in SUFFIXES for b in BASE if b != suf.strip()]
    rest += ["%s-%02d" % (p, n) for p in CODE_PREFIXES for n in range(1, 100)]
    add(rest, 1361)                     # modelos e codigos misturados (passo grande: vizinhos bem diferentes)
    return tuple(out)


NAMES = _build()


def name_for(pid, attempt=0):
    """Nome de robo do id `pid` (inteiro >= 1). attempt > 0 = alternativas para desviar de repeticao."""
    try:
        k = int(pid)
    except (TypeError, ValueError):
        k = 1
    return NAMES[(k - 1 + attempt * 1009) % len(NAMES)]


def unique_name(pid, taken):
    """name_for(pid) desviando dos nomes em `taken` (os outros robos do clube)."""
    for attempt in range(64):
        nm = name_for(pid, attempt)
        if nm not in taken:
            return nm
    return name_for(pid)
