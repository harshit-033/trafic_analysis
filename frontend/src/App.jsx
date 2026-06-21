import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  fetchLatestCounts, fetchStatus, fetchAlerts, computeTiming,
  uploadVideo, setCCTVUrl, stopStream, fetchDirectionCounts,
  fetchHistory, openFrameStream
} from './api';
import {
  PieChart, Pie, Cell, ResponsiveContainer, AreaChart, Area,
  XAxis, YAxis, CartesianGrid, Tooltip, BarChart, Bar,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, Legend
} from 'recharts';
import {
  Activity, AlertCircle, Map as MapIcon, BarChart3,
  LayoutDashboard, FileText, Settings, Video, Wifi,
  Camera, Upload, Square, RefreshCw, Zap, Clock,
  TrendingUp, Truck, Car
} from 'lucide-react';
import './index.css';

/* ── Constants ────────────────────────────────────────────────────────────── */
const ACCENT_GREEN = '#62ee86';
const ACCENT_LIME  = '#dfff45';
const ACCENT_BLUE  = '#4fb3ff';
const ACCENT_AMB   = '#ffb94a';
const COLORS = [ACCENT_GREEN, '#8ff266', ACCENT_LIME, '#f2ff7a', '#4ccf7b', ACCENT_BLUE, ACCENT_AMB];

const DIR_NAMES = { N: 'North', S: 'South', E: 'East', W: 'West' };
const DIR_COLORS = { N: ACCENT_GREEN, S: ACCENT_LIME, E: ACCENT_BLUE, W: ACCENT_AMB };

const INTERVALS = [
  { label: '5s', value: '5s' },
  { label: '1m', value: '1m' },
  { label: '1h', value: '1h' },
  { label: '1d', value: '1d' },
];

/* ═══════════════════════════════════════════════════════════════════════════
   CAMERA FEED CARD
══════════════════════════════════════════════════════════════════════════════ */
function CameraFeedCard({ direction, onCountsChange }) {
  const canvasRef    = useRef(null);
  const wsRef        = useRef(null);
  const fileInputRef = useRef(null);
  const imgRef       = useRef(new Image());

  const [counts,      setCounts]      = useState({});
  const [fps,         setFps]         = useState(0);
  const [active,      setActive]      = useState(false);
  const [sourceType,  setSourceType]  = useState(null); // 'video' | 'cctv' | null
  const [cctvUrl,     setCctvUrl]     = useState('');
  const [showCctv,    setShowCctv]    = useState(false);
  const [uploading,   setUploading]   = useState(false);
  const [error,       setError]       = useState(null);

  /* Connect / disconnect WebSocket whenever sourceType changes */
  useEffect(() => {
    if (!sourceType) {
      wsRef.current?.close();
      wsRef.current = null;
      return;
    }

    const connect = () => {
      const ws = openFrameStream(
        direction,
        (b64) => {
          if (!b64) return;
          const canvas = canvasRef.current;
          if (!canvas) return;
          const ctx = canvas.getContext('2d');
          const img = imgRef.current;
          img.onload = () => {
            ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
          };
          img.src = `data:image/jpeg;base64,${b64}`;
        },
        ({ counts: c, fps: f, active: a }) => {
          setCounts(c);
          setFps(f);
          setActive(a);
          if (onCountsChange) onCountsChange(direction, c);
        }
      );
      wsRef.current = ws;
    };

    connect();

    return () => {
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [sourceType, direction]);

  /* Upload handler */
  const handleUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setError(null);
    try {
      await uploadVideo(direction, file);
      setSourceType('video');
    } catch (err) {
      setError('Upload failed');
    } finally {
      setUploading(false);
    }
  };

  /* CCTV handler */
  const handleCctv = async () => {
    if (!cctvUrl.trim()) return;
    setError(null);
    try {
      await setCCTVUrl(direction, cctvUrl.trim());
      setSourceType('cctv');
      setShowCctv(false);
    } catch (err) {
      setError('CCTV connection failed');
    }
  };

  /* Stop handler */
  const handleStop = async () => {
    try {
      await stopStream(direction);
    } catch (_) {}
    setSourceType(null);
    setActive(false);
    setCounts({});
    setFps(0);
    /* Clear canvas */
    const canvas = canvasRef.current;
    if (canvas) canvas.getContext('2d').clearRect(0, 0, canvas.width, canvas.height);
  };

  const totalVehicles = Object.values(counts).reduce((a, b) => a + Number(b), 0);
  const statusClass = sourceType === 'cctv' ? 'cctv' : (active ? 'live' : '');
  const cardClass = `feed-card ${sourceType === 'video' && active ? 'active' : ''} ${sourceType === 'cctv' && active ? 'active-cctv' : ''}`;

  return (
    <div className={cardClass}>
      {/* Header */}
      <div className="feed-header">
        <div className="feed-dir-badge">
          <span className="dir-label">{direction}</span>
          <span className="dir-name">{DIR_NAMES[direction]}</span>
        </div>
        <div className="feed-status">
          {totalVehicles > 0 && (
            <span style={{ color: DIR_COLORS[direction], fontWeight: 700, fontSize: '0.78rem' }}>
              {totalVehicles} vehicles
            </span>
          )}
          <div className={`status-dot ${statusClass}`} />
          <span style={{ fontSize: '0.72rem', color: 'var(--muted)' }}>
            {active ? (sourceType === 'cctv' ? 'CCTV' : 'VIDEO') : 'IDLE'}
          </span>
        </div>
      </div>

      {/* Video area */}
      <div className="feed-canvas-wrap">
        {sourceType ? (
          <>
            <canvas
              ref={canvasRef}
              className="feed-canvas"
              width={640}
              height={360}
              style={{ display: 'block', width: '100%', height: '100%', objectFit: 'cover' }}
            />
            {fps > 0 && <div className="fps-badge">{fps} FPS</div>}
            {Object.keys(counts).length > 0 && (
              <div className="count-overlay">
                {Object.entries(counts).map(([cls, cnt]) => (
                  <div key={cls} className="count-chip">
                    <span>{cls === 'car' ? '🚗' : cls === 'bus' ? '🚌' : cls === 'truck' ? '🚛' : '🏍'}</span>
                    {cls}: <strong>{cnt}</strong>
                  </div>
                ))}
              </div>
            )}
            {!active && sourceType && (
              <div style={{ position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.6)' }}>
                <div className="feed-placeholder">
                  <span className="placeholder-icon shimmer">⏳</span>
                  <span>Connecting to inference...</span>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="feed-placeholder">
            <span className="placeholder-icon">📷</span>
            <span>No feed active</span>
            <span style={{ fontSize: '0.72rem' }}>Upload a video or add a CCTV URL below</span>
          </div>
        )}
      </div>

      {/* Controls */}
      <div className="feed-controls">
        {!sourceType ? (
          <>
            {/* Upload */}
            <input
              type="file"
              ref={fileInputRef}
              accept="video/*"
              style={{ display: 'none' }}
              onChange={handleUpload}
            />
            <button
              className="feed-btn primary"
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
            >
              <Upload size={13} />
              {uploading ? 'Uploading…' : 'Upload Video'}
            </button>

            {/* CCTV toggle */}
            <button className="feed-btn blue" onClick={() => setShowCctv(!showCctv)}>
              <Wifi size={13} />
              CCTV URL
            </button>

            {showCctv && (
              <div className="cctv-input-wrap">
                <input
                  type="text"
                  className="cctv-input"
                  placeholder="rtsp://... or http://..."
                  value={cctvUrl}
                  onChange={e => setCctvUrl(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && handleCctv()}
                />
                <button className="feed-btn blue" onClick={handleCctv}>
                  Connect
                </button>
              </div>
            )}
          </>
        ) : (
          <>
            <span style={{ fontSize: '0.75rem', color: 'var(--muted)', flex: 1 }}>
              {sourceType === 'video' ? '📹 Video file' : '📡 CCTV stream'} · AI inference active
            </span>
            <button className="feed-btn danger" onClick={handleStop}>
              <Square size={12} /> Stop
            </button>
          </>
        )}
        {error && <span style={{ color: 'var(--red)', fontSize: '0.72rem' }}>{error}</span>}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   TRAFFIC LIGHT (single unit)
══════════════════════════════════════════════════════════════════════════════ */
function TrafficLight({ direction, phase, countdown, greenTime }) {
  const isGreen  = phase === 'green';
  const isYellow = phase === 'yellow';
  const isRed    = phase === 'red';

  return (
    <div className="traffic-light">
      <div className="tl-dir">{direction}</div>
      <div className={`tl-dot ${isRed ? 'red-on' : 'red-off'}`} />
      <div className={`tl-dot ${isYellow ? 'yellow-on' : 'yellow-off'}`} />
      <div className={`tl-dot ${isGreen ? 'green-on' : 'green-off'}`} />
      <div className={`tl-countdown ${isRed ? '' : isYellow ? '' : ''}`} style={{
        color: isGreen ? ACCENT_GREEN : isYellow ? ACCENT_AMB : '#ff5c5c'
      }}>
        {countdown}s
      </div>
      <div className="tl-label">{greenTime}s</div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   SIGNAL SIMULATOR TAB
══════════════════════════════════════════════════════════════════════════════ */
function SignalSimulatorTab({ directionCounts, timing }) {
  const DIRECTIONS = ['N', 'S', 'E', 'W'];
  const YELLOW_DUR = 3;
  const ALL_RED_DUR = 1;

  /* Build phase sequence from timing */
  const buildSequence = useCallback((tim) => {
    const seq = [];
    const phases = tim?.phases || {};
    const dirs = DIRECTIONS.filter(d => phases[d]);
    dirs.forEach(dir => {
      const g = Math.round(phases[dir]?.green || 15);
      seq.push({ dir, phase: 'green', duration: g });
      seq.push({ dir, phase: 'yellow', duration: YELLOW_DUR });
      seq.push({ dir, phase: 'all_red', duration: ALL_RED_DUR });
    });
    if (seq.length === 0) {
      DIRECTIONS.forEach(dir => {
        seq.push({ dir, phase: 'green', duration: 15 });
        seq.push({ dir, phase: 'yellow', duration: YELLOW_DUR });
        seq.push({ dir, phase: 'all_red', duration: ALL_RED_DUR });
      });
    }
    return seq;
  }, []);

  const [sequence, setSequence]       = useState(() => buildSequence(timing));
  const [seqIdx,   setSeqIdx]         = useState(0);
  const [countdown, setCountdown]     = useState(sequence[0]?.duration || 15);

  /* Update sequence when timing changes */
  useEffect(() => {
    const seq = buildSequence(timing);
    setSequence(seq);
    setSeqIdx(0);
    setCountdown(seq[0]?.duration || 15);
  }, [timing, buildSequence]);

  /* Countdown tick */
  useEffect(() => {
    if (sequence.length === 0) return;
    const tick = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) {
          setSeqIdx(si => {
            const next = (si + 1) % sequence.length;
            setCountdown(sequence[next]?.duration || 15);
            return next;
          });
          return sequence[(seqIdx + 1) % sequence.length]?.duration || 15;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(tick);
  }, [sequence, seqIdx]);

  const currentStep = sequence[seqIdx] || { dir: 'N', phase: 'green' };

  /* Determine phase for each direction */
  const getDirPhase = (dir) => {
    if (currentStep.phase === 'all_red') return 'red';
    if (currentStep.dir === dir) return currentStep.phase;
    return 'red';
  };

  const phases = timing?.phases || {};
  const totalVehicles = DIRECTIONS.reduce((sum, d) => {
    return sum + Object.values(directionCounts[d]?.counts || {}).reduce((a, b) => a + Number(b), 0);
  }, 0);

  return (
    <div className="fade-in">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
        <h2 className="page-title" style={{ marginBottom: 0 }}>Signal Control — Junction J1</h2>
        <div className="status-badge ok">
          <span>●</span> Adaptive Mode Active
        </div>
      </div>

      <div className="signal-page">
        {/* Junction diagram */}
        <div className="junction-wrap">
          <div className="junction-diagram">
            {/* Top road block */}
            <div style={{ gridColumn: '1/4', gridRow: 1, display: 'grid', gridTemplateColumns: '120px 1fr 120px', background: 'transparent' }}>
              <div style={{ background: '#0a1018' }} />
              <div style={{ background: '#1a2130', display: 'flex', justifyContent: 'center', alignItems: 'flex-end', paddingBottom: 12 }}>
                {/* Road dashes */}
                {[...Array(4)].map((_, i) => (
                  <div key={i} style={{ width: 4, height: 18, background: 'rgba(255,255,255,0.15)', marginInline: 12, borderRadius: 2 }} />
                ))}
              </div>
              <div style={{ background: '#0a1018' }} />
            </div>

            {/* Middle row */}
            <div style={{ gridColumn: '1/4', gridRow: 2, display: 'grid', gridTemplateColumns: '120px 1fr 120px', background: 'transparent' }}>
              <div style={{ background: '#1a2130', display: 'flex', alignItems: 'center', justifyContent: 'flex-end', paddingRight: 12 }}>
                {[...Array(3)].map((_, i) => (
                  <div key={i} style={{ width: 18, height: 4, background: 'rgba(255,255,255,0.15)', marginBlock: 12, borderRadius: 2 }} />
                ))}
              </div>
              {/* Intersection center */}
              <div style={{ background: '#222d3e', display: 'flex', alignItems: 'center', justifyContent: 'center', position: 'relative' }}>
                <div className="junction-center-label">
                  <div style={{ fontSize: '1.4rem', marginBottom: 4 }}>🚦</div>
                  <div style={{ fontWeight: 800, color: 'var(--text)', fontSize: '0.82rem' }}>J1</div>
                  <div style={{ color: 'var(--muted)', fontSize: '0.68rem' }}>{totalVehicles} vehicles</div>
                </div>
              </div>
              <div style={{ background: '#1a2130', display: 'flex', alignItems: 'center', justifyContent: 'flex-start', paddingLeft: 12 }}>
                {[...Array(3)].map((_, i) => (
                  <div key={i} style={{ width: 18, height: 4, background: 'rgba(255,255,255,0.15)', marginBlock: 12, borderRadius: 2 }} />
                ))}
              </div>
            </div>

            {/* Bottom road block */}
            <div style={{ gridColumn: '1/4', gridRow: 3, display: 'grid', gridTemplateColumns: '120px 1fr 120px', background: 'transparent' }}>
              <div style={{ background: '#0a1018' }} />
              <div style={{ background: '#1a2130', display: 'flex', justifyContent: 'center', alignItems: 'flex-start', paddingTop: 12 }}>
                {[...Array(4)].map((_, i) => (
                  <div key={i} style={{ width: 4, height: 18, background: 'rgba(255,255,255,0.15)', marginInline: 12, borderRadius: 2 }} />
                ))}
              </div>
              <div style={{ background: '#0a1018' }} />
            </div>

            {/* Traffic lights — positioned absolutely over the grid */}
            {/* North */}
            <div style={{ position: 'absolute', top: 18, left: '50%', transform: 'translateX(-50%)' }}>
              <TrafficLight
                direction="N"
                phase={getDirPhase('N')}
                countdown={currentStep.dir === 'N' ? countdown : 0}
                greenTime={Math.round(phases?.N?.green || 15)}
              />
            </div>
            {/* South */}
            <div style={{ position: 'absolute', bottom: 18, left: '50%', transform: 'translateX(-50%)' }}>
              <TrafficLight
                direction="S"
                phase={getDirPhase('S')}
                countdown={currentStep.dir === 'S' ? countdown : 0}
                greenTime={Math.round(phases?.S?.green || 15)}
              />
            </div>
            {/* West */}
            <div style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)' }}>
              <TrafficLight
                direction="W"
                phase={getDirPhase('W')}
                countdown={currentStep.dir === 'W' ? countdown : 0}
                greenTime={Math.round(phases?.W?.green || 15)}
              />
            </div>
            {/* East */}
            <div style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)' }}>
              <TrafficLight
                direction="E"
                phase={getDirPhase('E')}
                countdown={currentStep.dir === 'E' ? countdown : 0}
                greenTime={Math.round(phases?.E?.green || 15)}
              />
            </div>
          </div>

          {/* Cycle length info */}
          <div className="glass" style={{ display: 'flex', gap: 20, alignItems: 'center', padding: 16 }}>
            <div>
              <div className="section-title" style={{ marginBottom: 4 }}>Cycle Length</div>
              <div style={{ fontSize: '2rem', fontWeight: 900, color: ACCENT_GREEN }}>
                {Math.round(timing?.cycle_length || 0)}
                <span style={{ fontSize: '1rem', color: 'var(--muted)', marginLeft: 4 }}>sec</span>
              </div>
            </div>
            <div style={{ width: 1, background: 'var(--border2)', alignSelf: 'stretch' }} />
            <div style={{ flex: 1 }}>
              <div className="section-title" style={{ marginBottom: 8 }}>Current Phase</div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <div style={{
                  width: 12, height: 12, borderRadius: '50%',
                  background: currentStep.phase === 'green' ? ACCENT_GREEN : currentStep.phase === 'yellow' ? ACCENT_AMB : '#ff5c5c',
                  boxShadow: `0 0 8px ${currentStep.phase === 'green' ? ACCENT_GREEN : currentStep.phase === 'yellow' ? ACCENT_AMB : '#ff5c5c'}`
                }} />
                <span style={{ fontWeight: 700, textTransform: 'uppercase' }}>
                  {DIR_NAMES[currentStep.dir]} — {currentStep.phase}
                </span>
                <span style={{ marginLeft: 'auto', fontWeight: 900, fontSize: '1.4rem',
                  color: currentStep.phase === 'green' ? ACCENT_GREEN : currentStep.phase === 'yellow' ? ACCENT_AMB : '#ff5c5c'
                }}>
                  {countdown}s
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Right panel — phase cards */}
        <div className="signal-info-panel">
          <div className="glass">
            <div className="card-title">Phase Schedule</div>
            {DIRECTIONS.map(dir => {
              const p = getDirPhase(dir);
              const isActive = currentStep.dir === dir && currentStep.phase !== 'all_red';
              return (
                <div
                  key={dir}
                  className={`signal-phase-card ${isActive ? 'active-phase' : ''} ${p === 'red' && !isActive ? 'red-phase' : ''} ${p === 'yellow' ? 'yellow-phase' : ''}`}
                  style={{ marginBottom: 10 }}
                >
                  <div className="spc-dir-badge" style={{ color: DIR_COLORS[dir], background: `${DIR_COLORS[dir]}18` }}>
                    {dir}
                  </div>
                  <div className="spc-info">
                    <div className="spc-phase-name">
                      {DIR_NAMES[dir]}
                    </div>
                    <div className="spc-timing">
                      Green: {Math.round(phases?.[dir]?.green || 15)}s · Yellow: 3s
                    </div>
                    <div style={{ marginTop: 4, display: 'flex', gap: 6 }}>
                      {Object.entries(directionCounts[dir]?.counts || {}).map(([cls, cnt]) => (
                        <span key={cls} className="cls-chip">{cls}: {cnt}</span>
                      ))}
                    </div>
                  </div>
                  <div className={`spc-countdown ${p === 'red' ? 'red' : p === 'yellow' ? 'yellow' : ''}`}>
                    {isActive ? countdown : '—'}
                  </div>
                </div>
              );
            })}
          </div>

          {/* Signal stats */}
          <div className="glass">
            <div className="card-title">Signal Statistics</div>
            {DIRECTIONS.map(dir => {
              const total = Object.values(directionCounts[dir]?.counts || {}).reduce((a, b) => a + Number(b), 0);
              const g = Math.round(phases?.[dir]?.green || 15);
              return (
                <div key={dir} className="health-row" style={{ marginBottom: 14 }}>
                  <span style={{ color: DIR_COLORS[dir], fontWeight: 700 }}>{dir} — {g}s</span>
                  <div className="bar-bg">
                    <div className="bar-fill" style={{
                      width: `${Math.min(100, (g / 60) * 100)}%`,
                      background: `linear-gradient(90deg, ${DIR_COLORS[dir]}aa, ${DIR_COLORS[dir]})`
                    }} />
                  </div>
                  <span style={{ textAlign: 'right', fontSize: '0.78rem' }}>{total}v</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   CHART WITH INTERVAL SELECTOR
══════════════════════════════════════════════════════════════════════════════ */
function ChartCard({ title, children, interval, onIntervalChange, icon }) {
  return (
    <div className="glass">
      <div className="card-title">
        <span style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {icon && <span className="icon">{icon}</span>}
          {title}
        </span>
        <div className="interval-selector">
          {INTERVALS.map(iv => (
            <button
              key={iv.value}
              className={`interval-btn ${interval === iv.value ? 'active' : ''}`}
              onClick={() => onIntervalChange(iv.value)}
            >
              {iv.label}
            </button>
          ))}
        </div>
      </div>
      {children}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════════════════
   MAIN APP
══════════════════════════════════════════════════════════════════════════════ */
export default function App() {
  const DIRECTIONS = ['N', 'S', 'E', 'W'];

  /* ── Global state ─────────────────────────────────────────────────────── */
  const [activeTab, setActiveTab] = useState('Overview');
  const [time, setTime] = useState('');
  const [isLive, setIsLive] = useState(false);

  /* Per-direction counts from WebSocket feeds */
  const [directionCounts, setDirectionCounts] = useState({
    N: { counts: {}, fps: 0, active: false },
    S: { counts: {}, fps: 0, active: false },
    E: { counts: {}, fps: 0, active: false },
    W: { counts: {}, fps: 0, active: false },
  });

  /* Legacy single-junction counts (for overview pie) */
  const [counts,  setCounts]  = useState({ car: 14, bike: 5, bus: 2, truck: 3 });
  const [status,  setStatus]  = useState({ status: 'OFFLINE', metrics: {} });
  const [alerts,  setAlerts]  = useState({ alerts: [] });
  const [timing,  setTiming]  = useState({
    cycle_length: 60,
    phases: { N: { green: 20 }, S: { green: 20 }, E: { green: 10 }, W: { green: 10 } }
  });

  /* History / chart state */
  const [historyInterval, setHistoryInterval]    = useState('5s');
  const [historyData,     setHistoryData]        = useState([]);
  const [effInterval,     setEffInterval]        = useState('1d');
  const [effData,         setEffData]            = useState([]);

  /* ── Clock ───────────────────────────────────────────────────────────── */
  useEffect(() => {
    const tick = () => {
      setTime(
        new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) +
        ', ' +
        new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
      );
    };
    tick();
    const id = setInterval(tick, 1000);
    return () => clearInterval(id);
  }, []);

  /* ── Callback: individual feed card updates direction counts ─────────── */
  const handleDirectionCounts = useCallback((dir, c) => {
    setDirectionCounts(prev => ({
      ...prev,
      [dir]: { ...prev[dir], counts: c, active: true }
    }));
  }, []);

  /* ── Poll backend for status / alerts / timing ──────────────────────── */
  useEffect(() => {
    const poll = async () => {
      try {
        const [stat, alr, dcRes] = await Promise.allSettled([
          fetchStatus(),
          fetchAlerts(),
          fetchDirectionCounts(),
        ]);

        if (stat.status === 'fulfilled') setStatus(stat.value);
        if (alr.status  === 'fulfilled') setAlerts(alr.value);
        if (dcRes.status === 'fulfilled') {
          const dirs = dcRes.value?.directions || {};
          setDirectionCounts(prev => {
            const next = { ...prev };
            DIRECTIONS.forEach(d => {
              if (dirs[d]) next[d] = { ...next[d], ...dirs[d] };
            });
            return next;
          });

          /* Aggregate all directions → compute timing */
          const allCounts = {};
          DIRECTIONS.forEach(d => {
            allCounts[d] = dirs[d]?.counts || {};
          });
          const hasData = DIRECTIONS.some(d => Object.keys(allCounts[d]).length > 0);
          if (hasData) {
            try {
              const tim = await computeTiming(allCounts);
              setTiming(tim);
              setIsLive(true);
              /* Combine counts for pie chart */
              const combined = {};
              DIRECTIONS.forEach(d => {
                Object.entries(allCounts[d]).forEach(([cls, cnt]) => {
                  combined[cls] = (combined[cls] || 0) + Number(cnt);
                });
              });
              if (Object.keys(combined).length > 0) setCounts(combined);
            } catch (_) {}
          }
        }
      } catch (e) {
        console.error('Poll error', e);
      }
    };

    poll();
    const id = setInterval(poll, 5000);
    return () => clearInterval(id);
  }, []);

  /* ── Poll history for charts ─────────────────────────────────────────── */
  useEffect(() => {
    const fetchH = async () => {
      try {
        const res = await fetchHistory(historyInterval, 20);
        setHistoryData(res.data || []);
      } catch (e) {
        console.error('History fetch error', e);
      }
    };
    fetchH();
    const intervalMap = { '5s': 5000, '1m': 60000, '1h': 3600000, '1d': 86400000 };
    const ms = intervalMap[historyInterval] || 5000;
    const id = setInterval(fetchH, Math.min(ms, 30000)); // max 30s real poll
    return () => clearInterval(id);
  }, [historyInterval]);

  useEffect(() => {
    const fetchE = async () => {
      try {
        const res = await fetchHistory(effInterval, 20);
        setEffData(res.data || []);
      } catch (e) {
        console.error('Eff fetch error', e);
      }
    };
    fetchE();
    const id = setInterval(fetchE, 15000);
    return () => clearInterval(id);
  }, [effInterval]);

  /* ── Derived ─────────────────────────────────────────────────────────── */
  const totalVehicles = Object.values(counts).reduce((a, b) => a + Number(b), 0);
  const pieData = Object.entries(counts).map(([key, val]) => ({ name: key, value: Number(val) }));

  const radarData = DIRECTIONS.map(dir => ({
    direction: DIR_NAMES[dir],
    vehicles: Object.values(directionCounts[dir]?.counts || {}).reduce((a, b) => a + Number(b), 0),
  }));

  /* ── Nav ──────────────────────────────────────────────────────────────── */
  const navItems = [
    { name: 'Overview',         icon: <LayoutDashboard size={17} /> },
    { name: 'Camera Feeds',     icon: <Camera size={17} /> },
    { name: 'Signal Control',   icon: <Zap size={17} /> },
    { name: 'Traffic Analytics',icon: <BarChart3 size={17} /> },
    { name: 'System Status',    icon: <Activity size={17} /> },
    { name: 'Alerts',           icon: <AlertCircle size={17} /> },
  ];

  const tooltipStyle = { backgroundColor: '#111820', borderColor: '#222d3e', fontSize: '0.8rem' };

  return (
    <div className="layout">
      {/* ── Sidebar ─────────────────────────────────────────────────────── */}
      <div className="sidebar">
        <div className="sidebar-header">
          <div className="sidebar-logo">S</div>
          <h2>SmartFlow</h2>
        </div>
        <div className="sidebar-section-label">Navigation</div>
        <div style={{ flex: 1 }}>
          {navItems.map(item => (
            <a
              key={item.name}
              href="#"
              className={`nav-link ${activeTab === item.name ? 'active' : ''}`}
              onClick={e => { e.preventDefault(); setActiveTab(item.name); }}
            >
              {item.icon}
              <span>{item.name}</span>
            </a>
          ))}
        </div>
        <div style={{ marginTop: 'auto', paddingTop: 16, borderTop: '1px solid var(--border2)' }}>
          <a href="#" className="nav-link"><Settings size={17} /><span>Settings</span></a>
        </div>
      </div>

      {/* ── Main ──────────────────────────────────────────────────────────── */}
      <div className="main-content">
        {/* Topbar */}
        <div className="topbar">
          <h1>{activeTab}</h1>
          <div className="top-actions">
            <span>{time}</span>
            <span className={`pill ${isLive ? '' : 'amber'}`}>
              {isLive ? '● Live' : '○ Preview'}
            </span>
            <span className="pill">J1 · {DIRECTIONS.filter(d => directionCounts[d]?.active).length}/4 feeds</span>
            <div className="avatar">AR</div>
          </div>
        </div>

        {/* ══════════════════════════════════════════════════════════════════
            OVERVIEW TAB
        ════════════════════════════════════════════════════════════════════ */}
        {activeTab === 'Overview' && (
          <div className="fade-in">
            <h2 className="page-title">Dashboard Overview — Junction J1</h2>

            {/* Direction summary cards */}
            <div className="dashboard-grid-4" style={{ marginBottom: 18 }}>
              {DIRECTIONS.map(dir => {
                const dc = directionCounts[dir];
                const total = Object.values(dc.counts).reduce((a, b) => a + Number(b), 0);
                return (
                  <div key={dir} className={`dir-summary-card ${dc.active ? 'active' : ''}`}>
                    <div className="dir-summary-title">{DIR_NAMES[dir]} Approach</div>
                    <div className="dir-summary-total" style={{ color: DIR_COLORS[dir] }}>
                      {total}
                    </div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--muted)' }}>vehicles detected</div>
                    <div className="dir-summary-classes">
                      {Object.entries(dc.counts).map(([cls, cnt]) => (
                        <span key={cls} className="cls-chip">{cls}: {cnt}</span>
                      ))}
                      {!dc.active && <span className="cls-chip" style={{ color: 'var(--muted)' }}>No feed</span>}
                    </div>
                    <span className="dir-letter">{dir}</span>
                    {dc.active && (
                      <div style={{ position: 'absolute', top: 10, right: 10 }}>
                        <div className="status-dot live" style={{ width: 7, height: 7 }} />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Main stats row */}
            <div className="dashboard-grid" style={{ gridTemplateColumns: 'repeat(3, 1fr)', marginBottom: 18 }}>
              {/* Pie */}
              <div className="glass">
                <div className="card-title">Vehicle Distribution</div>
                <div style={{ height: 170 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={pieData} innerRadius={50} outerRadius={78} paddingAngle={2} dataKey="value">
                        {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                      </Pie>
                      <Tooltip contentStyle={tooltipStyle} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px', justifyContent: 'center', fontSize: '0.75rem', marginTop: 8 }}>
                  {pieData.map((d, i) => (
                    <span key={d.name} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <span style={{ width: 8, height: 8, borderRadius: '50%', background: COLORS[i % COLORS.length] }} />
                      {d.name} ({d.value})
                    </span>
                  ))}
                </div>
              </div>

              {/* Total vehicles */}
              <div className="glass glow" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 8 }}>
                <div style={{ fontSize: '2.8rem' }}>🚗</div>
                <div className="big-number">{totalVehicles}</div>
                <div className="metric-label">TOTAL VEHICLES<br />ALL DIRECTIONS</div>
                <span className={`status-badge ${isLive ? 'ok' : 'warn'}`}>
                  {isLive ? '● Live AI' : '○ Preview'}
                </span>
              </div>

              {/* Adaptive Timing */}
              <div className="glass">
                <div className="card-title">Adaptive Signal Timing</div>
                {DIRECTIONS.map(dir => {
                  const g = Math.round(timing?.phases?.[dir]?.green || 15);
                  return (
                    <div key={dir} className="health-row" style={{ marginBottom: 12 }}>
                      <span style={{ color: DIR_COLORS[dir], fontWeight: 700, fontSize: '0.82rem' }}>
                        {dir} — {g}s
                      </span>
                      <div className="bar-bg">
                        <div className="bar-fill" style={{
                          width: `${Math.min(100, (g / 60) * 100)}%`,
                          background: `linear-gradient(90deg, ${DIR_COLORS[dir]}88, ${DIR_COLORS[dir]})`
                        }} />
                      </div>
                      <span style={{ fontSize: '0.75rem', textAlign: 'right' }}>{g}s</span>
                    </div>
                  );
                })}
                <div className="cycle" style={{ justifyContent: 'flex-start', marginTop: 14 }}>
                  <div className="cycle-number" style={{ fontSize: '2.5rem' }}>
                    {Math.round(timing?.cycle_length || 60)}
                    <span style={{ fontSize: '1.2rem', color: 'var(--muted)', marginLeft: 4 }}>s</span>
                  </div>
                  <div>
                    <div style={{ fontWeight: 800 }}>CYCLE</div>
                    <div className="muted">AutoRoute</div>
                  </div>
                </div>
              </div>
            </div>

            {/* Charts row */}
            <div className="dashboard-grid-bottom">
              <ChartCard
                title="Traffic Volume History"
                interval={historyInterval}
                onIntervalChange={setHistoryInterval}
                icon={<TrendingUp size={14} />}
              >
                <div style={{ height: 200, marginTop: 8 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={historyData}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.06)" />
                      <XAxis dataKey="time" stroke="var(--muted)" fontSize={11} tickLine={false} axisLine={false} />
                      <YAxis stroke="var(--muted)" fontSize={11} tickLine={false} axisLine={false} />
                      <Tooltip contentStyle={tooltipStyle} />
                      <Area type="monotone" dataKey="total" stroke={ACCENT_GREEN} fill={ACCENT_GREEN} fillOpacity={0.15} strokeWidth={2} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </ChartCard>

              <ChartCard
                title="Direction Comparison"
                interval={effInterval}
                onIntervalChange={setEffInterval}
                icon={<BarChart3 size={14} />}
              >
                <div style={{ height: 200, marginTop: 8 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={effData}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.06)" />
                      <XAxis dataKey="time" stroke="var(--muted)" fontSize={11} tickLine={false} axisLine={false} />
                      <YAxis stroke="var(--muted)" fontSize={11} tickLine={false} axisLine={false} />
                      <Tooltip contentStyle={tooltipStyle} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
                      {DIRECTIONS.map(dir => (
                        <Bar key={dir} dataKey={dir} stackId="a" fill={DIR_COLORS[dir]} radius={dir === 'W' ? [4, 4, 0, 0] : [0, 0, 0, 0]} />
                      ))}
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </ChartCard>
            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════════
            CAMERA FEEDS TAB
        ════════════════════════════════════════════════════════════════════ */}
        {activeTab === 'Camera Feeds' && (
          <div className="fade-in">
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
              <h2 className="page-title" style={{ marginBottom: 0 }}>Camera Feeds — 4 Directions</h2>
              <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
                <span className="muted" style={{ fontSize: '0.78rem' }}>
                  {DIRECTIONS.filter(d => directionCounts[d]?.active).length} / 4 feeds active
                </span>
                <span className="pill">AI Inference On</span>
              </div>
            </div>

            <div className="feeds-grid">
              {DIRECTIONS.map(dir => (
                <CameraFeedCard
                  key={dir}
                  direction={dir}
                  onCountsChange={handleDirectionCounts}
                />
              ))}
            </div>

            {/* Live count summary */}
            <div className="glass" style={{ marginTop: 18 }}>
              <div className="card-title">Live Detection Summary — All Directions</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
                {DIRECTIONS.map(dir => {
                  const dc = directionCounts[dir];
                  const total = Object.values(dc.counts).reduce((a, b) => a + Number(b), 0);
                  return (
                    <div key={dir} style={{ textAlign: 'center' }}>
                      <div style={{ fontSize: '0.72rem', color: DIR_COLORS[dir], fontWeight: 700, marginBottom: 4, textTransform: 'uppercase' }}>
                        {DIR_NAMES[dir]}
                      </div>
                      <div style={{ fontSize: '2rem', fontWeight: 900, color: dc.active ? DIR_COLORS[dir] : 'var(--muted)' }}>
                        {total}
                      </div>
                      <div style={{ fontSize: '0.72rem', color: 'var(--muted)' }}>
                        {dc.fps > 0 ? `${dc.fps} FPS` : dc.active ? 'Connecting...' : 'Idle'}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════════
            SIGNAL CONTROL TAB
        ════════════════════════════════════════════════════════════════════ */}
        {activeTab === 'Signal Control' && (
          <SignalSimulatorTab directionCounts={directionCounts} timing={timing} />
        )}

        {/* ══════════════════════════════════════════════════════════════════
            TRAFFIC ANALYTICS TAB
        ════════════════════════════════════════════════════════════════════ */}
        {activeTab === 'Traffic Analytics' && (
          <div className="fade-in">
            <h2 className="page-title">Traffic Analytics — Junction J1</h2>

            {/* Row 1 */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 16 }}>
              <ChartCard
                title="Volume Over Time"
                interval={historyInterval}
                onIntervalChange={setHistoryInterval}
                icon={<TrendingUp size={14} />}
              >
                <div style={{ height: 220, marginTop: 8 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={historyData}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.06)" />
                      <XAxis dataKey="time" stroke="var(--muted)" fontSize={11} tickLine={false} axisLine={false} />
                      <YAxis stroke="var(--muted)" fontSize={11} tickLine={false} axisLine={false} />
                      <Tooltip contentStyle={tooltipStyle} />
                      <Legend wrapperStyle={{ fontSize: '0.75rem' }} />
                      <Area type="monotone" dataKey="car"   stroke={ACCENT_GREEN} fill={ACCENT_GREEN} fillOpacity={0.12} strokeWidth={2} name="Car" />
                      <Area type="monotone" dataKey="truck" stroke={ACCENT_AMB}   fill={ACCENT_AMB}   fillOpacity={0.08} strokeWidth={2} name="Truck" />
                      <Area type="monotone" dataKey="bus"   stroke={ACCENT_BLUE}  fill={ACCENT_BLUE}  fillOpacity={0.08} strokeWidth={2} name="Bus" />
                      <Area type="monotone" dataKey="bike"  stroke={ACCENT_LIME}  fill={ACCENT_LIME}  fillOpacity={0.08} strokeWidth={2} name="Bike" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </ChartCard>

              <ChartCard
                title="Per-Direction Volume"
                interval={effInterval}
                onIntervalChange={setEffInterval}
                icon={<BarChart3 size={14} />}
              >
                <div style={{ height: 220, marginTop: 8 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={effData}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.06)" />
                      <XAxis dataKey="time" stroke="var(--muted)" fontSize={11} tickLine={false} axisLine={false} />
                      <YAxis stroke="var(--muted)" fontSize={11} tickLine={false} axisLine={false} />
                      <Tooltip contentStyle={tooltipStyle} cursor={{ fill: 'rgba(255,255,255,0.04)' }} />
                      <Legend wrapperStyle={{ fontSize: '0.75rem' }} />
                      {DIRECTIONS.map(dir => (
                        <Bar key={dir} dataKey={dir} stackId="a" fill={DIR_COLORS[dir]}
                          radius={dir === 'W' ? [4, 4, 0, 0] : [0, 0, 0, 0]}
                          name={DIR_NAMES[dir]} />
                      ))}
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </ChartCard>
            </div>

            {/* Row 2 */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              {/* Vehicle class pie */}
              <div className="glass">
                <div className="card-title">Vehicle Class Breakdown</div>
                <div style={{ height: 220 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={pieData} innerRadius={60} outerRadius={90} paddingAngle={3} dataKey="value">
                        {pieData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                      </Pie>
                      <Tooltip contentStyle={tooltipStyle} />
                      <Legend wrapperStyle={{ fontSize: '0.75rem' }} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* Radar */}
              <div className="glass">
                <div className="card-title">Direction Load Comparison</div>
                <div style={{ height: 220 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <RadarChart data={radarData} outerRadius={80}>
                      <PolarGrid stroke="rgba(255,255,255,0.1)" />
                      <PolarAngleAxis dataKey="direction" tick={{ fontSize: 11, fill: 'var(--muted)' }} />
                      <Radar
                        name="Vehicles"
                        dataKey="vehicles"
                        stroke={ACCENT_GREEN}
                        fill={ACCENT_GREEN}
                        fillOpacity={0.25}
                        strokeWidth={2}
                      />
                      <Tooltip contentStyle={tooltipStyle} />
                    </RadarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════════
            SYSTEM STATUS TAB
        ════════════════════════════════════════════════════════════════════ */}
        {activeTab === 'System Status' && (
          <div className="fade-in">
            <h2 className="page-title">System Status</h2>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <div className="glass">
                <div className="card-title">Service Health</div>
                {[
                  { label: 'Backend API',    val: status.status !== 'OFFLINE' ? 100 : 0,   tag: status.status },
                  { label: 'Edge AI (YOLO)', val: 98,                                       tag: 'OK' },
                  { label: 'Database',       val: 100,                                      tag: 'OK' },
                  { label: 'Camera N',       val: directionCounts.N.active ? 100 : 0,       tag: directionCounts.N.active ? 'OK' : 'IDLE' },
                  { label: 'Camera S',       val: directionCounts.S.active ? 100 : 0,       tag: directionCounts.S.active ? 'OK' : 'IDLE' },
                  { label: 'Camera E',       val: directionCounts.E.active ? 100 : 0,       tag: directionCounts.E.active ? 'OK' : 'IDLE' },
                  { label: 'Camera W',       val: directionCounts.W.active ? 100 : 0,       tag: directionCounts.W.active ? 'OK' : 'IDLE' },
                ].map(({ label, val, tag }) => (
                  <div key={label} className="health-row">
                    <span style={{ fontSize: '0.82rem' }}>{label}</span>
                    <div className="bar-bg">
                      <div className={`bar-fill ${val === 0 ? 'red' : val < 80 ? 'amber' : ''}`} style={{ width: `${val}%` }} />
                    </div>
                    <span style={{ fontSize: '0.72rem', textAlign: 'right', color: val === 0 ? 'var(--red)' : val < 80 ? 'var(--amber)' : 'var(--green)' }}>
                      {tag}
                    </span>
                  </div>
                ))}
              </div>

              <div className="glass">
                <div className="card-title">Live Feed Summary</div>
                {DIRECTIONS.map(dir => {
                  const dc = directionCounts[dir];
                  return (
                    <div key={dir} style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14, padding: '10px 12px', background: 'rgba(255,255,255,0.03)', borderRadius: 8 }}>
                      <div style={{ width: 36, height: 36, borderRadius: 10, background: `${DIR_COLORS[dir]}18`, display: 'grid', placeItems: 'center', fontWeight: 900, color: DIR_COLORS[dir] }}>
                        {dir}
                      </div>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontWeight: 700, fontSize: '0.85rem' }}>{DIR_NAMES[dir]}</div>
                        <div style={{ fontSize: '0.72rem', color: 'var(--muted)' }}>
                          {dc.source_type ? `${dc.source_type.toUpperCase()} · ${dc.fps} FPS` : 'No source'}
                        </div>
                      </div>
                      <span className={`status-badge ${dc.active ? 'ok' : 'warn'}`}>
                        {dc.active ? 'LIVE' : 'IDLE'}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* ══════════════════════════════════════════════════════════════════
            ALERTS TAB
        ════════════════════════════════════════════════════════════════════ */}
        {activeTab === 'Alerts' && (
          <div className="fade-in">
            <h2 className="page-title">System Alerts</h2>
            <div className="glass">
              <div className="card-title">Recent Alerts</div>
              {(alerts.alerts && alerts.alerts.length > 0 ? alerts.alerts : [
                { ts: '09:44:12', issue: 'J1 South: High Congestion Detected (18 vehicles)' },
                { ts: '09:41:05', issue: 'Edge AI: Reconnected successfully' },
                { ts: '09:32:44', issue: 'J1 North: FPS dropped below threshold' },
                { ts: '09:21:00', issue: 'System startup — all services initialized' },
              ]).map((a, i) => (
                <div key={i} className="alert-row">
                  <div className="alert-dot" />
                  <span>
                    <span className="muted">
                      {new Date(a.ts).toLocaleTimeString() !== 'Invalid Date'
                        ? new Date(a.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
                        : a.ts}
                    </span>
                    {' — '}
                    {a.issue}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
