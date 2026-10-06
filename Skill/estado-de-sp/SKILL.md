---
name: "estado-de-sp"
description: "Use ao receber um PDF do jornal O Estado de S. Paulo (Estadão) para gerar o resumo diário em HTML e o roteiro script.txt para áudio: destaques na ordem tecnologia, economia, demais temas, com página e caderno no rodapé."
---

# O Estado de S. Paulo: PDF → resumo diário em HTML

Você é um jornalista com mais de 30 anos de profissão. Ao receber uma edição do **Estadão em PDF**, leia o jornal inteiro e entregue um **resumo detalhado em HTML**: um deck navegável de arquivo único, salvo na pasta do projeto do usuário. Escreva tudo em português. Toda execução entrega também o **`script.txt`**, o roteiro para áudio (ver a seção "Roteiro de áudio").

## 1. Regras editoriais (obrigatórias)

### Hierarquia de destaques
A leitura do HTML sempre começa nesta ordem, mesmo que a manchete do jornal seja de outro tema:

1. **1º destaque: Tecnologia.** Inteligência artificial, chips, big techs, startups, regulação de IA, ciência e espaço, cibersegurança, IPOs de tecnologia e IA aplicada (saúde, Justiça, segurança, agro, consumo).
2. **2º destaque: Economia e mercados.** Bolsa, ações, câmbio, juros e BC, petróleo e energia, fiscal, empresas, bancos, crédito, agro, consumo e regulação econômica (por exemplo, as bets).
3. **3º destaque: Outros temas.** Política, eleições, Congresso, Estados, Judiciário, editoriais e opinião, internacional, cidade, saúde, esportes e cultura.

**Caça à tecnologia no Estadão:** o tema raramente tem caderno próprio e aparece espalhado. Procure em:
- **Internacional (A9–A11):** por exemplo, a página "Tecnologia e voto".
- **Metrópole (A12–A16):** a seção "Futuro e Inovação" e as notícias de ciência e espaço.
- **E&N (B1–B2):** IA e juros, data centers.
- **E-Investidor (B6–B7):** exposição a IA e Nvidia.
- **Coluna do Broadcast Agro (B8):** startups.
- **B4:** plataformas e dados.
- **A Fundo (C6–C7):** ciência e genômica.
- **Especial:** promessas de IA de candidatos e governos, como câmeras com IA.
- **Política (A8):** pesquisas que citam IA.

Se a edição tiver pouca tecnologia, faça ao menos 1 slide; nunca pule o 1º destaque.

### Página e caderno no rodapé
Cada slide traz no rodapé o código da página e o caderno/seção, com a retranca (chapéu) quando houver:
- Uma fonte: `Seção: <b>A9</b> · Internacional › Tecnologia e voto`
- Várias fontes: `Seções: <b>B1–B2</b> · Economia &amp; Negócios › Cenário · <b>B7</b> · E-Investidor`

Os cards também mostram a página no canto, por exemplo `<em>A15 · Metrópole › Futuro e Inovação</em>`.

### Mapa do Estadão
Mapa observado na edição de 05/10/2026 (4 cadernos, 56 páginas). Confirme no índice "Edição de hoje" da capa e no cabeçalho de cada página, porque cadernos e numeração variam por dia.

**Caderno A**

| Página | Seção |
|---|---|
| A1 | Capa |
| A2 | Coluna do Estadão (bastidores políticos) |
| A3 | Notas e Informações (editoriais do jornal) |
| A4–A6 | Espaço Aberto (artigos, Fórum dos Leitores) |
| A8 | Política |
| A9–A11 | Internacional (colunistas: seg. Oliver Stuenkel) |
| A12–A16 | Metrópole (Saúde, "Futuro e Inovação", séries especiais) |
| A17 | Classificados (ignorar) |
| A18–A19 | Esportes |
| A20 | "Para fechar… uma boa história" |

**Caderno B: Economia & Negócios (E&N)**

| Página | Seção |
|---|---|
| B1 | Destaque |
| B2–B3 | Cenário e artigos (colunistas: seg. Luiz Carlos Trabuco/Henrique Meirelles) |
| B4 | Negócios, com a tabela **Broadcast Mercados** (Ibovespa, dólar, Brent, bolsas, Selic, inflação): use-a para os números de mercado |
| B5 | Publicidade legal e licitações (ignorar) |
| B6–B7 | E-Investidor |
| B8 | Coluna do Broadcast Agro |

**Caderno C: Cultura & Comportamento**

| Página | Seção |
|---|---|
| C1–C5 | Streaming, cinema, horóscopo, quadrinhos, literatura e jogos |
| C6–C7 | A Fundo (medicina e estudos, entrevistas científicas) |
| C8 | Cultura & Comportamento |

**Caderno D: Especial.** Aparece em datas especiais, por exemplo "Especial Eleições" D1–D20. Pode ter "Notas e Informações" próprio (D13).

Outros cadernos (por exemplo, Link, Paladar ou suplementos de fim de semana) podem aparecer em outros dias. Registre-os com a letra e o nome impressos.

### Precisão
- Só use números, nomes e citações que estão no PDF.
- Não invente nem complete com memória; se a edição for posterior ao seu conhecimento, relate o que o jornal diz.
- Quando o próprio jornal trouxer números divergentes entre páginas (por exemplo, "19" e "20" vagas), use o número da matéria principal ou escreva sem o número exato.
- "Notas e Informações" é a opinião do jornal: atribua-a ao editorial, nunca como fato.
- As notas "Leitura do editor" são análise sua, curta e factual, sem opinião partidária.

## 2. Onde salvar
- Pasta de saída no computador do usuário (projeto Speech AI): `D:\Laboratorio de IA\speech-ai\speech-ai\output\Jornais`.
- **Sempre crie uma pasta nova** com o nome do jornal e a data de processamento (hoje, DD-MM-AAAA): `O Estado de S. Paulo - DD-MM-AAAA\`.
  Se ela já existir, use um sufixo, por exemplo `O Estado de S. Paulo - DD-MM-AAAA (2)\`.
- O arquivo vai dentro dela: `O Estado de S. Paulo - DD-MM-AAAA.html`.
- Na mesma pasta vai o **`script.txt`** (roteiro para áudio).
- **Claude Code local:** grave direto na pasta acima.
- **Cowork:** grave com device_commit_files a partir de `/mnt/user-data/outputs/` e envie com SendUserFile.
- Depois de gravar, gere o áudio (seção "Gerar o áudio").

## 3. Base visual (reutilize, não reinvente)

O padrão visual é o do modelo `D:\Laboratorio de IA\Jornais\Walk-Challenge-Ambassador-Connect-2026-09-embedded 1.html`:
- palco 1600x900;
- capa e divisórias escuras com pontos animados;
- slides claros com KPIs, cards e gráficos;
- teclado, visão geral (O), modo escuro (D), tela cheia (F);
- leitura vertical no celular;
- sem marca Stellantis.

**Atalho:**
1. Faça o stage do último resumo gerado em `D:\Laboratorio de IA\speech-ai\speech-ai\output\Jornais` (se não houver, em `D:\Laboratorio de IA\Jornais`): de preferência a pasta `O Estado de S. Paulo - *` mais recente; senão, `Valor Econômico - *`.
2. Mantenha intactos o `<head>`/`<style>` e o `<script>` final.
3. Troque só as `<section class="slide">` dentro de `<main class="deck">`.
4. Atualize `<title>`, a `meta description` e o texto da marca no topo: `Resumo da edição · O Estado de S. Paulo`.
5. Remova chamadas `lineChart(...)` que apontem para gráficos que não existam no novo conteúdo.

### Componentes disponíveis (classes)
- **Slide:** `<section class="slide" data-theme="light" data-tier="1|2|3" data-title="…">`. O script cria o selo do destaque a partir de `data-tier`.
  - Capa: `t-cover active`, tema dark.
  - Divisória: `t-div`, `data-divider="1"`, tema dark.
- **Topo:** `p.eyebrow.rv`, `h2.sh.rv`, `p.lede.rv`.
- **Fecho:** `p.takeaway.rv` com `<b>Leitura do editor:</b>`.
- **Rodapé:** `div.sfoot > span (seção) + span.pg`.
- **KPIs:** `.kgrid` (k2/k3/tight/tall) e `.kcard` (acc, pos, t1).
- **Faixas de destaque:** `.tiers > .trow.t1|t2|t3 > p.tlab` + 4 `.kcard`.
- **Cards:** `.cards` (c2/c3, `big`, `fill`) e `.card` (sig, flag, dk, t1c/t2c/t3c) com `.ctag <em>página · seção</em>`, h3, p/ul, `.quote` e `.qby`.
- **Colunas e passos:** `.lr` (w58/n58), `.colh` (a/b), `.steps` (big) e `.step` (o/g).
- **Gráficos:**
  - `.chart > h4 + .csub + .hbars > .hb[data-tip]`, com `span.hl`, `span.ht > i(style="--w:%;--d:s", c2/c3/c4/cm)` e `b`.
  - `.stack` para composição em %.
  - `.tbl` e `.mini > .pill`.
- **Capa:** `.cover-score` com "Ordem de leitura" e três `.cs-row.t1|t2|t3`.

Para gráficos, carregue a skill `dataviz`:
- uma série = uma cor; apoio em `cm`;
- nada de eixo duplo;
- tooltips via `data-tip`;
- legenda quando houver 2 séries ou mais.

## Roteiro de áudio: `script.txt` (obrigatório)

Toda execução desta skill entrega **dois arquivos** na mesma pasta: o HTML e um **`script.txt`**. O `script.txt` é o resumo do HTML reescrito para ser lido em voz alta por uma ferramenta de texto para fala (TTS).

**Conteúdo e ordem** (a mesma do HTML):
1. **Título falado:** "Resumo do jornal Estadão. Edição de {data por extenso}."
2. **Abertura:** "Bom dia. Este é o resumo…", citando os três destaques na ordem.
3. **"Primeiro destaque: tecnologia e inteligência artificial."** Um parágrafo por slide de tecnologia.
4. **"Segundo destaque: economia e mercados."** Um parágrafo por assunto.
5. **"Terceiro destaque: política e demais temas."** Um parágrafo por assunto.
6. **"O que acompanhar…":** em uma frase por destaque.
7. **Encerramento:** "Este foi o resumo do Estadão. Até a próxima edição."

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

**Gravação:** salve em `D:\Laboratorio de IA\speech-ai\speech-ai\output\Jornais\O Estado de S. Paulo - DD-MM-AAAA\script.txt`, ao lado do HTML (no Cowork, via `/mnt/user-data/outputs/<jornal>/script.txt` e device_commit_files).

## Gerar o áudio (Speech AI)

Depois de gravar o HTML e o `script.txt`, gere o áudio com o Speech AI. Esse comando lê o `script.txt` mais recente deste jornal (na pasta do jornal em `output\Jornais`) e grava o mp3 em `output\<Jornal> - DD-MM-AAAA_AAAA-MM-DD_HH-MM-SS.mp3` (nome da pasta + data e hora da geração):

```
cd "D:\Laboratorio de IA\speech-ai\speech-ai"
python main.py --skill estado-de-sp
```

- Se você tiver acesso ao terminal do computador do usuário, execute o comando e informe o caminho do mp3.
- Se não tiver (por exemplo, no Cowork sem terminal local), diga ao usuário para executar o comando acima.
- **Exceção:** quando o prompt disser que a execução é automática pelo `main.py`, não execute esta etapa; o Speech AI gera o áudio sozinho.


## 4. Procedimento

1. **Extrair.** Use `pdftotext -f i -l i` página a página. Limpe o texto:
   - una hifenizações;
   - descarte linhas só numéricas e a marca "Ines249".

   Algumas páginas (por exemplo, falecimentos) saem com fonte corrompida: aproveite só o texto legível. Pule A17 (classificados), B5 (editais) e anúncios de página inteira.
2. **Mapear.**
   - Leia a capa: índice "Edição de hoje", manchetes e chamadas com página.
   - Monte o mapa página → caderno → retranca da edição do dia.
3. **Ler tudo.** Para cada matéria, registre:
   - manchete e linha fina;
   - números;
   - 1 a 2 citações;
   - página e seção.

   Classifique em 1º, 2º ou 3º destaque.
4. **Planejar** (cerca de 18 a 24 slides), sempre nesta ordem:
   1. **Capa:** manchete-síntese citando os três destaques na ordem, mais a "Ordem de leitura".
   2. **"Em uma página":** três faixas de 4 KPIs.
   3. **Divisória 01 · Tecnologia e IA**, seguida de 2 a 5 slides.
   4. **Divisória 02 · Economia e mercados**, seguida de 3 a 6 slides. Use a tabela Broadcast (B4) para um painel de mercados.
   5. **Divisória 03 · Política e demais temas**, seguida dos slides restantes:
      - política e Especial;
      - editoriais (A3), Coluna do Estadão (A2) e Espaço Aberto;
      - um slide-mosaico com Internacional, Metrópole, Esportes, Cultura e "Para fechar".
   6. **Encerramento "O que acompanhar":** 6 cards `dk` na ordem t1c, t2c, t3c.
5. **Escrever.**
   - Cada slide de conteúdo leva `data-tier`, eyebrow com as páginas, título jornalístico, conteúdo denso e rodapé com página › seção.
   - Inclua "Leitura do editor" nos slides principais.
6. **Verificar (obrigatório).**
   - **Fontes:** baixe-as com `npm pack @fontsource/encode-sans-expanded @fontsource/encode-sans` e injete um `@font-face` local numa cópia de teste.
   - **Desktop:** com Playwright a 1600x900, percorra os slides com a seta direita.
     - Sinalize elementos fora de `.sfoot` com base > 842 px ou direita > 1512 px, normalizando pela escala do deck.
     - Confira se algum `.card`, `.kcard`, `.step`, `.chart` ou `.tbl` tem `scrollHeight > clientHeight`.
     - Confira o console sem erros.
   - **Revisão visual:** veja os screenshots em folhas de contato e corrija cortes, sobreposições e vazios grandes. Acrescente conteúdo real do jornal ou uma "Leitura do editor".
   - **Celular:** a 390x844, sem rolagem horizontal (`scrollWidth` = 390) e com os KPIs inteiros.
7. **Entregar.**
   - Escreva o `script.txt` a partir do HTML final e valide-o (seção "Roteiro de áudio").
   - Grave o HTML e o `script.txt` na pasta nova (seção "Onde salvar").
   - Gere o áudio (seção "Gerar o áudio").
   - Responda com 1 frase sobre o arquivo e uma lista curta dos principais pontos por destaque, na ordem 1º, 2º e 3º.

## 5. Lembretes
- Toda execução gera **dois arquivos**: o HTML e o `script.txt`. Sem o `script.txt`, a entrega está incompleta. Em seguida vem o áudio (mp3) do Speech AI.
- A ordem 1º → 2º → 3º vale para a capa, o "Em uma página", as seções e a agenda final.
- Todo slide de conteúdo tem rodapé com página + seção do Estadão.
- Não publique como artefato a menos que o usuário peça; o pedido é o arquivo na pasta.
- O documento do projeto `claude/padrao-de-entrega-dos-resumos.md` reúne as mesmas regras para os três jornais.