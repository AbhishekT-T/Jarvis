// ── State & Global Config ──────────────────────────────────────────
let currentState = "idle"; // "idle" | "listening" | "thinking" | "speaking"
let isProcessing = false;
let currentModel = "qwen2.5:3b";
let availableModels = ["qwen2.5:3b", "qwen3-coder:30b", "gemma4:e4b", "gemma4:26b"];

// ── Model Selection & Switching ────────────────────────────────────
async function fetchAvailableModels() {
  try {
    const res = await fetch("/api/models");
    if (!res.ok) return;
    const data = await res.json();
    if (data.models && data.models.length > 0) {
      availableModels = data.models;
    }
    if (data.active_model) {
      currentModel = data.active_model;
    }

    const sel = document.getElementById("modelSelect");
    if (sel) {
      sel.innerHTML = "";
      availableModels.forEach(m => {
        const opt = document.createElement("option");
        opt.value = m;
        let label = m;
        if (m.includes("3b")) label += " (Flash GPU)";
        else if (m.includes("30b")) label += " (Pro Coder)";
        else if (m.includes("e4b")) label += " (Vision)";
        else if (m.includes("26b")) label += " (Large Vision)";
        opt.innerText = label;
        if (m === currentModel) opt.selected = true;
        sel.appendChild(opt);
      });
    }
    updateModelUI(currentModel);
  } catch (err) {
    console.warn("Could not fetch models:", err);
  }
}

function updateModelUI(modelName) {
  const sel = document.getElementById("modelSelect");
  if (sel && sel.value !== modelName) {
    sel.value = modelName;
  }

  // Update tier cards
  const cards = [
    { id: "card-qwen2-5-3b", chipId: "chip-qwen2-5-3b", model: "qwen2.5:3b", label: "ACTIVE (GPU)" },
    { id: "card-qwen3-coder-30b", chipId: "chip-qwen3-coder-30b", model: "qwen3-coder:30b", label: "ACTIVE (CPU)" },
    { id: "card-gemma4-e4b", chipId: "chip-gemma4-e4b", model: "gemma4:e4b", label: "ACTIVE (VIS)" },
  ];

  cards.forEach(c => {
    const el = document.getElementById(c.id);
    const chip = document.getElementById(c.chipId);
    if (el && chip) {
      if (modelName === c.model) {
        el.classList.add("active");
        chip.classList.add("active-chip");
        chip.innerText = c.label;
      } else {
        el.classList.remove("active");
        chip.classList.remove("active-chip");
        chip.innerText = "SWITCH";
      }
    }
  });
}

async function switchModel(modelName) {
  if (!modelName || isProcessing) return;
  try {
    const res = await fetch("/api/set_model", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ model: modelName })
    });
    if (res.ok) {
      const data = await res.json();
      currentModel = data.active_model;
      updateModelUI(currentModel);
      appendMessage("assistant", `⚡ Model Switch: Active primary AI model manually set to [${currentModel}].`);
    }
  } catch (err) {
    console.error("Failed to switch model:", err);
  }
}

function onModelSelectChange(val) {
  switchModel(val);
}

function cycleNextModel() {
  if (!availableModels || availableModels.length === 0) {
    availableModels = ["qwen2.5:3b", "qwen3-coder:30b", "gemma4:e4b", "gemma4:26b"];
  }
  const idx = availableModels.indexOf(currentModel);
  const nextIdx = (idx + 1) % availableModels.length;
  switchModel(availableModels[nextIdx]);
}

// Initialize models on boot
fetchAvailableModels();

// ── Arc Reactor & Soundwave Canvas Animation ───────────────────────
const canvas = document.getElementById("arcCanvas");
const ctx = canvas.getContext("2d");
let angle1 = 0;
let angle2 = 0;
let pulsePhase = 0;

function drawArcReactor() {
  const width = canvas.width;
  const height = canvas.height;
  const cx = width / 2;
  const cy = height / 2;

  ctx.clearRect(0, 0, width, height);

  // Determine state-based color and rotation speeds
  let primaryColor = "rgba(0, 240, 255, ";
  let speedMultiplier = 1;
  let waveAmp = 5;

  if (currentState === "listening") {
    primaryColor = "rgba(0, 255, 136, ";
    speedMultiplier = 2.5;
    waveAmp = 15;
  } else if (currentState === "thinking") {
    primaryColor = "rgba(121, 40, 202, ";
    speedMultiplier = 4;
    waveAmp = 8;
  } else if (currentState === "speaking") {
    primaryColor = "rgba(255, 170, 0, ";
    speedMultiplier = 2;
    waveAmp = 20;
  }

  pulsePhase += 0.04 * speedMultiplier;
  angle1 += 0.015 * speedMultiplier;
  angle2 -= 0.02 * speedMultiplier;

  const dynamicRadius = 35 + Math.sin(pulsePhase) * waveAmp;

  // 1. Central Pulsing Core
  const coreGrad = ctx.createRadialGradient(cx, cy, 2, cx, cy, dynamicRadius);
  coreGrad.addColorStop(0, primaryColor + "0.9)");
  coreGrad.addColorStop(0.5, primaryColor + "0.35)");
  coreGrad.addColorStop(1, primaryColor + "0.0)");
  ctx.fillStyle = coreGrad;
  ctx.beginPath();
  ctx.arc(cx, cy, dynamicRadius * 1.5, 0, Math.PI * 2);
  ctx.fill();

  // 2. Inner segmented ring
  ctx.strokeStyle = primaryColor + "0.75)";
  ctx.lineWidth = 2.5;
  ctx.beginPath();
  ctx.arc(cx, cy, 55, angle1, angle1 + Math.PI * 1.2);
  ctx.stroke();

  ctx.beginPath();
  ctx.arc(cx, cy, 55, angle1 + Math.PI * 1.4, angle1 + Math.PI * 1.9);
  ctx.stroke();

  // 3. Middle segmented counter-rotating ring
  ctx.strokeStyle = primaryColor + "0.45)";
  ctx.lineWidth = 1.5;
  ctx.beginPath();
  ctx.arc(cx, cy, 75, angle2, angle2 + Math.PI * 0.8);
  ctx.stroke();

  ctx.beginPath();
  ctx.arc(cx, cy, 75, angle2 + Math.PI, angle2 + Math.PI * 1.7);
  ctx.stroke();

  // 4. Outer Soundwave Ray Ring
  const numRays = 32;
  for (let i = 0; i < numRays; i++) {
    const rayAngle = (i / numRays) * Math.PI * 2 + (angle1 * 0.2);
    let rayLength = 10;
    if (currentState === "listening" || currentState === "speaking") {
      rayLength = 8 + Math.abs(Math.sin(pulsePhase * 2 + i)) * 18;
    } else {
      rayLength = 6 + Math.sin(pulsePhase + i * 0.5) * 4;
    }

    const rInner = 88;
    const rOuter = rInner + rayLength;

    const x1 = cx + Math.cos(rayAngle) * rInner;
    const y1 = cy + Math.sin(rayAngle) * rInner;
    const x2 = cx + Math.cos(rayAngle) * rOuter;
    const y2 = cy + Math.sin(rayAngle) * rOuter;

    ctx.strokeStyle = primaryColor + (0.2 + (rayLength / 25) * 0.6) + ")";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.moveTo(x1, y1);
    ctx.lineTo(x2, y2);
    ctx.stroke();
  }

  requestAnimationFrame(drawArcReactor);
}

drawArcReactor();


// ── Telemetry & State Polling ──────────────────────────────────────
async function updateHUDTelemetry() {
  try {
    const res = await fetch("/api/status");
    if (!res.ok) return;
    const data = await res.json();

    // Telemetry updates
    if (data.cpu !== undefined) document.getElementById("cpuVal").innerText = `${data.cpu}%`;
    if (data.ram !== undefined) document.getElementById("ramVal").innerText = `${data.ram}%`;
    if (data.vram !== undefined) document.getElementById("gpuVal").innerText = `${data.vram} GB`;

    if (data.active_window) {
      const app = data.active_window.app_name || "Desktop";
      const cat = data.active_window.category ? ` (${data.active_window.category})` : "";
      document.getElementById("appContextVal").innerText = `${app}${cat}`;
    }

    // State updates
    if (!isProcessing && data.state) {
      setAssistantState(data.state);
    }

    // Active model sync
    if (data.active_model && data.active_model !== currentModel) {
      currentModel = data.active_model;
      updateModelUI(currentModel);
    }
  } catch (err) {
    // Server reconnecting
  }
}

setInterval(updateHUDTelemetry, 900);


// ── State Transitions ──────────────────────────────────────────────
function setAssistantState(state) {
  currentState = state;
  const statusDot = document.getElementById("statusDot");
  const statusText = document.getElementById("statusText");
  const arcLabel = document.getElementById("arcStateLabel");
  const micBtn = document.getElementById("micBtn");

  statusDot.className = `status-dot ${state}`;
  statusText.innerText = state.toUpperCase();
  arcLabel.innerText = state.toUpperCase();

  if (state === "listening") {
    micBtn.classList.add("active");
  } else {
    micBtn.classList.remove("active");
  }
}


// ── Chat & Tool Feed ───────────────────────────────────────────────
function appendMessage(sender, text, isUser = false) {
  const history = document.getElementById("chatHistory");
  const card = document.createElement("div");
  card.className = `message-card ${isUser ? "user" : "assistant"}`;

  const header = document.createElement("div");
  header.className = "msg-header";
  header.innerText = isUser ? "YOU" : "JARVIS // ASSISTANT";

  const bubble = document.createElement("div");
  bubble.className = "msg-bubble";
  bubble.innerText = text;

  card.appendChild(header);
  card.appendChild(bubble);
  history.appendChild(card);
  history.scrollTop = history.scrollHeight;
}

function appendToolExecution(toolName, output) {
  const history = document.getElementById("chatHistory");
  const chip = document.createElement("details");
  chip.className = "tool-chip";

  const summary = document.createElement("summary");
  summary.innerText = `⚙️ Executed Tool: ${toolName}`;

  const pre = document.createElement("pre");
  pre.innerText = output || "[No output]";

  chip.appendChild(summary);
  chip.appendChild(pre);
  history.appendChild(chip);
  history.scrollTop = history.scrollHeight;
}

async function submitChat() {
  const input = document.getElementById("chatInput");
  const text = input.value.trim();
  if (!text || isProcessing) return;

  input.value = "";
  appendMessage("user", text, true);

  isProcessing = true;
  setAssistantState("thinking");

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text })
    });

    if (!res.ok) {
      appendMessage("assistant", "Error: Failed to process query via local server.");
      return;
    }

    const data = await res.json();

    // Render any tools that were run
    if (data.tools && data.tools.length > 0) {
      data.tools.forEach(t => appendToolExecution(t.name, t.output));
    }

    setAssistantState("speaking");
    appendMessage("assistant", data.response || "Task complete.");

    setTimeout(() => {
      setAssistantState("idle");
    }, 2000);

  } catch (err) {
    appendMessage("assistant", `Connection error: ${err.message}`);
    setAssistantState("idle");
  } finally {
    isProcessing = false;
  }
}

// Enter key submit
document.getElementById("chatInput").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    submitChat();
  }
});


// ── Push-to-Talk / Mic Input ───────────────────────────────────────
async function toggleVoiceInput() {
  if (isProcessing) return;

  setAssistantState("listening");
  isProcessing = true;

  try {
    const res = await fetch("/api/trigger_listen", { method: "POST" });
    const data = await res.json();

    if (data.transcription) {
      appendMessage("user", data.transcription, true);
    }

    if (data.response) {
      setAssistantState("speaking");
      if (data.tools && data.tools.length > 0) {
        data.tools.forEach(t => appendToolExecution(t.name, t.output));
      }
      appendMessage("assistant", data.response);
      setTimeout(() => setAssistantState("idle"), 2500);
    } else {
      setAssistantState("idle");
    }
  } catch (err) {
    console.error("Voice trigger error:", err);
    setAssistantState("idle");
  } finally {
    isProcessing = false;
  }
}


// ── Quick Actions ──────────────────────────────────────────────────
function sendQuickAction(actionType) {
  const input = document.getElementById("chatInput");
  if (actionType === "diagnostics") {
    input.value = "What is eating my CPU and RAM? Run system diagnostics.";
    submitChat();
  } else if (actionType === "disk") {
    input.value = "Check my drive space and free storage.";
    submitChat();
  } else if (actionType === "reminders") {
    input.value = "What are my upcoming scheduled events and reminders?";
    submitChat();
  } else if (actionType === "window") {
    input.value = "What application and window do I currently have focused?";
    submitChat();
  }
}

function clearChat() {
  const history = document.getElementById("chatHistory");
  history.innerHTML = `
    <div class="message-card assistant">
      <div class="msg-header">JARVIS // SYSTEM CORE</div>
      <div class="msg-bubble">Conversation feed cleared. Standing by.</div>
    </div>
  `;
}
