const BACKEND_URL = "http://127.0.0.1:8001";
const JUNCTION = "J1";

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

export async function computeTiming(counts) {
  const payload = {
    junction_id: JUNCTION,
    approaches: { N: counts, S: counts, E: counts, W: counts }
  };
  const res = await fetch(`${BACKEND_URL}/compute_timing`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload)
  });
  if (!res.ok) throw new Error("Failed to compute timing");
  return res.json();
}
