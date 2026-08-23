## Multicart ROM Builder para MSX

23 de agosto de 2026

Meu projeto de criação de um único cartucho com multiplas Roms e menu de seleção ao longo do boot.  
Inicialmente criado de uma idéia de gerar uma única .rom para a família Nemesis do MSX - até o momento em Hold devido  
aos desafios de bank switching dos próprios jogos. 

### Requisitos

- Python 3 para rodar o script build  
- SJASMPLUS para compilar o menu.asm produzido pelo Build  
- A lista de jogos rom desejada  
Limites: até 20 jogos (limite do Menu no momento)  
Jogos devem ser de até 32K  

### O que o Builder faz

- 1:Builder pergunta a lista de jogos (nome e arquivo.rom) necessários  
- 2:Builder Gera o menu.asm com a lista desejada e compila menu.rom usando o sjasmplus.exe  
- 3:Builder Gera multicart.rom com o menu.rom + todos os jogos informados  

### Como começar

- Colocar builder.py em diretório com sjasmplus.exe e os jogos .rom  
- Executar o builder.py  
- Informar a lista e aguardar o arquivo .rom ser montado  
- Rodar arquivo multicar.rom no emulador - testado com WebMSX.

### Dados do cartucho gerado

-Formato ASCII8 - automaticamente detectado pelos emuladores  
-Permite até 2MB de jogos - +- 64 jogos de 32K, porém menu não suporta  
esta qtde de opcoes ainda - hoje max=20.

### Melhorias para o futuro

-Menu para 64 jogos  
-Suporte a Cartucho megaROM  




## Exemplo de saída


>C:\msx\multirom>python build_multicart.py  

  MSX MULTI-ROM BUILDER v5

  Use aspas para nomes com virgula ou apostrofo: (termine com //fim)

 >"Knight Mare",knightmare.rom, "King's Valley", kvalley.rom, "Pippols",pippols.rom//fim  


  3 jogos detectados:

  [1] Knight Mare              <- knightmare.rom  
  [2] King's Valley            <- kvalley.rom  
  [3] Pippols                  <- pippols.rom  

  Correto? (S/n): s

[1/4] Verificando ROMs...
(...)    

[2/4] Gerando menu.asm...
  OK menu.asm (3 jogos)

[3/4] Compilando com sjasmplus...
  OK menu.rom compilado

[4/4] Montando cartucho...
  OK multicart.rom (128KB)

  CARTUCHO PRONTO!

  Arquivo: multicart.rom (128KB)
  Mapper:  ASCII8 (auto-detectavel)
  
  Teste: arraste multicart.rom no WebMSX

