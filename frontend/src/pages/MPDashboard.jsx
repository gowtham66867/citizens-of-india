import React, { useState, useEffect, useCallback } from 'react';
import api from '../api';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend
} from 'recharts';
import { APIProvider, Map, useMap, useMapsLibrary } from '@vis.gl/react-google-maps';

const COLORS = ['#FF9933', '#138808', '#000080', '#e53e3e', '#d69e2e', '#805ad5', '#38a169', '#3182ce', '#dd6b20', '#718096'];
const URGENCY_COLOR = { High: '#e53e3e', Medium: '#d69e2e', Low: '#38a169' };

const MAPS_KEY = process.env.REACT_APP_GOOGLE_MAPS_KEY || '';

const THEME_COLORS = {
  'Roads & Infrastructure': '#e53e3e',
  'Healthcare & Sanitation': '#38a169',
  'Education': '#3182ce',
  'Water Supply': '#0bc5ea',
  'Electricity': '#d69e2e',
  'Agriculture Support': '#68d391',
  'Employment & Livelihood': '#9f7aea',
  'Environment & Waste': '#48bb78',
  'Public Safety': '#fc8181',
  'Other': '#a0aec0',
};

function HeatmapLayer({ points }) {
  const map = useMap();
  const viz = useMapsLibrary('visualization');
  const [heatmap, setHeatmap] = useState(null);

  useEffect(() => {
    if (!viz || !map) return;
    const h = new viz.HeatmapLayer({
      data: [],
      map,
      radius: 35,
      opacity: 0.8,
    });
    setHeatmap(h);
    return () => h.setMap(null);
  }, [viz, map]);

  useEffect(() => {
    if (!heatmap || !window.google) return;
    heatmap.setData(
      points.map(p => ({
        location: new window.google.maps.LatLng(p.lat, p.lng),
        weight: p.urgency === 'High' ? 3 : p.urgency === 'Medium' ? 2 : 1,
      }))
    );
  }, [heatmap, points]);

  return null;
}

function IssueMarkers({ points }) {
  const map = useMap();
  const [markers, setMarkers] = useState([]);

  useEffect(() => {
    if (!map || !window.google) return;
    markers.forEach(m => m.setMap(null));
    const newMarkers = points.map(p => {
      const color = THEME_COLORS[p.theme] || '#718096';
      const marker = new window.google.maps.Marker({
        position: { lat: p.lat, lng: p.lng },
        map,
        icon: {
          path: window.google.maps.SymbolPath.CIRCLE,
          scale: 8,
          fillColor: color,
          fillOpacity: 0.9,
          strokeColor: '#fff',
          strokeWeight: 2,
        },
        title: `${p.theme} · ${p.urgency}`,
      });
      return marker;
    });
    setMarkers(newMarkers);
    return () => newMarkers.forEach(m => m.setMap(null));
  }, [map, points]);

  return null;
}

function DemandHeatmap({ points }) {
  const [viewMode, setViewMode] = useState('heat');
  const CENTER = { lat: 16.22, lng: 80.12 };

  if (!MAPS_KEY) {
    return (
      <div style={{
        height: '420px', background: '#f7fafc', borderRadius: '12px',
        display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: '0.75rem'
      }}>
        <div style={{ fontSize: '2.5rem' }}>🗺️</div>
        <div style={{ fontWeight: 600, color: '#2d3748' }}>Map requires Google Maps API key</div>
        <div style={{ fontSize: '0.85rem', color: '#718096', textAlign: 'center', maxWidth: '320px' }}>
          Add <code>REACT_APP_GOOGLE_MAPS_KEY</code> to <code>frontend/.env</code> and restart
        </div>
        <div style={{ marginTop: '1rem', display: 'flex', flexDirection: 'column', gap: '0.5rem', width: '100%', maxWidth: '420px', padding: '0 1rem' }}>
          {points.slice(0, 6).map((p, i) => (
            <div key={i} style={{
              display: 'flex', justifyContent: 'space-between', alignItems: 'center',
              padding: '0.5rem 0.75rem', background: '#fff', borderRadius: '8px',
              border: '1px solid #e2e8f0', fontSize: '0.82rem'
            }}>
              <span style={{ color: THEME_COLORS[p.theme] || '#718096', fontWeight: 600 }}>● {p.theme}</span>
              <span style={{ color: URGENCY_COLOR[p.urgency], fontWeight: 600 }}>{p.urgency}</span>
              <span style={{ color: '#a0aec0' }}>{p.lat?.toFixed(3)}, {p.lng?.toFixed(3)}</span>
            </div>
          ))}
          {points.length === 0 && <div style={{ textAlign: 'center', color: '#a0aec0' }}>No geotagged submissions yet</div>}
        </div>
      </div>
    );
  }

  return (
    <div>
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '0.75rem' }}>
        {[['heat', '🔥 Heatmap'], ['markers', '📍 Issues']].map(([id, label]) => (
          <button key={id} onClick={() => setViewMode(id)} style={{
            padding: '5px 14px', borderRadius: '20px', fontSize: '0.82rem', fontWeight: 600,
            background: viewMode === id ? '#FF9933' : '#f0f4f8',
            color: viewMode === id ? '#fff' : '#4a5568', border: 'none',
          }}>{label}</button>
        ))}
      </div>
      <APIProvider apiKey={MAPS_KEY} libraries={['visualization']}>
        <Map
          defaultCenter={CENTER}
          defaultZoom={11}
          mapId="citizens-india-map"
          style={{ height: '380px', borderRadius: '12px', overflow: 'hidden' }}
        >
          {viewMode === 'heat' && <HeatmapLayer points={points} />}
          {viewMode === 'markers' && <IssueMarkers points={points} />}
        </Map>
      </APIProvider>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem', marginTop: '0.75rem' }}>
        {Object.entries(THEME_COLORS).filter(([k]) => points.some(p => p.theme === k)).map(([theme, color]) => (
          <span key={theme} style={{
            fontSize: '0.75rem', padding: '2px 10px', borderRadius: '12px',
            background: `${color}18`, color, fontWeight: 600, border: `1px solid ${color}40`
          }}>● {theme}</span>
        ))}
      </div>
    </div>
  );
}

function StatCard({ icon, label, value, sub, color }) {
  return (
    <div className="card" style={{ textAlign: 'center' }}>
      <div style={{ fontSize: '2rem', marginBottom: '0.25rem' }}>{icon}</div>
      <div style={{ fontSize: '2rem', fontWeight: 800, color: color || '#FF9933' }}>{value}</div>
      <div style={{ fontSize: '0.85rem', fontWeight: 600, color: '#2d3748' }}>{label}</div>
      {sub && <div style={{ fontSize: '0.78rem', color: '#718096', marginTop: '0.2rem' }}>{sub}</div>}
    </div>
  );
}

function PriorityCard({ item, rank }) {
  const rankColors = { 1: '#FF9933', 2: '#718096', 3: '#c05621' };
  return (
    <div className="card" style={{ borderLeft: `4px solid ${rankColors[rank] || '#e2e8f0'}`, marginBottom: '1rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flex: 1 }}>
          <div style={{
            width: '36px', height: '36px', borderRadius: '50%', flexShrink: 0,
            background: rankColors[rank] || '#e2e8f0', color: '#fff',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontWeight: 800, fontSize: '1.1rem',
          }}>#{rank}</div>
          <div>
            <h3 style={{ fontSize: '1rem', fontWeight: 700, color: '#1a202c', marginBottom: '0.25rem' }}>{item.theme}</h3>
            <p style={{ fontSize: '0.88rem', color: '#4a5568', lineHeight: 1.5 }}>{item.rationale}</p>
          </div>
        </div>
      </div>
      <div style={{
        marginTop: '0.75rem', padding: '0.6rem 0.9rem',
        background: '#f7fafc', borderRadius: '8px', display: 'flex', gap: '2rem', flexWrap: 'wrap'
      }}>
        <div>
          <span style={{ fontSize: '0.75rem', color: '#718096', fontWeight: 600 }}>NEXT STEP</span>
          <p style={{ fontSize: '0.85rem', color: '#2d3748', marginTop: '0.1rem' }}>{item.suggested_action}</p>
        </div>
        <div>
          <span style={{ fontSize: '0.75rem', color: '#718096', fontWeight: 600 }}>BENEFICIARIES</span>
          <p style={{ fontSize: '0.85rem', color: '#138808', fontWeight: 700, marginTop: '0.1rem' }}>{item.estimated_beneficiaries}</p>
        </div>
      </div>
    </div>
  );
}

function SubmissionRow({ s }) {
  const uc = URGENCY_COLOR[s.urgency] || '#718096';
  return (
    <tr style={{ borderBottom: '1px solid #f0f4f8' }}>
      <td style={{ padding: '0.75rem 1rem', fontSize: '0.88rem', maxWidth: '280px' }}>
        <div style={{ fontWeight: 500, color: '#2d3748', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
          {s.original_text?.slice(0, 80)}…
        </div>
        <div style={{ fontSize: '0.75rem', color: '#a0aec0', marginTop: '2px' }}>{s.source_language?.toUpperCase()} · {s.input_type}</div>
      </td>
      <td style={{ padding: '0.75rem 1rem' }}>
        <span style={{
          background: '#fff3e0', color: '#c05621', borderRadius: '12px',
          padding: '2px 10px', fontSize: '0.78rem', fontWeight: 600, whiteSpace: 'nowrap'
        }}>{s.theme}</span>
      </td>
      <td style={{ padding: '0.75rem 1rem' }}>
        <span style={{
          background: `${uc}18`, color: uc, borderRadius: '12px',
          padding: '2px 10px', fontSize: '0.78rem', fontWeight: 600
        }}>{s.urgency}</span>
      </td>
      <td style={{ padding: '0.75rem 1rem', fontSize: '0.82rem', color: '#718096' }}>
        {s.location_hint || '—'}
      </td>
    </tr>
  );
}

export default function MPDashboard() {
  const [summary, setSummary] = useState(null);
  const [themes, setThemes] = useState([]);
  const [priorities, setPriorities] = useState([]);
  const [submissions, setSubmissions] = useState([]);
  const [heatmapPoints, setHeatmapPoints] = useState([]);
  const [loading, setLoading] = useState(true);
  const [prioritiesLoading, setPrioritiesLoading] = useState(false);
  const [constituency, setConstituency] = useState('Demo Constituency');
  const [activeTab, setActiveTab] = useState('overview');
  const [error, setError] = useState(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    // Load fast endpoints independently so one failure doesn't block all
    const safe = async (fn) => { try { return await fn(); } catch { return null; } };
    const [sumRes, themeRes, subRes, heatRes] = await Promise.all([
      safe(() => api.get(`/analytics/summary?constituency=${encodeURIComponent(constituency)}`)),
      safe(() => api.get(`/analytics/themes?constituency=${encodeURIComponent(constituency)}`)),
      safe(() => api.get(`/submissions/list?constituency=${encodeURIComponent(constituency)}&limit=50`)),
      safe(() => api.get(`/analytics/heatmap?constituency=${encodeURIComponent(constituency)}`)),
    ]);
    setSummary(sumRes?.data || null);
    setThemes(themeRes?.data || []);
    setSubmissions(subRes?.data || []);
    setHeatmapPoints(heatRes?.data?.points || []);
    setLoading(false);
  };

  const loadPriorities = async () => {
    if (priorities.length > 0) return; // already loaded
    setPrioritiesLoading(true);
    try {
      const res = await api.get(`/analytics/priorities?constituency=${encodeURIComponent(constituency)}`);
      setPriorities(res.data.priorities || []);
    } catch (e) {
      console.error(e);
    } finally {
      setPrioritiesLoading(false);
    }
  };

  useEffect(() => { load(); }, [constituency]);

  const langData = summary?.languages
    ? Object.entries(summary.languages).map(([k, v]) => ({ name: k.toUpperCase(), value: v }))
    : [];

  return (
    <div style={{ padding: '2rem 0', minHeight: 'calc(100vh - 60px)' }}>
      <div className="container">
        {/* Header */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '1.5rem', flexWrap: 'wrap', gap: '1rem' }}>
          <div>
            <h1 style={{ fontSize: '1.6rem', fontWeight: 700, color: '#1a202c' }}>MP Dashboard</h1>
            <p style={{ color: '#718096', fontSize: '0.9rem' }}>AI-ranked citizen development priorities</p>
          </div>
          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <input
              value={constituency} onChange={e => setConstituency(e.target.value)}
              placeholder="Constituency" style={{ width: '200px' }}
              onKeyDown={e => e.key === 'Enter' && load()}
            />
            <button onClick={load} style={{
              padding: '0.6rem 1.2rem', background: '#FF9933', color: '#fff',
              borderRadius: '8px', fontWeight: 600, fontSize: '0.9rem',
            }}>Refresh</button>
          </div>
        </div>

        {loading ? (
          <div style={{ textAlign: 'center', padding: '4rem', color: '#718096' }}>
            <div style={{ fontSize: '2rem', marginBottom: '1rem' }}>⏳</div>
            Analyzing submissions with AI...
          </div>
        ) : (
          <>
            {/* Stats */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem', marginBottom: '2rem' }}>
              <StatCard icon="📨" label="Total Submissions" value={summary?.total_submissions || 0} />
              <StatCard icon="🚨" label="High Urgency" value={summary?.high_urgency_count || 0} color="#e53e3e"
                sub={summary?.total_submissions ? `${Math.round((summary.high_urgency_count / summary.total_submissions) * 100)}% of total` : ''} />
              <StatCard icon="📌" label="Issue Categories" value={themes.length} color="#000080" />
              <StatCard icon="🌐" label="Languages" value={Object.keys(summary?.languages || {}).length} color="#138808" sub="multilingual reach" />
            </div>

            {/* Tabs */}
            <div style={{ display: 'flex', gap: '0.25rem', marginBottom: '1.5rem', borderBottom: '2px solid #e2e8f0', paddingBottom: '0' }}>
              {[
                { id: 'overview', label: '📊 Overview' },
                { id: 'priorities', label: '🎯 AI Priorities' },
                { id: 'heatmap', label: '🗺️ Demand Map' },
                { id: 'submissions', label: '📋 Submissions' },
              ].map(t => (
                <button key={t.id} onClick={() => { setActiveTab(t.id); if (t.id === 'priorities') loadPriorities(); }} style={{
                  padding: '0.6rem 1.2rem', borderRadius: '8px 8px 0 0', fontWeight: 600, fontSize: '0.9rem',
                  background: activeTab === t.id ? '#FF9933' : 'transparent',
                  color: activeTab === t.id ? '#fff' : '#718096',
                  borderBottom: activeTab === t.id ? '2px solid #FF9933' : 'none',
                  marginBottom: '-2px',
                }}>{t.label}</button>
              ))}
            </div>

            {/* Overview tab */}
            {activeTab === 'overview' && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' }}>
                <div className="card">
                  <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '1rem', color: '#2d3748' }}>Submissions by Issue Type</h3>
                  <ResponsiveContainer width="100%" height={260}>
                    <BarChart data={themes} layout="vertical" margin={{ left: 10 }}>
                      <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                      <XAxis type="number" fontSize={11} />
                      <YAxis type="category" dataKey="theme" width={160} fontSize={11} />
                      <Tooltip />
                      <Bar dataKey="count" fill="#FF9933" radius={[0, 4, 4, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
                <div className="card">
                  <h3 style={{ fontSize: '0.95rem', fontWeight: 700, marginBottom: '1rem', color: '#2d3748' }}>Language Distribution</h3>
                  {langData.length > 0 ? (
                    <ResponsiveContainer width="100%" height={260}>
                      <PieChart>
                        <Pie data={langData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={90} label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                          {langData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                        </Pie>
                        <Tooltip />
                      </PieChart>
                    </ResponsiveContainer>
                  ) : (
                    <div style={{ textAlign: 'center', padding: '3rem', color: '#a0aec0' }}>No data yet</div>
                  )}
                </div>
              </div>
            )}

            {/* Priorities tab */}
            {activeTab === 'priorities' && (
              <div>
                <div style={{ marginBottom: '1rem', padding: '0.75rem 1rem', background: '#fff3e0', borderRadius: '8px', fontSize: '0.85rem', color: '#744210' }}>
                  🤖 AI-ranked by Gemini using submission volume, urgency signals, and constituency demographics
                </div>
                {prioritiesLoading ? (
                  <div style={{ textAlign: 'center', padding: '3rem', color: '#718096' }}>
                    <div style={{ fontSize: '1.5rem', marginBottom: '0.75rem' }}>🤖</div>
                    Gemini is analyzing {themes.length} issue categories…
                  </div>
                ) : priorities.length === 0 ? (
                  <div className="card" style={{ textAlign: 'center', padding: '3rem', color: '#a0aec0' }}>
                    No submissions yet. Add some via the citizen portal.
                  </div>
                ) : (
                  priorities.map(p => <PriorityCard key={p.rank} item={p} rank={p.rank} />)
                )}
              </div>
            )}

            {/* Heatmap tab */}
            {activeTab === 'heatmap' && (
              <div className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                  <h3 style={{ fontSize: '0.95rem', fontWeight: 700, color: '#2d3748' }}>
                    Demand Hotspot Map
                  </h3>
                  <span style={{ fontSize: '0.82rem', color: '#718096' }}>
                    {heatmapPoints.length} geotagged submissions
                  </span>
                </div>
                <DemandHeatmap points={heatmapPoints} />
              </div>
            )}

            {/* Submissions tab */}
            {activeTab === 'submissions' && (
              <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
                <div style={{ padding: '1rem 1.25rem', borderBottom: '1px solid #e2e8f0', fontWeight: 700, color: '#2d3748' }}>
                  Recent Submissions ({submissions.length})
                </div>
                <div style={{ overflowX: 'auto' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse' }}>
                    <thead>
                      <tr style={{ background: '#f7fafc' }}>
                        {['Submission', 'Theme', 'Urgency', 'Location'].map(h => (
                          <th key={h} style={{ padding: '0.75rem 1rem', textAlign: 'left', fontSize: '0.78rem', fontWeight: 700, color: '#718096', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {submissions.length === 0
                        ? <tr><td colSpan={4} style={{ padding: '3rem', textAlign: 'center', color: '#a0aec0' }}>No submissions yet</td></tr>
                        : submissions.map(s => <SubmissionRow key={s.id} s={s} />)
                      }
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
