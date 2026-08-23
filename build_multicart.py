
#!/usr/bin/env python3
"""
build_all.py v5 - Gerador COMPLETO de Cartucho MSX Multi-ROM (ASCII8)

INTERATIVO + AUTOMATIZADO:
  1. Rode: python build_all.py
  2. Digite a lista de jogos no formato:
     Nome,arquivo.rom, Nome2,arq2.rom//fim
  3. Ele gera menu.asm, compila, e monta multicart.rom

Formato de entrada:
  - Pares: Nome do Jogo, arquivo.rom
  - Use aspas para nomes com virgula: "King's Valley",kvalley.rom
  - Termine com //fim
  - Exemplo:
    "King's Valley",kvalley.rom, Knightmare,knightmare.rom//fim

Teclas no menu MSX:
  Jogos 1-9:   teclas '1'-'9'
  Jogo 10:     tecla '0'
  Jogos 11-20: teclas 'A'-'J'

Limites:
  - Mapper ASCII8: ate 2MB (256 bancos de 8KB)
  - Menu: ate 20 jogos
  - Jogos: 8KB, 16KB ou 32KB cada (ROMs simples)
"""

import os
import sys
import math
import subprocess


# ==============================================================
# CONSTANTES
# ==============================================================
BANK_SIZE = 8192
MAX_GAMES = 20
MENU_ASM = "menu.asm"
MENU_ROM = "menu.rom"
OUTPUT_ROM = "multicart.rom"
SJASMPLUS = "sjasmplus"

ORIGINAL_HEADER = b'AB'
MASKED_HEADER = b'CD'


# ==============================================================
# PARSING DO INPUT
# ==============================================================
def parse_input(text):
    """
    Parseia o texto de entrada no formato:
    "Nome com espaco",arquivo.rom, Nome,arq.rom//fim
    
    Retorna lista de tuplas: [(nome, arquivo), ...]
    """
    # Remove //fim e tudo depois
    if "//fim" in text.lower():
        idx = text.lower().index("//fim")
        text = text[:idx]
    elif "// fim" in text.lower():
        idx = text.lower().index("// fim")
        text = text[:idx]

    # Tokeniza respeitando aspas
    tokens = []
    current = ""
    in_quotes = False
    quote_char = None

    for ch in text:
        if ch in ('"', "'") and not in_quotes:
            in_quotes = True
            quote_char = ch
        elif ch == quote_char and in_quotes:
            in_quotes = False
            quote_char = None
        elif ch == ',' and not in_quotes:
            tokens.append(current.strip())
            current = ""
        else:
            current += ch

    # Ultimo token
    if current.strip():
        tokens.append(current.strip())

    # Remove aspas dos tokens
    cleaned = []
    for t in tokens:
        t = t.strip()
        if (t.startswith('"') and t.endswith('"')) or \
           (t.startswith("'") and t.endswith("'")):
            t = t[1:-1]
        cleaned.append(t)

    # Agrupa em pares (nome, arquivo)
    games = []
    i = 0
    while i < len(cleaned) - 1:
        name = cleaned[i]
        filename = cleaned[i + 1]

        # Detecta qual e o nome e qual e o arquivo
        # Se um termina em .rom, e o arquivo
        if filename.lower().endswith('.rom'):
            games.append((name, filename))
        elif name.lower().endswith('.rom'):
            games.append((filename, name))
        else:
            # Assume ordem: nome, arquivo
            games.append((name, filename))
        i += 2

    return games


def get_key_for_index(i):
    """Retorna a tecla correspondente ao indice (0-based)."""
    if i < 9:
        return str(i + 1)       # '1'-'9'
    elif i == 9:
        return '0'              # '0'
    else:
        return chr(ord('A') + i - 10)  # 'A'-'J'


# ==============================================================
# FUNCOES DE BUILD
# ==============================================================
def detect_size(filepath):
    size = os.path.getsize(filepath)
    valid_sizes = {8192: 8, 16384: 16, 32768: 32}
    if size in valid_sizes:
        return valid_sizes[size]
    for valid_size, kb in sorted(valid_sizes.items()):
        if size <= valid_size:
            print(f"  AVISO: {filepath} tem {size} bytes, padded para {kb}KB")
            return kb
    print(f"  ERRO: {filepath} tem {size} bytes (max: 32KB)")
    sys.exit(1)


def pad_to_bank(data, target_banks):
    target_size = target_banks * BANK_SIZE
    if len(data) > target_size:
        return data[:target_size]
    return data + bytes([0xFF] * (target_size - len(data)))


def pad_to_power_of_2(data):
    size = len(data)
    target = 1 << math.ceil(math.log2(size)) if size > 0 else 65536
    if target < 65536:
        target = 65536
    return data + bytes([0xFF] * (target - size))


def mask_header(data):
    data = bytearray(data)
    if data[0:2] == ORIGINAL_HEADER:
        data[0:2] = MASKED_HEADER
    return bytes(data)


def generate_menu_asm(games_info):
    """Gera o menu.asm completo com suporte a 20 jogos."""
    num = len(games_info)

    # Assinatura ASCII8
    sig_lines = []
    for _ in range(8):
        sig_lines.append("    db 32h, 00h, 60h           ; LD (6000h), A")
        sig_lines.append("    db 32h, 00h, 68h           ; LD (6800h), A")
        sig_lines.append("    db 32h, 00h, 70h           ; LD (7000h), A")
        sig_lines.append("    db 32h, 00h, 78h           ; LD (7800h), A")
    signature_block = "\n".join(sig_lines)

    # GameTable
    table_lines = []
    for i, g in enumerate(games_info):
        table_lines.append(
            f"    db {g['start_bank']}, {g['num_banks']}"
            f"            ; {g['name']} ({g['size_kb']}KB)"
        )
    game_table = "\n".join(table_lines)

    # GameNames (32 bytes fixos por entrada)
    name_lines = []
    for i, g in enumerate(games_info):
        key = get_key_for_index(i)
        label = f"{key} - {g['name']}"
        size_str = f"({g['size_kb']}K)"
        # Trunca nome se necessario (max 32 bytes com null)
        max_label_len = 32 - len(size_str) - 1  # -1 para null
        if len(label) > max_label_len:
            label = label[:max_label_len - 1]
        padded = f"{label:<{32 - len(size_str) - 1}}{size_str}"
        if len(padded) > 31:
            padded = padded[:31]
        str_bytes = len(padded) + 1
        ds_pad = 32 - str_bytes
        name_lines.append(f'    db "{padded}", 0')
        if ds_pad > 0:
            name_lines.append(f'    ds {ds_pad}, 0')
    game_names = "\n".join(name_lines)

    # Texto da instrucao
    if num <= 9:
        instr_text = f"Pressione 1-{num} para jogar"
    elif num == 10:
        instr_text = "Pressione 1-9/0 para jogar"
    else:
        last_letter = chr(ord('A') + num - 11)
        instr_text = f"Tecle 1-9,0,A-{last_letter} p/ jogar"

    asm = f"""; ============================================================
; menu.asm - GERADO AUTOMATICAMENTE por build_all.py
; MSX Multi-ROM Menu - ASCII8 Mapper - {num} jogos
; Teclas: 1-9, 0, A-J (ate 20 jogos)
; ============================================================

; --- Registradores ASCII8 Mapper ---
MAP_REG_4000    equ 6000h
MAP_REG_6000    equ 6800h
MAP_REG_8000    equ 7000h
MAP_REG_A000    equ 7800h

; --- BIOS ---
CHGET           equ 009Fh
CHPUT           equ 00A2h
CLS             equ 00C3h
POSIT           equ 00C6h
INITXT          equ 006Ch
LINL40          equ 0F3AEh
CLIKSW          equ 0F3DBh

; --- Constantes ---
NUM_GAMES       equ {num}
TRAMPOLINE      equ 0C000h

; ============================================================
; Header cartucho MSX
; ============================================================
    org 4000h

    db "AB"
    dw Start
    dw 0, 0, 0
    ds 6, 0

; ============================================================
; ASSINATURA ASCII8 (auto-deteccao em emuladores)
; ============================================================
{signature_block}

; ============================================================
; PONTO DE ENTRADA
; ============================================================
Start:
    xor a
    ld (CLIKSW), a

    ld a, 40
    ld (LINL40), a
    call INITXT
    call CLS

    call InstallTrampoline
    call DrawMenu

; ============================================================
; LOOP PRINCIPAL - Aceita teclas 1-9, 0, A-J (maiusc/minusc)
; ============================================================
MainLoop:
    call CHGET

    ; --- Verifica digitos '1'-'9' (jogos 1-9) ---
    cp '1'
    jr c, .checkZero
    cp '9' + 1
    jr nc, .checkZero
    ; A = '1'..'9'
    sub '0'                     ; A = 1..9
    jr .checkRange

.checkZero:
    ; --- Verifica '0' (jogo 10) ---
    cp '0'
    jr nz, .checkUpper
    ld a, 10
    jr .checkRange

.checkUpper:
    ; --- Verifica 'A'-'J' maiusculas (jogos 11-20) ---
    cp 'A'
    jr c, .checkLower
    cp 'J' + 1
    jr nc, .checkLower
    sub 'A'
    add a, 11                   ; A = 11..20
    jr .checkRange

.checkLower:
    ; --- Verifica 'a'-'j' minusculas (jogos 11-20) ---
    cp 'a'
    jr c, MainLoop
    cp 'j' + 1
    jr nc, MainLoop
    sub 'a'
    add a, 11                   ; A = 11..20

.checkRange:
    ; A = numero do jogo (1-based, 1..20)
    cp NUM_GAMES + 1
    jr nc, MainLoop             ; Se > NUM_GAMES, ignora

    dec a                       ; 0-based
    call LoadGame
    jr MainLoop

; ============================================================
; DESENHA O MENU
; ============================================================
DrawMenu:
    ld h, 5
    ld l, 1
    call POSIT
    ld hl, str_title
    call PrintStr

    ld h, 5
    ld l, 2
    call POSIT
    ld hl, str_separator
    call PrintStr

    ld b, NUM_GAMES
    ld de, GameNames
    ld c, 3                     ; Linha inicial

.drawLoop:
    ld h, 3                     ; Coluna
    ld l, c                     ; Linha
    push bc
    push de
    call POSIT

    pop hl
    push hl
    call PrintStr

    pop de
    pop bc

    ld hl, GAME_NAME_LEN
    add hl, de
    ex de, hl

    inc c                       ; Espacamento simples (1 linha por jogo)
    djnz .drawLoop

    ; Instrucao no rodape
    ld h, 5
    ld l, 24
    call POSIT
    ld hl, str_instruction
    call PrintStr
    ret

; ============================================================
; CARREGA JOGO
; ============================================================
LoadGame:
    push af

    ld h, 5
    ld l, 23
    call POSIT
    ld hl, str_loading
    call PrintStr

    pop af

    ld hl, GameTable
    ld d, 0
    ld e, a
    sla e
    add hl, de

    ld b, (hl)
    inc hl
    ld c, (hl)

    di
    jp TRAMPOLINE

; ============================================================
; INSTALA TRAMPOLIM NA RAM
; ============================================================
InstallTrampoline:
    ld hl, _tramp_code
    ld de, TRAMPOLINE
    ld bc, _tramp_end - _tramp_code
    ldir
    ret

_tramp_code:
    ld a, b
    ld (MAP_REG_4000), a

    inc a
    ld (MAP_REG_6000), a

    ld a, c
    cp 4
    jr c, _tramp_restore

    ld a, b
    add a, 2
    ld (MAP_REG_8000), a

    ld a, b
    add a, 3
    ld (MAP_REG_A000), a

_tramp_restore:
    ; Restaura header "AB" mascarado
    ld a, 41h
    ld (4000h), a
    ld a, 42h
    ld (4001h), a

    ld hl, (4002h)
    ei
    jp (hl)
_tramp_end:

; ============================================================
; PrintStr
; ============================================================
PrintStr:
    ld a, (hl)
    or a
    ret z
    call CHPUT
    inc hl
    jr PrintStr

; ============================================================
; TABELA DE JOGOS
; ============================================================
GameTable:
{game_table}

; ============================================================
; NOMES DOS JOGOS (32 bytes fixos)
; ============================================================
GAME_NAME_LEN   equ 32

GameNames:
{game_names}

; ============================================================
; STRINGS
; ============================================================
str_title:
    db "====== MSX MULTI-ROM MENU ======", 0

str_separator:
    db "--------------------------------", 0

str_instruction:
    db "{instr_text}", 0

str_loading:
    db ">>> Carregando... <<<", 0

; ============================================================
; PADDING ate 16KB
; ============================================================
    ds 8000h - $, 0FFh
"""
    return asm


# ==============================================================
# BUILD PRINCIPAL
# ==============================================================
def build():
    print()
    print("=" * 60)
    print("  MSX MULTI-ROM BUILDER v5")
    print("  Suporta ate 20 jogos | Teclas: 1-9, 0, A-J")
    print("=" * 60)
    print()
    print("  Digite a lista de jogos no formato:")
    print("  Nome,arquivo.rom, Nome2,arq2.rom//fim")
    print()
    print("  Use aspas para nomes com virgula ou apostrofo:")
    print('  "King\'s Valley",kvalley.rom, Knightmare,kmare.rom//fim')
    print()
    print("  (termine com //fim)")
    print()
    print("-" * 60)

    # Coleta input (pode ser multilinhas)
    lines = []
    while True:
        try:
            line = input("> ")
        except EOFError:
            break
        lines.append(line)
        full_text = " ".join(lines)
        if "//fim" in full_text.lower() or "// fim" in full_text.lower():
            break

    full_text = " ".join(lines)

    if not full_text.strip():
        print("ERRO: Nenhuma entrada fornecida!")
        sys.exit(1)

    # Parseia
    games = parse_input(full_text)

    if not games:
        print("ERRO: Nenhum jogo detectado na entrada!")
        print("Formato: Nome,arquivo.rom, Nome2,arq2.rom//fim")
        sys.exit(1)

    if len(games) > MAX_GAMES:
        print(f"ERRO: Maximo {MAX_GAMES} jogos! (voce informou {len(games)})")
        sys.exit(1)

    print()
    print(f"  {len(games)} jogos detectados:")
    print()
    for i, (name, filename) in enumerate(games):
        key = get_key_for_index(i)
        print(f"  [{key}] {name:<24} <- {filename}")
    print()

    # Confirma
    resp = input("  Correto? (S/n): ").strip().lower()
    if resp == 'n':
        print("  Cancelado. Rode novamente.")
        sys.exit(0)
    print()

    # --- Passo 1: Detecta tamanhos ---
    print("[1/4] Verificando ROMs...")
    games_info = []
    current_bank = 2

    for name, filename in games:
        if not os.path.exists(filename):
            print(f"  ERRO: '{filename}' nao encontrado!")
            sys.exit(1)
        size_kb = detect_size(filename)
        num_banks = size_kb * 1024 // BANK_SIZE
        games_info.append({
            "file": filename,
            "name": name,
            "size_kb": size_kb,
            "start_bank": current_bank,
            "num_banks": num_banks,
        })
        end = current_bank + num_banks - 1
        key = get_key_for_index(len(games_info) - 1)
        print(f"  OK [{key}] {filename:<20} {size_kb}KB (bancos {current_bank}-{end})")
        current_bank += num_banks
    print()

    # --- Passo 2: Gera menu.asm ---
    print("[2/4] Gerando menu.asm...")
    asm_content = generate_menu_asm(games_info)
    with open(MENU_ASM, "w") as f:
        f.write(asm_content)
    print(f"  OK {MENU_ASM} ({len(games_info)} jogos)")
    print()

    # --- Passo 3: Compila ---
    print("[3/4] Compilando com sjasmplus...")
    cmd = [SJASMPLUS, MENU_ASM, f"--raw={MENU_ROM}"]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print("  ERRO na compilacao!")
            print(result.stdout)
            print(result.stderr)
            sys.exit(1)
        print(f"  OK {MENU_ROM} compilado")
    except FileNotFoundError:
        print("  ERRO: 'sjasmplus' nao encontrado no PATH!")
        print("  Instale: https://github.com/z00m128/sjasmplus")
        sys.exit(1)
    print()

    # --- Passo 4: Monta cartucho ---
    print("[4/4] Montando cartucho...")
    with open(MENU_ROM, "rb") as f:
        menu_data = f.read()
    menu_data = pad_to_bank(menu_data, 2)

    all_data = bytearray(menu_data)
    for g in games_info:
        with open(g["file"], "rb") as f:
            game_data = f.read()
        game_data = pad_to_bank(game_data, g["num_banks"])
        game_data = mask_header(game_data)
        all_data += game_data

    all_data = pad_to_power_of_2(bytes(all_data))

    with open(OUTPUT_ROM, "wb") as f:
        f.write(all_data)

    final_kb = len(all_data) // 1024
    print(f"  OK {OUTPUT_ROM} ({final_kb}KB)")
    print()

    # --- Relatorio ---
    print("=" * 60)
    print("  CARTUCHO PRONTO!")
    print("=" * 60)
    print()
    print(f"  Arquivo: {OUTPUT_ROM} ({final_kb}KB)")
    print(f"  Mapper:  ASCII8 (auto-detectavel)")
    print()
    print(f"  {'Tecla':<7}{'Jogo':<24}{'Tam':<8}{'Bancos'}")
    print(f"  {'-'*48}")
    for i, g in enumerate(games_info):
        end = g['start_bank'] + g['num_banks'] - 1
        key = get_key_for_index(i)
        print(f"  [{key}]   {g['name']:<24}{g['size_kb']}KB    {g['start_bank']}-{end}")
    print()
    print(f"  Teste: arraste {OUTPUT_ROM} no WebMSX")
    print()


if __name__ == "__main__":
    build()

