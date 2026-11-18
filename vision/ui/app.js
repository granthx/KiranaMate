/**
 * KiranaVision — CNN & OpenCV Countertop Weighing Machine Client Application
 */

const state = {
    catalog: [],
    catalogBySku: {},
    thumbnailImages: {},
    sourceMode: "simulator",   // "simulator" | "webcam" | "upload"
    flowMode: "checkout",      // "checkout" (STOCK OUT) | "restock" (STOCK IN)
    packetsOnScale: [],        // Array of SKU IDs currently placed on the virtual weighing pan
    scaleWeightG: 0,
    detectedBasket: [],
    webcamStream: null,
    webcamAutoTimer: null,
};

// ── Initialization ──────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", async () => {
    bindUIEvents();
    await loadCatalogAndInventory();
    // Place Amul Toned Milk 500ml on the weighing scale by default for an immediate visual demo
    placePacketOnScale("SKU-D001");
});

function bindUIEvents() {
    // Source Tabs (Simulator / Webcam / Upload)
    document.querySelectorAll(".source-tab").forEach((btn) => {
        btn.addEventListener("click", () => switchInputSource(btn.dataset.source));
    });

    // Flow Mode Toggle (Checkout STOCK OUT vs Restock STOCK IN)
    document.querySelectorAll(".flow-btn").forEach((btn) => {
        btn.addEventListener("click", () => switchFlowMode(btn.dataset.mode));
    });

    // Clear Scale button
    document.getElementById("btn-clear-scale").addEventListener("click", () => {
        state.packetsOnScale = [];
        updateScaleLoadFromPackets(0);
        renderVirtualScaleAndDetect();
    });

    // Tare Scale button
    document.getElementById("btn-tare-scale").addEventListener("click", () => {
        state.packetsOnScale = [];
        updateScaleLoadFromPackets(0);
        renderVirtualScaleAndDetect();
    });

    // Manual Load-Cell Weight Slider Override
    const slider = document.getElementById("weight-slider");
    slider.addEventListener("input", (e) => {
        state.scaleWeightG = parseInt(e.target.value, 10) || 0;
        updateScaleLcdDisplay(state.scaleWeightG);
    });
    slider.addEventListener("change", () => {
        if (state.sourceMode === "simulator") {
            renderVirtualScaleAndDetect(false);
        } else if (state.sourceMode === "webcam") {
            captureAndDetectWebcamFrame();
        }
    });

    // Quick Test Presets
    document.querySelectorAll(".preset-chip").forEach((chip) => {
        chip.addEventListener("click", () => applyQuickPreset(chip.dataset.preset));
    });

    // Train CNN button
    document.getElementById("btn-retrain-cnn").addEventListener("click", triggerCNNTraining);

    // Commit Basket button
    document.getElementById("btn-commit-basket").addEventListener("click", commitCurrentBasket);

    // Webcam Controls
    document.getElementById("btn-webcam-scan").addEventListener("click", captureAndDetectWebcamFrame);
    document.getElementById("btn-webcam-auto").addEventListener("click", toggleWebcamAutoScan);
    document.getElementById("btn-enroll-frame").addEventListener("click", enrollCurrentWebcamPacket);

    // Photo Upload Control
    document.getElementById("file-upload-input").addEventListener("change", handlePhotoUpload);
}

// ── Load Product Catalog & Live Database Stock ──────────────────────────────
async function loadCatalogAndInventory() {
    try {
        const res = await fetch("/api/vision/catalog");
        const data = await res.json();
        state.catalog = data.products || [];
        state.catalogBySku = {};

        for (const prod of state.catalog) {
            state.catalogBySku[prod.sku_id] = prod;
            if (prod.thumbnail && !state.thumbnailImages[prod.sku_id]) {
                const img = new Image();
                img.src = prod.thumbnail;
                state.thumbnailImages[prod.sku_id] = img;
            }
        }

        renderProductTrays();
        renderInventoryTable();
        populateEnrollDropdown();
    } catch (err) {
        console.error("Failed to load vision catalog:", err);
    }
}

function renderProductTrays() {
    const heroGrid = document.getElementById("hero-tray-grid");
    const extraGrid = document.getElementById("extra-tray-grid");
    heroGrid.innerHTML = "";
    extraGrid.innerHTML = "";

    for (const prod of state.catalog) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "tray-item-btn";
        btn.innerHTML = `
            <div class="tray-thumb-row">
                <img class="tray-thumb" src="${prod.thumbnail}" alt="${prod.short_name}" />
                <span class="tray-stock-tag">${prod.current_stock} in stock</span>
            </div>
            <div class="tray-item-name">${prod.short_name}</div>
            <div class="tray-item-meta">₹${prod.selling_price} &bull; ~${prod.unit_weight_g}g</div>
        `;
        btn.addEventListener("click", () => {
            if (state.sourceMode !== "simulator") {
                // Also set the enroll select to this SKU if in webcam mode
                const sel = document.getElementById("enroll-sku-select");
                if (sel) sel.value = prod.sku_id;
            }
            placePacketOnScale(prod.sku_id);
        });

        if (prod.is_hero) {
            heroGrid.appendChild(btn);
        } else {
            extraGrid.appendChild(btn);
        }
    }
}

function renderInventoryTable() {
    const tbody = document.getElementById("inventory-tbody");
    tbody.innerHTML = "";

    for (const prod of state.catalog) {
        const isLow = prod.current_stock <= (prod.reorder_point || 10);
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td class="sku-mono">${prod.sku_id}</td>
            <td><strong>${prod.name}</strong></td>
            <td>${prod.category}</td>
            <td class="sku-mono">${prod.unit_weight_g} g</td>
            <td class="sku-mono">₹${prod.selling_price}</td>
            <td class="stock-num">${prod.current_stock}</td>
            <td>
                <span class="status-pill-sm ${isLow ? "low" : "ok"}">
                    ${isLow ? "LOW STOCK" : "IN STOCK"}
                </span>
            </td>
        `;
        tbody.appendChild(tr);
    }
}

function populateEnrollDropdown() {
    const sel = document.getElementById("enroll-sku-select");
    if (!sel || sel.options.length > 0) return;
    for (const prod of state.catalog) {
        const opt = document.createElement("option");
        opt.value = prod.sku_id;
        opt.textContent = `${prod.short_name} (${prod.sku_id})`;
        sel.appendChild(opt);
    }
}

// ── Virtual Weighing Scale & Countertop Scene Renderer ──────────────────────
function placePacketOnScale(skuId) {
    if (state.sourceMode !== "simulator") {
        switchInputSource("simulator");
    }
    if (state.packetsOnScale.length >= 4) {
        state.packetsOnScale.shift();
    }
    state.packetsOnScale.push(skuId);
    recalculateScaleWeightFromPackets();
    renderVirtualScaleAndDetect();
}

function applyQuickPreset(presetKey) {
    if (state.sourceMode !== "simulator") {
        switchInputSource("simulator");
    }
    if (presetKey === "amul_milk_2") {
        // 1 visual stack of Amul Milk with 2x weight (1030g) to demonstrate weight-sensor fusion
        state.packetsOnScale = ["SKU-D001"];
        updateScaleLoadFromPackets(1030);
        renderVirtualScaleAndDetect(false);
    } else if (presetKey === "morning_dairy") {
        state.packetsOnScale = ["SKU-D001", "SKU-D004", "SKU-D002"];
        recalculateScaleWeightFromPackets();
        renderVirtualScaleAndDetect();
    } else if (presetKey === "snack_combo") {
        state.packetsOnScale = ["SKU-SN001", "SKU-SN002", "SKU-B001"];
        recalculateScaleWeightFromPackets();
        renderVirtualScaleAndDetect();
    }
}

function recalculateScaleWeightFromPackets() {
    let totalG = 0;
    for (const sku of state.packetsOnScale) {
        const p = state.catalogBySku[sku];
        if (p) {
            totalG += p.unit_weight_g;
        }
    }
    updateScaleLoadFromPackets(totalG);
}

function updateScaleLoadFromPackets(weightG) {
    state.scaleWeightG = weightG;
    const slider = document.getElementById("weight-slider");
    if (slider) slider.value = Math.min(3000, weightG);
    updateScaleLcdDisplay(weightG);
}

function updateScaleLcdDisplay(weightG) {
    const padded = String(Math.round(weightG)).padStart(4, "0");
    document.getElementById("scale-lcd-digits").innerHTML = `${padded} <span class="unit">g</span>`;
}

async function renderVirtualScaleAndDetect() {
    const canvas = document.getElementById("scene-canvas");
    const ctx = canvas.getContext("2d");
    const W = canvas.width;
    const H = canvas.height;

    // 1. Draw Kirana Countertop surface
    ctx.fillStyle = "#262A30";
    ctx.fillRect(0, 0, W, H);

    // 2. Draw Stainless Steel Weighing Machine Platform inside ROI
    const padX = Math.round(W * 0.08);
    const padY = Math.round(H * 0.08);
    const panW = W - padX * 2;
    const panH = H - padY * 2;

    ctx.fillStyle = "#2B3038";
    ctx.strokeStyle = "#475569";
    ctx.lineWidth = 3;
    ctx.fillRect(padX, padY, panW, panH);
    ctx.strokeRect(padX, padY, panW, panH);

    // Subtle calibration crosshairs on weighing pan
    ctx.strokeStyle = "rgba(148, 163, 184, 0.14)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(W / 2, padY + 12);
    ctx.lineTo(W / 2, padY + panH - 12);
    ctx.moveTo(padX + 12, H / 2);
    ctx.lineTo(padX + panW - 12, H / 2);
    ctx.stroke();

    // 3. Draw each placed packet thumbnail in distinct quadrants/slots so OpenCV segments them cleanly
    const count = state.packetsOnScale.length;
    const slots = getPacketSlots(count, W, H);

    for (let i = 0; i < count; i++) {
        const sku = state.packetsOnScale[i];
        const slot = slots[i];
        let img = state.thumbnailImages[sku];

        if (img && !img.complete) {
            await new Promise((r) => {
                img.onload = r;
                img.onerror = r;
            });
        }
        if (img) {
            ctx.drawImage(img, slot.x, slot.y, slot.w, slot.h);
        }
    }

    const dataUri = canvas.toDataURL("image/jpeg", 0.90);
    await sendFrameForDetection(dataUri, state.scaleWeightG, state.packetsOnScale);
}

function getPacketSlots(count, W, H) {
    if (count <= 1) {
        return [{ x: Math.round(W * 0.31), y: Math.round(H * 0.16), w: 240, h: 280 }];
    }
    if (count === 2) {
        return [
            { x: Math.round(W * 0.13), y: Math.round(H * 0.20), w: 210, h: 250 },
            { x: Math.round(W * 0.54), y: Math.round(H * 0.20), w: 210, h: 250 },
        ];
    }
    if (count === 3) {
        return [
            { x: Math.round(W * 0.10), y: Math.round(H * 0.22), w: 165, h: 210 },
            { x: Math.round(W * 0.37), y: Math.round(H * 0.22), w: 165, h: 210 },
            { x: Math.round(W * 0.64), y: Math.round(H * 0.22), w: 165, h: 210 },
        ];
    }
    return [
        { x: Math.round(W * 0.14), y: Math.round(H * 0.12), w: 165, h: 155 },
        { x: Math.round(W * 0.54), y: Math.round(H * 0.12), w: 165, h: 155 },
        { x: Math.round(W * 0.14), y: Math.round(H * 0.52), w: 165, h: 155 },
        { x: Math.round(W * 0.54), y: Math.round(H * 0.52), w: 165, h: 155 },
    ];
}

// ── Backend OpenCV + PyTorch CNN Detection Call ─────────────────────────────
async function sendFrameForDetection(imageBase64, scaleWeightG, hintSkus = null) {
    if (state.sourceMode === "simulator" && (!state.packetsOnScale || state.packetsOnScale.length === 0)) {
        // Render empty weighing scale HUD
        const canvas = document.getElementById("scene-canvas");
        document.getElementById("annotated-output").src = canvas.toDataURL("image/jpeg", 0.85);
        resetInspectorAndBasket();
        return;
    }

    try {
        const res = await fetch("/api/vision/detect", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                image_base64: imageBase64,
                scale_weight_g: scaleWeightG > 0 ? scaleWeightG : null,
                hint_skus: hintSkus && hintSkus.length > 0 ? hintSkus : null,
            }),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const result = await res.json();
        updateVisionHUDAndTelemetry(result);
    } catch (err) {
        console.error("Vision detection error:", err);
    }
}

function updateVisionHUDAndTelemetry(result) {
    // 1. Update annotated OpenCV output frame
    if (result.annotated_frame) {
        document.getElementById("annotated-output").src = result.annotated_frame;
    }

    // 2. Top telemetry chips
    document.getElementById("chip-latency").textContent = `CNN: ${result.latency_ms} ms`;
    document.getElementById("chip-objects").textContent = `${result.objects_detected} Packet${result.objects_detected === 1 ? "" : "s"}`;

    // 3. Weighing Scale verification status
    document.getElementById("expected-weight-val").textContent = `${result.expected_weight_g || 0} g`;
    const wBadge = document.getElementById("weight-verify-badge");
    wBadge.textContent = result.weight_status || "STANDBY";
    wBadge.className = "weight-verify-badge";
    if (result.weight_status === "VERIFIED") wBadge.classList.add("verified");
    if (result.weight_status === "MISMATCH") wBadge.classList.add("mismatch");

    // 4. Detected Basket List
    state.detectedBasket = result.basket || [];
    renderDetectedBasket(result.basket, result.basket_total_inr);

    // 5. CNN Layer Inspector (Primary detection)
    if (result.primary_crop) {
        document.getElementById("inspector-roi-img").src = result.primary_crop;
    }
    const primaryDet = (result.detections && result.detections[0]) || null;
    if (primaryDet) {
        const confPct = (primaryDet.confidence * 100).toFixed(1);
        document.getElementById("insp-top-name").textContent = primaryDet.name;
        document.getElementById("insp-top-sku").textContent = `${primaryDet.sku_id} • ${primaryDet.category.toUpperCase()} • ₹${primaryDet.selling_price}`;
        document.getElementById("insp-top-conf").textContent = `Confidence: ${confPct}%`;

        // Top-3 Softmax bars
        const barsBox = document.getElementById("prob-bars-container");
        barsBox.innerHTML = "";
        for (const cand of primaryDet.top_3 || []) {
            const pct = Math.round(cand.confidence * 100);
            const row = document.createElement("div");
            row.className = "prob-row";
            row.innerHTML = `
                <div class="prob-row-head">
                    <span>${cand.short_name} (${cand.sku_id})</span>
                    <span>${pct}%</span>
                </div>
                <div class="prob-track">
                    <div class="prob-fill" style="width: ${pct}%; background: ${cand.ui_color || "#2563EB"};"></div>
                </div>
            `;
            barsBox.appendChild(row);
        }

        // Ensemble Feature Breakdown
        const m = primaryDet.metrics || {};
        document.getElementById("feat-cnn").textContent = `${((m.cnn_prob || 0) * 100).toFixed(1)}%`;
        document.getElementById("feat-emb").textContent = (m.embedding_sim || 0).toFixed(3);
        document.getElementById("feat-hsv").textContent = (m.opencv_hsv_score || 0).toFixed(3);
        document.getElementById("feat-weight").textContent = m.weight_verified
            ? `VERIFIED (${m.pack_multiplier || 1}x)`
            : `${((m.scale_weight_score || 0) * 100).toFixed(0)}%`;
    }
}

function renderDetectedBasket(basket, totalInr) {
    const listEl = document.getElementById("basket-items-list");
    const totalEl = document.getElementById("basket-total-inr");
    const commitBtn = document.getElementById("btn-commit-basket");

    totalEl.textContent = `₹${totalInr || 0}`;

    if (!basket || basket.length === 0) {
        listEl.innerHTML = `<div class="empty-basket-msg">No packets currently on the weighing scale.</div>`;
        commitBtn.disabled = true;
        return;
    }

    commitBtn.disabled = false;
    listEl.innerHTML = "";
    const isRestock = state.flowMode === "restock";

    for (const item of basket) {
        const deltaStr = isRestock ? `+${item.quantity} IN` : `-${item.quantity} OUT`;
        const row = document.createElement("div");
        row.className = "basket-row";
        row.style.borderLeftColor = item.ui_color || "#2563EB";
        row.innerHTML = `
            <div class="basket-row-left">
                <span class="basket-item-title">${item.quantity}× ${item.name}</span>
                <span class="basket-item-sub">${item.sku_id} &bull; ${Math.round(item.avg_confidence * 100)}% CNN Conf</span>
            </div>
            <div class="basket-row-right">
                <div class="basket-item-price">₹${item.total_price} (${deltaStr})</div>
                <div class="basket-item-stock">DB Stock: ${item.current_stock ?? "—"}</div>
            </div>
        `;
        listEl.appendChild(row);
    }
}

function resetInspectorAndBasket() {
    state.detectedBasket = [];
    renderDetectedBasket([], 0);
    document.getElementById("chip-objects").textContent = "0 Packets";
    document.getElementById("expected-weight-val").textContent = "0 g";
    document.getElementById("weight-verify-badge").textContent = "STANDBY";
    document.getElementById("insp-top-name").textContent = "Weighing Pan Empty";
    document.getElementById("insp-top-sku").textContent = "Tap any packet on the left tray";
    document.getElementById("insp-top-conf").textContent = "Confidence: —%";
}

// ── Commit Detected Basket to Live Database & Agent Book ────────────────────
async function commitCurrentBasket() {
    if (!state.detectedBasket || state.detectedBasket.length === 0) return;
    const btn = document.getElementById("btn-commit-basket");
    btn.disabled = true;

    try {
        const payload = {
            mode: state.flowMode,
            payment_mode: "upi",
            scale_weight_g: state.scaleWeightG > 0 ? state.scaleWeightG : null,
            items: state.detectedBasket.map((i) => ({
                sku_id: i.sku_id,
                quantity: i.quantity,
            })),
        };
        const res = await fetch("/api/vision/commit-basket", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data = await res.json();

        const toast = document.getElementById("commit-toast");
        const verb = state.flowMode === "restock" ? "Added to" : "Deducted from";
        const summary = data.updated_items
            .map((u) => `${Math.abs(u.quantity_delta)}× ${u.name} (Now: ${u.new_stock})`)
            .join(", ");
        toast.textContent = `✅ ${verb} DB & synced to Agent Book: ${summary}`;
        toast.style.display = "block";
        setTimeout(() => {
            toast.style.display = "none";
        }, 5500);

        await loadCatalogAndInventory();
    } catch (err) {
        console.error("Failed to commit basket:", err);
    } finally {
        btn.disabled = false;
    }
}

// ── Switch Flow Mode (Checkout vs Restock) ──────────────────────────────────
function switchFlowMode(mode) {
    state.flowMode = mode;
    document.querySelectorAll(".flow-btn").forEach((b) => {
        b.classList.toggle("active", b.dataset.mode === mode);
    });

    const kicker = document.getElementById("basket-mode-kicker");
    const btnLabel = document.getElementById("commit-btn-label");
    const commitBtn = document.getElementById("btn-commit-basket");

    if (mode === "restock") {
        kicker.textContent = "SUPPLIER DELIVERY (STOCK IN)";
        btnLabel.textContent = "Add Packets to Store Inventory (+IN)";
        commitBtn.classList.add("restock-mode");
    } else {
        kicker.textContent = "COUNTER CHECKOUT (STOCK OUT)";
        btnLabel.textContent = "Deduct from Inventory & Log Sale (-OUT)";
        commitBtn.classList.remove("restock-mode");
    }
    renderDetectedBasket(
        state.detectedBasket,
        state.detectedBasket.reduce((s, i) => s + i.total_price, 0)
    );
}

// ── Switch Input Source (Simulator / Live Webcam / Photo Upload) ────────────
async function switchInputSource(source) {
    state.sourceMode = source;
    document.querySelectorAll(".source-tab").forEach((t) => {
        t.classList.toggle("active", t.dataset.source === source);
    });

    const webcamToolbar = document.getElementById("webcam-toolbar");
    const uploadToolbar = document.getElementById("upload-toolbar");
    webcamToolbar.style.display = source === "webcam" ? "flex" : "none";
    uploadToolbar.style.display = source === "upload" ? "flex" : "none";

    if (source !== "webcam") {
        stopWebcamStream();
    }

    if (source === "simulator") {
        document.getElementById("cam-heading-text").textContent = "Top-Down Weighing Machine Camera Feed";
        if (state.packetsOnScale.length === 0) {
            state.packetsOnScale = ["SKU-D001"];
            recalculateScaleWeightFromPackets();
        }
        await renderVirtualScaleAndDetect();
    } else if (source === "webcam") {
        document.getElementById("cam-heading-text").textContent = "Live USB / Overhead Webcam Stream";
        await startWebcamStream();
    } else if (source === "upload") {
        document.getElementById("cam-heading-text").textContent = "Uploaded Countertop / Packet Frame";
    }
}

async function startWebcamStream() {
    try {
        const video = document.getElementById("webcam-video");
        const stream = await navigator.mediaDevices.getUserMedia({
            video: { width: { ideal: 640 }, height: { ideal: 480 } },
            audio: false,
        });
        state.webcamStream = stream;
        video.srcObject = stream;
        await video.play();
        setTimeout(captureAndDetectWebcamFrame, 400);
    } catch (err) {
        alert("Could not access webcam. Please check camera permissions or use the Virtual Weighing Scale Bench / Upload Photo mode.");
        switchInputSource("simulator");
    }
}

function stopWebcamStream() {
    if (state.webcamAutoTimer) {
        clearInterval(state.webcamAutoTimer);
        state.webcamAutoTimer = null;
        document.getElementById("btn-webcam-auto").textContent = "Auto-Scan (Every 1.5s): OFF";
    }
    if (state.webcamStream) {
        state.webcamStream.getTracks().forEach((t) => t.stop());
        state.webcamStream = null;
    }
}

async function captureAndDetectWebcamFrame() {
    const video = document.getElementById("webcam-video");
    if (!state.webcamStream || video.readyState < 2) return;

    const canvas = document.getElementById("scene-canvas");
    const ctx = canvas.getContext("2d");
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const dataUri = canvas.toDataURL("image/jpeg", 0.88);
    await sendFrameForDetection(dataUri, state.scaleWeightG, null);
}

function toggleWebcamAutoScan() {
    const btn = document.getElementById("btn-webcam-auto");
    if (state.webcamAutoTimer) {
        clearInterval(state.webcamAutoTimer);
        state.webcamAutoTimer = null;
        btn.textContent = "Auto-Scan (Every 1.5s): OFF";
    } else {
        captureAndDetectWebcamFrame();
        state.webcamAutoTimer = setInterval(captureAndDetectWebcamFrame, 1500);
        btn.textContent = "Auto-Scan (Every 1.5s): ON";
    }
}

async function enrollCurrentWebcamPacket() {
    const video = document.getElementById("webcam-video");
    const canvas = document.getElementById("scene-canvas");
    const ctx = canvas.getContext("2d");

    if (state.sourceMode === "webcam" && state.webcamStream && video.readyState >= 2) {
        ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    }

    const skuId = document.getElementById("enroll-sku-select").value;
    const dataUri = canvas.toDataURL("image/jpeg", 0.90);

    try {
        const res = await fetch("/api/vision/enroll", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ sku_id: skuId, image_base64: dataUri }),
        });
        const data = await res.json();
        const statusText = document.getElementById("cnn-status-text");
        statusText.textContent = `Enrolled ${data.name} (#${data.prototypes_count})`;
        await captureAndDetectWebcamFrame();
    } catch (err) {
        console.error("Enrollment failed:", err);
    }
}

function handlePhotoUpload(e) {
    const file = e.target.files && e.target.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = async (ev) => {
        const img = new Image();
        img.onload = async () => {
            const canvas = document.getElementById("scene-canvas");
            const ctx = canvas.getContext("2d");
            ctx.fillStyle = "#1E293B";
            ctx.fillRect(0, 0, canvas.width, canvas.height);
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
            const dataUri = canvas.toDataURL("image/jpeg", 0.90);
            await sendFrameForDetection(dataUri, state.scaleWeightG, null);
        };
        img.src = ev.target.result;
    };
    reader.readAsDataURL(file);
}

// ── Re-train PyTorch KiranaPacketCNN on Demand ──────────────────────────────
async function triggerCNNTraining() {
    const statusText = document.getElementById("cnn-status-text");
    statusText.textContent = "Training PyTorch CNN...";
    try {
        const res = await fetch("/api/vision/train", { method: "POST" });
        const data = await res.json();
        statusText.textContent = `CNN Trained (${data.train_accuracy_pct}% Acc, ${data.training_time_ms}ms)`;
        if (state.sourceMode === "simulator") {
            await renderVirtualScaleAndDetect();
        }
    } catch (err) {
        statusText.textContent = "PyTorch CNN Ready";
    }
}
