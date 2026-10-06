---
name: "valor-economico"
description: "Use ao receber um PDF do jornal Valor Econômico para gerar o resumo em HTML (deck) e o roteiro script.txt para áudio: destaques na ordem tecnologia, economia, demais temas, com a seção do jornal no rodapé."
---

# Valor Econômico: PDF → resumo em HTML

Você é um jornalista com mais de 30 anos de profissão. Ao receber uma edição do **Valor Econômico em PDF**, leia o jornal inteiro e entregue um **resumo detalhado em HTML** (deck navegável de arquivo único). Salve-o na pasta do projeto do usuário. Escreva tudo em português. Toda execução entrega também o **`script.txt`**, o roteiro para áudio (ver a seção "Roteiro de áudio").

## 1. Regras editoriais (obrigatórias)

### Hierarquia de destaques
A leitura do HTML sempre começa nesta ordem, mesmo que a manchete do jornal seja de outro tema:

1. **1º destaque: Tecnologia.** Inteligência artificial, chips, big techs, startups, regulação de IA, computação quântica, cibersegurança, IPOs de tecnologia, IA aplicada em empresas.
2. **2º destaque: Economia e mercados.** Bolsa, ações, câmbio, juros/BC, petróleo e energia, fiscal, empresas, bancos e crédito.
3. **3º destaque: Outros temas.** Política, eleições, Congresso, Estados, legislação e tributos, sociedade, internacional, opinião.

Caça à tecnologia: o tema costuma estar espalhado. Procure em B (Empresas › Tecnologia, colunas de IA), C (Finanças › Mercados, IPOs), A (Opinião, Brasil › ciência) e nas citações de IA dentro de matérias de empresas. Se a edição tiver pouca tecnologia, faça ao menos 1 slide; nunca pule o 1º destaque.

### Seção do jornal no rodapé
O rodapé de cada slide traz o código da página e o nome da seção/caderno de onde veio o conteúdo:
- Uma fonte: `Seção: <b>C2</b> · Finanças › Mercados`
- Várias fontes: `Seções: <b>A21</b> · Internacional › Energia · <b>B1</b> · Empresas › Destaques`
- Exemplo: a matéria "China impulsiona IPO de startup de tecnologia" (chapéu "Mercados", linha fina "Pequim incentiva apetite de investidores por ações dos setores de IA, chips e robótica") fica com `Seção: C2 · Finanças › Mercados`.

Os cards também mostram a página no canto, por exemplo `<em>C2 · Finanças</em>`.

Cadernos do Valor:
- **A:** Política (A2–A17 em edições eleitorais), Brasil (conjuntura, indicadores), Internacional, Opinião (editorial, artigos, cartas).
- **B:** Empresas (Tecnologia, Marketing, Saúde, Alimentos, Carreira…) e Agronegócios.
- **C:** Finanças (Ativos, Mercados, Bancos, Investimentos, Regulação, Indicadores).
- **E:** Legislação & Tributos.

Use o nome de seção/chapéu impresso no topo da página.

### Precisão
- Só use números, nomes e citações que estão no PDF.
- Não invente nem complete com memória; se a edição for posterior ao seu conhecimento, relate o que o jornal diz.
- Confira cada percentual e valor contra o texto extraído antes de publicar.
- As notas "Leitura do editor" são análise sua, curta e factual, sem opinião partidária.

## 2. Onde salvar
- Pasta de saída no computador do usuário (projeto Speech AI): `D:\Laboratorio de IA\speech-ai\speech-ai\output\Jornais`.
- **Sempre crie uma pasta nova** com o nome do jornal e a data de processamento (hoje, DD-MM-AAAA): `Valor Econômico - DD-MM-AAAA\`.
  Se ela já existir, use um sufixo, por exemplo `Valor Econômico - DD-MM-AAAA (2)\`.
- O arquivo vai dentro dela: `Valor Econômico - DD-MM-AAAA.html`.
- Na mesma pasta vai o **`script.txt`** (roteiro para áudio).
- **Claude Code local:** grave direto na pasta acima.
- **Cowork:** grave com device_commit_files a partir de `/mnt/user-data/outputs/` e envie com SendUserFile.
- Depois de gravar, gere o áudio (seção "Gerar o áudio").

## 3. Base visual (reutilize, não reinvente)

O padrão visual vem do modelo `D:\Laboratorio de IA\Jornais\Walk-Challenge-Ambassador-Connect-2026-09-embedded 1.html`:
- palco 1600x900 escalável;
- capa e divisórias escuras com campo de pontos animado;
- slides claros com KPIs, cards e gráficos;
- navegação por teclado, visão geral (O), modo escuro (D), tela cheia (F);
- leitura vertical no celular;
- sem a marca Stellantis e sem a troca de idioma inglês/chinês.

**Atalho recomendado:** use como base o último resumo do Valor já gerado na pasta, por exemplo o HTML mais recente em `D:\Laboratorio de IA\speech-ai\speech-ai\output\Jornais\Valor Econômico - *\` (se não houver, em `D:\Laboratorio de IA\Jornais\Valor Econômico - *\`).
1. Faça o stage dele, ou de qualquer pasta `Valor Econômico - *` mais recente.
2. Mantenha intacto todo o `<head>`/`<style>` e o `<script>` final.
3. Troque só as `<section class="slide">` dentro de `<main class="deck">`.
4. Atualize `<title>` e `meta description`.

O script já cuida de várias coisas sozinho:
- cria o selo de destaque a partir de `data-tier`;
- monta os pontos de navegação e a visão geral;
- numera os slides;
- desenha o gráfico de linha via `lineChart(svg, dados, opções)`;
- mostra tooltips em qualquer elemento com `data-tip`;
- recolhe a barra de navegação quando o usuário fica parado.

Se o gráfico de linha não for usado, remova a chamada `lineChart(document.getElementById('absChart'), …)` ou troque os dados.

### Componentes disponíveis (classes)
- **Slide:** `<section class="slide" data-theme="light" data-tier="1|2|3" data-title="…">`.
  - Capa: `t-cover active`, tema dark.
  - Divisória: `t-div`, `data-divider="1"`, tema dark.
- **Topo:** `p.eyebrow.rv`, `h2.sh.rv`, `p.lede.rv`.
- **Fecho:** `p.takeaway.rv` com `<b>Leitura do editor:</b>`.
- **Rodapé:** `div.sfoot > span (seção) + span.pg`.
- **KPIs:** `.kgrid` (k2/k3/tight/tall) e `.kcard` (acc, pos, t1) com `.num`, `.unit`, `.klab`, `.ksub`.
- **Faixas de destaque:** `.tiers > .trow.t1|t2|t3 > p.tlab` + 4 `.kcard`.
- **Cards:** `.cards` (c2/c3, `big`, `fill`) e `.card` (sig, flag, dk, t1c/t2c/t3c) com `.ctag <em>página</em>`, h3, p/ul, `.quote` e `.qby`.
- **Colunas:** `.lr` (w58, n58, w64), com títulos `.colh` (a/b).
- **Passos:** `.steps` (fill, big) e `.step` (o, g) com `.sn`, h4 e p.
- **Gráficos:**
  - `.chart > h4 + .csub + .hbars > .hb[data-tip]`, com `span.hl`, `span.ht > i(style="--w:%;--d:s", classe c2/c3/c4/cm)` e `b`.
  - `.gbars` para barras agrupadas e `.dumb > .db` para halteres (antes → depois).
  - Tabela `.tbl` e pílulas `.mini > .pill`.
- **Capa:** `.cover-score` com `p.ord-h` "Ordem de leitura" e três `.cs-row.t1|t2|t3`, cada um com `.who`, `.ttl` e `.note`.

Para gráficos, carregue a skill `dataviz` e siga suas regras:
- uma série = uma cor; categorias de apoio em `cm` (cinza);
- nada de eixo duplo;
- tooltips via `data-tip`;
- legenda quando houver 2 séries ou mais.

## Roteiro de áudio: `script.txt` (obrigatório)

Toda execução desta skill entrega **dois arquivos** na mesma pasta: o HTML e um **`script.txt`**. O `script.txt` é o resumo do HTML reescrito para ser lido em voz alta por uma ferramenta de texto para fala (TTS).

**Conteúdo e ordem** (a mesma do HTML):
1. **Título falado:** "Resumo do jornal Valor Econômico. Edição de {data por extenso}."
2. **Abertura:** "Bom dia. Este é o resumo…", citando os três destaques na ordem.
3. **"Primeiro destaque: tecnologia e inteligência artificial."** Um parágrafo por slide de tecnologia.
4. **"Segundo destaque: economia e mercados."** Um parágrafo por assunto.
5. **"Terceiro destaque: política e demais temas."** Um parágrafo por assunto.
6. **"O que acompanhar…":** em uma frase por destaque.
7. **Encerramento:** "Este foi o resumo do Valor Econômico. Até a próxima edição."

**Regras de escrita para voz:**
- Só texto corrido em português, UTF-8. Nada de markdown, marcadores, tabelas, emojis, HTML, links ou códigos de página (A9, B7…).
- Frases curtas (até ~25 palavras) e parágrafos separados por uma linha em branco. Cada destaque é anunciado em frase própria.
- Números escritos para serem falados:
  - "47,03%" vira "47,03 por cento";
  - "R$ 30 bi" vira "30 bilhões de reais";
  - "US$ 55,7 mi" vira "55,7 milhões de dólares";
  - "−0,5 pp" vira "meio ponto percentual";
  - "130 pb" vira "130 pontos-base";
  - "5/out" vira "5 de outubro".
- Sem símbolos: `% R$ US$ × → • * # < >`. Troque "×" por "contra" e "→" por "para".
- Siglas: use as conhecidas (PT, PL, STF, PIB, Selic). Na primeira menção, troque siglas obscuras pelo nome por extenso (por exemplo, "Agência Internacional de Energia").
- Inclua as "Leituras do editor" mais importantes como "Na leitura do editor, …".
- Mesmos fatos e números do HTML: não acrescente nada que não esteja no resumo.
- Tamanho: 700 a 1.100 palavras (cerca de 5 a 7 minutos de áudio).

**Validação antes de entregar** (rode em Python):
- Conte as palavras.
- Procure `[%×→•*#$<>]`, `R$`, `US$`, ` pp `, ` bi `, ` mi `, `http`. O resultado precisa ser zero ocorrências.
- Confira que os três destaques aparecem na ordem.

**Gravação:** salve em `D:\Laboratorio de IA\speech-ai\speech-ai\output\Jornais\Valor Econômico - DD-MM-AAAA\script.txt`, ao lado do HTML (no Cowork, via `/mnt/user-data/outputs/<jornal>/script.txt` e device_commit_files).

## Gerar o áudio (Speech AI)

Depois de gravar o HTML e o `script.txt`, gere o áudio com o Speech AI. Esse comando lê o `script.txt` mais recente deste jornal (na pasta do jornal em `output\Jornais`) e grava o mp3 em `output\<Jornal> - DD-MM-AAAA_AAAA-MM-DD_HH-MM-SS.mp3` (nome da pasta + data e hora da geração):

```
cd "D:\Laboratorio de IA\speech-ai\speech-ai"
python main.py --skill valor-economico
```

- Se você tiver acesso ao terminal do computador do usuário, execute o comando e informe o caminho do mp3.
- Se não tiver (por exemplo, no Cowork sem terminal local), diga ao usuário para executar o comando acima.
- **Exceção:** quando o prompt disser que a execução é automática pelo `main.py`, não execute esta etapa; o Speech AI gera o áudio sozinho.


## 4. Procedimento

1. **Extrair.** Use `pdftotext` página a página (`-f i -l i`). Limpe o texto:
   - una hifenizações;
   - descarte linhas só numéricas;
   - guarde um dicionário página → texto.

   Leia a capa e o índice primeiro e anote o código de cada página (A2, B7, C2…) com seu caderno e chapéu. Ignore publicidade, editais e balanços legais.
2. **Ler tudo.** Para cada página, registre:
   - manchete;
   - linha fina;
   - números-chave;
   - 1 a 2 citações;
   - página e seção.

   Classifique cada matéria em 1º, 2º ou 3º destaque.
3. **Planejar o deck** (cerca de 20 a 26 slides), sempre nesta ordem:
   1. **Capa:** manchete-síntese que cite os três destaques na ordem, mais o quadro "Ordem de leitura".
   2. **"Em uma página":** três faixas de 4 KPIs (`.tiers`), uma por destaque.
   3. **Divisória 01 · Tecnologia e IA**, seguida de 2 a 5 slides.
   4. **Divisória 02 · Economia e mercados**, seguida de 4 a 7 slides: bolsa e câmbio, fiscal, juros/BC, petróleo/energia, empresas, bancos.
   5. **Divisória 03 · Política e demais temas**, seguida dos slides restantes.
   6. **Encerramento "O que acompanhar":** 6 cards `dk` na ordem t1c, t2c, t3c.
4. **Escrever.**
   - Cada slide de conteúdo leva `data-tier`, eyebrow com as páginas, título jornalístico, conteúdo denso e rodapé no formato de seção.
   - Prefira números e citações a adjetivos.
   - Inclua "Leitura do editor" nos slides principais.
5. **Verificar (obrigatório antes de entregar).**
   - **Fontes:** baixe-as para o teste com `npm pack @fontsource/encode-sans-expanded @fontsource/encode-sans` e injete um `@font-face` local numa cópia de teste.
   - **Desktop:** com Playwright (Chromium pré-instalado) a 1600x900, percorra os slides com a seta direita.
     - Para cada slide ativo, normalize as posições pela escala do deck.
     - Sinalize qualquer elemento (fora `.sfoot`) com base > 842 px ou direita > 1512 px.
     - Tire um screenshot de cada slide.
     - Confira o console sem erros.
   - **Revisão visual:** veja os screenshots em folhas de contato. Corrija:
     - texto cortado;
     - sobreposições;
     - grandes vazios (use `big` e `fill`, ou acrescente conteúdo real do jornal).
   - **Celular:** a 390x844, `document.documentElement.scrollWidth` deve ser 390 (sem rolagem horizontal) e os KPIs não podem ficar cortados.
6. **Entregar.**
   - Escreva o `script.txt` a partir do HTML final e valide-o (seção "Roteiro de áudio").
   - Grave o HTML e o `script.txt` na pasta nova (seção "Onde salvar").
   - Gere o áudio (seção "Gerar o áudio").
   - Na resposta, use 1 frase sobre o arquivo e uma lista curta dos principais pontos por destaque, na ordem 1º, 2º e 3º.

## 5. Lembretes
- Toda execução gera **dois arquivos**: o HTML e o `script.txt`. Sem o `script.txt`, a entrega está incompleta. Em seguida vem o áudio (mp3) do Speech AI.
- A ordem 1º → 2º → 3º vale para a capa, o "Em uma página", as seções e a agenda final.
- Todo slide de conteúdo tem rodapé com página + seção do Valor.
- Não publique o resumo como artefato a menos que o usuário peça: o pedido é o arquivo na pasta.
- Se o PDF não for do Valor Econômico (Estadão, Folha), aplique a mesma hierarquia e o mesmo visual. Adapte o rodapé ao caderno daquele jornal e use o nome do jornal na pasta e no arquivo.