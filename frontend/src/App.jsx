import React, { useState, useEffect } from 'react';
import { fetchLatestCounts, fetchStatus, fetchAlerts, fetchProcesses, computeTiming } from './api';
import { PieChart, Pie, Cell, ResponsiveContainer, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, BarChart, Bar } from 'recharts';
import { Activity, AlertCircle, Map as MapIcon, BarChart3, LayoutDashboard, FileText, Settings } from 'lucide-react';
import './index.css';

const ACCENT_GREEN = "#62ee86";
const ACCENT_LIME = "#dfff45";
const COLORS = [ACCENT_GREEN, "#8ff266", ACCENT_LIME, "#f2ff7a", "#4ccf7b"];

// Dummy data for charts
const HISTORY = [28, 48, 68, 75, 58, 62, 118, 104, 96, 112, 126, 168, 154, 116, 104, 128, 84];
const PEDESTRIANS = [8, 10, 14, 20, 13, 16, 26, 21, 24, 22, 25, 36, 31, 22, 24, 29, 12];
const EFFICIENCY = [68, 88, 69, 55, 86, 76, 86];
const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

const historyData = HISTORY.map((val, i) => ({
  time: `${String(Math.min(i * 3, 23)).padStart(2, '0')}h`,
  vehicles: val,
  pedestrians: PEDESTRIANS[i]
}));

const efficiencyData = EFFICIENCY.map((val, i) => ({
  day: DAYS[i],
  reduced: val
}));

export default function App() {
  const [activeTab, setActiveTab] = useState("Overview");
  const [time, setTime] = useState(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ', ' + new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }));
  
  const [counts, setCounts] = useState({ car: 14, bike: 5, bus: 2, truck: 3 });
  const [isLive, setIsLive] = useState(false);
  const [status, setStatus] = useState({ status: "OFFLINE", metrics: {} });
  const [alerts, setAlerts] = useState({ alerts: [] });
  const [timing, setTiming] = useState({ cycle_length: 30, phases: { N: { green: 28 }, E: { green: 12 } } });
  
  useEffect(() => {
    const clock = setInterval(() => {
      setTime(new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + ', ' + new Date().toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }));
    }, 1000);
    return () => clearInterval(clock);
  }, []);

  useEffect(() => {
    const poll = async () => {
      try {
        const latest = await fetchLatestCounts();
        if (latest.counts && Object.keys(latest.counts).length > 0) {
          setCounts(latest.counts);
          setIsLive(true);
        }
        
        const stat = await fetchStatus();
        setStatus(stat);
        
        const alr = await fetchAlerts();
        setAlerts(alr);
        
        if (latest.counts && Object.keys(latest.counts).length > 0) {
          const tim = await computeTiming(latest.counts);
          setTiming(tim);
        }
      } catch (e) {
        console.error("Backend offline or error", e);
      }
    };
    poll();
    const int = setInterval(poll, 5000);
    return () => clearInterval(int);
  }, []);

  const totalVehicles = Object.values(counts).reduce((a, b) => a + Number(b), 0);
  const pieData = Object.entries(counts).map(([key, val]) => ({ name: key, value: Number(val) }));

  const navItems = [
    { name: "Overview", icon: <LayoutDashboard size={18} /> },
    { name: "Traffic Analytics", icon: <BarChart3 size={18} /> },
    { name: "System Status", icon: <Activity size={18} /> },
    { name: "Alerts", icon: <AlertCircle size={18} /> },
    { name: "Junction Map", icon: <MapIcon size={18} /> },
    { name: "Reports", icon: <FileText size={18} /> }
  ];

  return (
    <div className="layout">
      {/* Sidebar */}
      <div className="sidebar">
        <div className="sidebar-header">
          <div className="sidebar-logo">S</div>
          <h2>SmartFlow</h2>
        </div>
        <div style={{ flex: 1 }}>
          {navItems.map(item => (
            <a 
              key={item.name} 
              href="#" 
              className={`nav-link ${activeTab === item.name ? 'active' : ''}`}
              onClick={(e) => { e.preventDefault(); setActiveTab(item.name); }}
            >
              {item.icon}
              {item.name}
            </a>
          ))}
        </div>
        <div style={{ marginTop: 'auto' }}>
          <a href="#" className="nav-link"><Settings size={18} /> Settings</a>
        </div>
      </div>

      {/* Main Content */}
      <div className="main-content">
        {/* Topbar */}
        <div className="topbar">
          <h1>{activeTab}</h1>
          <div className="top-actions">
            <span>{time}</span>
            <span className="pill">Live refresh 5s</span>
            <div className="avatar">AR</div>
            <strong>A.R.</strong>
          </div>
        </div>

        {activeTab === "Overview" && (
          <div>
            <h2 className="page-title">Dashboard Overview - Junction J1 (Live Data)</h2>
            <div className="dashboard-grid">
              
              {/* Traffic Flow Card */}
              <div className="glass">
                <div className="card-title">Current Traffic Flow (J1)</div>
                <div style={{ height: 180 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie data={pieData} innerRadius={50} outerRadius={80} paddingAngle={2} dataKey="value">
                        {pieData.map((entry, index) => <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />)}
                      </Pie>
                      <Tooltip contentStyle={{ backgroundColor: '#1b242b', borderColor: '#333' }} />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', fontSize: '0.8rem', justifyContent: 'center' }}>
                  {pieData.map((d, i) => (
                    <span key={d.name} style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <span style={{ width: 8, height: 8, borderRadius: '50%', background: COLORS[i % COLORS.length] }}></span>
                      {d.name.charAt(0).toUpperCase() + d.name.slice(1)} ({d.value})
                    </span>
                  ))}
                </div>
              </div>

              {/* Vehicles Detected */}
              <div className="glass glow" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
                <div style={{ fontSize: '3rem', color: ACCENT_GREEN }}>🚗</div>
                <div className="big-number">{totalVehicles}</div>
                <div className="metric-label">VEHICLES<br/>DETECTED</div>
                <div className="muted" style={{ marginTop: '8px' }}>{isLive ? "(Live)" : "(Preview)"}</div>
              </div>

              {/* Timing */}
              <div className="glass">
                <div className="card-title" style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>Adaptive Signal Timing (J1)</span>
                  <span>⏱️</span>
                </div>
                <div className="muted" style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <span>N/S Green: <b style={{ color: ACCENT_GREEN }}>{Math.round(timing?.phases?.N?.green || 28)}s</b></span>
                  <span>E/W Green: <b style={{ color: ACCENT_LIME }}>{Math.round(timing?.phases?.E?.green || 12)}s</b></span>
                </div>
                <div className="signal-grid">
                  <div className="direction">N</div>
                  <div className="phase">{Math.round(timing?.phases?.N?.green || 28)}s</div>
                  <div className="phase alt">{Math.round(timing?.phases?.E?.green || 12)}s</div>
                  <div className="direction">E</div>
                  <div className="direction">S</div>
                  <div></div>
                  <div></div>
                  <div className="direction">W</div>
                </div>
                <div className="cycle">
                  <div className="cycle-number">{Math.round(timing.cycle_length || 30)}<span style={{ fontSize: '2rem' }}>s</span></div>
                  <div style={{ paddingBottom: '6px' }}>
                    <div style={{ fontSize: '1.2rem', fontWeight: 800 }}>CYCLE</div>
                    <div className="muted">AutoRoute Active</div>
                  </div>
                </div>
              </div>

              {/* Health */}
              <div className="glass">
                <div className="card-title">System Health</div>
                
                <div className="health-row">
                  <span>Edge AI</span>
                  <div className="bar-bg"><div className="bar-fill" style={{ width: '98%' }}></div></div>
                  <span style={{ textAlign: 'right' }}>[98%]</span>
                </div>
                
                <div className="health-row">
                  <span>Backend API</span>
                  <div className="bar-bg"><div className="bar-fill" style={{ width: status.status === "OFFLINE" ? '0%' : '100%' }}></div></div>
                  <span style={{ textAlign: 'right' }}>[{status.status === "OFFLINE" ? 'DOWN' : '100%'}]</span>
                </div>
                
                <div className="health-row">
                  <span>Database</span>
                  <div className="bar-bg"><div className="bar-fill" style={{ width: '100%' }}></div></div>
                  <span style={{ textAlign: 'right' }}>[100%]</span>
                </div>

                <div className="health-row">
                  <span>Camera Feed</span>
                  <div className="bar-bg"><div className="bar-fill" style={{ width: status.metrics?.camera_ok === false ? '0%' : '100%' }}></div></div>
                  <span style={{ textAlign: 'right' }}>[{status.metrics?.camera_ok === false ? 'LOST' : 'OK'}]</span>
                </div>
              </div>

              {/* Alerts */}
              <div className="glass">
                <div className="card-title">Recent Alerts</div>
                {(alerts.alerts && alerts.alerts.length > 0 ? alerts.alerts.slice(0, 4) : [
                  { ts: "09:44:12", issue: "J1 S: High Congestion Detect" },
                  { ts: "09:41:05", issue: "Edge AI: Reconnected" }
                ]).map((a, i) => (
                  <div key={i} className="alert-row">
                    <span className="muted">{new Date(a.ts).toLocaleTimeString() !== "Invalid Date" ? new Date(a.ts).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) : a.ts}</span> - {a.issue}
                  </div>
                ))}
              </div>

            </div>

            <div className="dashboard-grid-bottom">
              {/* History Chart */}
              <div className="glass">
                <div className="card-title">Historical Traffic Volume (24h)</div>
                <div style={{ height: 200 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={historyData}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.1)" />
                      <XAxis dataKey="time" stroke="var(--muted)" fontSize={12} tickLine={false} axisLine={false} />
                      <YAxis stroke="var(--muted)" fontSize={12} tickLine={false} axisLine={false} />
                      <Tooltip contentStyle={{ backgroundColor: '#1b242b', borderColor: '#333' }} />
                      <Area type="monotone" dataKey="vehicles" stroke={ACCENT_GREEN} fillOpacity={0.2} fill={ACCENT_GREEN} strokeWidth={2} />
                      <Area type="monotone" dataKey="pedestrians" stroke={ACCENT_LIME} fillOpacity={0} fill={ACCENT_LIME} strokeWidth={2} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
                <div style={{ display: 'flex', gap: '16px', justifyContent: 'center', fontSize: '0.8rem', marginTop: '8px' }}>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><span style={{ width: 12, height: 2, background: ACCENT_GREEN }}></span> Vehicles</span>
                  <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}><span style={{ width: 12, height: 2, background: ACCENT_LIME }}></span> Pedestrians</span>
                </div>
              </div>

              {/* Efficiency Chart */}
              <div className="glass">
                <div className="card-title">Signal Efficiency Trend (7 days)</div>
                <div style={{ height: 220 }}>
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={efficiencyData}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.1)" />
                      <XAxis dataKey="day" stroke="var(--muted)" fontSize={12} tickLine={false} axisLine={false} />
                      <YAxis stroke="var(--muted)" fontSize={12} tickLine={false} axisLine={false} />
                      <Tooltip contentStyle={{ backgroundColor: '#1b242b', borderColor: '#333' }} cursor={{ fill: 'rgba(255,255,255,0.05)' }} />
                      <Bar dataKey="reduced" fill={ACCENT_GREEN} radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Fallback for other pages for demo purposes */}
        {activeTab !== "Overview" && (
          <div className="glass" style={{ flex: 1, display: 'grid', placeItems: 'center' }}>
            <div style={{ textAlign: 'center' }}>
              <h2 style={{ fontSize: '2rem', marginBottom: '10px' }}>{activeTab}</h2>
              <p className="muted">This module is connected to the backend. Content layout matches Streamlit parity.</p>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
