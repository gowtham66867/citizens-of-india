import React, { useState, useEffect } from 'react';
import { HashRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import CitizenSubmission from './pages/CitizenSubmission';
import MPDashboard from './pages/MPDashboard';
import api from './api';

const API_BASE = process.env.REACT_APP_API_BASE || '';

function Nav({ healthy }) {
  const { pathname } = useLocation();
  return (
    <nav style={{
      background:'linear-gradient(135deg,#FF9933 0%,#e07b20 45%,#138808 100%)',
      boxShadow:'0 2px 12px rgba(0,0,0,0.18)',
      position:'sticky',top:0,zIndex:100,
    }}>
      <div className="container" style={{display:'flex',alignItems:'center',gap:'1.5rem',height:'62px'}}>
        <Link to="/" style={{display:'flex',alignItems:'center',gap:'10px',textDecoration:'none',flexShrink:0}}>
          <span style={{fontSize:'1.6rem'}}>🇮🇳</span>
          <div>
            <div style={{color:'#fff',fontWeight:800,fontSize:'1.05rem',letterSpacing:'-0.3px',lineHeight:1.1}}>Citizens of India</div>
            <div style={{color:'rgba(255,255,255,0.75)',fontSize:'0.62rem',letterSpacing:'0.08em'}}>PEOPLE'S PRIORITIES PLATFORM</div>
          </div>
        </Link>
        <div style={{display:'flex',gap:'0.4rem',marginLeft:'auto',alignItems:'center'}}>
          {[
            {to:'/',label:'Submit Issue',icon:'✍️'},
            {to:'/dashboard',label:'MP Dashboard',icon:'📊'},
          ].map(({to,label,icon})=>(
            <Link key={to} to={to} style={{
              color:pathname===to?'#FF9933':'#fff',
              textDecoration:'none',padding:'6px 16px',borderRadius:'20px',
              fontSize:'0.88rem',fontWeight:600,
              background:pathname===to?'rgba(255,255,255,0.95)':'rgba(255,255,255,0.12)',
              transition:'all 0.2s',display:'flex',alignItems:'center',gap:'6px',
            }}><span>{icon}</span>{label}</Link>
          ))}
          <a href={`${API_BASE}/docs`} target="_blank" rel="noreferrer" style={{
            color:'rgba(255,255,255,0.85)',fontSize:'0.8rem',textDecoration:'none',
            padding:'4px 12px',borderRadius:'20px',border:'1px solid rgba(255,255,255,0.3)',
            display:'flex',alignItems:'center',gap:'5px',
          }}>
            <span style={{
              display:'inline-block',width:'7px',height:'7px',borderRadius:'50%',
              background:healthy?'#4ade80':'#f87171',
              boxShadow:healthy?'0 0 6px #4ade80':'none',
            }}/>
            API {healthy?'Live':'Down'}
          </a>
        </div>
      </div>
    </nav>
  );
}

function Footer() {
  return (
    <footer style={{marginTop:'4rem',background:'#1a202c',color:'#a0aec0',padding:'2.5rem 0 1.5rem'}}>
      <div className="container">
        <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(200px,1fr))',gap:'2rem',marginBottom:'2rem'}}>
          <div>
            <div style={{display:'flex',alignItems:'center',gap:'8px',marginBottom:'0.75rem'}}>
              <span style={{fontSize:'1.3rem'}}>🇮🇳</span>
              <span style={{color:'#fff',fontWeight:700,fontSize:'1rem'}}>Citizens of India</span>
            </div>
            <p style={{fontSize:'0.85rem',lineHeight:1.7}}>
              AI-powered civic platform connecting 1.4 billion citizens with their elected representatives — in any language, any format.
            </p>
          </div>
          <div>
            <div style={{color:'#fff',fontWeight:600,marginBottom:'0.75rem',fontSize:'0.82rem',letterSpacing:'0.06em'}}>BUILT WITH</div>
            {['Google Cloud Run','Gemini 2.0 Flash','Cloud Speech-to-Text','FastAPI + SQLite','React + Recharts'].map(t=>(
              <div key={t} style={{fontSize:'0.82rem',marginBottom:'0.3rem'}}>▸ {t}</div>
            ))}
          </div>
          <div>
            <div style={{color:'#fff',fontWeight:600,marginBottom:'0.75rem',fontSize:'0.82rem',letterSpacing:'0.06em'}}>LINKS</div>
            {[
              {label:'Live Demo',href:'https://gowtham66867.github.io/citizens-of-india'},
              {label:'GitHub Repo',href:'https://github.com/gowtham66867/citizens-of-india'},
              {label:'API Docs',href:`${API_BASE}/docs`},
            ].map(({label,href})=>(
              <div key={label} style={{marginBottom:'0.3rem'}}>
                <a href={href} target="_blank" rel="noreferrer" style={{color:'#FF9933',fontSize:'0.82rem',textDecoration:'none'}}>↗ {label}</a>
              </div>
            ))}
          </div>
        </div>
        <div style={{borderTop:'1px solid #2d3748',paddingTop:'1rem',display:'flex',justifyContent:'space-between',flexWrap:'wrap',gap:'0.5rem',fontSize:'0.78rem'}}>
          <span>Built for Google Cloud AI Hackathon 2025</span>
          <span>gowtham66866@gmail.com</span>
        </div>
      </div>
    </footer>
  );
}

function AppInner() {
  const [healthy,setHealthy]=useState(true);
  useEffect(()=>{api.get('/health').then(()=>setHealthy(true)).catch(()=>setHealthy(false));},[]);
  return (
    <>
      <Toaster position="top-right" toastOptions={{style:{borderRadius:'10px',fontFamily:'inherit',fontSize:'0.9rem'}}}/>
      <Nav healthy={healthy}/>
      <Routes>
        <Route path="/" element={<CitizenSubmission/>}/>
        <Route path="/dashboard" element={<MPDashboard/>}/>
      </Routes>
      <Footer/>
    </>
  );
}

export default function App() {
  return <HashRouter><AppInner/></HashRouter>;
}
