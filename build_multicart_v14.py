
#!/usr/bin/env python3
"""
build_all.py v14 - Gerador COMPLETO de Cartucho MSX Multi-ROM (ASCII8)

Novidades v14:
  - Paginacao de saida: pausa quando a tela enche
  - Todas as funcionalidades da v13 mantidas

Uso: python build_all.py
"""

import os, sys, math, subprocess, shutil

BANK_SIZE = 8192
MAX_GAMES = 20
MENU_ASM = "menu.asm"
MENU_ROM = "menu.rom"
OUTPUT_ROM = "multicart.rom"
SJASMPLUS = "sjasmplus"

MAPPER_REGS = [
    (0x32, 0x00, 0x60, "6000h"),
    (0x32, 0x00, 0x68, "6800h"),
    (0x32, 0x00, 0x70, "7000h"),
    (0x32, 0x00, 0x78, "7800h"),
]

NOP = 0x00


# ==============================================================
# PAGINACAO DE SAIDA
# ==============================================================
class PagedOutput:
    def __init__(self):
        try:
            self.term_lines = shutil.get_terminal_size().lines
        except:
            self.term_lines = 24
        self.current_line = 0

    def reset(self):
        self.current_line = 0

    def print(self, text=""):
        lines = text.split("\n") if text else [""]
        for line in lines:
            if self.current_line >= self.term_lines - 2:
                input("  --- Pressione ENTER para continuar ---")
                self.current_line = 0
            print(line)
            self.current_line += 1

    def separator(self):
        self.print("-" * 62)

out = PagedOutput()


# ==============================================================
# PARSING DO INPUT
# ==============================================================
def parse_input(text):
    if "//fim" in text.lower():
        text = text[:text.lower().index("//fim")]
    elif "// fim" in text.lower():
        text = text[:text.lower().index("// fim")]

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
    if current.strip():
        tokens.append(current.strip())

    cleaned = []
    for t in tokens:
        t = t.strip()
        if (t.startswith('"') and t.endswith('"')) or \
           (t.startswith("'") and t.endswith("'")):
            t = t[1:-1]
        cleaned.append(t)

    games = []
    i = 0
    while i < len(cleaned) - 1:
        name = cleaned[i]
        filename = cleaned[i + 1]
        if filename.lower().endswith('.rom'):
            games.append((name, filename))
        elif name.lower().endswith('.rom'):
            games.append((filename, name))
        else:
            games.append((name, filename))
        i += 2
    return games


def get_key_for_index(i):
    if i < 9:
        return str(i + 1)
    elif i == 9:
        return '0'
    else:
        return chr(ord('A') + i - 10)


# ==============================================================
# VERIFICACAO DE COMPATIBILIDADE
# ==============================================================
def check_compatibility(filename):
    result = {
        "warnings": [],
        "patches": [],
        "status": "OK",
    }

    with open(filename, "rb") as f:
        raw = f.read()

    data = list(raw)
    size = len(data)

    if size > 32768:
        result["warnings"].append("ROM > 32KB (" + str(size) + " bytes) - MegaROM")
        result["status"] = "FAIL"
        return result

    for b0, b1, b2, reg_name in MAPPER_REGS:
        i = 0
        while i < size - 2:
            if data[i] == b0 and data[i + 1] == b1 and data[i + 2] == b2:
                result["patches"].append({
                    "offset": i,
                    "reg": reg_name,
                })
            i += 1

    if result["patches"]:
        result["status"] = "PATCH"

    checks = [
        (0xCD, 0x24, 0x00, "CALL ENASLT"),
        (0xCD, 0x1C, 0x00, "CALL CALSLT"),
        (0xCD, 0x38, 0x01, "CALL RSLREG"),
        (0xCD, 0x0C, 0x00, "CALL RDSLT"),
    ]
    for b0, b1, b2, name in checks:
        count = 0
        i = 0
        while i < size - 2:
            if data[i] == b0 and data[i + 1] == b1 and data[i + 2] == b2:
                count += 1
            i += 1
        if count > 0:
            result["warnings"].append(name + ": " + str(count) + "x")

    for opcode, name in [(0xD3, "OUT (A8h)"), (0xDB, "IN A,(A8h)")]:
        count = 0
        i = 0
        while i < size - 1:
            if data[i] == opcode and data[i + 1] == 0xA8:
                count += 1
            i += 1
        if count > 0:
            result["warnings"].append(name + ": " + str(count) + "x")

    count = 0
    i = 0
    while i < size - 2:
        if data[i] == 0x32 and data[i + 1] == 0xFF and data[i + 2] == 0xFF:
            count += 1
        i += 1
    if count > 0:
        result["warnings"].append("LD (FFFFh),A: " + str(count) + "x")

    return result


def apply_patches(data, patches):
    data = bytearray(data)
    for p in patches:
        off = p["offset"]
        data[off] = NOP
        data[off + 1] = NOP
        data[off + 2] = NOP
    return bytes(data)


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
            return kb
    out.print("  ERRO: " + filepath + " tem " + str(size) + " bytes (max: 32KB)")
    sys.exit(1)


def read_init_address(data):
    if len(data) >= 4 and data[0] == 0x41 and data[1] == 0x42:
        return data[2] + data[3] * 256, 0x0000
    if len(data) > 0x4003 and data[0x4000] == 0x41 and data[0x4001] == 0x42:
        return data[0x4002] + data[0x4003] * 256, 0x4000
    return 0x4000, -1


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


def mask_header(data, header_offset):
    data = bytearray(data)
    if header_offset >= 0 and header_offset + 1 < len(data):
        if data[header_offset] == 0x41 and data[header_offset + 1] == 0x42:
            data[header_offset + 1] = 0x00
    return bytes(data)


def generate_menu_asm(games_info, menu_title):
    num = len(games_info)

    sig_lines = []
    for _ in range(8):
        sig_lines.append("    db 32h, 00h, 60h           ; LD (6000h), A")
        sig_lines.append("    db 32h, 00h, 68h           ; LD (6800h), A")
        sig_lines.append("    db 32h, 00h, 70h           ; LD (7000h), A")
        sig_lines.append("    db 32h, 00h, 78h           ; LD (7800h), A")
    signature_block = "\n".join(sig_lines)

    table_lines = []
    for g in games_info:
        table_lines.append(
            "    db " + str(g['start_bank']) + ", " + str(g['num_banks'])
            + ", " + str(g['init_lo']) + ", " + str(g['init_hi'])
            + "    ; " + g['name'] + " INIT=" + hex(g['init_addr'])
        )
    game_table = "\n".join(table_lines)

    name_lines = []
    for i, g in enumerate(games_info):
        key = get_key_for_index(i)
        label = key + " - " + g['name']
        size_str = "(" + str(g['size_kb']) + "K)"
        max_label_len = 32 - len(size_str) - 1
        if len(label) > max_label_len:
            label = label[:max_label_len - 1]
        padded = label.ljust(32 - len(size_str) - 1) + size_str
        if len(padded) > 31:
            padded = padded[:31]
        str_bytes = len(padded) + 1
        ds_pad = 32 - str_bytes
        name_lines.append('    db "' + padded + '", 0')
        if ds_pad > 0:
            name_lines.append('    ds ' + str(ds_pad) + ', 0')
    game_names = "\n".join(name_lines)

    if num <= 9:
        instr_text = "Pressione 1-" + str(num) + " para jogar"
    elif num == 10:
        instr_text = "Pressione 1-9/0 para jogar"
    else:
        last_letter = chr(ord('A') + num - 11)
        instr_text = "Tecle 1-9,0,A-" + last_letter + " p/ jogar"

    menu_title = menu_title[:32]
    title_pad = (32 - len(menu_title)) // 2
    padded_title = (" " * title_pad + menu_title) if title_pad > 0 else menu_title

    asm = """; ============================================================
; menu.asm - GERADO AUTOMATICAMENTE por build_all.py v14
; MSX Multi-ROM Menu - ASCII8 Mapper - """ + str(num) + """ jogos
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
DISSCR          equ 0041h
ENASCR          equ 0044h
WRT_PSG         equ 0096h
LINL40          equ 0F3AEh
CLIKSW          equ 0F3DBh

; --- Constantes ---
NUM_GAMES       equ """ + str(num) + """
ENTRY_SIZE      equ 4
TRAMPOLINE      equ 0F000h
TRAMP_RETURN    equ 0F080h

; ============================================================
; Header cartucho MSX
; ============================================================
    org 4000h

    db "AB"
    dw Start
    dw 0, 0, 0
    ds 6, 0

; ============================================================
; ASSINATURA ASCII8 (auto-deteccao)
; ============================================================
""" + signature_block + """

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
; LOOP PRINCIPAL
; ============================================================
MainLoop:
    call CHGET

    cp '1'
    jr c, .checkZero
    cp '9' + 1
    jr nc, .checkZero
    sub '0'
    jr .checkRange

.checkZero:
    cp '0'
    jr nz, .checkUpper
    ld a, 10
    jr .checkRange

.checkUpper:
    cp 'A'
    jr c, .checkLower
    cp 'J' + 1
    jr nc, .checkLower
    sub 'A'
    add a, 11
    jr .checkRange

.checkLower:
    cp 'a'
    jr c, MainLoop
    cp 'j' + 1
    jr nc, MainLoop
    sub 'a'
    add a, 11

.checkRange:
    cp NUM_GAMES + 1
    jr nc, MainLoop

    dec a
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
    ld c, 3

.drawLoop:
    ld h, 3
    ld l, c
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

    inc c
    djnz .drawLoop

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

    ld e, 0
    ld a, 8
    call WRT_PSG
    ld e, 0
    ld a, 9
    call WRT_PSG
    ld e, 0
    ld a, 10
    call WRT_PSG

    call DISSCR

    pop af

    ld hl, GameTable
    ld d, 0
    ld e, a
    sla e
    sla e
    add hl, de

    ld b, (hl)
    inc hl
    ld c, (hl)
    inc hl
    ld e, (hl)
    inc hl
    ld d, (hl)
    ex de, hl

    di
    ld sp, 0F380h
    jp TRAMPOLINE

; ============================================================
; TRAMPOLIM NA RAM (F000h)
; ============================================================
InstallTrampoline:
    ld hl, _tramp_code
    ld de, TRAMPOLINE
    ld bc, _tramp_end - _tramp_code
    ldir

    ; Rotina de retorno em F080h (4 bytes: EI / HALT / JR -4)
    ld a, 0FBh
    ld (TRAMP_RETURN), a
    ld a, 076h
    ld (TRAMP_RETURN + 1), a
    ld a, 018h
    ld (TRAMP_RETURN + 2), a
    ld a, 0FCh
    ld (TRAMP_RETURN + 3), a
    ret

_tramp_code:
    in a, (0A8h)
    and 11111100b
    out (0A8h), a

    ld a, b
    ld (MAP_REG_4000), a
    inc a
    ld (MAP_REG_6000), a

    ld a, c
    cp 3
    jr c, _tramp_do_jump

    ld a, b
    add a, 2
    ld (MAP_REG_8000), a

    ld a, c
    cp 4
    jr c, _tramp_do_jump

    ld a, b
    add a, 3
    ld (MAP_REG_A000), a

_tramp_do_jump:
    ld de, TRAMP_RETURN
    push de

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
""" + game_table + """

; ============================================================
; NOMES DOS JOGOS (32 bytes fixos)
; ============================================================
GAME_NAME_LEN   equ 32

GameNames:
""" + game_names + """

; ============================================================
; STRINGS
; ============================================================
str_title:
    db \"""" + padded_title + """", 0

str_separator:
    db "--------------------------------", 0

str_instruction:
    db \"""" + instr_text + """", 0

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
    out.reset()
    out.print()
    out.print("=" * 62)
    out.print("  MSX MULTI-ROM BUILDER v14")
    out.print("  Suporta ate 20 jogos | Teclas: 1-9, 0, A-J")
    out.print("  Verificacao + patch + suporte a jogos com RET")
    out.print("=" * 62)
    out.print()

    # --- Titulo ---
    default_title = "MSX MULTI-ROM MENU"
    out.print("  Titulo do menu (max 32 chars)")
    out.print("  [Enter = " + default_title + "]")
    custom_title = input("  Titulo: ").strip()
    out.current_line += 1
    if not custom_title:
        custom_title = default_title
    custom_title = custom_title[:32]
    out.print()

    # --- Jogos ---
    out.print("  Digite a lista de jogos no formato:")
    out.print('  "Nome do Jogo",arquivo.rom, Nome2,arq2.rom//fim')
    out.print()
    out.print("  (termine com //fim)")
    out.print()
    out.separator()

    lines = []
    while True:
        try:
            line = input("> ")
            out.current_line += 1
        except EOFError:
            break
        lines.append(line)
        full_text = " ".join(lines)
        if "//fim" in full_text.lower() or "// fim" in full_text.lower():
            break

    full_text = " ".join(lines)
    if not full_text.strip():
        out.print("ERRO: Nenhuma entrada fornecida!")
        sys.exit(1)

    games = parse_input(full_text)
    if not games:
        out.print("ERRO: Nenhum jogo detectado!")
        sys.exit(1)
    if len(games) > MAX_GAMES:
        out.print("ERRO: Maximo " + str(MAX_GAMES) + " jogos!")
        sys.exit(1)

    # --- Passo 1: Verifica compatibilidade ---
    out.print()
    out.print("[1/5] Verificando ROMs e compatibilidade...")
    out.print()

    all_compat = []
    ok_count = 0
    patch_count = 0
    fail_count = 0

    for name, filename in games:
        if not os.path.exists(filename):
            out.print("  [ ERRO ] " + filename + " - arquivo nao encontrado!")
            sys.exit(1)

        size = os.path.getsize(filename)
        size_kb = size // 1024

        compat = check_compatibility(filename)
        compat["name"] = name
        compat["file"] = filename
        all_compat.append(compat)

        if compat["status"] == "OK":
            tag = "[  OK  ]"
            ok_count += 1
        elif compat["status"] == "PATCH":
            tag = "[PATCH ]"
            patch_count += 1
        else:
            tag = "[ FAIL ]"
            fail_count += 1

        out.print("  " + tag + " " + filename.ljust(22) + " " + str(size_kb) + "KB  " + name)
        for p in compat["patches"]:
            out.print("           ~ LD (" + p["reg"] + "),A em offset " + hex(p["offset"]) + " -> NOP")
        for warn in compat["warnings"]:
            out.print("           ! " + warn)

    out.print()
    out.print("  Resultado: " + str(ok_count) + " OK, " + str(patch_count) + " patchaveis, " + str(fail_count) + " incompativeis")
    out.print()

    # --- Se tem FAIL (MegaROM), pergunta ---
    fail_games = [(c["name"], c["file"]) for c in all_compat if c["status"] == "FAIL"]

    if fail_games:
        out.print("  ROMs incompativeis (MegaROM > 32KB):")
        for name, filename in fail_games:
            out.print("    - " + name + " (" + filename + ")")
        out.print()
        out.print("  Opcoes:")
        out.print("    S = Continuar SEM os incompativeis (recomendado)")
        out.print("    N = Cancelar")
        out.print()
        resp = input("  Escolha (S/N): ").strip().upper()
        out.current_line += 1

        if resp == 'N':
            out.print("  Cancelado.")
            sys.exit(0)

        fail_files = set(f for _, f in fail_games)
        final_compat = [c for c in all_compat if c["file"] not in fail_files]
        out.print("  Removidos " + str(len(fail_games)) + " MegaROMs.")
        out.print()
    else:
        final_compat = list(all_compat)

    if not final_compat:
        out.print("  ERRO: Nenhum jogo restante!")
        sys.exit(1)

    if len(final_compat) > MAX_GAMES:
        out.print("  ERRO: Maximo " + str(MAX_GAMES) + " jogos!")
        sys.exit(1)

    # --- Mostra lista final ---
    out.print("  " + str(len(final_compat)) + " jogos para o cartucho:")
    out.print("  Titulo: " + custom_title)
    out.print()
    for i, c in enumerate(final_compat):
        key = get_key_for_index(i)
        status = " [PATCH]" if c["patches"] else ""
        out.print("  [" + key + "] " + c["name"].ljust(24) + " <- " + c["file"] + status)
    out.print()

    resp = input("  Correto? (S/n): ").strip().lower()
    out.current_line += 1
    if resp == 'n':
        out.print("  Cancelado.")
        sys.exit(0)
    out.print()

    # --- Passo 2: Detecta tamanhos e INIT ---
    out.print("[2/5] Lendo INIT addresses...")
    games_info = []
    current_bank = 2

    for c in final_compat:
        filename = c["file"]
        name = c["name"]
        size_kb = detect_size(filename)
        num_banks = size_kb * 1024 // BANK_SIZE

        with open(filename, 'rb') as f:
            rom_data = list(f.read())

        init_addr, header_offset = read_init_address(rom_data)

        games_info.append({
            "file": filename,
            "name": name,
            "size_kb": size_kb,
            "start_bank": current_bank,
            "num_banks": num_banks,
            "init_addr": init_addr,
            "init_lo": init_addr & 0xFF,
            "init_hi": (init_addr >> 8) & 0xFF,
            "header_offset": header_offset,
            "patches": c["patches"],
        })
        end = current_bank + num_banks - 1
        key = get_key_for_index(len(games_info) - 1)
        patch_str = " [PATCH:" + str(len(c["patches"])) + " NOPs]" if c["patches"] else ""
        out.print("  [" + key + "] " + filename.ljust(18) + " " + str(size_kb) + "KB  bancos " + str(current_bank) + "-" + str(end) + "  INIT=" + hex(init_addr) + patch_str)
        current_bank += num_banks
    out.print()

    # --- Passo 3: Gera menu.asm ---
    out.print("[3/5] Gerando menu.asm...")
    asm_content = generate_menu_asm(games_info, custom_title)
    with open(MENU_ASM, "w") as f:
        f.write(asm_content)
    out.print("  OK " + MENU_ASM)
    out.print()

    # --- Passo 4: Compila ---
    out.print("[4/5] Compilando com sjasmplus...")
    cmd = [SJASMPLUS, MENU_ASM, "--raw=" + MENU_ROM]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            out.print("  ERRO na compilacao!")
            out.print(result.stdout)
            out.print(result.stderr)
            sys.exit(1)
        out.print("  OK " + MENU_ROM + " compilado")
    except FileNotFoundError:
        out.print("  ERRO: 'sjasmplus' nao encontrado!")
        sys.exit(1)
    out.print()

    # --- Passo 5: Monta cartucho ---
    out.print("[5/5] Montando cartucho...")
    with open(MENU_ROM, "rb") as f:
        menu_data = f.read()
    menu_data = pad_to_bank(menu_data, 2)

    all_data = bytearray(menu_data)
    patched_games = []

    for g in games_info:
        with open(g["file"], "rb") as f:
            game_data = f.read()

        if g["patches"]:
            game_data = apply_patches(game_data, g["patches"])
            patched_games.append(g["name"] + " (" + str(len(g["patches"])) + " NOPs)")

        game_data = pad_to_bank(game_data, g["num_banks"])
        game_data = mask_header(game_data, g["header_offset"])
        all_data += game_data

    all_data = pad_to_power_of_2(bytes(all_data))

    with open(OUTPUT_ROM, "wb") as f:
        f.write(all_data)

    final_kb = len(all_data) // 1024
    out.print("  OK " + OUTPUT_ROM + " (" + str(final_kb) + "KB)")
    out.print()

    # --- Relatorio final ---
    out.print("=" * 62)
    out.print("  CARTUCHO PRONTO!")
    out.print("=" * 62)
    out.print()
    out.print("  Arquivo: " + OUTPUT_ROM + " (" + str(final_kb) + "KB)")
    out.print("  Titulo:  " + custom_title)
    out.print("  Mapper:  ASCII8 (auto-detectavel)")
    out.print("  Jogos:   " + str(len(games_info)))
    out.print()
    out.print("  " + "Tecla".ljust(7) + "Jogo".ljust(20) + "Tam".ljust(6) + "Bancos".ljust(10) + "INIT")
    out.print("  " + "-" * 52)
    for i, g in enumerate(games_info):
        end = g['start_bank'] + g['num_banks'] - 1
        key = get_key_for_index(i)
        out.print("  [" + key + "]   " + g['name'].ljust(20) + str(g['size_kb']) + "KB  " + str(g['start_bank']) + "-" + str(end) + "       " + hex(g['init_addr']))
    out.print()

    if patched_games:
        out.print("  Patches aplicados:")
        for pg in patched_games:
            out.print("    ~ " + pg)
        out.print()

    if fail_games:
        out.print("  Excluidos (" + str(len(fail_games)) + " MegaROMs):")
        for name, filename in fail_games:
            out.print("    X " + name + " (" + filename + ")")
        out.print()

    out.print("  Teste: arraste " + OUTPUT_ROM + " no WebMSX")
    out.print()


if __name__ == "__main__":
    build()

