import React, { useState, useEffect, useCallback } from 'react';
import api from '../api';
import AgentStream from '../components/AgentStream';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell,
} from 'recharts';
import { MapContainer, TileLayer, CircleMarker, Tooltip as LT, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';

const COLORS = ['#FF9933','#138808','#000080','#e53e3e','#d69e2e','#805ad5','#38a169','#3182ce','#dd6b20','#718096'];
const URGENCY_COLOR = { High:'#e53e3e', Medium:'#d69e2e', Low:'#38a169' };
const THEME_COLORS = {
  'Roads & Infrastructure':'#e53e3e','Healthcare & Sanitation':'#38a169','Education':'#3182ce',
  'Water Supply':'#0bc5ea','Electricity':'#d69e2e','Agriculture & Irrigation':'#68d391',
  'Agriculture Support':'#68d391','Employment & Livelihood':'#9f7aea','Environment & Waste':'#48bb78',
  'Law & Order':'#f6ad55','Housing & Land':'#fc8181','Public Safety':'#fc8181','Other':'#a0aec0',
};

/* ── Skeleton ── */
function Skeleton({ w='100%', h=20, mb=8 }) {
  return <div className="skeleton" style={{ width:w, height:h, marginBottom:mb }} />;
}
function DashSkeleton() {
  return (
    <div>
      <div style={{ display:'grid', gridTemplateColumns:'repeat(4,1fr)', gap:'1rem', marginBottom:'2rem' }}>
        {[1,2,3,4].map(i=>(
          <div key={i} className="card"><Skeleton h={80}/></div>
        ))}
      </div>
      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'1.5rem' }}>
        <div className="card"><Skeleton h={260}/></div>
        <div className="card"><Skeleton h={260}/></div>
      </div>
    </div>
  );
}

/* ── Map ── */
function FitBounds({ points }) {
  const map = useMap();
  useEffect(() => {
    if (points.length > 0) {
      const lats = points.map(p=>p.lat), lngs = points.map(p=>p.lng);
      map.fitBounds([[Math.min(...lats)-0.05,Math.min(...lngs)-0.05],[Math.max(...lats)+0.05,Math.max(...lngs)+0.05]]);
    }
  }, [points,map]);
  return null;
}

function DemandHeatmap({ points }) {
  const activeThemes = [...new Set(points.map(p=>p.theme))];
  return (
    <div>
      <MapContainer center={[16.22,80.12]} zoom={10} style={{height:'400px',borderRadius:'12px',zIndex:0}} scrollWheelZoom>
        <TileLayer attribution='&copy; OpenStreetMap' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"/>
        <FitBounds points={points}/>
        {points.map((p,i)=>(
          <CircleMarker key={i} center={[p.lat,p.lng]}
            radius={p.urgency==='High'?10:p.urgency==='Medium'?7:5}
            pathOptions={{fillColor:THEME_COLORS[p.theme]||'#718096',fillOpacity:0.85,color:'#fff',weight:1.5}}>
            <LT><div style={{fontSize:'0.8rem'}}><b>{p.theme}</b><br/>Urgency: {p.urgency}<br/>{p.summary||''}</div></LT>
          </CircleMarker>
        ))}
      </MapContainer>
      <div style={{display:'flex',flexWrap:'wrap',gap:'0.5rem',marginTop:'0.75rem'}}>
        {activeThemes.map(t=>(
          <span key={t} style={{
            fontSize:'0.75rem',padding:'2px 10px',borderRadius:'12px',
            background:`${THEME_COLORS[t]||'#718096'}18`,color:THEME_COLORS[t]||'#718096',
            fontWeight:600,border:`1px solid ${THEME_COLORS[t]||'#718096'}40`,
          }}>● {t}</span>
        ))}
      </div>
      {points.length===0&&<div style={{textAlign:'center',color:'#a0aec0',marginTop:'1rem'}}>No geotagged submissions yet</div>}
    </div>
  );
}

/* ── Stat card ── */
function StatCard({ icon, label, value, sub, color, trend }) {
  return (
    <div className="card" style={{textAlign:'center',position:'relative',overflow:'hidden'}}>
      <div style={{position:'absolute',top:0,left:0,right:0,height:'3px',background:color||'#FF9933'}}/>
      <div style={{fontSize:'2rem',marginBottom:'0.25rem',marginTop:'0.5rem'}}>{icon}</div>
      <div style={{display:'flex',alignItems:'center',justifyContent:'center',gap:'6px'}}>
        <div style={{fontSize:'2rem',fontWeight:800,color:color||'#FF9933'}}>{value}</div>
        {trend!==undefined&&<span style={{fontSize:'0.78rem',color:trend>=0?'#38a169':'#e53e3e',fontWeight:700}}>
          {trend>=0?'↑':'↓'}{Math.abs(trend)}%
        </span>}
      </div>
      <div style={{fontSize:'0.85rem',fontWeight:600,color:'#2d3748'}}>{label}</div>
      {sub&&<div style={{fontSize:'0.78rem',color:'#718096',marginTop:'0.2rem'}}>{sub}</div>}
    </div>
  );
}

/* ── Priority card ── */
function PriorityCard({ item, rank }) {
  const rankColors={1:'#FF9933',2:'#718096',3:'#c05621'};
  const rankLabels={1:'🥇 Top Priority',2:'🥈 2nd Priority',3:'🥉 3rd Priority'};
  return (
    <div className="card fade-in-up" style={{borderLeft:`4px solid ${rankColors[rank]||'#e2e8f0'}`,marginBottom:'1rem'}}>
      <div style={{display:'flex',gap:'0.75rem',alignItems:'flex-start'}}>
        <div style={{
          width:'40px',height:'40px',borderRadius:'50%',flexShrink:0,
          background:rankColors[rank]||'#e2e8f0',color:'#fff',
          display:'flex',alignItems:'center',justifyContent:'center',fontWeight:800,fontSize:'1.1rem',
        }}>#{rank}</div>
        <div style={{flex:1}}>
          <div style={{display:'flex',alignItems:'center',gap:'8px',marginBottom:'0.2rem'}}>
            <h3 style={{fontSize:'1rem',fontWeight:700,color:'#1a202c'}}>{item.theme}</h3>
            <span style={{fontSize:'0.72rem',background:`${rankColors[rank]}18`,color:rankColors[rank],
              borderRadius:'12px',padding:'1px 10px',fontWeight:700}}>{rankLabels[rank]}</span>
          </div>
          <p style={{fontSize:'0.88rem',color:'#4a5568',lineHeight:1.5}}>{item.rationale}</p>
        </div>
      </div>
      <div style={{
        marginTop:'0.75rem',padding:'0.6rem 0.9rem',background:'#f7fafc',
        borderRadius:'10px',display:'flex',gap:'2rem',flexWrap:'wrap',
      }}>
        <div>
          <span style={{fontSize:'0.72rem',color:'#718096',fontWeight:700,letterSpacing:'0.06em'}}>NEXT STEP</span>
          <p style={{fontSize:'0.85rem',color:'#2d3748',marginTop:'0.1rem'}}>{item.suggested_action}</p>
        </div>
        <div>
          <span style={{fontSize:'0.72rem',color:'#718096',fontWeight:700,letterSpacing:'0.06em'}}>BENEFICIARIES</span>
          <p style={{fontSize:'0.85rem',color:'#138808',fontWeight:700,marginTop:'0.1rem'}}>{item.estimated_beneficiaries}</p>
        </div>
      </div>
    </div>
  );
}

/* ── Submission row ── */
function SubmissionRow({ s }) {
  const uc = URGENCY_COLOR[s.urgency]||'#718096';
  return (
    <tr style={{borderBottom:'1px solid #f0f4f8',transition:'background 0.15s'}}
      onMouseEnter={e=>e.currentTarget.style.background='#fafafa'}
      onMouseLeave={e=>e.currentTarget.style.background=''}>
      <td style={{padding:'0.75rem 1rem',fontSize:'0.88rem',maxWidth:'280px'}}>
        <div style={{fontWeight:500,color:'#2d3748',overflow:'hidden',textOverflow:'ellipsis',whiteSpace:'nowrap'}}>
          {(s.original_text||'').slice(0,80)}{s.original_text?.length>80?'…':''}
        </div>
        <div style={{fontSize:'0.75rem',color:'#a0aec0',marginTop:'2px'}}>
          {s.source_language?.toUpperCase()} · {s.input_type}
        </div>
      </td>
      <td style={{padding:'0.75rem 1rem'}}>
        <span style={{
          background:`${THEME_COLORS[s.theme]||'#718096'}18`,color:THEME_COLORS[s.theme]||'#718096',
          borderRadius:'12px',padding:'2px 10px',fontSize:'0.78rem',fontWeight:600,whiteSpace:'nowrap',
        }}>{s.theme}</span>
      </td>
      <td style={{padding:'0.75rem 1rem'}}>
        <span style={{
          background:`${uc}18`,color:uc,borderRadius:'12px',
          padding:'2px 10px',fontSize:'0.78rem',fontWeight:600,
        }}>{s.urgency}</span>
      </td>
      <td style={{padding:'0.75rem 1rem',fontSize:'0.82rem',color:'#718096'}}>{s.location_hint||'—'}</td>
    </tr>
  );
}

/* ── Main ── */
export default function MPDashboard() {
  const [summary,setSummary]=useState(null);
  const [themes,setThemes]=useState([]);
  const [priorities,setPriorities]=useState([]);
  const [submissions,setSubmissions]=useState([]);
  const [heatmapPoints,setHeatmapPoints]=useState([]);
  const [loading,setLoading]=useState(true);
  const [prioritiesLoading,setPrioritiesLoading]=useState(false);
  const [constituency,setConstituency]=useState('');
  const [inputVal,setInputVal]=useState('');
  const [activeTab,setActiveTab]=useState('overview');
  const [search,setSearch]=useState('');
  const [urgencyFilter,setUrgencyFilter]=useState('All');

  const load = useCallback(async(c)=>{
    setLoading(true);
    const safe=async fn=>{try{return await fn();}catch{return null;}};
    const q=encodeURIComponent(c||'');
    const [sumRes,themeRes,subRes,heatRes]=await Promise.all([
      safe(()=>api.get(`/analytics/summary${q?`?constituency=${q}`:''}`)),
      safe(()=>api.get(`/analytics/themes${q?`?constituency=${q}`:''}`)),
      safe(()=>api.get(`/submissions/list?${q?`constituency=${q}&`:''}limit=100`)),
      safe(()=>api.get(`/analytics/heatmap${q?`?constituency=${q}`:''}`)),
    ]);
    setSummary(sumRes?.data||null);
    setThemes(themeRes?.data||[]);
    setSubmissions(subRes?.data||[]);
    setHeatmapPoints(heatRes?.data?.points||[]);
    setPriorities([]);
    setLoading(false);
  },[]);

  useEffect(()=>{load(constituency);},[load]);

  const loadPriorities=async()=>{
    if(priorities.length>0) return;
    setPrioritiesLoading(true);
    try{
      const res=await api.get(`/analytics/priorities${constituency?`?constituency=${encodeURIComponent(constituency)}`:''}`);
      setPriorities(res.data.priorities||[]);
    }catch(e){console.error(e);}
    finally{setPrioritiesLoading(false);}
  };

  const handleSearch=()=>{ setConstituency(inputVal); load(inputVal); };

  const langData=summary?.languages
    ?Object.entries(summary.languages).map(([k,v])=>({name:k.toUpperCase(),value:v}))
    :[];

  const filteredSubs=submissions.filter(s=>{
    const matchSearch=!search||(s.original_text||'').toLowerCase().includes(search.toLowerCase())||(s.theme||'').toLowerCase().includes(search.toLowerCase());
    const matchUrgency=urgencyFilter==='All'||s.urgency===urgencyFilter;
    return matchSearch&&matchUrgency;
  });

  const tabs=[
    {id:'overview',label:'📊 Overview'},
    {id:'priorities',label:'🎯 AI Priorities'},
    {id:'heatmap',label:'🗺️ Demand Map'},
    {id:'submissions',label:'📋 Submissions'},
  ];

  return (
    <div style={{padding:'2rem 0',minHeight:'calc(100vh - 62px)',background:'#f8f9fa'}}>
      <div className="container">
        {/* Header */}
        <div style={{display:'flex',justifyContent:'space-between',alignItems:'flex-start',marginBottom:'1.5rem',flexWrap:'wrap',gap:'1rem'}}>
          <div>
            <h1 style={{fontSize:'1.6rem',fontWeight:800,color:'#1a202c'}}>MP Dashboard</h1>
            <p style={{color:'#718096',fontSize:'0.9rem'}}>AI-ranked citizen development priorities
              {constituency&&<span style={{marginLeft:'6px',color:'#FF9933',fontWeight:600}}>· {constituency}</span>}
            </p>
          </div>
          <div style={{display:'flex',gap:'0.5rem',alignItems:'center',flexWrap:'wrap'}}>
            <div style={{display:'flex',gap:'0',borderRadius:'10px',overflow:'hidden',border:'1.5px solid #e2e8f0',background:'#fff'}}>
              <input
                value={inputVal} onChange={e=>setInputVal(e.target.value)}
                onKeyDown={e=>e.key==='Enter'&&handleSearch()}
                placeholder="Filter by constituency…"
                style={{border:'none',borderRadius:'10px 0 0 10px',width:'200px',padding:'0.6rem 0.9rem',outline:'none',fontSize:'0.88rem'}}
              />
              <button onClick={handleSearch} style={{
                padding:'0.6rem 1rem',background:'#FF9933',color:'#fff',
                fontWeight:700,fontSize:'0.88rem',borderRadius:'0 8px 8px 0',border:'none',
              }}>Search</button>
            </div>
            {constituency&&(
              <button onClick={()=>{setConstituency('');setInputVal('');load('');}} style={{
                padding:'0.5rem 0.9rem',borderRadius:'8px',border:'1px solid #e2e8f0',
                background:'#fff',color:'#718096',fontSize:'0.82rem',cursor:'pointer',
              }}>✕ Clear</button>
            )}
            <AgentStream constituency={constituency}/>
          </div>
        </div>

        {loading ? <DashSkeleton/> : (
          <>
            {/* Stats */}
            <div style={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(175px,1fr))',gap:'1rem',marginBottom:'2rem'}}>
              <StatCard icon="📨" label="Total Submissions" value={summary?.total_submissions||0} color="#FF9933"/>
              <StatCard icon="🚨" label="High Urgency" value={summary?.high_urgency_count||0} color="#e53e3e"
                sub={summary?.total_submissions?`${Math.round((summary.high_urgency_count/summary.total_submissions)*100)}% of total`:''}/>
              <StatCard icon="📌" label="Issue Categories" value={themes.length} color="#000080"/>
              <StatCard icon="🌐" label="Languages Used" value={Object.keys(summary?.languages||{}).length} color="#138808" sub="multilingual reach"/>
            </div>

            {/* Tabs */}
            <div style={{display:'flex',gap:'0.25rem',marginBottom:'1.5rem',borderBottom:'2px solid #e2e8f0',overflowX:'auto'}}>
              {tabs.map(t=>(
                <button key={t.id} onClick={()=>{setActiveTab(t.id);if(t.id==='priorities')loadPriorities();}} style={{
                  padding:'0.6rem 1.2rem',borderRadius:'8px 8px 0 0',fontWeight:700,fontSize:'0.88rem',
                  whiteSpace:'nowrap',
                  background:activeTab===t.id?'#FF9933':'transparent',
                  color:activeTab===t.id?'#fff':'#718096',
                  borderBottom:activeTab===t.id?'2px solid #FF9933':'none',
                  marginBottom:'-2px',
                }}>{t.label}</button>
              ))}
            </div>

            {/* Overview */}
            {activeTab==='overview'&&(
              <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:'1.5rem'}}>
                <div className="card">
                  <h3 style={{fontSize:'0.95rem',fontWeight:700,marginBottom:'1rem',color:'#2d3748'}}>Submissions by Issue Type</h3>
                  {themes.length>0?(
                    <ResponsiveContainer width="100%" height={280}>
                      <BarChart data={themes} layout="vertical" margin={{left:10}}>
                        <CartesianGrid strokeDasharray="3 3" horizontal={false}/>
                        <XAxis type="number" fontSize={11}/>
                        <YAxis type="category" dataKey="theme" width={170} fontSize={11}/>
                        <Tooltip/>
                        <Bar dataKey="count" radius={[0,4,4,0]}>
                          {themes.map((t,i)=><Cell key={i} fill={THEME_COLORS[t.theme]||COLORS[i%COLORS.length]}/>)}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  ):<div style={{textAlign:'center',padding:'3rem',color:'#a0aec0'}}>No submissions yet</div>}
                </div>
                <div className="card">
                  <h3 style={{fontSize:'0.95rem',fontWeight:700,marginBottom:'1rem',color:'#2d3748'}}>Language Distribution</h3>
                  {langData.length>0?(
                    <ResponsiveContainer width="100%" height={280}>
                      <PieChart>
                        <Pie data={langData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100} innerRadius={40}
                          label={({name,percent})=>`${name} ${(percent*100).toFixed(0)}%`} labelLine>
                          {langData.map((_,i)=><Cell key={i} fill={COLORS[i%COLORS.length]}/>)}
                        </Pie>
                        <Tooltip/>
                      </PieChart>
                    </ResponsiveContainer>
                  ):<div style={{textAlign:'center',padding:'3rem',color:'#a0aec0'}}>No data yet</div>}
                </div>
              </div>
            )}

            {/* Priorities */}
            {activeTab==='priorities'&&(
              <div>
                <div style={{marginBottom:'1rem',padding:'0.75rem 1rem',background:'#fff3e0',borderRadius:'10px',fontSize:'0.85rem',color:'#744210',border:'1px solid #fde68a'}}>
                  🤖 AI-ranked by Gemini using submission volume, urgency signals, and constituency demographics
                </div>
                {prioritiesLoading?(
                  <div style={{textAlign:'center',padding:'3rem',color:'#718096'}}>
                    <div style={{fontSize:'2rem',marginBottom:'0.75rem',animation:'spin 1.5s linear infinite',display:'inline-block'}}>🤖</div>
                    <div>Gemini is analysing {themes.length} issue categories…</div>
                    <style>{`@keyframes spin{from{transform:rotate(0)}to{transform:rotate(360deg)}}`}</style>
                  </div>
                ):priorities.length===0?(
                  <div className="card" style={{textAlign:'center',padding:'3rem',color:'#a0aec0'}}>
                    No submissions to rank yet. Add issues via the citizen portal.
                  </div>
                ):priorities.map(p=><PriorityCard key={p.rank} item={p} rank={p.rank}/>)}
              </div>
            )}

            {/* Heatmap */}
            {activeTab==='heatmap'&&(
              <div className="card">
                <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:'1rem'}}>
                  <h3 style={{fontSize:'0.95rem',fontWeight:700,color:'#2d3748'}}>Demand Hotspot Map</h3>
                  <span style={{fontSize:'0.82rem',color:'#718096'}}>{heatmapPoints.length} geotagged submissions</span>
                </div>
                <DemandHeatmap points={heatmapPoints}/>
              </div>
            )}

            {/* Submissions */}
            {activeTab==='submissions'&&(
              <div className="card" style={{padding:0,overflow:'hidden'}}>
                {/* Toolbar */}
                <div style={{padding:'1rem 1.25rem',borderBottom:'1px solid #e2e8f0',display:'flex',gap:'0.75rem',flexWrap:'wrap',alignItems:'center'}}>
                  <span style={{fontWeight:700,color:'#2d3748',fontSize:'0.95rem'}}>
                    Recent Submissions <span style={{fontWeight:400,color:'#718096',fontSize:'0.85rem'}}>({filteredSubs.length})</span>
                  </span>
                  <input
                    value={search} onChange={e=>setSearch(e.target.value)}
                    placeholder="Search submissions…"
                    style={{width:'220px',padding:'0.45rem 0.8rem',fontSize:'0.85rem',marginLeft:'auto'}}
                  />
                  <div style={{display:'flex',gap:'0.3rem'}}>
                    {['All','High','Medium','Low'].map(u=>(
                      <button key={u} onClick={()=>setUrgencyFilter(u)} style={{
                        padding:'4px 12px',borderRadius:'20px',fontSize:'0.78rem',fontWeight:600,
                        background:urgencyFilter===u?(URGENCY_COLOR[u]||'#FF9933'):'#f0f4f8',
                        color:urgencyFilter===u?'#fff':'#4a5568',border:'none',cursor:'pointer',
                      }}>{u}</button>
                    ))}
                  </div>
                </div>
                <div style={{overflowX:'auto'}}>
                  <table style={{width:'100%',borderCollapse:'collapse'}}>
                    <thead>
                      <tr style={{background:'#f7fafc'}}>
                        {['Submission','Theme','Urgency','Location'].map(h=>(
                          <th key={h} style={{padding:'0.75rem 1rem',textAlign:'left',fontSize:'0.75rem',fontWeight:700,color:'#718096',textTransform:'uppercase',letterSpacing:'0.05em'}}>{h}</th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {filteredSubs.length===0
                        ?<tr><td colSpan={4} style={{padding:'3rem',textAlign:'center',color:'#a0aec0'}}>No submissions match your filter</td></tr>
                        :filteredSubs.map(s=><SubmissionRow key={s.id} s={s}/>)
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
