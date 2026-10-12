const FIELD_ORDER = [
  "customer_name",
  "contact_email",
  "contact_phone",
  "reference_code",
  "item_type",
  "category",
  "urgency",
  "preferred_contact",
  "description",
];

const COPY = {
  es: {
    name: "Nombre",
    email: "Email",
    phone: "Teléfono",
    reference: "Pedido",
    item: "Pieza",
    category: "Motivo",
    urgency: "Urgencia",
    window: "Aviso",
    description: "Descripción",
    missingName: "nombre",
    missingContact: "contacto",
    missingItem: "pieza",
    missingCategory: "motivo",
    missingDescription: "descripción",
    missingUrgency: "urgencia",
    collecting: "Recogiendo datos",
    review: "Pendiente de confirmar",
    closed: "Consulta cerrada",
    calm: "tranquilo",
    neutral: "neutro",
    frustrated: "frustrado",
    angry: "enfadado",
    confirm: "Confirmo los datos de la ficha.",
    emptySummary: "Todavía no hay datos suficientes.",
    noNotes: "Ninguna nota usada en el último mensaje.",
    you: "Tú",
    mara: "Mara",
  },
  en: {
    name: "Name",
    email: "Email",
    phone: "Phone",
    reference: "Order",
    item: "Piece",
    category: "Reason",
    urgency: "Urgency",
    window: "Call window",
    description: "Description",
    missingName: "name",
    missingContact: "contact",
    missingItem: "piece",
    missingCategory: "reason",
    missingDescription: "description",
    missingUrgency: "urgency",
    collecting: "Collecting",
    review: "Waiting for confirmation",
    closed: "Request filed",
    calm: "calm",
    neutral: "neutral",
    frustrated: "frustrated",
    angry: "angry",
    confirm: "Yes, I confirm the details.",
    emptySummary: "Not enough detail for a summary yet.",
    noNotes: "No workshop note was used on the last turn.",
    you: "You",
    mara: "Mara",
  },
};

const VALUES = {
  lamp: { es: "Lámpara", en: "Lamp" },
  furniture: { es: "Mueble", en: "Furniture" },
  textile: { es: "Tapizado", en: "Upholstery" },
  other: { es: "Otra", en: "Other" },
  damage: { es: "Daño", en: "Damage" },
  finish: { es: "Acabado", en: "Finish" },
  electrical: { es: "Fallo eléctrico", en: "Electrical" },
  parts: { es: "Pieza que falta", en: "Missing part" },
  scheduling: { es: "Cita", en: "Scheduling" },
  billing: { es: "Factura", en: "Billing" },
  low: { es: "Baja", en: "Low" },
  medium: { es: "Media", en: "Medium" },
  high: { es: "Alta", en: "High" },
  critical: { es: "Crítica", en: "Critical" },
  morning: { es: "Mañana", en: "Morning" },
  afternoon: { es: "Tarde", en: "Afternoon" },
  evening: { es: "Noche", en: "Evening" },
  any: { es: "Cualquiera", en: "Any time" },
};

const MISSING_KEY = {
  customer_name: "missingName",
  contact: "missingContact",
  item_type: "missingItem",
  category: "missingCategory",
  description: "missingDescription",
  urgency: "missingUrgency",
};

const state = {
  mode: "loading",
  ollama: false,
  model: "llama3.2",
  conversation: null,
  list: [],
  speaking: false,
  busy: false,
  recognition: null,
  notice: "",
};

const $ = (id) => document.getElementById(id);

function language() {
  return state.conversation?.language === "en" ? "en" : "es";
}

function text(key) {
  return COPY[language()][key];
}

function showValue(key, value) {
  if (!value) return "—";
  const translated = VALUES[value];
  if (translated) return translated[language()];
  return value;
}

async function boot() {
  try {
    const response = await fetch("api/health", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error("static");
    const health = await response.json();
    if (!health.ok) throw new Error("static");
    state.mode = "live";
    state.ollama = Boolean(health.ollama);
    state.model = health.model || "llama3.2";
    await refreshList();
    if (state.list.length) await openConversation(state.list[0].id);
    else await createConversation();
  } catch {
    state.mode = "static";
    state.conversation = await fetch("sample.json").then((response) => response.json());
    state.list = [
      {
        id: state.conversation.id,
        customer_name: state.conversation.intake.customer_name,
        status: state.conversation.status,
        preview: "Ejemplo publicado",
      },
    ];
    render();
  }
}

function render() {
  const live = state.mode === "live";
  const english = language() === "en";
  $("new-chat").textContent = english ? "New request" : "Nueva consulta";
  $("new-chat").disabled = !live || state.busy;
  $("voice").textContent = english ? "Read aloud" : "Leer en voz alta";
  $("mic").textContent = english ? "Speak" : "Hablar";
  $("confirm").textContent = english ? "Confirm ticket" : "Confirmar ficha";
  $("download").textContent = english ? "Download JSON" : "Descargar JSON";
  $("draft").placeholder = english
    ? "Tell Mara what needs restoring"
    : "Cuéntale a Mara qué hay que restaurar";
  $("dossier-kicker").textContent = english ? "Ticket" : "Ficha";
  $("summary-title").textContent = english ? "Summary" : "Resumen";
  $("notes-title").textContent = english ? "Workshop notes" : "Notas del taller";
  if (!state.busy) $("send").textContent = english ? "Send" : "Enviar";
  $("draft").disabled = !live || state.busy;
  $("send").disabled = !live || state.busy;
  $("mic").disabled = !live || state.busy;
  $("confirm").hidden = !live || state.conversation?.status !== "review";
  $("download").hidden = state.conversation?.status !== "closed";
  renderBanner();
  renderStatus();
  renderHistory();
  renderMessages();
  renderDossier();
}

function renderBanner() {
  const banner = $("banner");
  if (state.notice) {
    banner.hidden = false;
    banner.textContent = state.notice;
    return;
  }
  if (state.mode === "static") {
    banner.hidden = false;
    banner.textContent =
      "Estás viendo la página pública. Esta consulta es un ejemplo guardado. Para hablar con Mara hace falta el servidor local y Ollama: python serve.py";
    return;
  }
  if (!state.ollama) {
    banner.hidden = false;
    banner.textContent =
      "No encuentro Ollama en 127.0.0.1:11434. Puedes seguir la ficha: Mara preguntará los datos que faltan, sin redactar con el modelo.";
    return;
  }
  banner.hidden = true;
}

function renderStatus() {
  const pill = $("link-status");
  if (state.mode === "static") {
    pill.textContent = "Página estática";
    pill.className = "pill";
    return;
  }
  pill.textContent = state.ollama ? `Ollama · ${state.model}` : "Ollama sin conexión";
  pill.className = state.ollama ? "pill ok" : "pill warn";
}

function renderHistory() {
  const list = $("history");
  list.replaceChildren();
  for (const item of state.list) {
    const entry = document.createElement("li");
    const button = document.createElement("button");
    button.type = "button";
    if (item.id === state.conversation?.id) button.className = "active";
    const title = document.createElement("strong");
    title.textContent = item.customer_name || item.ticket_id || "Consulta nueva";
    const preview = document.createElement("span");
    preview.textContent = item.preview || item.status || "";
    button.append(title, preview);
    button.addEventListener("click", () => {
      if (state.mode === "live") openConversation(item.id);
    });
    entry.append(button);
    list.append(entry);
  }
}

function renderMessages() {
  const list = $("messages");
  list.replaceChildren();
  const messages = state.conversation?.messages || [];
  for (const message of messages) {
    const item = document.createElement("li");
    item.className = `message ${message.role === "user" ? "user" : "assistant"}`;
    const who = document.createElement("span");
    who.className = "who";
    who.textContent = message.role === "user" ? text("you") : text("mara");
    const body = document.createElement("p");
    body.textContent = message.content;
    item.append(who, body);
    list.append(item);
  }
  list.scrollTop = list.scrollHeight;
}

function renderDossier() {
  const conversation = state.conversation;
  const intake = conversation?.intake || {};
  $("ticket").textContent = conversation?.ticket_id || "Sin abrir";
  $("status").textContent = conversation ? text(conversation.status) : "—";
  $("sentiment").textContent = conversation ? text(conversation.sentiment) : "—";
  $("language").textContent = conversation?.language === "en" ? "English" : conversation ? "Español" : "—";
  $("summary").textContent = conversation?.summary || text("emptySummary");

  const missing = $("missing");
  missing.replaceChildren();
  for (const key of conversation?.missing || []) {
    const item = document.createElement("li");
    item.textContent = text(MISSING_KEY[key] || "missingDescription");
    missing.append(item);
  }

  const fields = $("fields");
  fields.replaceChildren();
  const labels = {
    customer_name: text("name"),
    contact_email: text("email"),
    contact_phone: text("phone"),
    reference_code: text("reference"),
    item_type: text("item"),
    category: text("category"),
    urgency: text("urgency"),
    preferred_contact: text("window"),
    description: text("description"),
  };
  for (const key of FIELD_ORDER) {
    const row = document.createElement("div");
    const term = document.createElement("dt");
    term.textContent = labels[key];
    const value = document.createElement("dd");
    value.textContent = showValue(key, intake[key]);
    if (intake[key]) value.className = "filled";
    row.append(term, value);
    fields.append(row);
  }

  const citations = $("citations");
  citations.replaceChildren();
  const notes = conversation?.citations || [];
  if (!notes.length) {
    const item = document.createElement("li");
    item.textContent = text("noNotes");
    citations.append(item);
    return;
  }
  for (const note of notes) {
    const item = document.createElement("li");
    item.textContent = `${note.title}. ${note.snippet}`;
    citations.append(item);
  }
}

async function refreshList() {
  const response = await fetch("api/conversations");
  const payload = await response.json();
  state.list = payload.conversations || [];
}

async function openConversation(id) {
  const response = await fetch(`api/conversations/${id}`);
  if (!response.ok) return;
  state.conversation = await response.json();
  render();
}

async function createConversation() {
  const response = await fetch("api/conversations", { method: "POST" });
  state.conversation = await response.json();
  await refreshList();
  render();
}

async function sendText(textValue) {
  const content = textValue.trim();
  if (!content || state.mode !== "live" || state.busy || !state.conversation) return;
  state.busy = true;
  state.conversation.messages = [
    ...state.conversation.messages,
    { role: "user", content, at: new Date().toISOString() },
  ];
  $("draft").value = "";
  render();
  const started = Date.now();
  $("send").textContent = "Mara escribe…";
  const ticker = setInterval(() => {
    const seconds = Math.round((Date.now() - started) / 1000);
    $("send").textContent = `Mara escribe… ${seconds}s`;
  }, 1000);
  try {
    const response = await fetch(`api/conversations/${state.conversation.id}/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: content }),
    });
    const payload = await response.json();
    if (!response.ok) throw new Error(payload.error || "No se pudo enviar");
    state.conversation = payload;
    $("draft").value = "";
    state.notice = "";
    await refreshList();
    if (state.speaking) speak(payload.messages.at(-1).content);
  } catch (error) {
    state.notice = error.message;
  } finally {
    clearInterval(ticker);
    $("send").textContent = "Enviar";
    state.busy = false;
    render();
  }
}

function speak(content) {
  if (!window.speechSynthesis) return;
  const utterance = new SpeechSynthesisUtterance(content);
  utterance.lang = language() === "en" ? "en-US" : "es-ES";
  window.speechSynthesis.cancel();
  window.speechSynthesis.speak(utterance);
}

function toggleVoice() {
  state.speaking = !state.speaking;
  $("voice").setAttribute("aria-pressed", String(state.speaking));
  if (!state.speaking && window.speechSynthesis) {
    window.speechSynthesis.cancel();
    return;
  }
  const last = [...(state.conversation?.messages || [])].reverse().find((item) => item.role === "assistant");
  if (last) speak(last.content);
}

function toggleMic() {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!Recognition) {
    state.notice = "Este navegador no transcribe voz. Chrome sí puede hacerlo.";
    render();
    return;
  }
  if (state.recognition) {
    state.recognition.stop();
    return;
  }
  const recognition = new Recognition();
  recognition.lang = language() === "en" ? "en-US" : "es-ES";
  recognition.interimResults = false;
  recognition.onresult = (event) => {
    const said = event.results[0][0].transcript;
    $("draft").value = `${$("draft").value} ${said}`.trim();
  };
  recognition.onend = () => {
    state.recognition = null;
    $("mic").setAttribute("aria-pressed", "false");
  };
  recognition.onerror = () => {
    state.recognition = null;
    $("mic").setAttribute("aria-pressed", "false");
  };
  state.recognition = recognition;
  $("mic").setAttribute("aria-pressed", "true");
  recognition.start();
}

function downloadTicket() {
  if (!state.conversation) return;
  const blob = new Blob([JSON.stringify(state.conversation, null, 2)], { type: "application/json" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `${state.conversation.ticket_id}.json`;
  link.click();
  URL.revokeObjectURL(link.href);
}

$("composer").addEventListener("submit", (event) => {
  event.preventDefault();
  sendText($("draft").value);
});

$("draft").addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendText($("draft").value);
  }
});

$("new-chat").addEventListener("click", createConversation);
$("confirm").addEventListener("click", () => sendText(text("confirm")));
$("download").addEventListener("click", downloadTicket);
$("voice").addEventListener("click", toggleVoice);
$("mic").addEventListener("click", toggleMic);

boot();
