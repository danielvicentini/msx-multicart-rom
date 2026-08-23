; ============================================================
; menu.asm - GERADO AUTOMATICAMENTE por build_all.py
; MSX Multi-ROM Menu - ASCII8 Mapper - 4 jogos
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
NUM_GAMES       equ 4
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
    db 32h, 00h, 60h           ; LD (6000h), A
    db 32h, 00h, 68h           ; LD (6800h), A
    db 32h, 00h, 70h           ; LD (7000h), A
    db 32h, 00h, 78h           ; LD (7800h), A
    db 32h, 00h, 60h           ; LD (6000h), A
    db 32h, 00h, 68h           ; LD (6800h), A
    db 32h, 00h, 70h           ; LD (7000h), A
    db 32h, 00h, 78h           ; LD (7800h), A
    db 32h, 00h, 60h           ; LD (6000h), A
    db 32h, 00h, 68h           ; LD (6800h), A
    db 32h, 00h, 70h           ; LD (7000h), A
    db 32h, 00h, 78h           ; LD (7800h), A
    db 32h, 00h, 60h           ; LD (6000h), A
    db 32h, 00h, 68h           ; LD (6800h), A
    db 32h, 00h, 70h           ; LD (7000h), A
    db 32h, 00h, 78h           ; LD (7800h), A
    db 32h, 00h, 60h           ; LD (6000h), A
    db 32h, 00h, 68h           ; LD (6800h), A
    db 32h, 00h, 70h           ; LD (7000h), A
    db 32h, 00h, 78h           ; LD (7800h), A
    db 32h, 00h, 60h           ; LD (6000h), A
    db 32h, 00h, 68h           ; LD (6800h), A
    db 32h, 00h, 70h           ; LD (7000h), A
    db 32h, 00h, 78h           ; LD (7800h), A
    db 32h, 00h, 60h           ; LD (6000h), A
    db 32h, 00h, 68h           ; LD (6800h), A
    db 32h, 00h, 70h           ; LD (7000h), A
    db 32h, 00h, 78h           ; LD (7800h), A
    db 32h, 00h, 60h           ; LD (6000h), A
    db 32h, 00h, 68h           ; LD (6800h), A
    db 32h, 00h, 70h           ; LD (7000h), A
    db 32h, 00h, 78h           ; LD (7800h), A

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
    db 2, 2            ; King's Valley (16KB)
    db 4, 4            ; KnightMare (32KB)
    db 8, 2            ; Road Fighter (16KB)
    db 10, 2            ; Pippols (16KB)

; ============================================================
; NOMES DOS JOGOS (32 bytes fixos)
; ============================================================
GAME_NAME_LEN   equ 32

GameNames:
    db "1 - King's Valley         (16K)", 0
    db "2 - KnightMare            (32K)", 0
    db "3 - Road Fighter          (16K)", 0
    db "4 - Pippols               (16K)", 0

; ============================================================
; STRINGS
; ============================================================
str_title:
    db "====== MSX MULTI-ROM MENU ======", 0

str_separator:
    db "--------------------------------", 0

str_instruction:
    db "Pressione 1-4 para jogar", 0

str_loading:
    db ">>> Carregando... <<<", 0

; ============================================================
; PADDING ate 16KB
; ============================================================
    ds 8000h - $, 0FFh
