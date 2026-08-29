"use strict";

/* ===== Konstanten (Werte = Enum-Werte des Loomi-Kerns) ===== */

const CATEGORIES = [
  { value: "top", label: "Top" },
  { value: "bottom", label: "Bottom" },
  { value: "outerwear", label: "Jacke / Mantel" },
  { value: "shoes", label: "Schuhe" },
  { value: "accessory", label: "Accessoire" },
];

const COLORS = [
  { value: "neutral", label: "Neutral", hex: "#8a857f" },
  { value: "red", label: "Rot", hex: "#d64545" },
  { value: "orange", label: "Orange", hex: "#e08a3c" },
  { value: "yellow", label: "Gelb", hex: "#d9b64a" },
  { value: "green", label: "Grün", hex: "#5c9d6e" },
  { value: "blue", label: "Blau", hex: "#4a6fa5" },
  { value: "purple", label: "Lila", hex: "#7d5ba6" },
  { value: "pink", label: "Pink", hex: "#d4789b" },
  { value: "brown", label: "Braun", hex: "#8a6b4f" },
];

const STYLES = [
  { value: "casual", label: "Casual" },
  { value: "smart_casual", label: "Smart Casual" },
  { value: "sporty", label: "Sporty" },
  { value: "elegant", label: "Elegant" },
  { value: "streetwear", label: "Streetwear" },
  { value: "business", label: "Business" },
  { value: "boho", label: "Boho" },
];

const CONDITIONS = [
  { value: "sunny", label: "Sonnig" },
  { value: "cloudy", label: "Bewölkt" },
  { value: "rain", label: "Regen" },
  { value: "snow", label: "Schnee" },
  { value: "windy", label: "Windig" },
];

const OCCASIONS = [
  { value: "casual", label: "Casual" },
  { value: "work", label: "Arbeit" },
  { value: "date", label: "Date" },
  { value: "party", label: "Party" },
  { value: "sport", label: "Sport" },
  { value: "formal", label: "Formell" },
  { value: "travel", label: "Reise" },
];

const COMPONENT_LABELS = {
  style: "Stil",
  color: "Farbe",
  occasion: "Anlass",
  weather: "Wetter",
  variety: "Abwechslung",
  preference: "Dein Geschmack",
};

const COLOR_HEX = Object.fromEntries(COLORS.map((c) => [c.value, c.hex]));
const COLOR_LABEL = Object.fromEntries(COLORS.map((c) => [c.value, c.label]));
const CATEGORY_LABEL = Object.fromEntries(CATEGORIES.map((c) => [c.value, c.label]));
const STYLE_LABEL = Object.fromEntries(STYLES.map((c) => [c.value, c.label]));

/* ===== Helfer ===== */

const $ = (sel) => document.querySelector(sel);

function escapeHtml(str) {
  return String(str).replace(/[&<>"']/g, (ch) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  }[ch]));
}

async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  let data = {};
  try { data = await res.json(); } catch (_) { /* kein JSON */ }
  if (!res.ok) throw new Error(data.error || `Fehler ${res.status}`);
  return data;
}

function toast(message, type = "") {
  const node = document.createElement("div");
  node.className = `toast ${type}`;
  node.textContent = message;
  $("#toasts").appendChild(node);
  setTimeout(() => node.remove(), 4000);
}

function dots(value, max = 5) {
  let html = `<span class="dots" title="${value}/5">`;
  for (let i = 1; i <= max; i++) {
    html += `<span class="${i <= value ? "on" : ""}"></span>`;
  }
  return html + "</span>";
}

function setLoading(btn, loading, label) {
  btn.disabled = loading;
  btn.textContent = loading ? "Einen Moment …" : label;
}

/* ===== State ===== */

const state = {
  condition: "sunny",
  lastContext: null,
};

/* ===== Navigation ===== */

function showView(name) {
  document.querySelectorAll(".view").forEach((v) => v.classList.remove("active"));
  document.querySelectorAll(".nav-btn").forEach((b) => b.classList.toggle("active", b.dataset.view === name));
  $(`#view-${name}`).classList.add("active");
  if (name === "wardrobe") loadWardrobe();
  if (name === "profile") loadProfile();
}

/* ===== Empfehlung ===== */

function renderConditionChips() {
  const wrap = $("#condition-chips");
  wrap.innerHTML = "";
  for (const c of CONDITIONS) {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = `chip ${c.value === state.condition ? "active" : ""}`;
    chip.textContent = c.label;
    chip.dataset.value = c.value;
    chip.addEventListener("click", () => {
      state.condition = c.value;
      wrap.querySelectorAll(".chip").forEach((el) => el.classList.toggle("active", el.dataset.value === c.value));
    });
    wrap.appendChild(chip);
  }
}

function fillSelect(sel, options, placeholder = null) {
  sel.innerHTML = "";
  if (placeholder) {
    const opt = document.createElement("option");
    opt.value = "";
    opt.textContent = placeholder;
    sel.appendChild(opt);
  }
  for (const o of options) {
    const opt = document.createElement("option");
    opt.value = o.value;
    opt.textContent = o.label;
    sel.appendChild(opt);
  }
}

async function runRecommend() {
  const btn = $("#btn-recommend");
  setLoading(btn, true, "Suche …");
  try {
    const payload = {
      temperature: parseFloat($("#temperature").value) || 20,
      condition: state.condition,
      occasion: $("#occasion").value,
      preferred_style: $("#preferred-style").value || null,
      top_k: 3,
    };
    const data = await api("/api/recommend", { method: "POST", body: JSON.stringify(payload) });
    state.lastContext = data.context;
    renderResults(data);
  } catch (err) {
    toast(err.message, "error");
  } finally {
    setLoading(btn, false, "Outfits finden");
  }
}

function componentBarClass(score) {
  if (score >= 0.8) return "good";
  if (score >= 0.6) return "mid";
  return "low";
}

function outfitCardHtml(scored, rank) {
  const items = scored.outfit.items
    .map((it) => `
      <div class="item-row">
        <span class="color-dot" style="background:${COLOR_HEX[it.color] || "#ccc"}" title="${escapeHtml(COLOR_LABEL[it.color] || it.color)}"></span>
        <span class="item-name">${escapeHtml(it.name)}</span>
        <span class="item-meta">
          <span class="chip-tag">${escapeHtml(CATEGORY_LABEL[it.slot] || it.slot)}</span>
          <span class="chip-tag">${escapeHtml(STYLE_LABEL[it.style] || it.style)}</span>
        </span>
      </div>`)
    .join("");

  const components = scored.components
    .map((comp) => {
      const label = COMPONENT_LABELS[comp.component] || comp.component;
      const pct = Math.round(comp.score * 100);
      return `
        <div class="comp-row">
          <span class="comp-label">${label}</span>
          <span class="comp-bar"><span class="${componentBarClass(comp.score)}" style="width:${pct}%"></span></span>
          <span class="comp-value">${comp.score.toFixed(2)} · Gewicht ${comp.weight.toFixed(2)}</span>
          <span class="comp-details">${escapeHtml(comp.details)}</span>
        </div>`;
    })
    .join("");

  return `
    <div class="card outfit-card">
      <div class="outfit-head">
        <span class="rank">#${rank}</span>
        <span class="total">${scored.total.toFixed(3)} <small>Score</small></span>
      </div>
      <div class="item-list">${items}</div>
      <div class="components">${components}</div>
      <div class="rating" data-key="${escapeHtml(JSON.stringify(scored.outfit.items))}">
        <span class="hint">Wie findest du es?</span>
        ${[1, 2, 3, 4, 5].map((n) => `<button type="button" class="star" data-rating="${n}" title="${n} von 5">★</button>`).join("")}
      </div>
    </div>`;
}

function renderResults(data) {
  const results = $("#results");
  if (!data.outfits.length) {
    const hasItems = data.wardrobe_count > 0;
    results.innerHTML = `
      <div class="card placeholder">
        <div>
          <p><strong>Keine Outfits möglich.</strong></p>
          <p>${hasItems
            ? "Im Kleiderschrank fehlen Pflicht-Kategorien (z. B. Top oder Bottom)."
            : "Dein Kleiderschrank ist leer."}</p>
          <div class="actions" style="justify-content:center">
            <button type="button" class="btn secondary" id="btn-empty-sample">Beispieldaten laden &amp; neu suchen</button>
            <button type="button" class="btn ghost" id="btn-empty-wardrobe">Zum Kleiderschrank</button>
          </div>
        </div>
      </div>`;
    $("#btn-empty-sample").addEventListener("click", async () => {
      try {
        const res = await api("/api/wardrobe/sample", { method: "POST" });
        toast(`${res.added} Beispiel-Kleidungsstücke geladen.`);
        runRecommend();
      } catch (err) { toast(err.message, "error"); }
    });
    $("#btn-empty-wardrobe").addEventListener("click", () => showView("wardrobe"));
    return;
  }

  results.innerHTML = data.outfits
    .map((scored, i) => outfitCardHtml(scored, i + 1))
    .join("");

  // Sterne-Bewertung je Karte -> POST /api/feedback
  results.querySelectorAll(".rating").forEach((row) => {
    const key = row.dataset.key;
    row.querySelectorAll(".star").forEach((star) => {
      star.addEventListener("click", async () => {
        const rating = parseInt(star.dataset.rating, 10);
        const items = JSON.parse(key);
        try {
          await api("/api/feedback", {
            method: "POST",
            body: JSON.stringify({ rating, outfit: { items }, context: state.lastContext }),
          });
          row.classList.add("rated");
          row.querySelectorAll(".star").forEach((s) => s.classList.toggle("active", parseInt(s.dataset.rating, 10) <= rating));
          const thanks = document.createElement("span");
          thanks.className = "thanks";
          thanks.textContent = `Danke! (${rating}/5)`;
          row.appendChild(thanks);
          toast(`Feedback (${rating}/5) wurde erfasst.`, "ok");
        } catch (err) {
          toast(err.message, "error");
        }
      });
    });
  });
}

/* ===== Kleiderschrank ===== */

function itemCardHtml(item) {
  return `
    <div class="item-card">
      <div class="item-name">${escapeHtml(item.name)}</div>
      <div class="item-tags">
        <span class="chip-tag">${escapeHtml(CATEGORY_LABEL[item.category] || item.category)}</span>
        <span class="chip-tag">${escapeHtml(COLOR_LABEL[item.color] || item.color)}</span>
        <span class="chip-tag">${escapeHtml(STYLE_LABEL[item.style] || item.style)}</span>
      </div>
      <div class="meta-line">
        <span>Wärme ${dots(item.warmth)}</span>
        <span>Formalität ${dots(item.formality)}</span>
      </div>
      <button type="button" class="delete-btn" data-id="${escapeHtml(item.id)}">Entfernen</button>
    </div>`;
}

async function loadWardrobe() {
  try {
    const data = await api("/api/wardrobe");
    $("#wardrobe-count").textContent =
      data.count === 1 ? "1 Kleidungsstück in deinem Schrank." : `${data.count} Kleidungsstücke in deinem Schrank.`;
    const list = $("#wardrobe-list");
    if (!data.items.length) {
      list.innerHTML = `<p class="empty-note">Noch leer – füge oben etwas hinzu oder lade die Beispieldaten.</p>`;
      return;
    }
    list.innerHTML = data.items.map(itemCardHtml).join("");
    list.querySelectorAll(".delete-btn").forEach((btn) => {
      btn.addEventListener("click", () => deleteItem(btn.dataset.id, btn));
    });
  } catch (err) {
    toast(err.message, "error");
  }
}

async function deleteItem(id, btn) {
  const name = btn.closest(".item-card").querySelector(".item-name").textContent;
  if (!confirm(`„${name}" aus dem Kleiderschrank entfernen?`)) return;
  btn.disabled = true;
  try {
    await api(`/api/wardrobe/items/${encodeURIComponent(id)}`, { method: "DELETE" });
    toast(`„${name}" entfernt.`);
    loadWardrobe();
  } catch (err) {
    toast(err.message, "error");
    btn.disabled = false;
  }
}

async function addItem(event) {
  event.preventDefault();
  const payload = {
    name: $("#item-name").value.trim(),
    category: $("#item-category").value,
    color: $("#item-color").value,
    style: $("#item-style").value,
    warmth: parseInt($("#item-warmth").value, 10),
    formality: parseInt($("#item-formality").value, 10),
  };
  try {
    const item = await api("/api/wardrobe/items", { method: "POST", body: JSON.stringify(payload) });
    toast(`„${item.name}" gespeichert.`, "ok");
    event.target.reset();
    $("#item-warmth").value = 3;
    $("#item-formality").value = 2;
    loadWardrobe();
  } catch (err) {
    toast(err.message, "error");
  }
}

async function loadSample() {
  try {
    const res = await api("/api/wardrobe/sample", { method: "POST" });
    toast(res.added === res.total
      ? `${res.total} Beispiel-Kleidungsstücke hinzugefügt.`
      : `${res.added} hinzugefügt (${res.total - res.added} waren bereits vorhanden).`, "ok");
    loadWardrobe();
  } catch (err) {
    toast(err.message, "error");
  }
}

async function removeSample() {
  if (!confirm("Alle 32 Beispiel-Kleidungsstücke entfernen? (Eigene Teile bleiben.)")) return;
  try {
    const res = await api("/api/wardrobe/sample", { method: "DELETE" });
    toast(res.removed ? `${res.removed} Beispiel-Kleidungsstücke entfernt.` : "Keine Beispiel-Teile in der Datenbank.");
    loadWardrobe();
  } catch (err) {
    toast(err.message, "error");
  }
}

/* ===== Profil ===== */

async function loadProfile() {
  const card = $("#profile-card");
  try {
    const data = await api("/api/preferences");
    if (!data.feedback_count) {
      card.innerHTML = `
        <p class="empty-state"><strong>Noch kein Feedback.</strong><br>
        Bewerte nach einer Empfehlung dein Lieblingsoutfit (1–5) – Loomi lernt dann
        daraus, was dir gefällt.</p>`;
      return;
    }

    const rows = data.values.map((v) => `
      <div class="pref-row">
        <span class="pref-label">${escapeHtml(v.label)}</span>
        <span class="comp-bar"><span class="${componentBarClass(v.score)}" style="width:${Math.round(v.score * 100)}%"></span></span>
        <span class="pref-value">${escapeHtml(v.value)} <span class="pref-count">${v.score.toFixed(2)} · ${v.count}×</span></span>
      </div>`).join("");

    const numeric = Object.values(data.numeric)
      .map((n) => `<span><strong>${escapeHtml(n.label)}:</strong> bevorzugt ${n.preferred.toFixed(1)}/5</span>`)
      .join("");

    card.innerHTML = `
      <div class="stat-row">
        <div class="stat"><div class="num">${data.feedback_count}</div><div class="lbl">Bewertungen</div></div>
      </div>
      <div class="numeric-prefs">${numeric}</div>
      <h2>Gelernte Vorlieben</h2>
      <div class="pref-list">${rows}</div>
      <button type="button" class="btn ghost" id="btn-reset-profile">Profil zurücksetzen</button>`;
    $("#btn-reset-profile").addEventListener("click", resetProfile);
  } catch (err) {
    card.innerHTML = `<p class="empty-state">Profil konnte nicht geladen werden.</p>`;
  }
}

async function resetProfile() {
  if (!confirm("Gespeicherte Vorlieben wirklich löschen? Loomi startet dann neutral.")) return;
  try {
    await api("/api/preferences", { method: "DELETE" });
    toast("Präferenzprofil zurückgesetzt.", "ok");
    loadProfile();
  } catch (err) {
    toast(err.message, "error");
  }
}

/* ===== Init ===== */

function init() {
  renderConditionChips();
  fillSelect($("#occasion"), OCCASIONS);
  fillSelect($("#preferred-style"), STYLES, "Egal");
  fillSelect($("#item-category"), CATEGORIES);
  fillSelect($("#item-color"), COLORS);
  fillSelect($("#item-style"), STYLES);

  document.querySelectorAll(".nav-btn").forEach((btn) =>
    btn.addEventListener("click", () => showView(btn.dataset.view))
  );
  $("#btn-recommend").addEventListener("click", runRecommend);
  $("#add-item-form").addEventListener("submit", addItem);
  $("#btn-load-sample").addEventListener("click", loadSample);
  $("#btn-remove-sample").addEventListener("click", removeSample);

  showView("recommend");
}

document.addEventListener("DOMContentLoaded", init);
