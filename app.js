const state = {
  status: null,
  imageFile: null
};

const el = {
  statusDot: document.querySelector("#statusDot"),
  statusText: document.querySelector("#statusText"),
  heroVerdict: document.querySelector("#heroVerdict"),
  heroConfidence: document.querySelector("#heroConfidence"),
  heroDatabase: document.querySelector("#heroDatabase"),
  productModelState: document.querySelector("#productModelState"),
  reviewModelState: document.querySelector("#reviewModelState"),
  productForm: document.querySelector("#productForm"),
  productImage: document.querySelector("#productImage"),
  expectedBrand: document.querySelector("#expectedBrand"),
  dropzone: document.querySelector("#dropzone"),
  imagePreview: document.querySelector("#imagePreview"),
  productResult: document.querySelector("#productResult"),
  reviewForm: document.querySelector("#reviewForm"),
  productName: document.querySelector("#productName"),
  reviewRating: document.querySelector("#reviewRating"),
  reviewText: document.querySelector("#reviewText"),
  reviewResult: document.querySelector("#reviewResult"),
  historyList: document.querySelector("#historyList"),
  refreshHistory: document.querySelector("#refreshHistory")
};

async function request(path, options = {}) {
  const response = await fetch(path, options);
  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.text();
  if (!response.ok) {
    const detail = typeof payload === "object" ? payload.detail || JSON.stringify(payload) : payload;
    throw new Error(detail || `${response.status} ${response.statusText}`);
  }
  return payload;
}

function setStatus(kind, text) {
  el.statusDot.className = `status-dot ${kind}`;
  el.statusText.textContent = text;
}

function setPill(node, ok, readyText, missingText) {
  node.className = `pill ${ok ? "ok" : "warn"}`;
  node.textContent = ok ? readyText : missingText;
}

async function loadStatus() {
  try {
    const status = await request("/api/status");
    state.status = status;
    const productOk = status.models.product.available;
    const reviewOk = status.models.review.available;
    const dbOk = status.database.connected;

    setPill(el.productModelState, productOk, "Product model ready", "Product model missing");
    setPill(el.reviewModelState, reviewOk, "Review model ready", "Review model missing");
    el.heroDatabase.textContent = dbOk ? "Connected" : "Offline";

    if (productOk && reviewOk && dbOk) {
      setStatus("ok", "Ready");
    } else if (productOk || reviewOk) {
      setStatus("warn", "Partial setup");
    } else {
      setStatus("fail", "Models missing");
    }
  } catch (error) {
    setStatus("fail", "API offline");
    el.heroDatabase.textContent = "Offline";
  }
}

function showImage(file) {
  state.imageFile = file;
  const url = URL.createObjectURL(file);
  el.imagePreview.src = url;
  el.imagePreview.hidden = false;
  el.dropzone.classList.add("has-image");
}

function toneForVerdict(verdict) {
  if (verdict === "Original") return "safe";
  if (verdict === "Suspicious") return "warning";
  return "danger";
}

function renderProductResult(data) {
  const tone = toneForVerdict(data.verdict);
  const modeText = data.decision_mode === "expected_brand"
    ? `Brand locked to ${data.expected_brand}; fake vs original is compared within that brand.`
    : "Auto brand mode; the highest class across all supported brands is shown.";
  const predictionTitle = data.decision_mode === "expected_brand"
    ? `${data.expected_brand} authenticity graph`
    : "Top model classes";
  el.productResult.className = `result-card ${tone}`;
  el.productResult.innerHTML = `
    <span class="result-kicker">${data.brand} ${data.authenticity}</span>
    <strong>${data.verdict} product</strong>
    <p>${data.confidence}% confidence. ${modeText}</p>
    ${data.authenticity_scores ? `
      <div class="prediction-list">
        <strong>${predictionTitle}</strong>
        ${Object.entries(data.authenticity_scores)
          .map(
            ([label, score]) => `
              <div class="prediction-row">
                <span>${label}</span>
                <strong>${score}%</strong>
                <div class="bar"><span style="width:${Math.max(score, 4)}%"></span></div>
              </div>
            `
          )
          .join("")}
      </div>
    ` : `
    <div class="prediction-list">
      <strong>${predictionTitle}</strong>
      ${data.top_predictions
        .map(
          (item) => `
            <div class="prediction-row">
              <span>${item.brand} ${item.authenticity}</span>
              <strong>${item.confidence}%</strong>
              <div class="bar"><span style="width:${Math.max(item.confidence, 4)}%"></span></div>
            </div>
          `
        )
        .join("")}
    </div>
    `}
  `;
  el.heroVerdict.textContent = `${data.verdict} product`;
  el.heroConfidence.textContent = `${data.confidence}%`;
}

function renderReviewResult(data) {
  const tone = data.tone || toneForVerdict(data.verdict);
  el.reviewResult.className = `result-card ${tone}`;
  el.reviewResult.innerHTML = `
    <span class="result-kicker">Fake probability ${data.fake_probability}%</span>
    <strong>${data.verdict} review</strong>
    <p>${data.confidence}% confidence from ${data.signals.word_count} words, ${data.signals.exclamation_count} exclamation marks, and ${data.signals.uppercase_words} uppercase words.</p>
  `;
  el.heroVerdict.textContent = `${data.verdict} review`;
  el.heroConfidence.textContent = `${data.confidence}%`;
}

function renderError(node, title, message) {
  node.className = "result-card warning";
  node.innerHTML = `
    <span class="result-kicker">Needs attention</span>
    <strong>${title}</strong>
    <p>${message}</p>
  `;
}

async function scanProduct(event) {
  event.preventDefault();
  const file = state.imageFile || el.productImage.files[0];
  if (!file) {
    renderError(el.productResult, "Choose an image", "Upload a real product photo before scanning.");
    return;
  }
  if (!el.expectedBrand.value) {
    renderError(el.productResult, "Select the brand", "Choose Adidas, Gucci, LV, Nike, or Puma so the model compares fake vs original inside the correct brand.");
    return;
  }

  const form = new FormData();
  form.append("image", file);
  form.append("expected_brand", el.expectedBrand.value);

  el.productResult.className = "result-card";
  el.productResult.innerHTML = `<span class="result-kicker">Scanning</span><strong>Analyzing product image</strong><p>The trained Keras model is checking brand and authenticity signals.</p>`;

  try {
    const data = await request("/api/detect/product", {
  method: "POST",
  body: form
});
    renderProductResult(data);
    await loadHistory();
  } catch (error) {
    renderError(el.productResult, "Product scan unavailable", error.message);
  }
}

async function scanReview(event) {
  event.preventDefault();
  const payload = {
    product_name: el.productName.value.trim(),
    review_text: el.reviewText.value.trim(),
    rating: el.reviewRating.value ? Number(el.reviewRating.value) : null
  };

  el.reviewResult.className = "result-card";
  el.reviewResult.innerHTML = `<span class="result-kicker">Analyzing</span><strong>Checking review authenticity</strong><p>The saved review model and vectorizer are required for this scan.</p>`;

  try {
    const data = await request("/api/detect/review", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    renderReviewResult(data);
    await loadHistory();
  } catch (error) {
    renderError(el.reviewResult, "Review scan unavailable", error.message);
  }
}

function historyRow(item) {
  const tone = toneForVerdict(item.verdict);
  const date = new Date(item.created_at).toLocaleString([], {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit"
  });
  return `
    <article class="history-row">
      <strong>${item.type === "product" ? item.brand || "Product" : "Review"} - ${item.verdict}</strong>
      <span class="badge ${tone}">${item.confidence ? `${item.confidence}%` : item.type}</span>
      <p>${date} - ${item.input_summary || "No summary saved"}</p>
    </article>
  `;
}

async function loadHistory() {
  try {
    const data = await request("/api/history");
    if (!data.database_connected) {
      el.historyList.innerHTML = `
        <article class="history-row">
          <strong>PostgreSQL is not connected</strong>
          <span class="badge warning">Offline</span>
          <p>${data.error || "Set DATABASE_URL to enable saved scan history."}</p>
        </article>
      `;
      return;
    }
    el.historyList.innerHTML = data.items.length
      ? data.items.map(historyRow).join("")
      : `<article class="history-row"><strong>No scans logged yet</strong><span class="badge">Empty</span><p>Run a product or review scan to create the first database record.</p></article>`;
  } catch (error) {
    el.historyList.innerHTML = `<article class="history-row"><strong>History unavailable</strong><span class="badge warning">Error</span><p>${error.message}</p></article>`;
  }
}

function setupUpload() {
  el.productImage.addEventListener("change", () => {
    const file = el.productImage.files[0];
    if (file) showImage(file);
  });

  ["dragenter", "dragover"].forEach((eventName) => {
    el.dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      el.dropzone.classList.add("dragging");
    });
  });

  ["dragleave", "drop"].forEach((eventName) => {
    el.dropzone.addEventListener(eventName, (event) => {
      event.preventDefault();
      el.dropzone.classList.remove("dragging");
    });
  });

  el.dropzone.addEventListener("drop", (event) => {
    const file = event.dataTransfer.files[0];
    if (file && file.type.startsWith("image/")) {
      const transfer = new DataTransfer();
      transfer.items.add(file);
      el.productImage.files = transfer.files;
      showImage(file);
    }
  });
}

el.productForm.addEventListener("submit", scanProduct);
el.reviewForm.addEventListener("submit", scanReview);
el.refreshHistory.addEventListener("click", loadHistory);

setupUpload();
loadStatus();
loadHistory();

/* Mouse Glow */

const glow = document.querySelector(".cursor-glow");

document.addEventListener("mousemove", (e) => {

    glow.style.left = e.clientX + "px";
    glow.style.top = e.clientY + "px";

});
