"""
Citizens of India — Google Cloud Hackathon Submission PDF
Clean 3-page presentation, GCP-aligned.
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak,
)

# ── Palette ───────────────────────────────────────────────────────────────────
NAVY   = colors.HexColor("#0F172A")
GCBLUE = colors.HexColor("#1A73E8")   # Google Cloud blue
GCGRN  = colors.HexColor("#34A853")   # Google green
GCRED  = colors.HexColor("#EA4335")   # Google red
GCYEL  = colors.HexColor("#FBBC04")   # Google yellow
INDIGO = colors.HexColor("#3949AB")
VIOLET = colors.HexColor("#6D28D9")
SLATE  = colors.HexColor("#475569")
MUTED  = colors.HexColor("#94A3B8")
LGRAY  = colors.HexColor("#F8FAFC")
LBLUE  = colors.HexColor("#E8F0FE")
LGRN   = colors.HexColor("#E6F4EA")
WHITE  = colors.white
HERO   = colors.HexColor("#1A237E")

PW  = A4[0] - 3.6*cm
OUT = "/Users/gowtham/Downloads/AIAgent/Citizens of India/Citizens_of_India_Presentation.pdf"

doc = SimpleDocTemplate(OUT, pagesize=A4,
    leftMargin=1.8*cm, rightMargin=1.8*cm,
    topMargin=1.4*cm,  bottomMargin=1.6*cm)

# ── Style helpers ─────────────────────────────────────────────────────────────
def sp(n=6):  return Spacer(1, n)
def HR(c=GCBLUE, t=0.5): return HRFlowable(width="100%", thickness=t,
                                             color=c, spaceBefore=4, spaceAfter=6)
def S(name="", **kw):
    d = dict(fontName="Helvetica", fontSize=9.5, textColor=NAVY,
             leading=14, spaceAfter=0, spaceBefore=0)
    d.update(kw)
    return ParagraphStyle(name or "_s", **d)

def T(text, **kw):   return Paragraph(text, S(**kw))
def BT(text, **kw):  return Paragraph(f"<b>{text}</b>", S(fontName="Helvetica-Bold", **kw))
def WT(text, **kw):  return Paragraph(f"<b>{text}</b>",
                          S(fontName="Helvetica-Bold", textColor=WHITE, **kw))

def sec_label(text, color=GCBLUE):
    return T(text.upper(), fontSize=7.5, textColor=color,
             fontName="Helvetica-Bold", letterSpacing=1.3, spaceBefore=10, spaceAfter=4)

def heading(text, size=15, color=NAVY):
    return T(f"<b>{text}</b>", fontSize=size, textColor=color,
             fontName="Helvetica-Bold", leading=int(size*1.3), spaceAfter=5)

def body(text, size=9, color=NAVY):
    return T(text, fontSize=size, textColor=color, leading=14, spaceAfter=2)

def gtable(rows, widths, hbg=GCBLUE, alt=None):
    """Auto-wrapping grid table."""
    if alt is None: alt = [LBLUE, WHITE]
    hs = S(fontName="Helvetica-Bold", fontSize=8.5, textColor=WHITE, leading=12)
    ds = S(fontSize=8.5, textColor=NAVY, leading=12)
    wrapped = []
    for ri, row in enumerate(rows):
        new = []
        for cell in row:
            if isinstance(cell, str):
                new.append(Paragraph(cell, hs if ri == 0 else ds))
            else:
                new.append(cell)
        wrapped.append(new)
    t = Table(wrapped, colWidths=widths)
    t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  hbg),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), alt),
        ("GRID",          (0,0), (-1,-1), 0.35, colors.HexColor("#CBD5E1")),
        ("PADDING",       (0,0), (-1,-1), 6),
        ("VALIGN",        (0,0), (-1,-1), "TOP"),
    ]))
    return t

def kpi_cell(value, label, vcolor):
    """Single KPI as a mini-table: big number over label, no nesting issues."""
    return Table([
        [T(f"<b>{value}</b>", fontSize=20, textColor=vcolor,
           fontName="Helvetica-Bold", alignment=TA_CENTER)],
        [T(label, fontSize=7.5, textColor=SLATE,
           alignment=TA_CENTER, leading=10)],
    ], colWidths=[PW/6 - 1])

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 1  —  Cover · Problem · Solution · GCP Services
# ══════════════════════════════════════════════════════════════════════════════
story = []

# ── Hero ──────────────────────────────────────────────────────────────────────
hero = Table([
    [T("CITIZENS OF INDIA", fontSize=24, textColor=WHITE,
       fontName="Helvetica-Bold", alignment=TA_CENTER)],
    [T("AI for Constituency Development Planning  —  Built on Google Cloud",
       fontSize=11, textColor=colors.HexColor("#90CAF9"),
       fontName="Helvetica-Bold", alignment=TA_CENTER)],
    [T("Turning 930 million citizen voices into actionable intelligence for India's MPs",
       fontSize=9.5, textColor=colors.HexColor("#BBDEFB"),
       fontName="Helvetica-Oblique", alignment=TA_CENTER)],
], colWidths=[PW])
hero.setStyle(TableStyle([
    ("BACKGROUND",    (0,0), (-1,-1), HERO),
    ("TOPPADDING",    (0,0), (-1,0),  16),
    ("PADDING",       (0,1), (-1,1),  8),
    ("BOTTOMPADDING", (0,2), (-1,2),  16),
]))
story += [hero, sp(5)]

story.append(T(
    "Google Cloud Hackathon  ·  People's Priorities Track  ·  "
    "gowtham66866@gmail.com  ·  github.com/gowtham66867/citizens-of-india",
    fontSize=7.5, textColor=SLATE, alignment=TA_CENTER))
story += [sp(12)]

# ── Google Cloud Services banner ───────────────────────────────────────────────
story.append(sec_label("Google Cloud Services Used", GCBLUE))
gcp_services = [
    ("Gemini 2.5\nFlash Lite", GCBLUE),
    ("Cloud Run\n(Serverless)", GCGRN),
    ("Cloud\nScheduler", GCRED),
    ("Cloud\nTranslation API", colors.HexColor("#0097A7")),
    ("Cloud\nSpeech-to-Text", INDIGO),
    ("Google Cloud\nContainer Registry", colors.HexColor("#E65100")),
]
svc_cells = [[
    T(f"<b>{name}</b>", fontSize=8, textColor=WHITE, fontName="Helvetica-Bold",
      alignment=TA_CENTER, leading=11)
    for name, _ in gcp_services
]]
svc_table = Table(svc_cells, colWidths=[PW/6]*6)
svc_styles = [("PADDING",(0,0),(-1,-1),8), ("ALIGN",(0,0),(-1,-1),"CENTER"),
              ("BOX",(0,0),(-1,-1),0,WHITE), ("INNERGRID",(0,0),(-1,-1),1,WHITE)]
for i, (_, c) in enumerate(gcp_services):
    svc_styles.append(("BACKGROUND",(i,0),(i,0),c))
svc_table.setStyle(TableStyle(svc_styles))
story += [svc_table, sp(12)]

# ── Problem ───────────────────────────────────────────────────────────────────
story.append(sec_label("The Problem", GCRED))
story.append(heading("India's Governance Gap is a $40B Opportunity", 14, GCRED))
story += [sp(5)]

stat_data = [[
    Table([[T(v, fontSize=18, textColor=c, fontName="Helvetica-Bold",
              alignment=TA_CENTER, leading=22)],
           [T(l, fontSize=7.5, textColor=SLATE, alignment=TA_CENTER, leading=10)]],
          colWidths=[PW/4 - 3])
    for v,l,c in [("543","Lok Sabha\nConstituencies",GCBLUE),
                  ("930M","Registered\nVoters",INDIGO),
                  ("Rs.3.2L Cr","Annual MPLAD\n& Dev Spend",GCGRN),
                  ("<2%","Citizens Give\nFormal Feedback",GCRED)]
]]
stats = Table(stat_data, colWidths=[PW/4]*4)
stats.setStyle(TableStyle([
    ("BACKGROUND",(0,0),(-1,-1),LBLUE),
    ("BOX",(0,0),(-1,-1),0.5,colors.HexColor("#90CAF9")),
    ("INNERGRID",(0,0),(-1,-1),0.35,colors.HexColor("#90CAF9")),
    ("PADDING",(0,0),(-1,-1),10),("VALIGN",(0,0),(-1,-1),"MIDDLE"),
]))
story += [stats, sp(6)]
story.append(body(
    "Public development spending decisions are made with <b>almost zero structured citizen input</b>. "
    "Town halls reach &lt;0.1% of a constituency. Paper forms are never digitised. "
    "Regional languages — spoken by 78% of India — are invisible to policy. "
    "Result: misallocated MPLAD funds, repeated infrastructure failures, citizen disillusionment."))
story += [sp(12)]

# ── Solution + GCP Architecture flow ─────────────────────────────────────────
story.append(sec_label("Our Solution — Built on Google Cloud", GCBLUE))
story.append(heading("One Platform. Every Voice. Instant Intelligence.", 14))
story += [sp(5)]

flow_items = [
    ("CAPTURE",    "Text · Voice · Photo\nWhatsApp · SMS\nAny Indian language",      GCBLUE),
    ("GEMINI AI",  "Cloud Translation API\nGemini 2.5 Flash Lite\nClassify in <2 sec", GCGRN),
    ("AGENT PIPELINE","Claude Subagents\nSemantic cluster\nUrgency x Reach score",   INDIGO),
    ("MP BRIEFING","Cloud Run API\nReal-time heatmap\nDownloadable report",          GCRED),
]
fh = [T(f"<b>{h}</b>", fontSize=8, textColor=WHITE, fontName="Helvetica-Bold",
        alignment=TA_CENTER) for h,_,_ in flow_items]
fb = [T(d, fontSize=8.5, textColor=NAVY, alignment=TA_CENTER, leading=13)
      for _,d,_ in flow_items]
flow = Table([fh, fb], colWidths=[PW/4]*4)
fst = [("PADDING",(0,0),(-1,-1),9),("ALIGN",(0,0),(-1,-1),"CENTER"),
       ("VALIGN",(0,0),(-1,-1),"MIDDLE"),
       ("BOX",(0,0),(-1,-1),0.5,colors.HexColor("#CBD5E1")),
       ("INNERGRID",(0,0),(-1,-1),0.5,WHITE),
       ("LINEBELOW",(0,0),(-1,0),0.5,WHITE)]
for i,(_,_,c) in enumerate(flow_items):
    fst += [("BACKGROUND",(i,0),(i,0),c), ("BACKGROUND",(i,1),(i,1),LGRAY)]
flow.setStyle(TableStyle(fst))
story += [flow]

story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 2  —  Business Value · Go-to-Market · Competitive Moat
# ══════════════════════════════════════════════════════════════════════════════

story.append(sec_label("Business Value", GCGRN))
story.append(heading("What Every Stakeholder Gains", 14, GCGRN))
story += [sp(5)]

sh_data = [
    ["Stakeholder", "Current Pain", "Value with Citizens of India", "Outcome"],
    ["MP / MLA",
     "Anecdotal feedback,\nslow decisions",
     "Data-driven briefing every Monday via Cloud Scheduler",
     "10x more issues\nsurfaced"],
    ["Rural Citizen",
     "No voice,\nlanguage barrier",
     "WhatsApp/voice in mother tongue — Gemini translates instantly",
     "First time heard\ndigitally"],
    ["State Government",
     "Manual aggregation,\nmonths of lag",
     "Real-time theme heatmaps streamed via Cloud Run API",
     "Policy response\nin days"],
    ["NGOs & Media",
     "No structured\nground truth",
     "Open API on Cloud Run — queryable citizen priority data",
     "Evidence-based\nadvocacy"],
    ["MPLAD Office",
     "Reactive fund\nallocation",
     "Urgency-ranked pipeline scored by Claude AI agents",
     "Better ROI on\nRs.5 Cr/MP spend"],
]
story.append(gtable(sh_data, [2.8*cm, 3.4*cm, 7.4*cm, 3.8*cm], GCGRN, [LGRN, WHITE]))
story += [sp(12)]

# ── Go-to-Market ─────────────────────────────────────────────────────────────
story.append(sec_label("Go-To-Market & Revenue Model", INDIGO))
story.append(heading("From Hackathon to National GCP-Powered Infrastructure", 14, INDIGO))
story += [sp(5)]

phases = [
    ("Phase 1 — Pilot\n(0–6 months)",
     "5 pilot constituencies\nFree for MPs\nGemini free tier\nCloud Run free tier",
     GCBLUE, LBLUE),
    ("Phase 2 — State SaaS\n(7–18 months)",
     "State Govt licence\nRs.5L / district / year\nWhatsApp Business API\nFirestore + Cloud SQL",
     INDIGO, colors.HexColor("#EDE7F6")),
    ("Phase 3 — National\n(Year 2+)",
     "NIC / MeitY partnership\n543 constituencies\nRs.25 Cr ARR potential\nFull GCP enterprise stack",
     GCGRN, LGRN),
]
ph_h = [T(f"<b>{h}</b>", fontSize=8.5, textColor=WHITE, fontName="Helvetica-Bold",
          alignment=TA_CENTER, leading=13) for h,_,c,_ in phases]
ph_b = [T(d, fontSize=9, textColor=NAVY, alignment=TA_CENTER, leading=14)
        for _,d,_,_ in phases]
ph = Table([ph_h, ph_b], colWidths=[PW/3]*3)
pst = [("PADDING",(0,0),(-1,-1),10),("ALIGN",(0,0),(-1,-1),"CENTER"),
       ("VALIGN",(0,0),(-1,-1),"TOP"),
       ("BOX",(0,0),(-1,-1),0.5,colors.HexColor("#CBD5E1")),
       ("INNERGRID",(0,0),(-1,-1),0.5,WHITE)]
for i,(_,_,hc,bc) in enumerate(phases):
    pst += [("BACKGROUND",(i,0),(i,0),hc), ("BACKGROUND",(i,1),(i,1),bc)]
ph.setStyle(TableStyle(pst))
story += [ph, sp(12)]

# ── Moat ─────────────────────────────────────────────────────────────────────
story.append(sec_label("Competitive Moat", colors.HexColor("#E65100")))
story.append(heading("Why This Is Hard to Replicate", 14, colors.HexColor("#E65100")))
story += [sp(5)]

moat_data = [
    ["Advantage", "What It Means", "Why Competitors Can't Copy Easily"],
    ["Gemini multilingual AI",
     "22 Indian languages via Google Cloud Translation + Gemini",
     "Requires deep GCP integration, massive multilingual training data"],
    ["Multi-agent reasoning",
     "4 Claude subagents on Cloud Run: cluster, score, brief",
     "Needs Anthropic + GCP expertise and complex prompt engineering"],
    ["Omnichannel capture",
     "WhatsApp, voice, photo, SMS — zero app install",
     "Rural reach needs telecom + Speech-to-Text + zero-literacy UX"],
    ["Cloud-native automation",
     "Cloud Scheduler runs weekly briefs autonomously",
     "Most civic tech is batch-processed, not event-driven cloud-native"],
    ["Data network effect",
     "More submissions > better Gemini clustering > better policy",
     "Cold-start moat; compounds with every citizen submission"],
]
story.append(gtable(moat_data,
    [3.5*cm, 5.8*cm, 8.1*cm],
    colors.HexColor("#E65100"),
    [colors.HexColor("#FFF3E0"), WHITE]))

story.append(PageBreak())

# ══════════════════════════════════════════════════════════════════════════════
# PAGE 3  —  GCP Architecture · Demo Flow · Metrics · Claude Features
# ══════════════════════════════════════════════════════════════════════════════

story.append(sec_label("Google Cloud Architecture", GCBLUE))
story.append(heading("Enterprise-Grade GCP Stack — Built in 72 Hours", 14))
story += [sp(5)]

tech_data = [
    ["GCP Service / Layer", "Technology", "Role in the Platform"],
    ["Gemini 2.5 Flash Lite",
     "google-genai SDK · REST API",
     "Multilingual triage: theme, urgency, sentiment, location in <2 sec"],
    ["Cloud Run (Python 3.11)",
     "FastAPI + Uvicorn · Docker · GCR",
     "Serverless API — auto-scales to zero, public HTTPS endpoint"],
    ["Cloud Translation API",
     "google-cloud-translate v3",
     "Detects and translates 22 Indian languages to English"],
    ["Cloud Speech-to-Text",
     "google-cloud-speech v2",
     "Transcribes voice submissions (WhatsApp audio, field recordings)"],
    ["Cloud Scheduler",
     "Cron jobs — weekly + daily triggers",
     "Autonomous Monday briefing + daily theme aggregation per constituency"],
    ["Container Registry (GCR)",
     "gcr.io/gowthamaccount/...",
     "Stores versioned Docker images; deployed directly to Cloud Run"],
    ["Claude claude-sonnet-4-6 Agents",
     "Anthropic API · MCP stdio server",
     "4 subagents: DataAgent -> ClusterAgent -> PriorityAgent -> BriefingAgent"],
    ["React + GitHub Pages",
     "gh-pages · axios · SSE EventSource",
     "MP Dashboard and Citizen forms — zero-cost static hosting"],
    ["SQLite / Firestore path",
     "sqlite3 (demo) · firebase-admin (prod)",
     "Zero infra cost for hackathon; Firestore for production scale"],
]
story.append(gtable(tech_data,
    [3.8*cm, 4.8*cm, 8.8*cm], GCBLUE, [LBLUE, WHITE]))
story += [sp(10)]

# ── Demo Flow ─────────────────────────────────────────────────────────────────
story.append(sec_label("Live Demo — End-to-End Flow", GCGRN))
story.append(heading("The 90-Second Constituency Intelligence Loop", 14, GCGRN))
story += [sp(5)]

demo_steps = [
    ("01  Submit",
     "Citizen opens the web app and submits a complaint in Telugu about a broken road."),
    ("02  Gemini Triages",
     "Cloud Translation API detects Telugu, translates. Gemini 2.5 classifies: Roads & Infrastructure / High Urgency / GPS extracted. All in <2 sec."),
    ("03  Dashboard Live",
     "MP opens the Cloud Run-hosted dashboard. Heatmap updates, theme chart shows Roads trending, submission appears in the live feed."),
    ("04  Agent Pipeline",
     "MP clicks 'Run AI Analysis'. 4 Claude subagents stream progress via SSE: Fetch -> Cluster -> Prioritize -> Briefing (live step-by-step)."),
    ("05  MP Briefing",
     "Structured brief: top 3 clusters, urgency x reach scores, affected population, recommended actions. Downloadable .txt."),
    ("06  Autopilot",
     "Cloud Scheduler fires every Monday 8 AM IST — full pipeline runs autonomously for all 4 constituencies. MP wakes up to fresh intelligence."),
]
demo_rows = [[
    T(f"<b>{n}</b>", fontSize=8.5, textColor=WHITE, fontName="Helvetica-Bold",
      alignment=TA_CENTER),
    T(d, fontSize=9, textColor=NAVY, leading=13),
] for n, d in demo_steps]
demo = Table(demo_rows, colWidths=[2.8*cm, PW - 2.8*cm])
dst = [("VALIGN",(0,0),(-1,-1),"MIDDLE"),("PADDING",(0,0),(-1,-1),7),
       ("GRID",(0,0),(-1,-1),0.35,colors.HexColor("#A5D6A7")),
       ("ROWBACKGROUNDS",(1,0),(1,-1),[LGRN, WHITE])]
for i in range(len(demo_rows)):
    dst.append(("BACKGROUND",(0,i),(0,i),GCGRN))
demo.setStyle(TableStyle(dst))
story += [demo, sp(10)]

# ── KPI strip ─────────────────────────────────────────────────────────────────
story.append(sec_label("Live on Google Cloud — Right Now", GCBLUE))
story += [sp(4)]

kpis = [
    ("93",  "Live\nSubmissions",  GCBLUE),
    ("10",  "Issue\nThemes",      INDIGO),
    ("5",   "Indian\nLanguages",  GCGRN),
    ("85",  "Tests\nPassing",     GCGRN),
    ("6",   "MCP\nTools",         colors.HexColor("#E65100")),
    ("4",   "Claude\nSubagents",  GCRED),
]
cw = PW / 6
kpi_row = [[
    Table(
        [[T(f"<b>{v}</b>", fontSize=22, textColor=c, fontName="Helvetica-Bold",
             alignment=TA_CENTER, leading=26)],
         [T(l, fontSize=7.5, textColor=SLATE, alignment=TA_CENTER, leading=10)]],
        colWidths=[cw],
        style=TableStyle([
            ("TOPPADDING",    (0,0),(-1,0), 10),
            ("BOTTOMPADDING", (0,0),(-1,0), 2),
            ("TOPPADDING",    (0,1),(-1,1), 0),
            ("BOTTOMPADDING", (0,1),(-1,1), 10),
            ("ALIGN",         (0,0),(-1,-1),"CENTER"),
            ("VALIGN",        (0,0),(-1,-1),"MIDDLE"),
        ])
    )
    for v, l, c in kpis
]]
kpi = Table(kpi_row, colWidths=[cw]*6)
kpi.setStyle(TableStyle([
    ("BACKGROUND", (0,0),(-1,-1), LBLUE),
    ("BOX",        (0,0),(-1,-1), 0.5, colors.HexColor("#90CAF9")),
    ("INNERGRID",  (0,0),(-1,-1), 0.35, colors.HexColor("#90CAF9")),
    ("PADDING",    (0,0),(-1,-1), 0),
    ("VALIGN",     (0,0),(-1,-1), "MIDDLE"),
]))
story += [kpi, sp(10)]

# ── Claude Code / Advanced Features ───────────────────────────────────────────
story.append(sec_label("Advanced Claude Code Features", INDIGO))
story += [sp(4)]

feats = [
    ["Feature", "Implementation", "Business Value"],
    ["MCP Server",
     "6 tools via stdio — submit_issue, get_priorities, run_agent_pipeline...",
     "Claude Desktop queries live GCP-hosted citizen data in plain English"],
    ["Multi-Agent Pipeline",
     "claude-sonnet-4-6 orchestrator, tool_use loop, 4 subagents on Cloud Run",
     "Scales to any constituency; each agent specialises for accuracy"],
    ["SSE Streaming",
     "EventSource -> /agents/stream; live step-by-step pipeline UI",
     "MPs see AI reasoning live — builds trust in the output"],
    ["Cloud Scheduler Cron",
     "Weekly + daily GCP Scheduler jobs; CRON_SECRET header auth",
     "Fully autonomous intelligence — zero manual MP intervention"],
    ["CLAUDE.md + Hooks",
     "CLAUDE.md loads full GCP architecture; post-tool-use.sh syntax checks",
     "Production-quality code — every edit validated before it can break Cloud Run"],
]
story.append(gtable(feats, [3*cm, 6*cm, 8.4*cm], INDIGO, [LBLUE, WHITE]))
story += [sp(8)]

# ── Footer ────────────────────────────────────────────────────────────────────
footer_items = [
    ("Live App",      "gowtham66867.github.io\n/citizens-of-india"),
    ("GitHub Repo",   "github.com/gowtham66867\n/citizens-of-india"),
    ("Cloud Run API", "citizens-india-backend-564262191703\n.us-central1.run.app/docs"),
    ("Contact",       "gowtham66866\n@gmail.com"),
]
footer = Table([[
    T(f"<b>{l}</b>\n{v}", fontSize=7.5, textColor=WHITE,
      alignment=TA_CENTER, leading=11)
    for l, v in footer_items
]], colWidths=[PW/4]*4)
footer.setStyle(TableStyle([
    ("BACKGROUND", (0,0),(-1,-1), HERO),
    ("INNERGRID",  (0,0),(-1,-1), 0.3, colors.HexColor("#283593")),
    ("BOX",        (0,0),(-1,-1), 0, WHITE),
    ("PADDING",    (0,0),(-1,-1), 10),
    ("VALIGN",     (0,0),(-1,-1), "MIDDLE"),
    ("ALIGN",      (0,0),(-1,-1), "CENTER"),
]))
story += [HR(HERO, 1), footer]

doc.build(story)
print(f"PDF ready: {OUT}")
