# Speech AI — Jornais e roteiros viram áudio, com IA local e custo zero

**Documento-fonte para geração de vídeo e áudio no NotebookLM (Google).**
Projeto: `speech-ai` · Última atualização: 9 de outubro de 2026.

---

## 1. O que é o Speech AI

O Speech AI é uma solução que transforma, todos os dias, dois tipos de material em áudio narrado em português:

1. **Jornais em PDF** — hoje, o Valor Econômico e O Estado de S. Paulo (Estadão).
2. **Roteiros de texto (.txt)** — texto já pronto para narração.

Para os jornais, a saída não é só áudio: é um **resumo executivo em HTML** (um deck navegável, com capa, destaques organizados por hierarquia editorial, KPIs, gráficos e citações), um **roteiro de voz** (`script.txt`) e o **MP3** narrado — tudo gerado a partir do PDF bruto, sem intervenção humana no meio do caminho.

A missão do projeto, desde o início, foi reduzir drasticamente o tempo entre "o jornal chegou" e "o resumo em áudio está pronto para ouvir", sem perder qualidade editorial. Ao longo de três sprints, essa missão ganhou uma segunda frente: reduzir também o **custo**, até chegar a zero.

---

## 2. A evolução em três etapas

### Etapa 1 — A skill original (manual, via Claude Code)

No desenho original, o Claude Code executava uma *skill* inteira (um arquivo `SKILL.md` com instruções editoriais) como um agente autônomo: ele mesmo extraía o texto do PDF, lia o jornal em pedaços, copiava a base visual de edições anteriores, escrevia o HTML e revisava o resultado — tudo isso em **100 a 126 rodadas de interação** por jornal. O processo levava de **15 a 20 minutos** e custava entre **US$ 5,60 e US$ 6,55** por jornal, porque cada rodada do agente consumia tokens de raciocínio e ferramentas, não só de escrita.

### Etapa 2 — O processo rápido, com IA paga (Sprint 12)

A mudança central da Sprint 12 foi uma pergunta simples: *o que, nesse processo, realmente precisa de inteligência artificial?* A resposta foi: só a parte editorial — decidir o que é notícia, como hierarquizar, como resumir, como escrever para voz. Tudo o mais (extrair o PDF, montar o HTML, verificar se o texto cabe no layout) é trabalho mecânico que o Python faz melhor, mais rápido e mais barato.

Nasceu assim o **motor "fast"**: o Python extrai o texto do PDF em segundos (`pdftotext`, página a página, com limpeza de anúncios e editais), identifica a seção de cada página, e entrega esse texto para **cinco chamadas de IA em paralelo** — uma para tecnologia, duas para economia (mercados/macro e empresas/setores) e duas para os demais temas (política/eleições e demais assuntos) — mais uma sexta chamada curta para escrever a capa. Cada chamada usava o Claude (Opus 5.5 para o conteúdo, Sonnet 5.5 para a capa) em modo não-interativo, sem ferramentas, com saída validada por um schema JSON estrito: slides, KPIs, cards, citações, fontes e o parágrafo de áudio de cada slide, tudo num único disparo.

O truque de performance e custo foi o **cache de contexto da Anthropic**: o jornal inteiro (de 176 mil a 354 mil tokens, dependendo da edição) era enviado uma vez no *system prompt*, idêntico para todas as chamadas. A primeira chamada gravava esse cache; as outras cinco liam o mesmo texto a uma fração do custo — um bloco de contexto que custaria US$ 1,64 para processar do zero caía para US$ 0,05 quando lido do cache.

O resultado: do PDF ao MP3 completo, o Valor Econômico de 6 de outubro de 2026 levou **2 minutos e 21 segundos** e custou **US$ 1,02**. O Estadão, com a tecnologia mais espalhada entre cadernos, levou cerca de **3,5 minutos** e custou **US$ 2,57**. Em ambos os casos, um teste de fidelidade comparando os números dos slides contra o texto original do jornal encontrou **166 de 166 números corretos**, com citações sempre literais.

### Etapa 3 — IA local, custo zero (Sprint 13)

A etapa 2 já tinha resolvido o problema de tempo. A Sprint 13 atacou o problema de **custo**: trocar o Claude (API paga da Anthropic) por um modelo de IA rodando **localmente**, na GPU da própria máquina, via **Ollama**.

A máquina disponível tem uma GPU **NVIDIA RTX A3000 Laptop, com 6 GB de VRAM** — uma GPU de notebook profissional, não um acelerador dedicado para IA. Entre os modelos testados (gemma3:4b, deepseek-r1:8b, deepseek-r1:32b, qwen2.5:72b-instruct, llama3), só os menores cabem inteiros nesses 6 GB; o qwen2.5:72b, por exemplo, levou quase três minutos só para carregar e responder uma frase trivial, porque precisa rodar parcialmente na CPU. A escolha recaiu sobre o **gemma3:4b**: o único que mantém velocidade aceitável rodando 100% na GPU.

Essa troca trouxe um problema novo: a GPU local não tem — nem de longe — espaço de contexto para receber o jornal inteiro como a nuvem da Anthropic recebia. A solução foi mover trabalho para o Python: `newsroom/profiles.py` agora mantém listas de **palavras-chave por destaque** (cerca de 40 termos só para tecnologia, por exemplo), e antes de cada chamada de IA o sistema seleciona, dentro de um orçamento de 5.000 palavras, só as páginas do jornal mais relevantes para aquele destaque específico — descartando o resto.

O resultado directo: **custo de IA caiu a zero**. O que sobra é a conta de energia da GPU, que é irrisória — medida diretamente com `nvidia-smi` durante uma execução real e completa, a GPU consumiu em média 34,2 W, totalizando **17,8 Wh por jornal**, o equivalente a cerca de **R$ 0,02** na tarifa da CEMIG em Contagem, Minas Gerais.

O preço dessa troca é tempo: o mesmo jornal que levava 2 a 3 minutos com a IA paga agora leva **entre 25 e 43 minutos** — de 11 a 18 vezes mais lento — porque a GPU de 6 GB processa uma fração da velocidade da nuvem, mesmo com o recorte de texto reduzido.

---

## 3. Bugs reais encontrados — e corrigidos — na migração

Trocar de modelo não foi apenas uma troca de API. Um modelo quatro vezes menor que o Opus se comporta de forma diferente, e isso expôs problemas reais, encontrados em execuções de teste com jornais de verdade:

- **Conversão de moeda quebrada**: a regra que transforma "R$ 3,2 bi" em "3,2 bilhões de reais" (para a fala) só reconhecia abreviações. Quando a IA escrevia a palavra por extenso ("R$ 3,2 bilhões"), o resultado saía como "3,2 reaisbilhões" — colado, errado. Corrigido ao ensinar a mesma regra a reconhecer as duas formas.
- **Data errada no áudio**: com um modelo menor, a IA às vezes copiava literalmente o exemplo de formato dado nas instruções do sistema, em vez de escrever a data real da edição — um jornal de 8 de outubro saía anunciado como "edição de 3, 4 e 5 de outubro". A correção foi tirar essa tarefa da IA por completo: a data certa já está impressa na capa do próprio PDF, então agora ela é **lida diretamente do texto extraído**, em Python, de forma determinística.
- **Citações que não eram citações**: o modelo local, por vezes, parafraseava uma frase do jornal e a apresentava como citação literal entre aspas — ou pior, trocava os campos, colocando o nome do entrevistado no lugar da frase e vice-versa. A correção tem duas partes: uma validação que descarta qualquer citação que não apareça, palavra por palavra, no texto original enviado à IA; e uma heurística que detecta e desfaz a inversão de campos quando ela acontece.
- **Respostas cortadas no meio**: com um orçamento de contexto pequeno (16 mil tokens), algumas chamadas esgotavam o espaço disponível antes de terminar de escrever o JSON, resultando em respostas inválidas. A correção foi dobrar o contexto para 32.768 tokens e reduzir levemente o recorte de entrada, abrindo espaço de sobra para a resposta.

Depois dessas correções, uma execução completa e real (Valor Econômico, 8 de outubro) fechou com as seis chamadas de IA certas já na primeira tentativa, roteiro dentro da meta de palavras, data correta e nenhuma citação fabricada.

---

## 4. O processo, passo a passo

1. **Entrada**: PDFs chegam em `input\Jornais\`; roteiros de texto chegam em `input\`. Pode ser por cópia manual ou pelo frontend web.
2. **Orquestração** (`main.py`, sem IA): identifica o tipo de cada arquivo e decide a ordem — roteiros de texto primeiro, depois os jornais.
3. **Extração** (Python, ~2 segundos): o texto de cada página do PDF é extraído, limpo (removendo anúncios, editais, tabelas numéricas) e marcado com o código e a seção da página.
4. **IA editorial** (gemma3:4b, na GPU local, 20 a 43 minutos): cinco chamadas em paralelo escrevem o conteúdo de cada destaque, seguidas de uma sexta chamada curta para a capa — manchete, subtítulo e abertura do áudio.
5. **Roteiro e HTML** (Python): o roteiro de voz é montado e validado (700 a 1.100 palavras, sem símbolos proibidos, números convertidos para a forma falada); o HTML é montado num modelo visual fixo e verificado num navegador headless (Playwright), que ajusta automaticamente o layout caso algum slide fique apertado.
6. **Áudio** (Python, em paralelo com o HTML, sem custo de IA): o roteiro passa por um pipeline de síntese de voz — análise de texto, inteligência de fala (detecção de idioma e escolha da voz), construção da narração e, por fim, síntese neural via Microsoft Edge TTS (voz Francisca, em português).
7. **Saída**: tudo fica junto, na mesma pasta do jornal — `output\Jornais\<Jornal> - DD-MM-AAAA\` — contendo o HTML, o `script.txt`, o MP3, e dois arquivos de auditoria (`editorial.json`, com o conteúdo gerado pela IA, e `relatorio.json`, com tempos, tentativas e validações de cada etapa).
8. **Arquivamento**: PDFs e roteiros processados com sucesso são movidos para pastas `processados\`, organizadas por data; um item com falha simplesmente permanece na entrada para a próxima execução, sem perda de dados.

Para roteiros `.txt`, o caminho é mais direto: não há etapa de IA — o texto já está pronto, e o pipeline de voz o transforma diretamente em MP3, sem custo algum, como sempre foi.

---

## 5. O custo em escala: quanto isso vale na prática

Um jornal por vez parece pouco. Em escala, a diferença fica impossível de ignorar.

Considerando um cenário hipotético de **100 jornais processados por dia, 365 dias por ano** (36.500 jornais/ano):

- **IA paga (Claude, etapa 2)** custaria cerca de **US$ 37.230 por ano** — na cotação de outubro de 2026 (R$ 5,01), isso é **aproximadamente R$ 186.589 por ano**.
- **IA local (Ollama, etapa 3)** custa **R$ 0** de IA; a conta de energia da GPU, nessa mesma escala, fica em torno de **R$ 781 por ano**.

A economia potencial é de **R$ 185.808 por ano — uma redução de 99,6%** no custo de inteligência artificial.

Mas esse número vem com uma ressalva importante, descoberta ao fazer a conta de capacidade: processar 100 jornais por dia, no ritmo de 25 a 43 minutos cada, exigiria até **51,7 horas de GPU — mais do que existem num único dia**. Uma GPU de 6 GB como a usada aqui sustenta, no máximo, cerca de **46 jornais por dia rodando sem parar**. Escalar de verdade para 100/dia exigiria o equivalente a **2 a 3 GPUs** trabalhando em paralelo, ou uma GPU bem mais rápida e com mais memória.

Em outras palavras: a economia financeira é real e enorme, mas ela tem um preço em infraestrutura — não em dinheiro de IA, mas em capacidade de hardware.

---

## 6. Arquitetura do código

- **`main.py`** — ponto de entrada único: parâmetros `--txt`, `--jornais`, `--skill`, `--pdf`, `--list-skills`.
- **`app/`** — `SpeechAIApp` (o pipeline de voz, do roteiro ao MP3) e `ScriptInbox` (processa e arquiva os `.txt`).
- **`skill_bridge/`** — a ponte entre a entrada e o processamento: `NewspaperInbox` (identifica o jornal pelo nome do arquivo ou pela capa do PDF), `SkillCatalog`, `SkillPipeline` (escolhe entre o motor `fast` e o motor `agent`) e `SkillRunner` (executa a skill completa via Claude Code, quando o motor `agent` é usado).
- **`newsroom/`** — o coração do processo rápido: `extractor` (extração do PDF), `profiles` (regras editoriais e palavras-chave de cada jornal e destaque), `editor` (monta os prompts, filtra o texto relevante e chama a IA), `ollama_client` (fala com a API local do Ollama), `renderer` (monta e verifica o HTML) e `script_writer` (monta e valida o roteiro de voz).
- **`pipeline/` e `services/`** — o pipeline de texto-para-fala: análise de texto, inteligência de fala, construção de narração e o motor de síntese (Edge TTS).
- **`web/`** — a interface local: `server.py` (API em FastAPI), `job_runner.py` (executa o `main.py` em segundo plano) e os arquivos estáticos do frontend.
- **`config/settings.json`** — toda a configuração: pastas de entrada e saída, catálogo de jornais, motor ativo (`fast` ou `agent`), modelo do Ollama, tamanho do contexto, número de tentativas e orçamento de palavras do recorte.

Dois motores convivem no mesmo sistema: **`fast`** (padrão, hoje com IA local e custo zero) e **`agent`** (a skill completa original, que ainda depende do Claude Code e ainda é paga — mantido como plano B, caso a qualidade ou a velocidade do motor local não sejam suficientes para um caso específico).

---

## 7. Operação do dia a dia

A forma mais simples de usar o Speech AI é pelo **frontend web local**: um duplo clique em `start.bat` sobe um servidor em `127.0.0.1:8000` e abre o navegador automaticamente. Dali, dá para enviar arquivos `.txt` e PDFs de jornais por arrastar-e-soltar, disparar o processamento com um clique, acompanhar o log em tempo real e, ao final, ouvir o áudio e abrir o resumo HTML diretamente na página — cada resumo de jornal já vem com seu próprio player de áudio, guardado na mesma pasta do HTML.

Para quem prefere linha de comando, `python main.py` processa tudo (roteiros primeiro, depois jornais); `--txt` ou `--jornais` isolam um dos dois fluxos; e `--skill valor --pdf caminho.pdf` processa um jornal específico diretamente.

O sistema é resiliente por desenho: uma falha num item nunca derruba os demais, e um arquivo que falha simplesmente permanece na fila de entrada, pronto para ser reprocessado na próxima execução — nenhum dado é perdido.

---

## 8. O que vem a seguir

Com a migração para IA local funcionando e os bugs de qualidade corrigidos, os próximos passos giram em torno de **escala e maturidade**:

- Dimensionar o investimento em GPU necessário para sustentar o volume real de processamento desejado — seja uma placa mais potente, seja mais de uma GPU em paralelo.
- Revisar manualmente os primeiros áudios e HTMLs gerados pela IA local antes de distribuí-los amplamente, já que a qualidade editorial ainda fica atrás do que o Claude entregava.
- Avaliar um modelo intermediário (como o qwen2.5:7b-instruct) caso o gemma3:4b não seja suficiente no dia a dia, sem abrir mão da velocidade de rodar na GPU.
- Automatizar a execução diária, seja por um script `.bat` em loop com o Agendador de Tarefas do Windows, seja por uma rotina agendada — lembrando que isso resolve a operação (rodar sem supervisão), não a capacidade (quantos jornais cabem num dia).
- Versionar formalmente o código no Git: até o momento, as mudanças desta evolução ainda não foram commitadas.

---

## 9. Em uma frase

O Speech AI começou como uma skill manual de 20 minutos por jornal e chegou a um processo automatizado que roda em menos de meia hora, inteiramente na própria máquina, sem custo de inteligência artificial — pagando esse ganho com tempo e com um investimento futuro em GPU, em vez de pagar, para sempre, por token.
