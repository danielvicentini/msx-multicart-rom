
# Documentação Técnica — MSX Multi-ROM Cartridge (ASCII8)
## build_all.py v14

---

## 1. Visão Geral

O MSX Multi-ROM Cartridge é um cartucho virtual que combina até 20 jogos MSX
(de 8KB, 16KB ou 32KB cada) em um único arquivo `.rom`, utilizando o mapper
ASCII8 para gerenciar o acesso aos bancos de memória. O cartucho inclui um menu
interativo em Assembly Z80 que permite ao usuário selecionar e carregar qualquer
jogo usando o teclado.

**Ferramentas necessárias:**
- Python 3.x (PC) — gera o menu.asm e monta o cartucho final
- sjasmplus (PC) — compilador Assembly Z80

---

## 2. Estrutura do Arquivo multicart.rom

### 2.1 Layout Geral

```
+=============================================+
|  BANCO 0-1  |  MENU (16KB)                 |  0x0000 - 0x3FFF
|             |  Header AB + código do menu   |
+---------------------------------------------+
|  BANCO 2-N  |  JOGO 1                      |  Tamanho: 1, 2 ou 4 bancos
+---------------------------------------------+
|  BANCO N+1  |  JOGO 2                      |
+---------------------------------------------+
|     ...     |  ...                          |
+---------------------------------------------+
|  BANCO X    |  JOGO 20 (máximo)            |
+---------------------------------------------+
|  PADDING    |  0xFF até potência de 2       |
+=============================================+
```

### 2.2 Tamanhos

| Elemento         | Tamanho         | Bancos ASCII8 (8KB cada) |
|------------------|-----------------|--------------------------|
| Menu             | 16KB fixo       | 2 bancos (0-1)           |
| Jogo de 8KB      | 8KB             | 1 banco                  |
| Jogo de 16KB     | 16KB            | 2 bancos                 |
| Jogo de 32KB     | 32KB            | 4 bancos                 |
| Padding final    | Variável        | Até completar potência de 2 |

### 2.3 Limite do Mapper ASCII8

- Máximo: **2MB** (256 bancos de 8KB)
- Máximo prático: **20 jogos** (limite do menu/teclado)
- Arquivo final é sempre **potência de 2** (64KB, 128KB, 256KB, 512KB, 1MB, 2MB)

### 2.4 Exemplo com 19 jogos (cartucho Konami testado)

```
Bancos 0-1:    Menu (16KB)
Bancos 2-3:    Antarctic Adventure (16KB)
Bancos 4-5:    Cabbage Patch Kids (16KB)
Bancos 6-7:    Circus Charlie (16KB)
Bancos 8-9:    Comic Bakery (16KB)
Bancos 10-11:  Frogger (16KB)
Bancos 12-15:  The Goonies (32KB)
Bancos 16-19:  Knightmare (32KB)
Bancos 20-21:  King's Valley (16KB)
Bancos 22-23:  Monkey Academy (16KB)
Bancos 24-25:  Mopiranger (16KB)
Bancos 26-27:  Magical Tree (16KB)
Bancos 28-29:  Pippols (16KB)
Bancos 30-33:  Q*bert (32KB) [PATCH: 1 NOP]
Bancos 34-35:  Road Fighter (16KB)
Bancos 36-37:  Sky Jaguar (16KB)
Bancos 38-39:  Time Pilot (16KB)
Bancos 40-43:  Twin Bee (32KB)
Bancos 44-45:  Yie Ar Kung Fu 1 (16KB)
Bancos 46-49:  Yie Ar Kung Fu 2 (32KB)
Bancos 50-63:  Padding (0xFF)

Total: 512KB (64 bancos)
```

---

## 3. Mapper ASCII8 — Funcionamento

### 3.1 Conceito

O Z80 tem barramento de 16 bits (64KB endereçáveis). O mapper ASCII8 divide
a faixa do cartucho (4000h-BFFFh = 32KB) em 4 janelas de 8KB cada, e permite
trocar qual banco de 8KB aparece em cada janela escrevendo nos registradores:

### 3.2 Registradores

| Registrador | Endereço de escrita | Janela que controla | Faixa de memória |
|-------------|--------------------|--------------------|-----------------|
| MAP_REG_0   | 6000h              | Janela 0           | 4000h - 5FFFh   |
| MAP_REG_1   | 6800h              | Janela 1           | 6000h - 7FFFh   |
| MAP_REG_2   | 7000h              | Janela 2           | 8000h - 9FFFh   |
| MAP_REG_3   | 7800h              | Janela 3           | A000h - BFFFh   |

### 3.3 Operação de troca de banco

```asm
; Exemplo: colocar o banco 12 na janela 0 (4000h-5FFFh)
ld a, 12
ld (6000h), a       ; agora 4000h-5FFFh mostra o conteúdo do banco 12
```

### 3.4 Auto-detecção pelo emulador

Para que emuladores (WebMSX, openMSX) detectem automaticamente o mapper ASCII8,
o menu inclui uma **assinatura** — 32 repetições dos padrões de escrita nos
registradores do mapper:

```asm
; Repetido 8x (32 escritas no total)
db 32h, 00h, 60h    ; LD (6000h), A
db 32h, 00h, 68h    ; LD (6800h), A
db 32h, 00h, 70h    ; LD (7000h), A
db 32h, 00h, 78h    ; LD (7800h), A
```

O emulador escaneia a ROM procurando esses padrões. Quando encontra muitas
ocorrências, identifica como ASCII8.

---

## 4. Mapa de Memória do MSX durante execução

```
0000h - 3FFFh : BIOS (Slot 0) — sempre acessível
4000h - 5FFFh : Janela 0 do mapper (banco selecionado via 6000h)
6000h - 7FFFh : Janela 1 do mapper (banco selecionado via 6800h)
8000h - 9FFFh : Janela 2 do mapper (banco selecionado via 7000h)
A000h - BFFFh : Janela 3 do mapper (banco selecionado via 7800h)
C000h - FFFFh : RAM (Slot 3) — variáveis, stack, trampolim
```

---

## 5. Tratamento das ROMs dos Jogos

### 5.1 Mascaramento do Header "AB"

Todo cartucho MSX tem o header "AB" (41h 42h) que a BIOS usa para detectar
cartuchos no boot. No multicart, apenas o menu deve ter o header ativo.
Os headers dos jogos são **mascarados** (42h → 00h) para que a BIOS não
tente inicializá-los diretamente.

```
Original:  41 42 xx xx  ("AB" + INIT address)
Mascarado: 41 00 xx xx  (BIOS ignora)
```

O header pode estar em duas posições:
- **Offset 0000h** do arquivo (jogos antigos, ex: Q*bert, Egger)
- **Offset 4000h** do arquivo (padrão mais comum)

O build detecta automaticamente a posição e mascara corretamente.

### 5.2 Patch Automático (escritas acidentais no mapper)

Alguns jogos antigos (anteriores à era dos mappers) fazem escritas em
endereços que coincidem com os registradores do mapper ASCII8:

```
LD (6000h), A  →  No cartucho original: escrita ignorada (ROM)
               →  No multicart ASCII8: TROCA O BANCO! (problema)
```

O build detecta essas escritas e as substitui por NOP (00h):

```
Antes:  32 00 60     ; LD (6000h), A  — 3 bytes
Depois: 00 00 00     ; NOP NOP NOP    — 3 bytes (não faz nada)
```

Isso reproduz o comportamento original: a escrita simplesmente não acontece.

**Endereços patcheados:** 6000h, 6800h, 7000h, 7800h

### 5.3 Padding

Cada ROM é padded com 0xFF até completar o número exato de bancos de 8KB:
- 8KB → 1 banco (sem padding)
- 16KB → 2 bancos (sem padding)
- 32KB → 4 bancos (sem padding)
- ROMs menores são padded para o próximo tamanho válido

---

## 6. Código Assembly do Menu (menu.asm)

### 6.1 Estrutura Geral

```
4000h - 400Fh : Header do cartucho (AB + INIT + reservado)
4010h - 408Fh : Assinatura ASCII8 (auto-detecção)
4090h+        : Código executável
                ├── Start (ponto de entrada)
                ├── MainLoop (loop de leitura de teclas)
                ├── DrawMenu (desenha o menu na tela)
                ├── LoadGame (prepara e pula para o jogo)
                ├── InstallTrampoline (copia trampolim para RAM)
                ├── PrintStr (imprime string na tela)
                ├── GameTable (tabela de jogos: banco, tamanho, INIT)
                ├── GameNames (nomes dos jogos, 32 bytes cada)
                ├── Strings (título, separador, instrução)
                └── Padding até 8000h (0xFF)
```

### 6.2 Header do Cartucho

```asm
org 4000h

db "AB"              ; Identificação de cartucho MSX
dw Start             ; Endereço INIT (ponto de entrada)
dw 0, 0, 0           ; STATEMENT, DEVICE, TEXT (não usados)
ds 6, 0              ; Reservado
```

### 6.3 Ponto de Entrada (Start)

```asm
Start:
    xor a
    ld (CLIKSW), a       ; Desliga click do teclado

    ld a, 40
    ld (LINL40), a       ; Define 40 colunas
    call INITXT           ; Inicializa SCREEN 0 (texto)
    call CLS              ; Limpa a tela

    call InstallTrampoline ; Copia trampolim para RAM (F000h)
    call DrawMenu          ; Desenha o menu na tela
```

### 6.4 Loop Principal (MainLoop)

Lê uma tecla e converte para índice do jogo (0-19):

```asm
MainLoop:
    call CHGET            ; Espera tecla (BIOS)

    ; Teclas 1-9 → jogos 1-9 (índice 0-8)
    cp '1'
    jr c, .checkZero
    cp '9' + 1
    jr nc, .checkZero
    sub '0'               ; A = 1-9
    jr .checkRange

    ; Tecla 0 → jogo 10 (índice 9)
.checkZero:
    cp '0'
    jr nz, .checkUpper
    ld a, 10
    jr .checkRange

    ; Teclas A-J → jogos 11-20 (índice 10-19)
.checkUpper:
    cp 'A'
    jr c, .checkLower
    cp 'J' + 1
    jr nc, .checkLower
    sub 'A'
    add a, 11              ; A = 11-20
    jr .checkRange

    ; Teclas a-j (minúsculas) → mesmo que A-J
.checkLower:
    cp 'a'
    jr c, MainLoop
    cp 'j' + 1
    jr nc, MainLoop
    sub 'a'
    add a, 11

    ; Verifica se o índice é válido
.checkRange:
    cp NUM_GAMES + 1
    jr nc, MainLoop        ; Ignora se > número de jogos

    dec a                  ; Converte para índice base 0
    call LoadGame
    jr MainLoop            ; Nunca retorna (LoadGame faz JP)
```

### 6.5 Desenho do Menu (DrawMenu)

```asm
DrawMenu:
    ; Posiciona e imprime título centralizado
    ld h, 5 : ld l, 1
    call POSIT
    ld hl, str_title
    call PrintStr

    ; Linha separadora
    ld h, 5 : ld l, 2
    call POSIT
    ld hl, str_separator
    call PrintStr

    ; Loop: imprime cada nome de jogo
    ld b, NUM_GAMES        ; Contador
    ld de, GameNames        ; Ponteiro para nomes
    ld c, 3                 ; Linha inicial (linha 3)

.drawLoop:
    ld h, 3 : ld l, c      ; Posiciona cursor (coluna 3, linha C)
    push bc : push de
    call POSIT

    pop hl : push hl
    call PrintStr           ; Imprime nome do jogo

    pop de : pop bc
    ld hl, GAME_NAME_LEN    ; Avança 32 bytes para próximo nome
    add hl, de
    ex de, hl

    inc c                   ; Próxima linha
    djnz .drawLoop

    ; Instrução na linha 24
    ld h, 5 : ld l, 24
    call POSIT
    ld hl, str_instruction
    call PrintStr
    ret
```

**Layout da tela (SCREEN 0, 40 colunas x 24 linhas):**

```
Linha 1:       "       dani 26       "  (título centralizado)
Linha 2:       "  --------------------------------"
Linha 3:       "  1 - Antarctic Adventure   (16K)"
Linha 4:       "  2 - Cabbage Patch Kids    (16K)"
...
Linha 21:      "  I - Yie Ar Kung Fu 2      (32K)"
Linha 22:      (vazio)
Linha 23:      ">>> Carregando... <<<"  (aparece ao selecionar)
Linha 24:      "  Tecle 1-9,0,A-I p/ jogar"
```

### 6.6 Carregamento do Jogo (LoadGame)

```asm
LoadGame:
    push af                 ; Salva índice do jogo

    ; Mostra "Carregando..."
    ld h, 5 : ld l, 23
    call POSIT
    ld hl, str_loading
    call PrintStr

    ; Silencia os 3 canais do PSG (som)
    ld e, 0 : ld a, 8 : call WRT_PSG    ; Canal A volume = 0
    ld e, 0 : ld a, 9 : call WRT_PSG    ; Canal B volume = 0
    ld e, 0 : ld a, 10 : call WRT_PSG   ; Canal C volume = 0

    ; Desliga a tela (VDP)
    call DISSCR

    pop af                  ; Recupera índice

    ; Calcula offset na GameTable: índice × 4
    ld hl, GameTable
    ld d, 0 : ld e, a
    sla e : sla e           ; E = índice × 4
    add hl, de              ; HL aponta para entrada do jogo

    ; Lê os 4 bytes da entrada
    ld b, (hl) : inc hl     ; B = banco inicial
    ld c, (hl) : inc hl     ; C = número de bancos
    ld e, (hl) : inc hl     ; E = INIT low byte
    ld d, (hl)              ; D = INIT high byte
    ex de, hl               ; HL = endereço INIT

    ; Prepara e pula para o trampolim na RAM
    di                      ; Desabilita interrupções
    ld sp, 0F380h           ; Stack na RAM alta
    jp TRAMPOLINE           ; Pula para F000h (RAM)
```

### 6.7 Trampolim na RAM (F000h)

O trampolim é copiado para a RAM (F000h) durante a inicialização porque,
quando os bancos do mapper são trocados, o código do menu desaparece.
O trampolim precisa estar na RAM (C000h-FFFFh) que não é afetada pelo mapper.

```asm
; Recebe: B = banco inicial, C = número de bancos, HL = endereço INIT

_tramp_code:
    ; Garante BIOS acessível em 0000h-3FFFh
    in a, (0A8h)            ; Lê registrador de slots
    and 11111100b           ; Limpa bits 0-1 (slot 0 = BIOS)
    out (0A8h), a           ; Aplica

    ; Mapeia banco inicial nas janelas 0 e 1
    ld a, b
    ld (6000h), a           ; Janela 0 (4000h-5FFFh) = banco B
    inc a
    ld (6800h), a           ; Janela 1 (6000h-7FFFh) = banco B+1

    ; Se jogo tem 3+ bancos, mapeia janela 2
    ld a, c
    cp 3
    jr c, _tramp_do_jump

    ld a, b
    add a, 2
    ld (7000h), a           ; Janela 2 (8000h-9FFFh) = banco B+2

    ; Se jogo tem 4 bancos, mapeia janela 3
    ld a, c
    cp 4
    jr c, _tramp_do_jump

    ld a, b
    add a, 3
    ld (7800h), a           ; Janela 3 (A000h-BFFFh) = banco B+3

_tramp_do_jump:
    ; Empilha endereço de retorno (para jogos que fazem RET)
    ld de, 0F080h           ; TRAMP_RETURN
    push de

    ei                      ; Habilita interrupções
    jp (hl)                 ; Pula para o INIT do jogo!
```

### 6.8 Rotina de Retorno (F080h)

Alguns jogos (ex: Egger) fazem RET na fase 1 da inicialização, esperando
que a BIOS retome o controle e chame hooks de interrupção. Esta rotina
simula esse comportamento:

```asm
; Instalada em F080h como bytes diretos (evita problemas de relocação)
; FB        EI          ; Habilita interrupções
; 76        HALT        ; Espera próxima interrupção
; 18 FC     JR -4       ; Volta para EI (loop infinito)
```

Quando a interrupção ocorre, o Z80 executa o handler em 0038h (BIOS),
que por sua vez chama o hook H.TIMI (FD9Fh). Se o jogo instalou um
hook nesse endereço durante a fase 1, ele toma controle na fase 2.

### 6.9 Tabela de Jogos (GameTable)

Cada entrada tem **4 bytes**:

```
Byte 0: Banco inicial no mapper (2-255)
Byte 1: Número de bancos (1, 2 ou 4)
Byte 2: INIT address low byte
Byte 3: INIT address high byte
```

Exemplo:
```asm
GameTable:
    db 2, 2, 16, 64       ; Antarctic Adv.  banco=2, 2 bancos, INIT=4010h
    db 4, 2, 79, 64       ; Cabbage Patch   banco=4, 2 bancos, INIT=404Fh
    db 12, 4, 106, 64     ; The Goonies     banco=12, 4 bancos, INIT=406Ah
    ...
```

### 6.10 Nomes dos Jogos (GameNames)

Cada nome ocupa exatamente **32 bytes** (fixo), terminado com 0:

```
Formato: "T - Nome do Jogo          (XXK)\0"
         |   |                       |
         |   |                       +-- Tamanho (8K/16K/32K)
         |   +-- Nome (truncado se necessário)
         +-- Tecla (1-9, 0, A-J)
```

Exemplo:
```asm
GameNames:
    db "1 - Antarctic Adventure (16K)", 0
    ds 2, 0              ; Padding até 32 bytes
    db "2 - Cabbage Patch Kids  (16K)", 0
    ds 2, 0
    ...
```

---

## 7. Fluxo de Execução Completo

```
1. MSX liga / Reset
   │
2. BIOS escaneia slots procurando header "AB"
   │
3. Encontra "AB" no multicart (4000h) → chama INIT (Start)
   │
4. Start:
   ├── Desliga click do teclado
   ├── Configura SCREEN 0 (40 colunas)
   ├── Limpa tela
   ├── Copia trampolim para RAM (F000h)
   ├── Copia rotina de retorno para RAM (F080h)
   └── Desenha menu
   │
5. MainLoop: espera tecla
   │
6. Tecla pressionada (ex: "7" = Knightmare)
   │
7. LoadGame:
   ├── Mostra "Carregando..."
   ├── Silencia PSG (3 canais)
   ├── Desliga tela (VDP)
   ├── Lê GameTable[6] → banco=16, bancos=4, INIT=407Eh
   ├── DI (desabilita interrupções)
   ├── SP = F380h
   └── JP F000h (trampolim na RAM)
   │
8. Trampolim (F000h):
   ├── Garante BIOS em 0000h-3FFFh
   ├── LD (6000h), 16    → 4000h-5FFFh = banco 16
   ├── LD (6800h), 17    → 6000h-7FFFh = banco 17
   ├── LD (7000h), 18    → 8000h-9FFFh = banco 18
   ├── LD (7800h), 19    → A000h-BFFFh = banco 19
   ├── PUSH F080h         → endereço de retorno no stack
   ├── EI
   └── JP 407Eh           → INIT do Knightmare
   │
9. Knightmare executa!
   ├── O menu "desapareceu" — os bancos agora mostram o jogo
   ├── O jogo não sabe que está num multicart
   └── Funciona como se fosse o único cartucho
```

---

## 8. Processo de Build (build_all.py)

```
Passo 1: Verificação de compatibilidade
         ├── Lê cada ROM
         ├── Verifica tamanho (max 32KB)
         ├── Detecta escritas acidentais no mapper → status PATCH
         ├── Detecta ENASLT, OUT A8h, etc → status AVISO
         └── Detecta MegaROM (> 32KB) → status FAIL

Passo 2: Leitura de INIT addresses
         ├── Detecta posição do header AB (0000h ou 4000h)
         ├── Lê endereço INIT do header
         └── Calcula banco inicial de cada jogo

Passo 3: Geração do menu.asm
         ├── Gera assinatura ASCII8
         ├── Gera GameTable com bancos e INIT de cada jogo
         ├── Gera GameNames com nomes formatados
         └── Gera código Assembly completo

Passo 4: Compilação com sjasmplus
         └── sjasmplus menu.asm --raw=menu.rom

Passo 5: Montagem do cartucho
         ├── menu.rom (16KB, bancos 0-1)
         ├── Para cada jogo:
         │   ├── Aplica patches (NOPs) se necessário
         │   ├── Pad para múltiplo de 8KB
         │   └── Mascara header AB
         ├── Concatena tudo
         └── Pad final para potência de 2
```

---

## 9. Compatibilidade

### 9.1 Status de verificação

| Status   | Significado                              | Ação automática        |
|----------|------------------------------------------|------------------------|
| OK       | Compatível, sem problemas                | Inclui normalmente     |
| PATCH    | Escrita acidental no mapper              | Aplica NOPs, inclui    |
| AVISO    | Padrões suspeitos (podem ser dados)      | Inclui normalmente     |
| FAIL     | MegaROM (> 32KB)                         | Exclui                 |

### 9.2 Jogos testados e confirmados

**33 jogos funcionando** de 36 testados (92% de compatibilidade).

### 9.3 Casos conhecidos de incompatibilidade

| Jogo     | Problema                                    |
|----------|---------------------------------------------|
| Egger    | Inicialização em 2 fases (RET + hook H.TIMI)|
| Kid Wiz  | Manipula slots por hardware (OUT A8h)        |
| Thexder  | Trava após menu do jogo (causa em investigação)|

---

## 10. Endereços de Memória Importantes

### 10.1 BIOS

| Endereço | Nome    | Função                          |
|----------|---------|---------------------------------|
| 0024h    | ENASLT  | Habilita slot                   |
| 0041h    | DISSCR  | Desliga tela                    |
| 0044h    | ENASCR  | Liga tela                       |
| 006Ch    | INITXT  | Inicializa modo texto           |
| 0096h    | WRT_PSG | Escreve no PSG (som)            |
| 009Fh    | CHGET   | Lê tecla do teclado             |
| 00A2h    | CHPUT   | Imprime caractere               |
| 00C3h    | CLS     | Limpa tela                      |
| 00C6h    | POSIT   | Posiciona cursor                |

### 10.2 Variáveis do sistema

| Endereço | Nome    | Função                          |
|----------|---------|---------------------------------|
| F3AEh    | LINL40  | Largura da linha (SCREEN 0)     |
| F3DBh    | CLIKSW  | Click do teclado (0=desligado)  |
| FD9Fh    | H.TIMI  | Hook de interrupção do timer    |

### 10.3 Mapper ASCII8

| Endereço | Janela  | Faixa controlada                |
|----------|---------|---------------------------------|
| 6000h    | 0       | 4000h - 5FFFh                   |
| 6800h    | 1       | 6000h - 7FFFh                   |
| 7000h    | 2       | 8000h - 9FFFh                   |
| 7800h    | 3       | A000h - BFFFh                   |

### 10.4 RAM usada pelo multicart

| Endereço | Uso                                      |
|----------|------------------------------------------|
| F000h    | Trampolim (código de troca de banco)     |
| F080h    | Rotina de retorno (EI/HALT loop)         |
| F380h    | Stack pointer durante transição          |

---

## 11. Histórico de Versões

| Versão | Novidade principal                                        |
|--------|-----------------------------------------------------------|
| v1     | Menu básico + build manual                                |
| v5     | Input interativo com lista de jogos                       |
| v9     | Inicialização completa (BIOS setup) antes do jogo         |
| v10    | Suporte a header AB em offset 0000h                       |
| v11    | Verificação de compatibilidade + patch automático (NOPs)  |
| v12    | Correção de falsos positivos (ENASLT/OUT A8h → AVISO)     |
| v13    | Trampolim com PUSH retorno (suporte a jogos com RET)      |
| v14    | Paginação de saída no terminal                            |
