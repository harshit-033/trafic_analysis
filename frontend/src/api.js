const BACKEND_URL = "http://127.0.0.1:8001";
const WS_URL = "ws://127.0.0.1:8001";
const JUNCTION = "J1";

export { BACKEND_URL, WS_URL, JUNCTION };

// ── Existing endpoints ──────────────────────────────────────────────────────

export async function fetchLatestCounts() {
  const res = await fetch(`${BACKEND_URL}/latest/${JUNCTION}`);
  if (!res.ok) throw new Error("Failed to fetch latest counts");
  return res.json();
}

export async function fetchStatus() {
  const res = await fetch(`${BACKEND_URL}/status/${JUNCTION}`);
  if (!res.ok) throw new Error("Failed to fetch status");
  return res.json();
}

export async function fetchAlerts() {
  const res = await fetch(`${BACKEND_URL}/alerts/${JUNCTION}`);
  if (!res.ok) throw new Error("Failed to fetch alerts");
  return res.json();
}

export async function fetchProcesses() {
  const res = await fetch(`${BACKEND_URL}/process_status/${JUNCTION}`);
  if (!res.ok) throw new Error("Failed to fetch processes");
  return res.json();
}

export async function computeTiming(approaches) {
  const payload = {
    junction_id: JUNCTION,
    approaches,
  };
  const res = await fetch(`${BACKEND_URL}/compute_timing`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to compute timing");
  return res.json();
}

// ── New direction endpoints ─────────────────────────────────────────────────

/** Upload a video file for a direction (N/S/E/W) */
export async function uploadVideo(direction, file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BACKEND_URL}/upload_video/${direction}`, {
    method: "POST",
    body: form,
  });
  if (!res.ok) throw new Error(`Upload failed for ${direction}`);
  return res.json();
}

/** Set a CCTV/RTSP URL for a direction */
export async function setCCTVUrl(direction, url) {
  const res = await fetch(`${BACKEND_URL}/set_cctv/${direction}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });
  if (!res.ok) throw new Error(`CCTV set failed for ${direction}`);
  return res.json();
}

/** Stop streaming for a direction */
export async function stopStream(direction) {
  const res = await fetch(`${BACKEND_URL}/stop_stream/${direction}`, {
    method: "POST",
  });
  if (!res.ok) throw new Error(`Stop failed for ${direction}`);
  return res.json();
}

/** Get latest counts for all 4 directions */
export async function fetchDirectionCounts() {
  const res = await fetch(`${BACKEND_URL}/direction_counts/${JUNCTION}`);
  if (!res.ok) throw new Error("Failed to fetch direction counts");
  return res.json();
}

/** Get historical aggregated traffic data for charts */
export async function fetchHistory(interval = "5s", limit = 20) {
  const res = await fetch(
    `${BACKEND_URL}/history/${JUNCTION}?interval=${interval}&limit=${limit}`
  );
  if (!res.ok) throw new Error("Failed to fetch history");
  return res.json();
}

// ── WebSocket stream helper ─────────────────────────────────────────────────

/**
 * Open a WebSocket to stream video frames + counts for a direction.
 * @param {string} direction - 'N' | 'S' | 'E' | 'W'
 * @param {function} onFrame   - called with base64 JPEG string (or null)
 * @param {function} onCounts  - called with { counts, fps, active }
 * @returns {WebSocket} - call .close() to stop
 */
export function openFrameStream(direction, onFrame, onCounts) {
  const ws = new WebSocket(`${WS_URL}/stream/${direction}`);

  ws.onmessage = (evt) => {
    try {
      const data = JSON.parse(evt.data);
      if (typeof onFrame === "function") onFrame(data.frame ?? null);
      if (typeof onCounts === "function")
        onCounts({ counts: data.counts ?? {}, fps: data.fps ?? 0, active: data.active ?? false });
    } catch (e) {
      console.warn("WS parse error", e);
    }
  };

  ws.onerror = (e) => console.warn(`WS error [${direction}]`, e);

  return ws;
}
