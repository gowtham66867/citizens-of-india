import React, { useState, useRef } from 'react';
import toast from 'react-hot-toast';
import api from '../api';

const LANGUAGES = [
  { code: 'en', label: 'English' },
  { code: 'hi', label: 'हिंदी' },
  { code: 'te', label: 'తెలుగు' },
  { code: 'ta', label: 'தமிழ்' },
  { code: 'kn', label: 'ಕನ್ನಡ' },
  { code: 'ml', label: 'മലയാളം' },
  { code: 'mr', label: 'मराठी' },
  { code: 'bn', label: 'বাংলা' },
];

const URGENCY_COLOR = { High: '#e53e3e', Medium: '#d69e2e', Low: '#38a169' };

const SAMPLE_SUBMISSIONS = [
  "The road from our village to the taluk hospital is broken for 2 km. Ambulances can't pass. 300 families affected.",
  "हमारे गाँव में पिछले 6 महीने से पानी की समस्या है। टंकी टूटी हुई है।",
  "The primary school has no functioning toilets. Girls are dropping out because of this.",
];

function ResultCard({ result }) {
  if (!result) return null;
  const urgencyColor = URGENCY_COLOR[result.urgency] || '#718096';
  return (
    <div className="card" style={{ marginTop: '1.5rem', borderLeft: `4px solid ${urgencyColor}` }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '0.75rem' }}>
        <h3 style={{ color: '#2d3748', fontSize: '1rem' }}>Submission Analyzed ✓</h3>
        <span style={{
          background: urgencyColor, color: '#fff', borderRadius: '12px',
          padding: '2px 12px', fontSize: '0.8rem', fontWeight: 600
        }}>{result.urgency} Urgency</span>
      </div>
      <div style={{ display: 'grid', gap: '0.5rem', fontSize: '0.9rem' }}>
        <div><span style={{ color: '#718096' }}>Theme: </span><strong>{result.theme}</strong></div>
        <div><span style={{ color: '#718096' }}>Summary: </span>{result.summary}</div>
        <div><span style={{ color: '#718096' }}>Keywords: </span>{(result.keywords || []).join(', ')}</div>
        {result.location_hint && (
          <div><span style={{ color: '#718096' }}>Location: </span>{result.location_hint}</div>
        )}
      </div>
      <div style={{ marginTop: '0.75rem', padding: '0.5rem 0.75rem', background: '#f7fafc', borderRadius: '8px', fontSize: '0.82rem', color: '#4a5568' }}>
        Your submission ID: <code style={{ fontFamily: 'monospace' }}>{result.id}</code>
      </div>
    </div>
  );
}

export default function CitizenSubmission() {
  const [mode, setMode] = useState('text'); // text | voice | photo
  const [text, setText] = useState('');
  const [language, setLanguage] = useState('en');
  const [constituency, setConstituency] = useState('Demo Constituency');
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [recording, setRecording] = useState(false);
  const [photoFile, setPhotoFile] = useState(null);
  const [photoPreview, setPhotoPreview] = useState(null);
  const mediaRef = useRef(null);
  const chunksRef = useRef([]);

  const handleTextSubmit = async () => {
    if (!text.trim()) return toast.error('Please enter your issue');
    setLoading(true);
    try {
      const res = await api.post('/submissions/text', { text, language, constituency });
      setResult(res.data);
      toast.success('Submitted successfully!');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Submission failed');
    } finally {
      setLoading(false);
    }
  };

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
      chunksRef.current = [];
      mr.ondataavailable = e => chunksRef.current.push(e.data);
      mr.onstop = async () => {
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
        const fd = new FormData();
        fd.append('audio', blob, 'recording.webm');
        fd.append('language', language);
        fd.append('constituency', constituency);
        setLoading(true);
        try {
          const res = await api.post('/submissions/voice', fd);
          setResult(res.data);
          toast.success('Voice submission analyzed!');
        } catch (e) {
          toast.error('Voice upload failed');
        } finally {
          setLoading(false);
        }
        stream.getTracks().forEach(t => t.stop());
      };
      mr.start();
      mediaRef.current = mr;
      setRecording(true);
    } catch {
      toast.error('Microphone access denied');
    }
  };

  const stopRecording = () => {
    mediaRef.current?.stop();
    setRecording(false);
  };

  const handlePhotoChange = e => {
    const file = e.target.files[0];
    if (!file) return;
    setPhotoFile(file);
    setPhotoPreview(URL.createObjectURL(file));
  };

  const handlePhotoSubmit = async () => {
    if (!photoFile) return toast.error('Please select a photo');
    const fd = new FormData();
    fd.append('photo', photoFile);
    fd.append('description', text);
    fd.append('constituency', constituency);
    setLoading(true);
    try {
      const res = await api.post('/submissions/photo', fd);
      setResult(res.data);
      toast.success('Photo analyzed!');
    } catch (e) {
      toast.error('Photo submission failed');
    } finally {
      setLoading(false);
    }
  };

  const fillSample = () => setText(SAMPLE_SUBMISSIONS[Math.floor(Math.random() * SAMPLE_SUBMISSIONS.length)]);

  return (
    <div style={{ padding: '2rem 0', minHeight: 'calc(100vh - 60px)' }}>
      <div className="container" style={{ maxWidth: '680px' }}>
        {/* Hero */}
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <h1 style={{ fontSize: '1.8rem', fontWeight: 700, color: '#1a202c', marginBottom: '0.5rem' }}>
            Share Your Development Request
          </h1>
          <p style={{ color: '#718096', fontSize: '1rem' }}>
            Tell your MP what your community needs — in any language, any format
          </p>
        </div>

        <div className="card">
          {/* Constituency */}
          <div style={{ marginBottom: '1.25rem' }}>
            <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: '#4a5568', marginBottom: '0.4rem' }}>
              Your Constituency
            </label>
            <input value={constituency} onChange={e => setConstituency(e.target.value)} placeholder="e.g. Narasaraopet" />
          </div>

          {/* Mode tabs */}
          <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.25rem' }}>
            {[
              { id: 'text', icon: '✍️', label: 'Text' },
              { id: 'voice', icon: '🎙️', label: 'Voice' },
              { id: 'photo', icon: '📷', label: 'Photo' },
            ].map(m => (
              <button key={m.id} onClick={() => { setMode(m.id); setResult(null); }} style={{
                flex: 1, padding: '0.6rem', borderRadius: '8px', fontSize: '0.9rem', fontWeight: 600,
                background: mode === m.id ? '#FF9933' : '#f7fafc',
                color: mode === m.id ? '#fff' : '#4a5568',
                border: mode === m.id ? 'none' : '1px solid #e2e8f0',
                transition: 'all 0.2s',
              }}>
                {m.icon} {m.label}
              </button>
            ))}
          </div>

          {/* Language selector */}
          <div style={{ marginBottom: '1.25rem' }}>
            <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, color: '#4a5568', marginBottom: '0.4rem' }}>
              Language
            </label>
            <select value={language} onChange={e => setLanguage(e.target.value)}>
              {LANGUAGES.map(l => <option key={l.code} value={l.code}>{l.label}</option>)}
            </select>
          </div>

          {/* Text mode */}
          {mode === 'text' && (
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.4rem' }}>
                <label style={{ fontSize: '0.85rem', fontWeight: 600, color: '#4a5568' }}>Your Issue</label>
                <button onClick={fillSample} style={{
                  fontSize: '0.78rem', color: '#FF9933', background: 'none', textDecoration: 'underline'
                }}>Try a sample</button>
              </div>
              <textarea
                value={text}
                onChange={e => setText(e.target.value)}
                placeholder="Describe the issue your community faces — road, water, school, health..."
                rows={5}
              />
              <button onClick={handleTextSubmit} disabled={loading} style={{
                marginTop: '1rem', width: '100%', padding: '0.75rem',
                background: loading ? '#e2e8f0' : '#FF9933', color: loading ? '#a0aec0' : '#fff',
                borderRadius: '8px', fontSize: '1rem', fontWeight: 700, transition: 'background 0.2s',
              }}>
                {loading ? 'Analyzing...' : 'Submit to MP'}
              </button>
            </div>
          )}

          {/* Voice mode */}
          {mode === 'voice' && (
            <div style={{ textAlign: 'center', padding: '1rem 0' }}>
              <div style={{
                width: '100px', height: '100px', borderRadius: '50%', margin: '0 auto 1rem',
                background: recording ? '#fed7d7' : '#f7fafc',
                border: `3px solid ${recording ? '#e53e3e' : '#e2e8f0'}`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '2.5rem', cursor: 'pointer',
                animation: recording ? 'pulse 1.5s infinite' : 'none',
              }} onClick={recording ? stopRecording : startRecording}>
                🎙️
              </div>
              <p style={{ color: '#718096', fontSize: '0.9rem', marginBottom: '1rem' }}>
                {recording ? 'Recording... tap to stop' : 'Tap the mic to start recording'}
              </p>
              {loading && <p style={{ color: '#FF9933' }}>Transcribing & analyzing...</p>}
            </div>
          )}

          {/* Photo mode */}
          {mode === 'photo' && (
            <div>
              <label style={{
                display: 'block', border: '2px dashed #e2e8f0', borderRadius: '12px',
                padding: '2rem', textAlign: 'center', cursor: 'pointer', marginBottom: '1rem',
              }}>
                {photoPreview
                  ? <img src={photoPreview} alt="preview" style={{ maxHeight: '200px', borderRadius: '8px', objectFit: 'cover' }} />
                  : <div><div style={{ fontSize: '2rem', marginBottom: '0.5rem' }}>📷</div>
                    <span style={{ color: '#718096', fontSize: '0.9rem' }}>Tap to upload a photo of the issue</span></div>
                }
                <input type="file" accept="image/*" onChange={handlePhotoChange} style={{ display: 'none' }} />
              </label>
              <textarea value={text} onChange={e => setText(e.target.value)} placeholder="Add a brief description (optional)" rows={3} />
              <button onClick={handlePhotoSubmit} disabled={loading || !photoFile} style={{
                marginTop: '1rem', width: '100%', padding: '0.75rem',
                background: loading || !photoFile ? '#e2e8f0' : '#FF9933',
                color: loading || !photoFile ? '#a0aec0' : '#fff',
                borderRadius: '8px', fontSize: '1rem', fontWeight: 700,
              }}>
                {loading ? 'Analyzing photo...' : 'Submit Photo'}
              </button>
            </div>
          )}
        </div>

        <ResultCard result={result} />
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { box-shadow: 0 0 0 0 rgba(229, 62, 62, 0.4); }
          50% { box-shadow: 0 0 0 12px rgba(229, 62, 62, 0); }
        }
      `}</style>
    </div>
  );
}
