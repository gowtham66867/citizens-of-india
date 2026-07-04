import React, { useState, useRef, useEffect } from 'react';
import toast from 'react-hot-toast';
import { Link } from 'react-router-dom';
import api from '../api';

const LANGUAGES = [
  { code:'en', label:'English', bcp:'en-IN' },
  { code:'hi', label:'हिंदी', bcp:'hi-IN' },
  { code:'te', label:'తెలుగు', bcp:'te-IN' },
  { code:'ta', label:'தமிழ்', bcp:'ta-IN' },
  { code:'kn', label:'ಕನ್ನಡ', bcp:'kn-IN' },
  { code:'ml', label:'മലയാളം', bcp:'ml-IN' },
  { code:'mr', label:'मराठी', bcp:'mr-IN' },
  { code:'bn', label:'বাংলা', bcp:'bn-IN' },
];

const URGENCY_COLOR = { High:'#e53e3e', Medium:'#d69e2e', Low:'#38a169' };
const URGENCY_BG    = { High:'#fff5f5', Medium:'#fffff0', Low:'#f0fff4' };

const SAMPLES = [
  "The road from our village to the taluk hospital is broken for 2 km. Ambulances can't pass. 300 families affected.",
  "हमारे गाँव में पिछले 6 महीने से पानी की समस्या है। टंकी टूटी हुई है।",
  "The primary school has no functioning toilets. Girls are dropping out because of this.",
  "ఇక్కడ వీధి దీపాలు పని చేయడం లేదు. రాత్రిపూట ప్రమాదాలు జరుగుతున్నాయి.",
];

function getSupportedMimeType() {
  if (!window.MediaRecorder) return '';
  const types=['audio/webm;codecs=opus','audio/webm','audio/ogg;codecs=opus','audio/ogg','audio/mp4'];
  for(const t of types) if(MediaRecorder.isTypeSupported(t)) return t;
  return '';
}

/* ── Hero ── */
function Hero() {
  const stats=[
    {n:'8',l:'Indian Languages'},
    {n:'3',l:'Input Modes'},
    {n:'AI',l:'Ranked Priorities'},
    {n:'Live',l:'MP Dashboard'},
  ];
  return (
    <div style={{
      background:'linear-gradient(135deg,#FF9933 0%,#e07b20 40%,#138808 100%)',
      padding:'3.5rem 0 2.5rem', color:'#fff', textAlign:'center',
    }}>
      <div className="container">
        <div style={{fontSize:'3rem',marginBottom:'0.75rem'}}>🇮🇳</div>
        <h1 style={{fontSize:'clamp(1.6rem,4vw,2.6rem)',fontWeight:900,lineHeight:1.15,marginBottom:'0.75rem',letterSpacing:'-0.5px'}}>
          Your Voice Reaches Your MP
        </h1>
        <p style={{fontSize:'1.05rem',opacity:0.92,maxWidth:'540px',margin:'0 auto 2rem',lineHeight:1.6}}>
          Submit community development requests in any language — text, voice, or photo.
          AI categorises, prioritises, and routes them to your elected representative.
        </p>
        <div style={{display:'flex',justifyContent:'center',gap:'1.5rem',flexWrap:'wrap'}}>
          {stats.map(({n,l})=>(
            <div key={l} style={{textAlign:'center'}}>
              <div style={{fontSize:'1.8rem',fontWeight:900,lineHeight:1}}>{n}</div>
              <div style={{fontSize:'0.75rem',opacity:0.82,marginTop:'2px'}}>{l}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── How It Works ── */
function HowItWorks() {
  const steps=[
    {icon:'🗣️',title:'You speak or type',desc:'In any of 8 Indian languages. Voice, text, or photo of the problem.'},
    {icon:'🤖',title:'AI understands',desc:'Gemini 2.0 Flash transcribes, categorises, and assesses urgency instantly.'},
    {icon:'📊',title:'MP sees priorities',desc:'Your MP sees AI-ranked development priorities on a live constituency dashboard.'},
  ];
  return (
    <div style={{background:'#fff',padding:'2.5rem 0',borderBottom:'1px solid #e2e8f0'}}>
      <div className="container">
        <div style={{textAlign:'center',marginBottom:'1.75rem'}}>
          <h2 style={{fontSize:'1.3rem',fontWeight:800,color:'#1a202c'}}>How It Works</h2>
          <p style={{color:'#718096',fontSize:'0.9rem',marginTop:'0.25rem'}}>Three steps from your phone to your MP's desk</p>
        </div>
        <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(220px,1fr))',gap:'1.25rem'}}>
          {steps.map(({icon,title,desc},i)=>(
            <div key={i} style={{textAlign:'center',padding:'1.5rem 1rem'}}>
              <div style={{
                width:'64px',height:'64px',borderRadius:'50%',margin:'0 auto 1rem',
                background:'linear-gradient(135deg,#fff3e0,#ffe0b2)',
                display:'flex',alignItems:'center',justifyContent:'center',fontSize:'2rem',
                boxShadow:'0 4px 16px rgba(255,153,51,0.2)',
              }}>{icon}</div>
              <div style={{
                display:'inline-block',background:'#FF9933',color:'#fff',
                borderRadius:'20px',padding:'2px 12px',fontSize:'0.72rem',fontWeight:700,
                marginBottom:'0.5rem',letterSpacing:'0.05em',
              }}>STEP {i+1}</div>
              <h3 style={{fontSize:'1rem',fontWeight:700,marginBottom:'0.4rem',color:'#1a202c'}}>{title}</h3>
              <p style={{fontSize:'0.88rem',color:'#718096',lineHeight:1.6}}>{desc}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ── Success card ── */
function SuccessCard({result,onReset}) {
  const uc = URGENCY_COLOR[result.urgency] || '#718096';
  const ub = URGENCY_BG[result.urgency]   || '#f7fafc';
  const copied = () => {
    navigator.clipboard.writeText(`Submission ID: ${result.id}\nTheme: ${result.theme}\nSummary: ${result.summary}`);
    toast.success('Copied to clipboard');
  };
  return (
    <div className="scale-in" style={{
      border:`2px solid ${uc}`,borderRadius:'16px',background:ub,padding:'2rem',
      boxShadow:`0 8px 32px ${uc}22`,
    }}>
      <div style={{textAlign:'center',marginBottom:'1.25rem'}}>
        <div style={{fontSize:'3rem',animation:'popIn 0.5s cubic-bezier(.34,1.56,.64,1) both'}}>✅</div>
        <h2 style={{fontSize:'1.2rem',fontWeight:800,color:'#1a202c',marginTop:'0.5rem'}}>Submission Received!</h2>
        <p style={{fontSize:'0.88rem',color:'#718096',marginTop:'0.25rem'}}>Your issue has been analysed and sent to the MP dashboard.</p>
      </div>

      <div style={{
        background:'#fff',borderRadius:'12px',padding:'1.25rem',marginBottom:'1rem',
        border:'1px solid #e2e8f0',display:'grid',gap:'0.6rem',fontSize:'0.9rem',
      }}>
        <div style={{display:'flex',justifyContent:'space-between',alignItems:'center'}}>
          <span style={{color:'#718096'}}>Urgency</span>
          <span style={{
            background:uc,color:'#fff',borderRadius:'12px',
            padding:'2px 14px',fontSize:'0.8rem',fontWeight:700,
          }}>{result.urgency}</span>
        </div>
        <div><span style={{color:'#718096'}}>Theme: </span><strong>{result.theme}</strong></div>
        <div><span style={{color:'#718096'}}>Summary: </span>{result.summary}</div>
        {result.transcription && (
          <div style={{borderTop:'1px solid #e2e8f0',paddingTop:'0.6rem'}}>
            <span style={{color:'#718096'}}>Transcribed: </span><em>"{result.transcription}"</em>
          </div>
        )}
        {result.location_hint && (
          <div><span style={{color:'#718096'}}>Location: </span>{result.location_hint}</div>
        )}
        {(result.keywords||[]).length>0 && (
          <div style={{display:'flex',flexWrap:'wrap',gap:'4px',marginTop:'0.25rem'}}>
            {result.keywords.map(k=>(
              <span key={k} style={{
                background:'#e2e8f0',borderRadius:'12px',padding:'2px 10px',fontSize:'0.75rem',color:'#4a5568',
              }}>{k}</span>
            ))}
          </div>
        )}
      </div>

      <div style={{
        background:'#f7fafc',borderRadius:'10px',padding:'0.75rem 1rem',
        fontFamily:'monospace',fontSize:'0.8rem',color:'#4a5568',
        marginBottom:'1.25rem',display:'flex',justifyContent:'space-between',alignItems:'center',
      }}>
        <span>ID: <strong>{result.id}</strong></span>
        <button onClick={copied} style={{
          background:'none',color:'#FF9933',fontSize:'0.78rem',fontWeight:600,cursor:'pointer',
        }}>📋 Copy</button>
      </div>

      <div style={{display:'flex',gap:'0.75rem',flexWrap:'wrap'}}>
        <button onClick={onReset} style={{
          flex:1,padding:'0.7rem',borderRadius:'10px',fontWeight:700,fontSize:'0.9rem',
          background:'#FF9933',color:'#fff',
        }}>➕ Submit Another</button>
        <Link to="/dashboard" style={{
          flex:1,padding:'0.7rem',borderRadius:'10px',fontWeight:700,fontSize:'0.9rem',
          background:'#138808',color:'#fff',textAlign:'center',textDecoration:'none',display:'block',
        }}>📊 View Dashboard</Link>
      </div>
    </div>
  );
}

/* ── Main component ── */
export default function CitizenSubmission() {
  const [mode,setMode]=useState('text');
  const [text,setText]=useState('');
  const [language,setLanguage]=useState('en');
  const [constituency,setConstituency]=useState('');
  const [loading,setLoading]=useState(false);
  const [result,setResult]=useState(null);
  const [recording,setRecording]=useState(false);
  const [recSecs,setRecSecs]=useState(0);
  const [micError,setMicError]=useState('');
  const [photoFile,setPhotoFile]=useState(null);
  const [photoPreview,setPhotoPreview]=useState(null);
  const mediaRef=useRef(null);
  const streamRef=useRef(null);
  const chunksRef=useRef([]);
  const timerRef=useRef(null);
  const autoStopRef=useRef(null);
  const formRef=useRef(null);

  // Scroll to top when page loads so Hero is visible
  useEffect(()=>{ window.scrollTo({top:0,behavior:'instant'}); },[]);

  useEffect(()=>{
    if(recording){
      setRecSecs(0);
      timerRef.current=setInterval(()=>setRecSecs(s=>s+1),1000);
      autoStopRef.current=setTimeout(()=>stopRecording(),30000);
    } else {
      clearInterval(timerRef.current);
      clearTimeout(autoStopRef.current);
    }
    return ()=>{
      clearInterval(timerRef.current);
      clearTimeout(autoStopRef.current);
    };
  },[recording]);

  const handleTextSubmit=async()=>{
    if(!text.trim()) return toast.error('Please enter your issue');
    setLoading(true);
    try {
      const res=await api.post('/submissions/text',{text,language,constituency:constituency||'General'});
      setResult(res.data);
      toast.success('Submitted!');
    } catch(e){ toast.error(e.response?.data?.detail||'Submission failed'); }
    finally{ setLoading(false); }
  };

  const submitVoiceBlob=async(blob, filename='recording.webm')=>{
    if(blob.size<1000){
      toast.error('Recording too short');
      return;
    }
    const fd=new FormData();
    fd.append('audio',blob,filename);
    fd.append('language',language);
    fd.append('constituency',constituency||'General');
    setLoading(true);
    try {
      const res=await api.post('/submissions/voice',fd,{timeout:60000});
      setResult(res.data);
      setMicError('');
      toast.success('Voice analysed!');
    } catch(e){
      if(!e.response){
        toast.error('Connection lost — check your internet and try again');
      } else {
        const d=e.response?.data?.detail||'Could not transcribe — speak clearly and retry';
        toast.error(d.length>80?'Could not transcribe — speak clearly and retry':d);
      }
    } finally{ setLoading(false); }
  };

  const startRecording=async()=>{
    setMicError('');
    if(!navigator.mediaDevices?.getUserMedia){
      const msg='Microphone recording needs HTTPS or localhost';
      setMicError(msg);
      toast.error(msg);
      return;
    }
    if(!window.MediaRecorder){
      const msg='Audio recording is not supported in this browser';
      setMicError(msg);
      toast.error(msg);
      return;
    }
    try {
      const stream=await navigator.mediaDevices.getUserMedia({audio:true});
      streamRef.current=stream;
      const mimeType=getSupportedMimeType();
      const mr=mimeType?new MediaRecorder(stream,{mimeType}):new MediaRecorder(stream);
      chunksRef.current=[];
      mr.ondataavailable=e=>{ if(e.data.size>0) chunksRef.current.push(e.data); };
      mr.onstop=async()=>{
        const blob=new Blob(chunksRef.current,{type:mr.mimeType||'audio/webm'});
        stream.getTracks().forEach(t=>t.stop());
        streamRef.current=null;
        await submitVoiceBlob(blob);
      };
      mr.start(100); mediaRef.current=mr; setRecording(true);
    } catch(err){
      streamRef.current?.getTracks().forEach(t=>t.stop());
      streamRef.current=null;
      const msg=err.name==='NotAllowedError'
        ? 'Microphone permission denied. Click the tune icon in the address bar, allow Microphone, then reload.'
        : 'Could not start recording';
      setMicError(msg);
      toast.error(msg);
    }
  };

  const stopRecording=()=>{
    if(mediaRef.current?.state==='recording') mediaRef.current.stop();
    else streamRef.current?.getTracks().forEach(t=>t.stop());
    setRecording(false);
  };
  const fmtSecs=s=>`${Math.floor(s/60).toString().padStart(2,'0')}:${(s%60).toString().padStart(2,'0')}`;

  const handlePhotoChange=e=>{
    const file=e.target.files[0]; if(!file) return;
    setPhotoFile(file); setPhotoPreview(URL.createObjectURL(file));
  };

  const handleAudioUpload=async(e)=>{
    const file=e.target.files[0]; if(!file) return;
    await submitVoiceBlob(file,file.name||'voice-upload.webm');
    e.target.value='';
  };

  const handlePhotoSubmit=async()=>{
    if(!photoFile) return toast.error('Please select a photo');
    const fd=new FormData();
    fd.append('photo',photoFile); fd.append('description',text); fd.append('constituency',constituency||'General');
    setLoading(true);
    try {
      const res=await api.post('/submissions/photo',fd);
      setResult(res.data); toast.success('Photo analysed!');
    } catch(e){ toast.error(e.response?.data?.detail||'Photo submission failed'); }
    finally{ setLoading(false); }
  };

  const reset=()=>{ setResult(null); setText(''); setPhotoFile(null); setPhotoPreview(null); };
  const fillSample=()=>setText(SAMPLES[Math.floor(Math.random()*SAMPLES.length)]);

  return (
    <div style={{minHeight:'calc(100vh - 62px)',background:'#f8f9fa'}}>
      <Hero/>
      <HowItWorks/>

      {/* Form section */}
      <div style={{padding:'2.5rem 0'}}>
        <div className="container" style={{maxWidth:'700px'}} ref={formRef}>
          {result ? (
            <SuccessCard result={result} onReset={reset}/>
          ) : (
            <div className="card fade-in-up" style={{padding:'2rem'}}>
              <h2 style={{fontSize:'1.15rem',fontWeight:800,color:'#1a202c',marginBottom:'1.5rem',display:'flex',alignItems:'center',gap:'8px'}}>
                📝 Submit Your Issue
              </h2>

              {/* Constituency */}
              <div style={{marginBottom:'1.25rem'}}>
                <label style={{display:'block',fontSize:'0.82rem',fontWeight:700,color:'#4a5568',marginBottom:'0.4rem',textTransform:'uppercase',letterSpacing:'0.05em'}}>
                  Your Constituency
                </label>
                <input value={constituency} onChange={e=>setConstituency(e.target.value)}
                  placeholder="e.g. Narasaraopet, Kodathi, Mumbai North…"/>
              </div>

              {/* Mode tabs */}
              <div style={{display:'flex',gap:'0.5rem',marginBottom:'1.25rem'}}>
                {[{id:'text',icon:'✍️',label:'Text'},{id:'voice',icon:'🎙️',label:'Voice'},{id:'photo',icon:'📷',label:'Photo'}].map(m=>(
                  <button key={m.id} onClick={()=>{setMode(m.id);setResult(null);}} style={{
                    flex:1,padding:'0.65rem',borderRadius:'10px',fontSize:'0.9rem',fontWeight:700,
                    background:mode===m.id?'linear-gradient(135deg,#FF9933,#e07b20)':'#f7fafc',
                    color:mode===m.id?'#fff':'#4a5568',
                    border:mode===m.id?'none':'1.5px solid #e2e8f0',
                    transition:'all 0.2s',
                    boxShadow:mode===m.id?'0 4px 12px rgba(255,153,51,0.35)':'none',
                  }}>{m.icon} {m.label}</button>
                ))}
              </div>

              {/* Language */}
              <div style={{marginBottom:'1.25rem'}}>
                <label style={{display:'block',fontSize:'0.82rem',fontWeight:700,color:'#4a5568',marginBottom:'0.4rem',textTransform:'uppercase',letterSpacing:'0.05em'}}>
                  Language
                </label>
                <select value={language} onChange={e=>setLanguage(e.target.value)}>
                  {LANGUAGES.map(l=><option key={l.code} value={l.code}>{l.label}</option>)}
                </select>
              </div>

              {/* TEXT mode */}
              {mode==='text' && (
                <div>
                  <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:'0.4rem'}}>
                    <label style={{fontSize:'0.82rem',fontWeight:700,color:'#4a5568',textTransform:'uppercase',letterSpacing:'0.05em'}}>Your Issue</label>
                    <button onClick={fillSample} style={{fontSize:'0.8rem',color:'#FF9933',background:'none',textDecoration:'underline',cursor:'pointer'}}>
                      Try a sample ✨
                    </button>
                  </div>
                  <textarea value={text} onChange={e=>setText(e.target.value)}
                    placeholder="Describe the issue your community faces — road, water, school, health…"
                    rows={5}/>
                  <div style={{display:'flex',justifyContent:'flex-end',marginTop:'4px'}}>
                    <span style={{fontSize:'0.75rem',color:text.length>500?'#e53e3e':'#a0aec0'}}>{text.length} chars</span>
                  </div>
                  <button onClick={handleTextSubmit} disabled={loading} style={{
                    marginTop:'1rem',width:'100%',padding:'0.85rem',
                    background:loading?'#e2e8f0':'linear-gradient(135deg,#FF9933,#e07b20)',
                    color:loading?'#a0aec0':'#fff',borderRadius:'12px',fontSize:'1rem',fontWeight:800,
                    boxShadow:loading?'none':'0 4px 16px rgba(255,153,51,0.4)',
                    transition:'all 0.2s',cursor:loading?'not-allowed':'pointer',letterSpacing:'0.02em',
                  }}>
                    {loading?'Analysing with Gemini AI…':'🚀 Submit to MP'}
                  </button>
                </div>
              )}

              {/* VOICE mode */}
              {mode==='voice' && (
                <div style={{textAlign:'center',padding:'1.5rem 0'}}>
                  <button
                    onClick={recording?stopRecording:startRecording}
                    disabled={loading}
                    style={{
                      width:'120px',height:'120px',borderRadius:'50%',
                      background:loading?'#e2e8f0':recording?'linear-gradient(135deg,#fed7d7,#feb2b2)':'linear-gradient(135deg,#FF9933,#e07b20)',
                      border:`4px solid ${recording?'#e53e3e':loading?'#cbd5e0':'#FF9933'}`,
                      display:'flex',flexDirection:'column',alignItems:'center',justifyContent:'center',
                      fontSize:'2.8rem',cursor:loading?'not-allowed':'pointer',
                      boxShadow:recording?'0 0 0 8px rgba(229,62,62,0.2)':'0 6px 24px rgba(255,153,51,0.4)',
                      animation:recording?'pulse 1.5s infinite':'none',
                      transition:'all 0.2s',margin:'0 auto',
                    }}
                  >
                    {loading?'⏳':recording?'⏹️':'🎙️'}
                  </button>

                  {recording && (
                    <div style={{marginTop:'1rem',display:'flex',alignItems:'center',justifyContent:'center',gap:'8px'}}>
                      <span style={{display:'inline-block',width:'10px',height:'10px',borderRadius:'50%',background:'#e53e3e',animation:'blink 1s infinite'}}/>
                      <span style={{color:'#e53e3e',fontWeight:700,fontSize:'1.2rem',fontFamily:'monospace'}}>{fmtSecs(recSecs)}</span>
                      <span style={{color:'#e53e3e',fontSize:'0.9rem'}}>Recording…</span>
                    </div>
                  )}
                  {!recording&&!loading&&<p style={{color:'#718096',fontSize:'0.9rem',marginTop:'1rem'}}>Tap the mic to start recording</p>}
                  {loading&&<div style={{marginTop:'1rem'}}><p style={{color:'#FF9933',fontWeight:700}}>Transcribing with Cloud Speech-to-Text…</p><p style={{color:'#718096',fontSize:'0.82rem'}}>This may take a few seconds</p></div>}

                  {micError && !loading && (
                    <div style={{
                      margin:'1rem auto 0',maxWidth:'430px',padding:'0.85rem 1rem',
                      background:'#fff5f5',border:'1px solid #feb2b2',borderRadius:'10px',
                      color:'#9b2c2c',fontSize:'0.84rem',textAlign:'left',lineHeight:1.55,
                    }}>
                      <strong>Microphone is blocked.</strong>
                      <div>Click the tune icon beside the address bar, set Microphone to Allow, then reload this page.</div>
                    </div>
                  )}

                  {!recording && !loading && (
                    <label style={{
                      display:'inline-flex',alignItems:'center',justifyContent:'center',
                      marginTop:'1rem',padding:'0.62rem 1rem',borderRadius:'10px',
                      border:'1.5px solid #e2e8f0',background:'#fff',color:'#4a5568',
                      fontSize:'0.86rem',fontWeight:700,cursor:'pointer',
                    }}>
                      Upload audio instead
                      <input type="file" accept="audio/*,.webm,.ogg,.m4a,.mp3,.wav" onChange={handleAudioUpload} style={{display:'none'}}/>
                    </label>
                  )}

                  <div style={{
                    marginTop:'1.5rem',padding:'0.85rem 1rem',background:'#fffbeb',
                    borderRadius:'10px',fontSize:'0.83rem',color:'#92400e',textAlign:'left',
                    border:'1px solid #fde68a',
                  }}>
                    💡 Speak clearly for 3–30 seconds in your chosen language.
                    {recording&&<strong> Tap ⏹️ to stop and submit.</strong>}
                  </div>

                  <div style={{marginTop:'1rem',display:'flex',justifyContent:'center',gap:'0.5rem',flexWrap:'wrap'}}>
                    {LANGUAGES.map(l=>(
                      <button key={l.code} onClick={()=>setLanguage(l.code)} style={{
                        padding:'3px 12px',borderRadius:'20px',fontSize:'0.78rem',fontWeight:600,
                        background:language===l.code?'#FF9933':'#f0f4f8',
                        color:language===l.code?'#fff':'#4a5568',
                        border:language===l.code?'none':'1px solid #e2e8f0',cursor:'pointer',
                      }}>{l.label}</button>
                    ))}
                  </div>
                </div>
              )}

              {/* PHOTO mode */}
              {mode==='photo' && (
                <div>
                  <label style={{
                    display:'block',border:'2px dashed #e2e8f0',borderRadius:'14px',
                    padding:'2.5rem',textAlign:'center',cursor:'pointer',marginBottom:'1rem',
                    background:'#fafafa',transition:'border-color 0.2s',
                  }}>
                    {photoPreview
                      ? <div>
                          <img src={photoPreview} alt="preview" style={{maxHeight:'220px',borderRadius:'10px',objectFit:'cover',boxShadow:'0 4px 16px rgba(0,0,0,0.1)'}}/>
                          <p style={{fontSize:'0.82rem',color:'#718096',marginTop:'0.5rem'}}>Tap to change photo</p>
                        </div>
                      : <div>
                          <div style={{fontSize:'3rem',marginBottom:'0.5rem'}}>📷</div>
                          <div style={{color:'#4a5568',fontWeight:600,marginBottom:'0.25rem'}}>Upload a photo of the issue</div>
                          <div style={{color:'#a0aec0',fontSize:'0.82rem'}}>JPG, PNG up to 10MB</div>
                        </div>
                    }
                    <input type="file" accept="image/*" onChange={handlePhotoChange} style={{display:'none'}}/>
                  </label>
                  <textarea value={text} onChange={e=>setText(e.target.value)}
                    placeholder="Add a brief description of what's wrong (optional)" rows={3}/>
                  <button onClick={handlePhotoSubmit} disabled={loading||!photoFile} style={{
                    marginTop:'1rem',width:'100%',padding:'0.85rem',
                    background:loading||!photoFile?'#e2e8f0':'linear-gradient(135deg,#FF9933,#e07b20)',
                    color:loading||!photoFile?'#a0aec0':'#fff',
                    borderRadius:'12px',fontSize:'1rem',fontWeight:800,
                    cursor:loading||!photoFile?'not-allowed':'pointer',
                  }}>
                    {loading?'Analysing photo with Gemini Vision…':'📸 Submit Photo'}
                  </button>
                </div>
              )}
            </div>
          )}

          {/* Channels info strip */}
          {!result && (
            <div style={{marginTop:'1rem',padding:'0.85rem 1.25rem',background:'#fff',borderRadius:'12px',display:'flex',alignItems:'center',gap:'0.75rem',flexWrap:'wrap',boxShadow:'0 1px 4px rgba(0,0,0,0.06)'}}>
              <span style={{fontSize:'0.8rem',color:'#718096',fontWeight:600}}>Also available via:</span>
              {['📱 WhatsApp','💬 SMS','📞 Voice IVR'].map(c=>(
                <span key={c} style={{fontSize:'0.8rem',padding:'3px 12px',borderRadius:'20px',background:'#f0f4f8',color:'#4a5568',fontWeight:600}}>{c}</span>
              ))}
              <span style={{fontSize:'0.78rem',color:'#a0aec0',marginLeft:'auto'}}>Powered by Google Cloud</span>
            </div>
          )}
        </div>
      </div>

      <style>{`
        @keyframes popIn{0%{opacity:0;transform:scale(0.5) rotate(-10deg)}70%{transform:scale(1.1) rotate(3deg)}100%{opacity:1;transform:scale(1) rotate(0)}}
      `}</style>
    </div>
  );
}
