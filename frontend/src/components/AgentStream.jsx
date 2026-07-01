/**
 * AgentStream — Live multi-agent pipeline progress panel.
 *
 * Shows a "Run AI Analysis" button that opens a real-time SSE stream
 * from /agents/stream, displaying each subagent step as it happens,
 * then renders the final MP briefing in a styled card.
 */
import React, { useState, useRef, useEffect } from 'react';

const API_BASE = process.env.REACT_APP_API_BASE || '';

const STEP_LABELS = {
  fetch_submissions:   { icon: '📥', label: 'Fetching citizen submissions…' },
  cluster_issues:      { icon: '🧩', label: 'Clustering issues semantically…' },
  prioritize_clusters: { icon: '📊', label: 'Scoring urgency × reach × actionability…' },
  generate_briefing:   { icon: '📝', label: 'Drafting MP briefing…' },
};

export default function AgentStream({ constituency }) {
  const [open, setOpen] = useState(false);
  const [status, setStatus] = useState('idle'); // idle | running | done | error
  const [steps, setSteps] = useState([]);
  const [briefing, setBriefing] = useState('');
  const [jobId, setJobId] = useState('');
  const esRef = useRef(null);
  const briefingRef = useRef(null);

  const run = () => {
    if (status === 'running') return;
    setOpen(true);
    setStatus('running');
    setSteps([]);
    setBriefing('');

    const url = `${API_BASE}/agents/stream?constituency=${encodeURIComponent(constituency)}`;
    const es = new EventSource(url);
    esRef.current = es;

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data);
        if (data.event === 'started') {
          setJobId(data.job_id || '');
        } else if (data.event === 'progress') {
          setSteps(prev => [...prev, data]);
        } else if (data.event === 'completed') {
          setBriefing(data.briefing || '');
          setStatus('done');
          es.close();
          setTimeout(() => briefingRef.current?.scrollIntoView({ behavior: 'smooth' }), 100);
        } else if (data.event === 'error') {
          setStatus('error');
          es.close();
        }
      } catch {}
    };

    es.onerror = () => {
      setStatus('error');
      es.close();
    };
  };

  useEffect(() => () => esRef.current?.close(), []);

  if (!open) {
    return (
      <button onClick={run} style={{
        display: 'flex', alignItems: 'center', gap: '8px',
        padding: '10px 20px', borderRadius: '10px', fontWeight: 700,
        fontSize: '0.9rem', border: 'none', cursor: 'pointer',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        color: '#fff', boxShadow: '0 4px 14px rgba(102,126,234,0.4)',
        transition: 'transform 0.15s, box-shadow 0.15s',
      }}
        onMouseEnter={e => { e.currentTarget.style.transform = 'translateY(-1px)'; e.currentTarget.style.boxShadow = '0 6px 20px rgba(102,126,234,0.5)'; }}
        onMouseLeave={e => { e.currentTarget.style.transform = ''; e.currentTarget.style.boxShadow = '0 4px 14px rgba(102,126,234,0.4)'; }}
      >
        <span style={{ fontSize: '1.1rem' }}>🤖</span>
        Run AI Analysis Pipeline
      </button>
    );
  }

  return (
    <div style={{
      background: '#0f0f1a', borderRadius: '16px', padding: '1.5rem',
      border: '1px solid #2d2d4e', color: '#e2e8f0', fontFamily: 'monospace',
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.25rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '1.2rem' }}>🤖</span>
          <div>
            <div style={{ fontWeight: 700, fontSize: '0.95rem', color: '#a78bfa' }}>
              Multi-Agent Analysis Pipeline
            </div>
            {jobId && <div style={{ fontSize: '0.72rem', color: '#4a5568' }}>job: {jobId}</div>}
          </div>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          {status === 'running' && (
            <span style={{ fontSize: '0.78rem', color: '#fbd38d', animation: 'blink 1.2s infinite' }}>
              ● LIVE
            </span>
          )}
          {status === 'done' && <span style={{ fontSize: '0.78rem', color: '#68d391' }}>✓ COMPLETE</span>}
          {status === 'error' && <span style={{ fontSize: '0.78rem', color: '#fc8181' }}>✗ ERROR</span>}
          <button onClick={() => { setOpen(false); setStatus('idle'); }} style={{
            background: '#2d2d4e', border: 'none', color: '#718096', cursor: 'pointer',
            borderRadius: '6px', padding: '4px 10px', fontSize: '0.8rem',
          }}>✕</button>
        </div>
      </div>

      {/* Agent steps */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', marginBottom: '1rem' }}>
        {['fetch_submissions', 'cluster_issues', 'prioritize_clusters', 'generate_briefing'].map((stepKey, idx) => {
          const done = steps.some(s => s.step === stepKey);
          const current = status === 'running' && steps.length === idx;
          const meta = STEP_LABELS[stepKey];
          return (
            <div key={stepKey} style={{
              display: 'flex', alignItems: 'center', gap: '12px',
              padding: '10px 14px', borderRadius: '10px',
              background: done ? '#1a2a1a' : current ? '#1a1a2e' : '#16162a',
              border: `1px solid ${done ? '#276749' : current ? '#553c9a' : '#2d2d4e'}`,
              transition: 'all 0.3s',
            }}>
              <span style={{ fontSize: '1.1rem', opacity: done || current ? 1 : 0.3 }}>
                {done ? '✅' : current ? '⚡' : meta.icon}
              </span>
              <div style={{ flex: 1 }}>
                <div style={{
                  fontSize: '0.83rem', fontWeight: 600,
                  color: done ? '#68d391' : current ? '#a78bfa' : '#4a5568',
                }}>
                  {done ? meta.label.replace('…', ' — done') : meta.label}
                </div>
              </div>
              {current && (
                <div style={{ display: 'flex', gap: '3px' }}>
                  {[0,1,2].map(i => (
                    <div key={i} style={{
                      width: '5px', height: '5px', borderRadius: '50%', background: '#a78bfa',
                      animation: `bounce 1s ${i * 0.2}s infinite`,
                    }} />
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Briefing output */}
      {briefing && (
        <div ref={briefingRef} style={{
          background: '#1a1a2e', borderRadius: '12px', padding: '1.25rem',
          border: '1px solid #553c9a', marginTop: '0.5rem',
        }}>
          <div style={{ fontSize: '0.75rem', color: '#a78bfa', fontWeight: 700, marginBottom: '0.75rem', letterSpacing: '0.08em' }}>
            📄 GENERATED MP BRIEFING
          </div>
          <pre style={{
            fontFamily: 'system-ui, sans-serif', fontSize: '0.85rem', lineHeight: 1.7,
            color: '#e2e8f0', whiteSpace: 'pre-wrap', wordBreak: 'break-word', margin: 0,
          }}>
            {briefing}
          </pre>
          <div style={{ marginTop: '1rem', display: 'flex', gap: '8px' }}>
            <button onClick={() => navigator.clipboard.writeText(briefing)} style={{
              padding: '6px 14px', borderRadius: '8px', fontSize: '0.8rem', fontWeight: 600,
              background: '#553c9a', color: '#fff', border: 'none', cursor: 'pointer',
            }}>📋 Copy Briefing</button>
            <button onClick={() => {
              const blob = new Blob([briefing], { type: 'text/plain' });
              const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
              a.download = `mp-briefing-${constituency.replace(/\s/g,'-')}.txt`; a.click();
            }} style={{
              padding: '6px 14px', borderRadius: '8px', fontSize: '0.8rem', fontWeight: 600,
              background: '#276749', color: '#fff', border: 'none', cursor: 'pointer',
            }}>⬇️ Download</button>
            <button onClick={() => { setOpen(false); setStatus('idle'); setBriefing(''); setSteps([]); run(); }} style={{
              padding: '6px 14px', borderRadius: '8px', fontSize: '0.8rem', fontWeight: 600,
              background: '#2d2d4e', color: '#a78bfa', border: '1px solid #553c9a', cursor: 'pointer',
            }}>🔄 Re-run</button>
          </div>
        </div>
      )}

      {status === 'error' && (
        <div style={{ padding: '0.75rem 1rem', background: '#2d1515', borderRadius: '8px', color: '#fc8181', fontSize: '0.85rem' }}>
          Pipeline failed — ANTHROPIC_API_KEY may not be set. Check /health for service status.
        </div>
      )}

      <style>{`
        @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0.3} }
        @keyframes bounce { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-5px)} }
      `}</style>
    </div>
  );
}
