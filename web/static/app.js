// Speech AI · Central de Processamento
const $ = (s, el = document) => el.querySelector(s);

const state = { job: null, lines: 0, polling: null };

// ---------------------------------------------------------------- utilidades

function esc(text) {
  return String(text ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function size(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
}

function when(iso) {
  const d = new Date(iso);
  return d.toLocaleDateString("pt-BR") + " " + d.toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
}

function clock(seconds) {
  const h = Math.floor(seconds / 3600), m = Math.floor(seconds / 60) % 60, s = seconds % 60;
  return (h ? `${h}:` : "") + `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

function toast(message, kind = "") {
  const el = document.createElement("div");
  el.className = `toast ${kind}`;
  el.textContent = message;
  $("#toasts").append(el);
  setTimeout(() => el.remove(), 5000);
}

async function api(path, options = {}) {
  const res = await fetch(path, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `Erro ${res.status}`);
  return data;
}

function confirmBox(title, text) {
  return new Promise(resolve => {
    $("#modalTitle").textContent = title;
    $("#modalText").textContent = text;
    $("#modal").hidden = false;
    const done = answer => { $("#modal").hidden = true; resolve(answer); };
    $("#modalYes").onclick = () => done(true);
    $("#modalNo").onclick = () => done(false);
  });
}

// ---------------------------------------------------------------- arquivos

async function loadFiles() {
  let data;
  try { data = await api("/api/files"); } catch (e) { return toast(e.message, "err"); }

  document.querySelectorAll("[data-folder]").forEach(el => {
    el.textContent = data.folders[el.dataset.folder] || "";
    el.title = el.textContent;
  });

  const running = state.job?.status === "running";

  $("#list-txt").innerHTML = data.txt.length ? data.txt.map(f => `
    <li><svg class="i"><use href="#i-txt"/></svg>
      <div class="nm"><b title="${esc(f.name)}">${esc(f.name)}</b><small>${f.words} palavras · ${size(f.size)} · ${when(f.modified)}</small></div>
      <button class="btn-del" data-del="txt" data-name="${esc(f.name)}" title="Remover da fila" ${running ? "disabled" : ""}><svg class="i"><use href="#i-trash"/></svg></button>
    </li>`).join("") : `<li class="empty">Nenhum roteiro na fila.</li>`;

  $("#list-jornais").innerHTML = data.jornais.length ? data.jornais.map(f => `
    <li><svg class="i"><use href="#i-news"/></svg>
      <div class="nm"><b title="${esc(f.name)}">${esc(f.name)}</b><small>${size(f.size)} · ${when(f.modified)}</small></div>
      ${f.newspaper ? `<span class="badge b-ok">${esc(f.newspaper)}</span>` : `<span class="badge b-warn" title="Renomeie com Valor ou Estadão no nome">não identificado</span>`}
      <button class="btn-del" data-del="jornais" data-name="${esc(f.name)}" title="Remover da fila" ${running ? "disabled" : ""}><svg class="i"><use href="#i-trash"/></svg></button>
    </li>`).join("") : `<li class="empty">Nenhum jornal na fila.</li>`;

  $("#list-audios").innerHTML = data.audios.length ? data.audios.map(a => {
    const url = `/media/audio/${encodeURIComponent(a.name)}`;
    return `<li><svg class="i"><use href="#i-mp3"/></svg>
      <div class="nm"><b title="${esc(a.name)}">${esc(a.name)}</b><small>${size(a.size)} · ${when(a.modified)}</small></div>
      <audio controls preload="none" src="${url}"></audio>
      <div class="links"><a href="${url}?download=true" title="Baixar">⇩</a></div>
    </li>`;
  }).join("") : `<li class="empty">Nenhum áudio gerado ainda.</li>`;

  $("#list-resumos").innerHTML = data.resumos.length ? data.resumos.map(r => {
    const base = `/media/resumos/${encodeURIComponent(r.folder)}/`;
    const audioUrl = r.audio ? `${base}${encodeURIComponent(r.audio)}` : null;
    return `<li><svg class="i"><use href="#i-html"/></svg>
      <div class="nm"><b title="${esc(r.folder)}">${esc(r.folder)}</b><small>${when(r.modified)}</small></div>
      ${audioUrl ? `<audio controls preload="none" src="${audioUrl}"></audio>` : ""}
      <div class="links">
        ${r.html ? `<a href="${base}${encodeURIComponent(r.html)}" target="_blank" rel="noopener">Abrir resumo</a>` : ""}
        ${r.script ? `<a href="${base}script.txt" target="_blank" rel="noopener">Roteiro</a>` : ""}
        ${audioUrl ? `<a href="${audioUrl}?download=true" title="Baixar áudio">⇩ Áudio</a>` : ""}
      </div>
    </li>`;
  }).join("") : `<li class="empty">Nenhum resumo gerado ainda.</li>`;

  $("#run-txt").dataset.count = data.txt.length;
  $("#run-jornais").dataset.count = data.jornais.length;
  $("#run-jornais").dataset.unknown = data.jornais.filter(j => !j.newspaper).length;
  updateButtons();
}

async function upload(kind, fileList) {
  const files = [...fileList];
  if (!files.length) return;
  const ext = kind === "txt" ? ".txt" : ".pdf";
  const wrong = files.filter(f => !f.name.toLowerCase().endsWith(ext));
  if (wrong.length) return toast(`Envie apenas arquivos ${ext}: ${wrong.map(f => f.name).join(", ")}`, "err");

  const drop = document.querySelector(`.drop[data-kind="${kind}"]`);
  const form = new FormData();
  files.forEach(f => form.append("files", f));
  drop.classList.add("busy");
  try {
    const data = await api(`/api/upload/${kind}`, { method: "POST", body: form });
    if (kind === "jornais") {
      const unknown = data.saved.filter(s => !s.newspaper).map(s => s.name);
      toast(`${data.saved.length} jornal(is) enviado(s) para input\\Jornais.`, "ok");
      if (unknown.length) toast(`Não identificado: ${unknown.join(", ")}. Inclua "Valor" ou "Estadão" no nome.`, "err");
    } else {
      toast(`${data.saved.length} roteiro(s) enviado(s) para input.`, "ok");
    }
  } catch (e) {
    toast(e.message, "err");
  } finally {
    drop.classList.remove("busy");
    loadFiles();
  }
}

async function removeFile(kind, name) {
  try {
    await api(`/api/files/${kind}/${encodeURIComponent(name)}`, { method: "DELETE" });
    toast(`${name} removido da fila.`);
  } catch (e) {
    toast(e.message, "err");
  }
  loadFiles();
}

// ---------------------------------------------------------------- rotinas

function updateButtons() {
  const running = state.job?.status === "running";
  for (const id of ["#run-txt", "#run-jornais"]) {
    const btn = $(id);
    btn.disabled = running || Number(btn.dataset.count || 0) === 0;
  }
  $("#cancelJob").hidden = !running;
  const pill = $("#statusPill");
  pill.className = `status ${running ? "running" : "idle"}`;
  pill.querySelector("span").textContent = running
    ? `Executando: ${state.job.mode === "txt" ? "textos" : "jornais"}`
    : "Pronto para processar";
}

async function runJob(mode) {
  const btn = $(`#run-${mode}`);
  if (mode === "jornais") {
    const count = Number(btn.dataset.count), unknown = Number(btn.dataset.unknown);
    const ok = await confirmBox(
      "Processar jornais com IA local?",
      `${count} PDF(s) na fila. Cada jornal leva cerca de 20 a 40 minutos, sem custo (Ollama, roda na GPU desta máquina).` +
      (unknown ? ` Atenção: ${unknown} arquivo(s) não identificado(s) serão ignorados.` : "")
    );
    if (!ok) return;
  }
  try {
    state.job = await api(`/api/run/${mode}`, { method: "POST" });
    state.lines = 0;
    allLines.length = 0;
    $("#console").innerHTML = "";
    $("#jobSteps").innerHTML = "";
    toast(`Rotina iniciada: ${state.job.command}`);
    renderJob(state.job);
    startPolling();
  } catch (e) {
    toast(e.message, "err");
  }
}

async function cancelJob() {
  const ok = await confirmBox("Cancelar a rotina?", "Os arquivos ainda não processados continuam na fila para a próxima execução.");
  if (!ok) return;
  try { await api("/api/job/cancel", { method: "POST" }); } catch (e) { toast(e.message, "err"); }
}

function lineClass(line) {
  if (/\[ERROR\]|Traceback|Error:|failed|cancelada/i.test(line)) return "err";
  if (/\[aviso\]/.test(line)) return "ai";
  if (/\[OK\]|\[ok\]|Pipeline Finished|Skill finished/.test(line)) return "ok";
  if (/^\s+(>|\[\w+\])/.test(line)) return "ai";
  if (/^=+$|^ [A-Z][\w ]+$|Running skill|Fast newspaper pipeline/.test(line)) return "hd";
  return "";
}

function appendLines(lines) {
  if (!lines.length) return;
  const con = $("#console");
  $(".dim", con)?.remove();
  const atBottom = con.scrollTop + con.clientHeight >= con.scrollHeight - 30;
  con.insertAdjacentHTML("beforeend", lines.map(l => `<span class="${lineClass(l)}">${esc(l)}</span>\n`).join(""));
  if (atBottom) con.scrollTop = con.scrollHeight;
}

function renderSteps(allLines) {
  const steps = [];
  for (const line of allLines) {
    let m;
    if ((m = line.match(/(?:Running skill|Fast newspaper pipeline): (.+)/))) steps.push({ t: `Processando: ${m[1]}`, c: "" });
    else if ((m = line.match(/Skill finished\.+ (.+)/))) steps.push({ t: `Resumo pronto · ${m[1]}`, c: "ok" });
    else if ((m = line.match(/^\[OK\]\s+(.+?):/))) steps.push({ t: `Áudio: ${m[1]}`, c: "ok" });
    else if ((m = line.match(/^\[(ERROR|IGNORED)\]\s+(.+?)(:|$)/))) steps.push({ t: `${m[1] === "IGNORED" ? "Ignorado" : "Erro"}: ${m[2]}`, c: "err" });
  }
  $("#jobSteps").innerHTML = steps.map(s => `<span class="${s.c}">${esc(s.t)}</span>`).join("");
}

const allLines = [];

function renderJob(job) {
  if (!job || job.status === "idle") return;
  const labels = { running: "em execução", success: "concluído", failed: "com falhas", cancelled: "cancelado" };
  const chip = $("#jobChip");
  chip.className = `chip ${job.status}`;
  chip.textContent = labels[job.status] || job.status;
  $("#jobElapsed").textContent = clock(job.elapsed_seconds || 0);
  $("#jobInfo").innerHTML = `<code>${esc(job.command)}</code> · início ${when(job.started)}`;
  updateButtons();
}

async function poll() {
  try {
    const job = await api(`/api/job?since=${state.lines}`);
    if (job.status === "idle") return;
    if (state.job && job.id !== state.job.id) { state.lines = 0; allLines.length = 0; $("#console").innerHTML = ""; }
    appendLines(job.lines);
    allLines.push(...job.lines);
    state.lines = job.total_lines;
    const wasRunning = state.job?.status === "running";
    state.job = job;
    renderJob(job);
    renderSteps(allLines);
    if (wasRunning && job.status !== "running") {
      stopPolling();
      const msg = { success: ["Rotina concluída.", "ok"], failed: ["Rotina terminou com falhas. Veja o log.", "err"], cancelled: ["Rotina cancelada.", "err"] }[job.status];
      if (msg) toast(...msg);
      loadFiles();
    }
    if (job.status === "running" && !state.polling) startPolling();
  } catch (e) {
    console.warn(e);
  }
}

function startPolling() {
  if (!state.polling) state.polling = setInterval(poll, 1500);
}

function stopPolling() {
  clearInterval(state.polling);
  state.polling = null;
}

// ---------------------------------------------------------------- eventos

document.querySelectorAll(".drop").forEach(drop => {
  const input = $("input", drop);
  input.addEventListener("change", () => { upload(drop.dataset.kind, input.files); input.value = ""; });
  drop.addEventListener("dragover", e => { e.preventDefault(); drop.classList.add("over"); });
  drop.addEventListener("dragleave", () => drop.classList.remove("over"));
  drop.addEventListener("drop", e => { e.preventDefault(); drop.classList.remove("over"); upload(drop.dataset.kind, e.dataTransfer.files); });
});

document.addEventListener("click", e => {
  const del = e.target.closest("[data-del]");
  if (del) removeFile(del.dataset.del, del.dataset.name);
});

$("#run-txt").addEventListener("click", () => runJob("txt"));
$("#run-jornais").addEventListener("click", () => runJob("jornais"));
$("#cancelJob").addEventListener("click", cancelJob);
$("#refresh").addEventListener("click", loadFiles);

// Atualiza a lista periodicamente (arquivos colocados direto na pasta também aparecem).
setInterval(() => { if (state.job?.status !== "running") loadFiles(); }, 10000);

loadFiles();
poll();
