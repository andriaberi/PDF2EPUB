// Rebind's window. Python does the work (window.pywebview.api); this page shows it.

const $ = (id) => document.getElementById(id);

const state = { book: null, cover: "", output: "", result: null };

function api() {
  return window.pywebview.api;
}

function setStatus(text, kind = "") {
  $("status").textContent = text.charAt(0).toUpperCase() + text.slice(1);
  $("status").className = kind;
}

function setWorking(working) {
  document.body.classList.toggle("working", working);
  for (const element of document.querySelectorAll("input, select, button")) {
    element.disabled = working;
  }
  if (!working) setReady(Boolean(state.book));
}

// Converting and choosing where to save need a PDF first.
function setReady(ready) {
  $("convert").disabled = !ready;
  $("save-as").disabled = !ready;
}

async function choosePdf() {
  const book = await api().choose_pdf();
  if (book) showBook(book);
}

// Python calls this when a PDF is dropped onto the window.
function onPicked(book) {
  if (!document.body.classList.contains("working")) showBook(book);
}

function showBook(book) {
  document.body.classList.remove("done");
  if (book.error) {
    setStatus(book.error, "error");
    return;
  }
  state.book = book;
  state.output = book.saveAs;
  document.body.classList.add("has-pdf");
  $("file-name").textContent = book.name;
  $("file-meta").textContent = `${book.pages} ${book.pages === 1 ? "page" : "pages"} · ${book.size}`;
  $("title").value = book.title;
  $("author").value = book.author;
  $("pages").value = "";
  $("save-path").textContent = book.saveAsLabel;
  $("save-path").title = book.saveAs;
  setReady(true);
  setStatus("");
}

async function chooseCover() {
  const cover = await api().choose_cover();
  if (!cover) return;
  state.cover = cover.path;
  $("cover-path").textContent = cover.name;
  $("cover-path").classList.remove("muted");
  $("cover-path").title = cover.path;
}

async function chooseOutput() {
  const chosen = await api().choose_output();
  if (!chosen) return;
  state.output = chosen.path;
  $("save-path").textContent = chosen.label;
  $("save-path").title = chosen.path;
}

async function convert(event) {
  event.preventDefault();
  if (!state.book || document.body.classList.contains("working")) return;
  const error = await api().convert({
    pdf: state.book.path,
    output: state.output,
    title: $("title").value,
    author: $("author").value,
    language: $("language").value,
    pages: $("pages").value,
    cover: state.cover,
  });
  if (error) {
    setStatus(error.error, "error");
    return;
  }
  document.body.classList.remove("done");
  $("progress").value = 0;
  setStatus("Starting…");
  setWorking(true);
}

function onProgress(progress) {
  $("progress").max = progress.count;
  $("progress").value = progress.index + 0.5;
  setStatus(`${progress.step}…`);
}

function onDone(result) {
  state.result = result;
  setWorking(false);
  const found = [`${result.headings} headings`, `${result.paragraphs} paragraphs`];
  if (result.notes) found.push(`${result.notes} notes`);
  found.push(result.cover);
  $("result-text").textContent = `Saved ${result.name} (${result.size}): ${found.join(" · ")}.`;
  document.body.classList.add("done");
  setStatus("Done.", "ok");
}

function onError(error) {
  setWorking(false);
  setStatus(error.message, "error");
}

function startOver() {
  state.book = null;
  state.cover = "";
  state.result = null;
  document.body.classList.remove("has-pdf", "done");
  $("form").reset();
  $("cover-path").textContent = "Only used if the PDF has no cover";
  $("cover-path").classList.add("muted");
  $("save-path").textContent = "";
  setReady(false);
  setStatus("");
}

// Dragging a file over the window: Python receives the drop, the box shows it's welcome.

function initDragging() {
  let depth = 0;
  window.addEventListener("dragenter", (e) => { e.preventDefault(); depth++; document.body.classList.add("dragging"); });
  window.addEventListener("dragleave", () => { if (--depth <= 0) { depth = 0; document.body.classList.remove("dragging"); } });
  window.addEventListener("dragover", (e) => e.preventDefault());
  window.addEventListener("drop", (e) => { e.preventDefault(); depth = 0; document.body.classList.remove("dragging"); });
}

async function init() {
  initDragging();
  $("browse").addEventListener("click", choosePdf);
  $("change-pdf").addEventListener("click", choosePdf);
  $("cover").addEventListener("click", chooseCover);
  $("save-as").addEventListener("click", chooseOutput);
  $("form").addEventListener("submit", convert);
  $("show").addEventListener("click", () => api().show_in_folder(state.result.output));
  $("again").addEventListener("click", startOver);
  setReady(false);
}

window.rebind = { onPicked, onProgress, onDone, onError };

if (window.pywebview && window.pywebview.api) init();
else window.addEventListener("pywebviewready", init);
