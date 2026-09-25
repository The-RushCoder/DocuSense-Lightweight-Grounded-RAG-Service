const API_BASE = `${window.location.protocol}//${window.location.hostname || "127.0.0.1"}:8000`;
const form = document.querySelector("#query-form");
const question = document.querySelector("#question");
const count = document.querySelector("#character-count");
const resultArea = document.querySelector("#result-area");
const answer = document.querySelector("#answer");
const sources = document.querySelector("#sources");
const resultMeta = document.querySelector("#result-meta");
const submitButton = document.querySelector(".submit-button");
const submitLabel = document.querySelector("#submit-label");
const status = document.querySelector("#status");
const statusText = document.querySelector("#status-text");

function updateCount() {
  count.textContent = `${question.value.length} / 2000`;
}

function setStatus(kind, text) {
  status.className = `status ${kind}`;
  statusText.textContent = text;
}

function showSources(items = []) {
  sources.replaceChildren();
  if (!items.length) return;

  const heading = document.createElement("p");
  heading.className = "panel-kicker";
  heading.textContent = "Sources used";
  sources.append(heading);

  items.forEach((item) => {
    const details = document.createElement("details");
    details.className = "source";
    const summary = document.createElement("summary");
    summary.textContent = `${item.chunk_id} · similarity ${(item.similarity_score * 100).toFixed(0)}%`;
    const text = document.createElement("p");
    text.textContent = item.text_snippet;
    details.append(summary, text);
    sources.append(details);
  });
}

async function checkHealth() {
  try {
    const response = await fetch(`${API_BASE}/health`);
    const data = await response.json();
    if (data.vector_store_loaded) setStatus("ready", "Knowledge base ready");
    else setStatus("error", "Index needs attention");
  } catch {
    setStatus("error", "API unavailable");
  }
}

async function askQuestion(event) {
  event.preventDefault();
  const value = question.value.trim();
  if (!value) return;

  submitButton.disabled = true;
  submitLabel.textContent = "Searching...";
  resultArea.hidden = false;
  answer.textContent = "Looking through the policy documentation...";
  sources.replaceChildren();
  resultMeta.textContent = "";

  try {
    const response = await fetch(`${API_BASE}/api/query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question: value }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "The request could not be completed.");

    answer.textContent = data.answer;
    resultMeta.textContent = data.tokens_used ? `${data.tokens_used} tokens used` : "Grounded response";
    showSources(data.sources);
    setStatus("ready", "Knowledge base ready");
  } catch (error) {
    answer.textContent = error.message;
    resultMeta.textContent = "Request failed";
    setStatus("error", "Check API connection");
  } finally {
    submitButton.disabled = false;
    submitLabel.textContent = "Ask DocuSense";
  }
}

question.addEventListener("input", updateCount);
form.addEventListener("submit", askQuestion);
document.querySelectorAll("[data-question]").forEach((button) => {
  button.addEventListener("click", () => {
    question.value = button.dataset.question;
    updateCount();
    question.focus();
  });
});

updateCount();
checkHealth();