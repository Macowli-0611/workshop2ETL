"""
Build script to generate a standalone, professional HTML presentation deck for Workshop-2 Defense.
Embeds all charts as Base64 data URIs and outputs:
- docs/presentation.html
"""
import base64
import os

def get_base64_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        data = f.read()
    return f"data:image/png;base64,{base64.b64encode(data).decode('utf-8')}"

def build_deck():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    kpi1_b64 = get_base64_image(os.path.join(base_dir, "docs", "evidence", "kpi", "kpi1_audio_profile.png"))
    kpi2_b64 = get_base64_image(os.path.join(base_dir, "docs", "evidence", "kpi", "kpi2_genre_uplift.png"))
    kpi3_b64 = get_base64_image(os.path.join(base_dir, "docs", "evidence", "kpi", "kpi3_decade_trends.png"))

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Workshop-2: Building a Reliable Batch Data Pipeline — Technical Defense Deck</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {{
      --bg-dark: #070b14;
      --bg-surface: #0c1220;
      --bg-card: rgba(15, 23, 42, 0.78);
      --bg-card-hover: rgba(30, 41, 59, 0.9);
      --border-color: rgba(148, 163, 184, 0.16);
      --border-highlight: rgba(56, 189, 248, 0.45);
      --accent-cyan: #38bdf8;
      --accent-purple: #a855f7;
      --accent-emerald: #10b981;
      --accent-rose: #f43f5e;
      --accent-amber: #f59e0b;
      --accent-indigo: #6366f1;
      --text-main: #f8fafc;
      --text-muted: #94a3b8;
      --text-dim: #64748b;
      --font-sans: 'Plus Jakarta Sans', system-ui, -apple-system, sans-serif;
      --font-mono: 'JetBrains Mono', monospace;
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    body {{
      background-color: var(--bg-dark);
      color: var(--text-main);
      font-family: var(--font-sans);
      overflow: hidden;
      width: 100vw;
      height: 100vh;
      display: flex;
      flex-direction: column;
      user-select: none;
      -webkit-font-smoothing: antialiased;
    }}

    /* Background Ambient Lights */
    .ambient-glow {{
      position: fixed;
      width: 650px;
      height: 650px;
      border-radius: 50%;
      filter: blur(140px);
      pointer-events: none;
      z-index: 0;
      opacity: 0.16;
      transition: all 1s ease;
    }}
    .glow-1 {{ top: -120px; left: -100px; background: var(--accent-cyan); }}
    .glow-2 {{ bottom: -120px; right: -100px; background: var(--accent-purple); }}

    /* Top Navigation Header */
    header {{
      position: relative;
      z-index: 30;
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 12px 28px;
      background: rgba(10, 15, 29, 0.88);
      backdrop-filter: blur(16px);
      border-bottom: 1px solid var(--border-color);
    }}
    .brand {{
      display: flex;
      align-items: center;
      gap: 12px;
      font-weight: 700;
      font-size: 0.95rem;
    }}
    .brand-badge {{
      background: linear-gradient(135deg, var(--accent-cyan), var(--accent-purple));
      color: #050811;
      font-size: 0.72rem;
      font-weight: 800;
      padding: 3px 8px;
      border-radius: 6px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}
    .deck-meta {{
      display: flex;
      align-items: center;
      gap: 14px;
      font-size: 0.82rem;
      color: var(--text-muted);
    }}
    .timer-badge {{
      display: flex;
      align-items: center;
      gap: 6px;
      background: rgba(15, 23, 42, 0.8);
      border: 1px solid var(--border-color);
      padding: 4px 10px;
      border-radius: 8px;
      font-family: var(--font-mono);
      font-size: 0.82rem;
      color: var(--accent-cyan);
      cursor: pointer;
    }}
    .deck-controls {{
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .btn-ctrl {{
      background: rgba(30, 41, 59, 0.65);
      border: 1px solid var(--border-color);
      color: var(--text-main);
      padding: 6px 12px;
      border-radius: 8px;
      font-size: 0.8rem;
      font-weight: 500;
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 6px;
      transition: all 0.2s ease;
    }}
    .btn-ctrl:hover {{
      background: rgba(51, 65, 85, 0.85);
      border-color: var(--accent-cyan);
      color: #fff;
    }}
    .btn-ctrl.active {{
      background: rgba(56, 189, 248, 0.2);
      border-color: var(--accent-cyan);
      color: var(--accent-cyan);
    }}

    /* Viewport Container */
    main#deck-container {{
      position: relative;
      flex: 1;
      width: 100%;
      height: calc(100vh - 105px);
      z-index: 10;
      overflow: hidden;
    }}

    .slide {{
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      padding: 28px 52px;
      display: none;
      flex-direction: column;
      justify-content: flex-start;
      opacity: 0;
      transform: translateY(14px) scale(0.99);
      transition: opacity 0.35s cubic-bezier(0.16, 1, 0.3, 1), transform 0.35s cubic-bezier(0.16, 1, 0.3, 1);
      overflow-y: auto;
    }}
    .slide.active {{
      display: flex;
      opacity: 1;
      transform: translateY(0) scale(1);
    }}

    /* Header in Slide */
    .slide-header {{
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 14px;
    }}
    .slide-tag {{
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      font-weight: 700;
      color: var(--accent-cyan);
      display: flex;
      align-items: center;
      gap: 8px;
      margin-bottom: 4px;
    }}
    .slide-tag::before {{
      content: "";
      width: 8px;
      height: 8px;
      background: var(--accent-cyan);
      border-radius: 50%;
      box-shadow: 0 0 10px var(--accent-cyan);
    }}
    .rubric-pill {{
      display: inline-flex;
      align-items: center;
      gap: 6px;
      background: rgba(99, 102, 241, 0.15);
      border: 1px solid rgba(99, 102, 241, 0.35);
      color: #c7d2fe;
      font-size: 0.72rem;
      font-weight: 600;
      padding: 4px 10px;
      border-radius: 20px;
      letter-spacing: 0.02em;
    }}
    .slide-title {{
      font-size: 2.15rem;
      font-weight: 800;
      line-height: 1.15;
      letter-spacing: -0.02em;
      margin-bottom: 6px;
      background: linear-gradient(135deg, #ffffff 30%, #cbd5e1 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }}
    .slide-subtitle {{
      font-size: 0.98rem;
      color: var(--text-muted);
      line-height: 1.45;
      max-width: 950px;
    }}

    /* Layout Grids */
    .grid-2 {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 18px;
      flex: 1;
      min-height: 0;
    }}
    .grid-3 {{
      display: grid;
      grid-template-columns: repeat(3, 1fr);
      gap: 16px;
      flex: 1;
      min-height: 0;
    }}
    .grid-4 {{
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      gap: 14px;
      flex: 1;
      min-height: 0;
    }}

    /* Cards */
    .card {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 14px;
      padding: 20px;
      display: flex;
      flex-direction: column;
      position: relative;
      overflow: hidden;
      backdrop-filter: blur(10px);
      transition: all 0.25s ease;
    }}
    .card:hover {{
      background: var(--bg-card-hover);
      border-color: var(--border-highlight);
    }}
    .card-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
    }}
    .card-title {{
      font-size: 1rem;
      font-weight: 700;
      color: #fff;
      display: flex;
      align-items: center;
      gap: 8px;
    }}
    .badge {{
      font-size: 0.72rem;
      padding: 3px 8px;
      border-radius: 6px;
      font-weight: 600;
      letter-spacing: 0.02em;
      white-space: nowrap;
    }}
    .badge-cyan {{ background: rgba(56, 189, 248, 0.15); color: var(--accent-cyan); border: 1px solid rgba(56, 189, 248, 0.3); }}
    .badge-purple {{ background: rgba(168, 85, 247, 0.15); color: var(--accent-purple); border: 1px solid rgba(168, 85, 247, 0.3); }}
    .badge-emerald {{ background: rgba(16, 185, 129, 0.15); color: var(--accent-emerald); border: 1px solid rgba(16, 185, 129, 0.3); }}
    .badge-rose {{ background: rgba(244, 63, 94, 0.15); color: var(--accent-rose); border: 1px solid rgba(244, 63, 94, 0.3); }}
    .badge-amber {{ background: rgba(245, 158, 11, 0.15); color: var(--accent-amber); border: 1px solid rgba(245, 158, 11, 0.3); }}
    .badge-indigo {{ background: rgba(99, 102, 241, 0.15); color: #818cf8; border: 1px solid rgba(99, 102, 241, 0.3); }}

    .card-body {{
      flex: 1;
      font-size: 0.86rem;
      color: #cbd5e1;
      line-height: 1.5;
    }}
    .card-body ul {{
      padding-left: 18px;
      margin-top: 6px;
    }}
    .card-body li {{
      margin-bottom: 5px;
    }}

    /* Metric Box */
    .metric-box {{
      background: rgba(15, 23, 42, 0.9);
      border: 1px solid var(--border-color);
      border-radius: 10px;
      padding: 12px 14px;
      display: flex;
      flex-direction: column;
      gap: 3px;
    }}
    .metric-value {{
      font-family: var(--font-mono);
      font-size: 1.6rem;
      font-weight: 700;
      color: #fff;
    }}
    .metric-label {{
      font-size: 0.74rem;
      color: var(--text-muted);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }}

    /* Tables */
    .table-clean {{
      width: 100%;
      border-collapse: collapse;
      font-size: 0.78rem;
    }}
    .table-clean th {{
      background: rgba(30, 41, 59, 0.6);
      color: var(--text-muted);
      text-align: left;
      padding: 8px 10px;
      font-weight: 600;
      border-bottom: 1px solid var(--border-color);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-size: 0.7rem;
    }}
    .table-clean td {{
      padding: 8px 10px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
      color: #cbd5e1;
    }}
    .table-clean tr:hover td {{
      background: rgba(255, 255, 255, 0.02);
    }}

    /* Code Block */
    .code-block {{
      background: #040711;
      border: 1px solid rgba(255, 255, 255, 0.08);
      border-radius: 10px;
      padding: 12px 14px;
      font-family: var(--font-mono);
      font-size: 0.76rem;
      line-height: 1.45;
      color: #e2e8f0;
      overflow-x: auto;
      white-space: pre;
    }}
    .code-accent {{ color: var(--accent-cyan); }}
    .code-keyword {{ color: var(--accent-purple); }}
    .code-success {{ color: var(--accent-emerald); }}
    .code-fail {{ color: var(--accent-rose); }}
    .code-warn {{ color: var(--accent-amber); }}

    /* Interactive Visual Architecture Diagram */
    .arch-container {{
      display: flex;
      flex-direction: column;
      gap: 12px;
      height: 100%;
      justify-content: space-between;
    }}
    .arch-row {{
      display: flex;
      gap: 14px;
      align-items: center;
      justify-content: center;
      width: 100%;
    }}
    .arch-node {{
      background: rgba(15, 23, 42, 0.85);
      border: 1px solid var(--border-color);
      border-radius: 10px;
      padding: 10px 14px;
      display: flex;
      flex-direction: column;
      gap: 3px;
      min-width: 200px;
      text-align: center;
      position: relative;
      box-shadow: 0 4px 12px rgba(0,0,0,0.3);
      transition: all 0.2s ease;
    }}
    .arch-node:hover {{
      border-color: var(--accent-cyan);
      transform: translateY(-2px);
    }}
    .arch-node-title {{
      font-size: 0.84rem;
      font-weight: 700;
      color: #fff;
    }}
    .arch-node-sub {{
      font-size: 0.7rem;
      color: var(--text-muted);
      font-family: var(--font-mono);
    }}
    .arch-arrow-down {{
      display: flex;
      justify-content: center;
      align-items: center;
      font-size: 1.1rem;
      color: var(--accent-cyan);
      animation: pulseArrow 2s infinite;
    }}
    @keyframes pulseArrow {{
      0%, 100% {{ opacity: 0.6; transform: translateY(0); }}
      50% {{ opacity: 1; transform: translateY(3px); }}
    }}

    /* Images */
    .img-kpi-container {{
      width: 100%;
      height: 155px;
      background: #020617;
      border-radius: 8px;
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
      border: 1px solid var(--border-color);
      margin: 8px 0;
    }}
    .img-kpi-container img {{
      max-width: 100%;
      max-height: 100%;
      object-fit: contain;
    }}

    /* Drawer for Speaker Defense Notes (N key) */
    aside#defense-notes-drawer {{
      position: fixed;
      top: 55px;
      right: 0;
      width: 440px;
      height: calc(100vh - 105px);
      background: rgba(10, 15, 30, 0.96);
      backdrop-filter: blur(20px);
      border-left: 1px solid var(--border-highlight);
      z-index: 50;
      display: flex;
      flex-direction: column;
      transform: translateX(100%);
      transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1);
      box-shadow: -10px 0 30px rgba(0,0,0,0.6);
      padding: 24px;
      overflow-y: auto;
    }}
    aside#defense-notes-drawer.open {{
      transform: translateX(0);
    }}
    .notes-title {{
      font-size: 1.05rem;
      font-weight: 700;
      color: var(--accent-cyan);
      margin-bottom: 12px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border-color);
      padding-bottom: 8px;
    }}
    .notes-section-title {{
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--accent-purple);
      font-weight: 700;
      margin-top: 14px;
      margin-bottom: 6px;
    }}
    .notes-content {{
      font-size: 0.88rem;
      line-height: 1.6;
      color: #e2e8f0;
    }}
    .notes-content p {{
      margin-bottom: 10px;
    }}
    .notes-content ul {{
      padding-left: 18px;
      margin-bottom: 10px;
    }}
    .notes-content li {{
      margin-bottom: 6px;
    }}
    .trap-box {{
      background: rgba(244, 63, 94, 0.1);
      border: 1px solid rgba(244, 63, 94, 0.3);
      border-radius: 8px;
      padding: 10px 12px;
      margin-top: 10px;
      font-size: 0.8rem;
      color: #fecdd3;
    }}

    /* Grid Overview Modal (G key) */
    #grid-overview-modal {{
      position: fixed;
      inset: 0;
      background: rgba(5, 8, 18, 0.94);
      backdrop-filter: blur(20px);
      z-index: 100;
      display: none;
      flex-direction: column;
      padding: 30px 40px;
      overflow-y: auto;
    }}
    #grid-overview-modal.open {{
      display: flex;
    }}
    .grid-modal-header {{
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 24px;
    }}
    .slide-grid-cards {{
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
      gap: 16px;
    }}
    .grid-slide-thumb {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 14px;
      cursor: pointer;
      display: flex;
      flex-direction: column;
      gap: 6px;
      transition: all 0.2s ease;
    }}
    .grid-slide-thumb:hover {{
      border-color: var(--accent-cyan);
      background: var(--bg-card-hover);
      transform: translateY(-3px);
    }}
    .grid-slide-thumb.active-thumb {{
      border-color: var(--accent-cyan);
      box-shadow: 0 0 15px rgba(56, 189, 248, 0.3);
    }}

    /* Bottom Control Bar */
    footer {{
      position: relative;
      z-index: 30;
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 10px 28px;
      background: rgba(10, 15, 29, 0.88);
      backdrop-filter: blur(16px);
      border-top: 1px solid var(--border-color);
      font-size: 0.8rem;
    }}
    .progress-bar-container {{
      flex: 1;
      max-width: 400px;
      height: 6px;
      background: rgba(30, 41, 59, 0.6);
      border-radius: 999px;
      overflow: hidden;
      margin: 0 20px;
    }}
    .progress-bar-fill {{
      height: 100%;
      background: linear-gradient(90deg, var(--accent-cyan), var(--accent-purple));
      width: 7%;
      transition: width 0.3s ease;
    }}
    .key-hint {{
      background: rgba(255, 255, 255, 0.08);
      padding: 2px 6px;
      border-radius: 4px;
      font-family: var(--font-mono);
      font-size: 0.72rem;
      border: 1px solid rgba(255, 255, 255, 0.12);
    }}

    /* Star Schema ER Diagram Styling */
    .er-diagram {{
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 12px;
      height: 100%;
      justify-content: center;
    }}
    .er-fact {{
      background: linear-gradient(135deg, rgba(30, 58, 138, 0.4), rgba(88, 28, 135, 0.4));
      border: 2px solid var(--accent-cyan);
      border-radius: 12px;
      padding: 12px 18px;
      width: 70%;
      text-align: center;
      box-shadow: 0 0 20px rgba(56, 189, 248, 0.15);
    }}
    .er-dims {{
      display: grid;
      grid-template-columns: repeat(5, 1fr);
      gap: 10px;
      width: 100%;
    }}
    .er-dim {{
      background: rgba(15, 23, 42, 0.85);
      border: 1px solid var(--border-color);
      border-radius: 10px;
      padding: 10px 12px;
      text-align: center;
      font-size: 0.75rem;
    }}

    /* Accordion in Slide 13 */
    .qa-accordion {{
      display: flex;
      flex-direction: column;
      gap: 10px;
      height: 100%;
      overflow-y: auto;
    }}
    .qa-card {{
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 10px;
      padding: 12px 16px;
      cursor: pointer;
      transition: all 0.2s ease;
    }}
    .qa-card:hover {{
      border-color: var(--accent-cyan);
      background: var(--bg-card-hover);
    }}
    .qa-q {{
      font-weight: 700;
      color: #fff;
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 0.88rem;
    }}
    .qa-a {{
      margin-top: 8px;
      font-size: 0.82rem;
      color: #cbd5e1;
      line-height: 1.5;
      display: none;
      border-top: 1px solid var(--border-color);
      padding-top: 8px;
    }}
    .qa-card.open .qa-a {{
      display: block;
    }}

    @media print {{
      body {{
        overflow: visible !important;
        height: auto !important;
        background: #000 !important;
      }}
      header, footer, aside, #grid-overview-modal, .ambient-glow {{
        display: none !important;
      }}
      main#deck-container {{
        height: auto !important;
        overflow: visible !important;
      }}
      .slide {{
        position: relative !important;
        display: flex !important;
        opacity: 1 !important;
        transform: none !important;
        page-break-after: always;
        height: 100vh !important;
        padding: 40px !important;
      }}
    }}
  </style>
</head>
<body>

  <div class="ambient-glow glow-1"></div>
  <div class="ambient-glow glow-2"></div>

  <!-- Top Navigation Header -->
  <header>
    <div class="brand">
      <span class="brand-badge">ETL G01</span>
      <span>Workshop-2: Reliable Batch Data Pipeline</span>
      <span style="color: var(--text-dim);">|</span>
      <span style="font-size: 0.82rem; color: var(--text-muted);">UAO Engineering Defense</span>
    </div>

    <div class="deck-meta">
      <div id="defense-timer" class="timer-badge" onclick="toggleTimer()" title="Click to Pause/Start (Key: T)">
        <span>⏱️</span>
        <span id="timer-display">00:00</span>
      </div>
      <span id="current-slide-num">Slide 1 of 14</span>
    </div>

    <div class="deck-controls">
      <button class="btn-ctrl" onclick="toggleGridOverview()" title="Slide Grid Overview (Key: G)">
        <span>▦</span> Grid
      </button>
      <button class="btn-ctrl" onclick="toggleNotes()" id="btn-notes" title="Toggle Speaker Defense Script (Key: N)">
        <span>💬</span> Notes
      </button>
      <button class="btn-ctrl" onclick="toggleFullscreen()" title="Toggle Fullscreen (Key: F)">
        <span>⛶</span> Fullscreen
      </button>
    </div>
  </header>

  <!-- Main Slide Viewport -->
  <main id="deck-container">

    <!-- ============================================================== -->
    <!-- SLIDE 1: Title & Executive Summary                             -->
    <!-- ============================================================== -->
    <section class="slide active" data-notes="
<p><strong>Opening Script:</strong></p>
<p>'Good morning professors and evaluators. Today I am presenting our implementation of Workshop-2: Building a Reliable Batch Data Pipeline. The problem we solve is the integration of two decoupled, heterogeneous sources: Spotify streaming telemetry and historical Grammy Awards acclaim.'</p>
<div class='notes-section-title'>Core Engineering Axiom</div>
<p>Stress to the panel: 'A Data Engineer does not build scripts. A Data Engineer designs systems.' Emphasize that our system has strict separation of concerns, automated quality gates, and 100% idempotent reruns.</p>
<div class='trap-box'>
<strong>Evaluator Trap:</strong> If asked why this is an 'engineering system' rather than a script, answer: 'Because data validation detects violations while transformation applies known engineering rules; failures are isolated before downstream corruption, and runs are completely reproducible.'
</div>
">
      <div class="slide-header">
        <div>
          <div class="slide-tag">Workshop-2 Defense • 20% Oral Examination</div>
          <h1 class="slide-title" style="font-size: 2.8rem;">Building a Reliable Batch Data Pipeline</h1>
          <p class="slide-subtitle" style="font-size: 1.15rem;">Heterogeneous Music Data Integration: Spotify Streaming Telemetry & Historical Grammy Awards Acclaim</p>
        </div>
        <div class="rubric-pill">Rubric: Sec 10.2 Defense (1.00 pt)</div>
      </div>

      <div class="grid-3" style="margin-top: 12px; height: 55%;">
        <div class="card" style="border-left: 3px solid var(--accent-cyan);">
          <div class="card-title" style="color: var(--accent-cyan);">🏛️ Engineering Philosophy</div>
          <div class="card-body" style="font-size: 0.92rem; line-height: 1.6; margin-top: 8px;">
            <em>"A Data Engineer does not build scripts. A Data Engineer designs systems."</em><br><br>
            Separation of concerns across extraction, automated validation, deterministic transformation, and transactional loading.
          </div>
        </div>

        <div class="card" style="border-left: 3px solid var(--accent-purple);">
          <div class="card-title" style="color: var(--accent-purple);">🛡️ Quality Verification Axiom</div>
          <div class="card-body" style="font-size: 0.92rem; line-height: 1.6; margin-top: 8px;">
            <em>"Reliable pipelines do not assume data is correct. They verify it."</em><br><br>
            Validation detects violations; transformation applies known engineering rules. Modifying data to force a test pass is strictly prohibited.
          </div>
        </div>

        <div class="card" style="border-left: 3px solid var(--accent-emerald);">
          <div class="card-title" style="color: var(--accent-emerald);">🔁 Reliability Defined</div>
          <div class="card-body" style="font-size: 0.92rem; line-height: 1.6; margin-top: 8px;">
            <em>"Reliable does not mean nothing fails. It means failures are anticipated, controlled, and observable."</em><br><br>
            Enforcing selective retries, gated downstream halts, and 100% idempotent repeatability.
          </div>
        </div>
      </div>

      <div style="margin-top: 14px; display: flex; justify-content: space-between; font-size: 0.8rem; color: var(--text-muted); border-top: 1px solid var(--border-color); padding-top: 10px;">
        <span><strong>Course:</strong> ETL (G01) — Faculty of Engineering & Basic Sciences</span>
        <span><strong>Academic Program:</strong> Data Engineering & AI — UAO 2026-2</span>
        <span><strong>Orchestrator:</strong> Apache Airflow 3.1.8 | Great Expectations</span>
      </div>
    </section>

    <!-- ============================================================== -->
    <!-- SLIDE 2: Analytical Requirements & Traceability                -->
    <!-- ============================================================== -->
    <section class="slide" data-notes="
<p><strong>Script:</strong></p>
<p>'In Section 6.1, the brief mandates at least three analytical requirements strictly requiring the combination of both datasets. Spotify provides raw telemetry and streaming popularity; Grammys provides 60+ years of institutional acclaim. Neither dataset alone can answer these questions.'</p>
<div class='notes-section-title'>Key Points to Defend</div>
<ul>
  <li><strong>RQ-01:</strong> Differentiates acoustic fingerprints of winners vs catalog tracks.</li>
  <li><strong>RQ-02:</strong> Measures the commercial uplift across genres (Soul +45.6 pts, Country +23.6 pts).</li>
  <li><strong>RQ-03:</strong> Analyzes temporal shifts in collaborations (35.71% in the 2010s) and explicit lyrics (rising to 20.24%).</li>
</ul>
">
      <div class="slide-header">
        <div>
          <div class="slide-tag">Section 6.1 • Scope & Business Traceability</div>
          <h2 class="slide-title">The Three Analytical Requirements</h2>
          <p class="slide-subtitle">Unifying consumer streaming telemetry with institutional industry accolades through strict traceability.</p>
        </div>
        <div class="rubric-pill">Rubric: Sec 10.1 Req & Arch (0.40 pts)</div>
      </div>

      <div class="grid-3" style="height: 68%;">
        <div class="card">
          <div class="card-header">
            <span class="card-title">RQ-01: Acoustic Profile</span>
            <span class="badge badge-cyan">Perceptual Signals</span>
          </div>
          <div class="card-body">
            <p><strong>Business Question:</strong> Do acoustic attributes (Danceability, Energy, Valence, Acousticness) statistically differentiate Grammy winners from standard catalog songs?</p>
            <ul>
              <li><strong>Required Data:</strong> Spotify audio telemetry + Grammy category & winner status.</li>
              <li><strong>Expected KPI:</strong> Comparative Audio Fingerprint & Feature Ratio.</li>
              <li><strong>DW Grain:</strong> Track, award edition year, and award category.</li>
            </ul>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <span class="card-title">RQ-02: Genre Uplift</span>
            <span class="badge badge-purple">Popularity Telemetry</span>
          </div>
          <div class="card-body">
            <p><strong>Business Question:</strong> What is the popularity multiplier of Grammy acclaim across musical genres?</p>
            <ul>
              <li><strong>Required Data:</strong> Spotify <code>popularity</code> & <code>track_genre</code> + Grammy winner acclaim.</li>
              <li><strong>Expected KPI:</strong> Genre Popularity Uplift Delta (Winners vs. Catalog).</li>
              <li><strong>DW Grain:</strong> Catalog genre and award acclaim tier.</li>
            </ul>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <span class="card-title">RQ-03: Temporal Evolution</span>
            <span class="badge badge-emerald">Historical & Credits</span>
          </div>
          <div class="card-body">
            <p><strong>Business Question:</strong> How have explicit lyrical content and multi-artist collaborations evolved in awarded music across decades?</p>
            <ul>
              <li><strong>Required Data:</strong> Spotify <code>explicit</code> & artist parsing + Grammy historical year.</li>
              <li><strong>Expected KPI:</strong> Explicit Content Share % & Collaboration Ratio.</li>
              <li><strong>DW Grain:</strong> Award edition decade and calendar year.</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <!-- ============================================================== -->
    <!-- SLIDE 3: Evidence-Based Data Profiling                         -->
    <!-- ============================================================== -->
    <section class="slide" data-notes="
<p><strong>Script:</strong></p>
<p>'In Section 6.3, the brief demands evidence-based profiling before writing any transformation code. In our reproducible Jupyter notebook (notebooks/data_profiling.ipynb), we discovered critical empirical anomalies that dictated our exact cleaning rules and validation thresholds.'</p>
<div class='notes-section-title'>Key Empirical Findings</div>
<ul>
  <li>Spotify has 114,000 rows across 114 genres, but only 89,741 unique IDs. 450 duplicate pairs exist on <code>(track_id, track_genre)</code>.</li>
  <li>Row 65,900 contained <code>duration_ms = 0</code> with NaN metadata. We tolerated this at raw (99.9% threshold) and strictly filtered it in transformation.</li>
  <li>Grammys has 4,810 records from 1958-2019, 100% winners, but 1,840 null artists due to classical/craft categories crediting the work in nominee.</li>
</ul>
">
      <div class="slide-header">
        <div>
          <div class="slide-tag">Section 6.3 • Empirical Discovery</div>
          <h2 class="slide-title">Source Data Profiling Findings</h2>
          <p class="slide-subtitle">Empirical insights from <code>notebooks/data_profiling.ipynb</code> driving our cleaning rules and quality thresholds.</p>
        </div>
        <div class="rubric-pill">Rubric: Sec 10.1 Profiling (0.60 pts)</div>
      </div>

      <div class="grid-2" style="height: 68%;">
        <div class="card">
          <div class="card-header">
            <span class="card-title">🎧 Spotify Dataset Profiling</span>
            <span class="badge badge-cyan">114,000 Records (CSV)</span>
          </div>
          <div class="card-body">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px;">
              <div class="metric-box">
                <span class="metric-value">89,741</span>
                <span class="metric-label">Unique Track IDs</span>
              </div>
              <div class="metric-box">
                <span class="metric-value" style="color: var(--accent-amber);">450</span>
                <span class="metric-label">Duplicate Tuples</span>
              </div>
            </div>
            <ul>
              <li><strong>Grain Ambiguity:</strong> 24,259 tracks appear in multiple genres; exactly 450 duplicate pairs on <code>(track_id, track_genre)</code>.</li>
              <li><strong>Physical Outlier:</strong> Row 65,900 had <code>duration_ms = 0</code> and NaN track metadata.</li>
              <li><strong>Audio Bounds:</strong> Valence, Danceability, and Energy strictly within $[0.0, 1.0]$.</li>
              <li><strong>Collaborations:</strong> Artists delimited by semicolons (<code>;</code>) in Spotify.</li>
            </ul>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <span class="card-title">🏆 Grammy Awards Profiling</span>
            <span class="badge badge-purple">4,810 Records (Relational DB)</span>
          </div>
          <div class="card-body">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px;">
              <div class="metric-box">
                <span class="metric-value" style="color: var(--accent-emerald);">0</span>
                <span class="metric-label">Grain Duplicates</span>
              </div>
              <div class="metric-box">
                <span class="metric-value">100%</span>
                <span class="metric-label">Historical Winners</span>
              </div>
            </div>
            <ul>
              <li><strong>Operational Constraint:</strong> Seeded into PostgreSQL <code>source_music_db</code>; extracted strictly via SQL.</li>
              <li><strong>Missing Artists:</strong> 1,840 records lack artist names because classical and producer categories credit the work in <code>nominee</code>.</li>
              <li><strong>Temporal Span:</strong> Valid historical span from 1958 to 2019 across 638 distinct categories.</li>
              <li><strong>Collaborative Tokens:</strong> Multi-artist credits use tokens like <code>featuring</code>, <code>&</code>, and <code>with</code>.</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <!-- ============================================================== -->
    <!-- SLIDE 4: End-to-End System Architecture                        -->
    <!-- ============================================================== -->
    <section class="slide" data-notes="
<p><strong>Script:</strong></p>
<p>'Here is our end-to-end architecture conforming to Section 5. Notice the two independent source branches. Spotify reads CSV; Grammys extracts from PostgreSQL through SQL as required by Section 4.3. Both branches undergo independent Great Expectations Raw Validation. If and only if both pass, they converge into Transformation, followed by Prepared Validation, and an idempotent load to PostgreSQL DW.'</p>
<div class='notes-section-title'>Architectural Highlights</div>
<ul>
  <li>Decoupled extraction: Independent parallel branches maximize throughput and isolate failures.</li>
  <li>Parquet Staging: Large DataFrames are NEVER passed via XCom; only file paths and compact metadata dictionaries are transferred.</li>
  <li>Gated Downstream: A failure in either raw gate immediately aborts transformation and loading.</li>
</ul>
">
      <div class="slide-header">
        <div>
          <div class="slide-tag">Section 5 & 6.7 • End-to-End Architecture</div>
          <h2 class="slide-title">Reliable Pipeline Architecture</h2>
          <p class="slide-subtitle">Two independent observable source branches converging through gated automated quality checkpoints.</p>
        </div>
        <div class="rubric-pill">Rubric: Sec 10.2 Architecture (0.35 pts)</div>
      </div>

      <div class="card" style="height: 70%; justify-content: center; background: #030712; padding: 20px;">
        <div class="arch-container">
          <!-- Row 1: Sources -->
          <div class="arch-row">
            <div class="arch-node" style="border-color: var(--accent-cyan);">
              <span class="badge badge-cyan" style="width: fit-content; margin: 0 auto;">Source 1: CSV File</span>
              <span class="arch-node-title">Spotify Dataset</span>
              <span class="arch-node-sub">spotify_dataset.csv (114,000 rows)</span>
            </div>
            <div style="width: 80px;"></div>
            <div class="arch-node" style="border-color: var(--accent-purple);">
              <span class="badge badge-purple" style="width: fit-content; margin: 0 auto;">Source 2: Relational DB</span>
              <span class="arch-node-title">Grammy Awards</span>
              <span class="arch-node-sub">source_music_db.grammy_awards (SQL Query)</span>
            </div>
          </div>

          <div class="arch-row">
            <div class="arch-arrow-down" style="width: 200px;">↓</div>
            <div style="width: 80px;"></div>
            <div class="arch-arrow-down" style="width: 200px;">↓</div>
          </div>

          <!-- Row 2: Raw Validation Gates -->
          <div class="arch-row">
            <div class="arch-node" style="border-color: var(--accent-emerald);">
              <span class="badge badge-emerald" style="width: fit-content; margin: 0 auto;">Raw Quality Gate 1</span>
              <span class="arch-node-title">validate_spotify_raw</span>
              <span class="arch-node-sub">Great Expectations: DQ-RAW-SPT-01..06</span>
            </div>
            <div style="width: 80px;"></div>
            <div class="arch-node" style="border-color: var(--accent-emerald);">
              <span class="badge badge-emerald" style="width: fit-content; margin: 0 auto;">Raw Quality Gate 2</span>
              <span class="arch-node-title">validate_grammys_raw</span>
              <span class="arch-node-sub">Great Expectations: DQ-RAW-GRM-01..04</span>
            </div>
          </div>

          <div class="arch-row">
            <div style="display: flex; align-items: center; justify-content: center; width: 100%; color: var(--accent-cyan); font-size: 0.82rem; font-weight: 600;">
              <span>Convergence Barrier (Both Raw Gates Must PASS) ────▼</span>
            </div>
          </div>

          <!-- Row 3: Transformation & Prepared Gate -->
          <div class="arch-row">
            <div class="arch-node" style="border-color: var(--accent-indigo); min-width: 420px;">
              <span class="badge badge-indigo" style="width: fit-content; margin: 0 auto;">Convergence & Harmonization</span>
              <span class="arch-node-title">transform_and_integrate</span>
              <span class="arch-node-sub">Cleaning, Primary Artist Parsing, Integration Contract (N-to-1)</span>
            </div>
          </div>

          <div class="arch-row">
            <div class="arch-arrow-down">↓</div>
          </div>

          <!-- Row 4: DW Load -->
          <div class="arch-row">
            <div class="arch-node" style="border-color: var(--accent-amber); min-width: 420px;">
              <span class="badge badge-amber" style="width: fit-content; margin: 0 auto;">Prepared Quality Gate & DW Upsert</span>
              <span class="arch-node-title">validate_prepared ➔ load_dw</span>
              <span class="arch-node-sub">GX DQ-PREP-INT-01..08 ➔ dw_music_analytics (Star Schema ON CONFLICT DO UPDATE)</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ============================================================== -->
    <!-- SLIDE 5: Great Expectations Validation Gates                   -->
    <!-- ============================================================== -->
    <section class="slide" data-notes="
<p><strong>Script:</strong></p>
<p>'Section 6.5 requires at least six rules mapped to explicit severities. We designed 18 rules in Great Expectations across two raw gates and the prepared gate, each run through a Suite, a Validation Definition and a Checkpoint. Critical severities halt the pipeline immediately without retrying. Warning severities log actionable diagnostic audit trails without blocking execution.'</p>
<div class='notes-section-title'>Operational Quality Policies</div>
<ul>
  <li><strong>Critical Rules:</strong> Non-null track IDs, duration > 1,000ms (99.9% tolerance in raw), valid Grammy years [1958-2026], and audio bounds [0.0, 1.0].</li>
  <li><strong>Warning Rules:</strong> Grammy nominee completeness (6 nulls), Spotify (track, genre) duplicates below 1%, match rate below 5%.</li>
  <li><strong>Audit Trails:</strong> Machine-readable JSON logs preserved in <code>gx/results/</code>.</li>
</ul>
">
      <div class="slide-header">
        <div>
          <div class="slide-tag">Section 6.5 & 6.6 • Quality Engineering</div>
          <h2 class="slide-title">Great Expectations Validation Gates</h2>
          <p class="slide-subtitle">18 quality rules (13 Critical, 3 Warning, 2 Informational) across Raw and Prepared gates.</p>
        </div>
        <div class="rubric-pill">Rubric: Sec 10.1 GX Validation (0.80 pts)</div>
      </div>

      <div class="card" style="height: 70%;">
        <table class="table-clean">
          <thead>
            <tr>
              <th>Rule ID</th>
              <th>Gate / Layer</th>
              <th>Target Attribute</th>
              <th>Quality Dimension</th>
              <th>Severity</th>
              <th>Operational Threshold & GX Expectation</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td><strong class="code-accent">DQ-RAW-SPT-05 · GRM-03 · PREP-INT-03</strong></td>
              <td>All gates</td>
              <td>schema</td>
              <td>Conformity</td>
              <td><span class="badge badge-rose">Critical</span></td>
              <td>Required columns present / exact load contract (<code>expect_table_columns_to_match_set</code>)</td>
            </tr>
            <tr>
              <td><strong class="code-accent">DQ-RAW-SPT-01</strong></td>
              <td>Spotify Raw</td>
              <td><code>track_id</code></td>
              <td>Completeness</td>
              <td><span class="badge badge-rose">Critical</span></td>
              <td>100% non-null</td>
            </tr>
            <tr>
              <td><strong class="code-accent">DQ-RAW-SPT-02</strong></td>
              <td>Spotify Raw</td>
              <td><code>duration_ms</code></td>
              <td>Validity</td>
              <td><span class="badge badge-rose">Critical</span></td>
              <td>&gt; 1,000 ms in &ge; 99.9% (1 corrupted row found)</td>
            </tr>
            <tr>
              <td><strong class="code-accent">DQ-RAW-SPT-03 · 04</strong></td>
              <td>Spotify Raw</td>
              <td>4 audio features · popularity</td>
              <td>Range</td>
              <td><span class="badge badge-rose">Critical</span></td>
              <td>[0, 1] and [0, 100], 100%</td>
            </tr>
            <tr>
              <td><strong class="code-accent">DQ-RAW-SPT-06</strong></td>
              <td>Spotify Raw</td>
              <td>(track_id, track_genre)</td>
              <td>Uniqueness</td>
              <td><span class="badge badge-amber">Warning</span></td>
              <td>&ge; 99% unique (450 dups = 0.39%, removed by TR-03)</td>
            </tr>
            <tr>
              <td><strong class="code-accent">DQ-RAW-GRM-01</strong></td>
              <td>Grammys Raw</td>
              <td><code>year</code></td>
              <td>Temporal validity</td>
              <td><span class="badge badge-rose">Critical</span></td>
              <td>[1958, 2026], 100% &mdash; <strong>Test B</strong></td>
            </tr>
            <tr>
              <td><strong class="code-accent">DQ-RAW-GRM-02 · 04</strong></td>
              <td>Grammys Raw</td>
              <td><code>nominee</code> · row count</td>
              <td>Completeness · Volume</td>
              <td><span class="badge badge-amber">Warning / Info</span></td>
              <td>&ge; 99.5% non-null · 4,000&ndash;10,000 rows</td>
            </tr>
            <tr>
              <td><strong class="code-accent">DQ-PREP-INT-02 · 04</strong></td>
              <td>Prepared</td>
              <td>keys · ranges</td>
              <td>Completeness · Validity</td>
              <td><span class="badge badge-rose">Critical</span></td>
              <td>Keys non-null; ranges hold after transform (no tolerance)</td>
            </tr>
            <tr>
              <td><strong class="code-accent">DQ-PREP-INT-05</strong></td>
              <td>Prepared</td>
              <td>fact grain</td>
              <td>Uniqueness</td>
              <td><span class="badge badge-rose">Critical</span></td>
              <td>(track, genre, year, category) unique</td>
            </tr>
            <tr>
              <td><strong class="code-accent">DQ-PREP-INT-06 · 07</strong></td>
              <td>Prepared</td>
              <td>award fields</td>
              <td>Integration integrity</td>
              <td><span class="badge badge-rose">Critical</span></td>
              <td>Matched &rArr; valid year &amp; award_count &ge; 1; unmatched &rArr; year 0; both tiers exist</td>
            </tr>
            <tr>
              <td><strong class="code-accent">DQ-PREP-INT-08 · 01</strong></td>
              <td>Prepared</td>
              <td><code>is_grammy_winner</code></td>
              <td>Plausibility · Domain</td>
              <td><span class="badge badge-amber">Warning / Info</span></td>
              <td>Match rate &le; 5% (observed 0.42%) · boolean</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>

    <!-- ============================================================== -->
    <!-- SLIDE 6: Transformation & The Integration Contract             -->
    <!-- ============================================================== -->
    <section class="slide" data-notes="
<p><strong>Script:</strong></p>
<p>'Section 6.8 emphasizes that integration is not just a blind merge; it is a formal data contract. We established a normalized composite matching key pair: clean track name and clean primary artist.'</p>
<div class='notes-section-title'>Integration Contract Details</div>
<ul>
  <li>Matching Keys: <code>(clean_track_name, clean_primary_artist)</code> after stripping punctuation, lowercase conversion, and trimming.</li>
  <li>Collaborative Tokens: Splitting <code>;</code> in Spotify and <code>featuring</code>, <code>&</code>, <code>with</code> in Grammys.</li>
  <li>Cardinality: N-to-1 (tracks appearing in multiple genres map to the same award honor).</li>
  <li>Unmatched Catalog Rows: Preserved via Left Join with <code>is_grammy_winner=False</code> and mapped to surrogate key 0 in dimension tables.</li>
</ul>
">
      <div class="slide-header">
        <div>
          <div class="slide-tag">Section 6.8 • Integration Contract</div>
          <h2 class="slide-title">Transformation & The Integration Contract</h2>
          <p class="slide-subtitle">A formal contract specifying matching keys, cardinality, text normalization, and unmatched record policies.</p>
        </div>
        <div class="rubric-pill">Rubric: Sec 10.1 ETL Transformation (0.60 pts)</div>
      </div>

      <div class="grid-2" style="height: 68%;">
        <div class="card">
          <div class="card-header">
            <span class="card-title">🧼 Evidence-Based Cleaning</span>
            <span class="badge badge-cyan">Preprocessing</span>
          </div>
          <div class="card-body">
            <ul>
              <li><strong>Duplicate Pruning:</strong> Removed 450 duplicate rows on <code>(track_id, track_genre)</code> identified during profiling.</li>
              <li><strong>Corrupted Outlier Filter:</strong> Filtered row 65,900 with duration = 0 ms and NaN track metadata.</li>
              <li><strong>Textual Normalization:</strong> Stripped punctuation, converted to lowercase, and trimmed redundant whitespace.</li>
              <li><strong>Artist Parsing:</strong> Extracted primary artist by splitting on <code>;</code> for Spotify and collaborative tokens (<code>featuring</code>, <code>&</code>, <code>with</code>) for Grammys.</li>
            </ul>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <span class="card-title">🤝 The Integration Contract</span>
            <span class="badge badge-purple">Data Contract</span>
          </div>
          <div class="card-body">
            <ul>
              <li><strong>Matching Keys:</strong> <code>(clean_track_name, clean_primary_artist)</code>.</li>
              <li><strong>Cardinality:</strong> N-to-1 (multi-genre catalog tracks map to a single award honor).</li>
              <li><strong>Unmatched Catalog Rows:</strong> Preserved via Left Join with <code>is_grammy_winner = False</code>, <code>award_count = 0</code>, mapped to default surrogate key 0.</li>
              <li><strong>Reconciliation Result:</strong> 113,549 prepared tracks with 475 confirmed Grammy-winning tracks (0.42% of catalog).</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <!-- ============================================================== -->
    <!-- SLIDE 7: Star Schema Data Warehouse Modeling                   -->
    <!-- ============================================================== -->
    <section class="slide" data-notes="
<p><strong>Script:</strong></p>
<p>'In Section 6.4 and 6.10, we implemented our star schema in PostgreSQL dw_music_analytics. SQLite was explicitly rejected because it lacks concurrent upsert locking and was forbidden in the workshop brief. The grain is one row per audio track, catalog genre, and award edition.'</p>
<div class='notes-section-title'>Key Schema Engineering</div>
<ul>
  <li>Surrogate Keys: <code>SERIAL</code> autoincrementing integers across all 5 dimensions.</li>
  <li>Default Dimension Records: SK = 0 created for <code>dim_time</code> ('Unknown') and <code>dim_grammy_category</code> ('Not Applicable').</li>
  <li>Idempotency Invariant: <code>CONSTRAINT uq_fact_grain UNIQUE (track_sk, genre_sk, time_sk, category_sk)</code>.</li>
</ul>
">
      <div class="slide-header">
        <div>
          <div class="slide-tag">Section 6.4 & 6.10 • Dimensional Modeling</div>
          <h2 class="slide-title">Star Schema Data Warehouse in PostgreSQL</h2>
          <p class="slide-subtitle">Requirements-driven dimensional model hosted in <code>dw_music_analytics</code> (SQLite strictly rejected).</p>
        </div>
        <div class="rubric-pill">Rubric: Sec 10.1 Dimensional DW (0.40 pts)</div>
      </div>

      <div class="grid-2" style="height: 68%;">
        <div class="card">
          <div class="card-header">
            <span class="card-title">⭐ Fact & Dimension Grain</span>
            <span class="badge badge-emerald">PostgreSQL 16</span>
          </div>
          <div class="card-body">
            <div class="er-diagram">
              <div class="er-fact">
                <strong style="color: var(--accent-cyan); font-size: 0.95rem;">fact_music_performance</strong><br>
                <span style="font-size: 0.72rem; color: #cbd5e1;">Grain: 1 row per track, catalog genre, and award edition</span><br>
                <span style="font-size: 0.7rem; color: var(--accent-amber);">Measures: popularity, danceability, energy, valence, is_grammy_winner</span>
              </div>
              <div style="color: var(--accent-cyan); font-size: 0.9rem;">▲ Foreign Keys (Surrogate Keys) ▲</div>
              <div class="er-dims">
                <div class="er-dim"><strong style="color: #fff;">dim_artist</strong><br>artist_sk (PK)<br>artist_name</div>
                <div class="er-dim"><strong style="color: #fff;">dim_track</strong><br>track_sk (PK)<br>track_id</div>
                <div class="er-dim"><strong style="color: #fff;">dim_genre</strong><br>genre_sk (PK)<br>genre_name</div>
                <div class="er-dim"><strong style="color: #fff;">dim_time</strong><br>time_sk (PK)<br>year, decade</div>
                <div class="er-dim"><strong style="color: #fff;">dim_grammy_category</strong><br>category_sk (PK)<br>category_name</div>
              </div>
            </div>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <span class="card-title">🔒 Production Data Warehouse Standards</span>
            <span class="badge badge-cyan">PostgreSQL vs SQLite</span>
          </div>
          <div class="card-body">
            <ul>
              <li><strong>Why SQLite Was Banned:</strong> SQLite lacks row-level locking, concurrent writes, and production ANSI SQL capabilities.</li>
              <li><strong>Composite Unique Grain Constraint:</strong>
                <div class="code-block" style="font-size: 0.72rem; margin: 6px 0;">CONSTRAINT uq_fact_grain UNIQUE (track_sk, genre_sk, time_sk, category_sk)</div>
              </li>
              <li><strong>Surrogate Keys:</strong> Pure <code>SERIAL</code> autoincrementing integers decoupled from operational source natural keys.</li>
              <li><strong>Special Dimension Keys:</strong> Default SK = 0 inserted for non-awarded catalog tracks, avoiding NULL foreign keys.</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <!-- ============================================================== -->
    <!-- SLIDE 8: Airflow 3.1.8 & Selective Retries                     -->
    <!-- ============================================================== -->
    <section class="slide" data-notes="
<p><strong>Script:</strong></p>
<p>'Section 6.11 requires orchestration using Apache Airflow 3.1.8 with the modern TaskFlow API. We imported dag and task directly from airflow.sdk. We strictly avoided blanket retries (retries=3). Transient I/O and DB connections receive 2 retries; deterministic data validation failures receive 0 retries.'</p>
<div class='notes-section-title'>Core Defense Points</div>
<ul>
  <li>TaskFlow API: Modern functional paradigm with automatic dependency inference.</li>
  <li>Selective Retries: Blanket retries hide bugs and waste compute on deterministic failures.</li>
  <li>Zero XCom Data Passing: DataFrames are persisted as Parquet; only URIs travel through XCom.</li>
</ul>
">
      <div class="slide-header">
        <div>
          <div class="slide-tag">Section 6.11 • Modern Orchestration</div>
          <h2 class="slide-title">Apache Airflow 3.1.8 & TaskFlow API</h2>
          <p class="slide-subtitle">Executable dependency model with justified selective retry policies and zero XCom bulk transport.</p>
        </div>
        <div class="rubric-pill">Rubric: Sec 10.1 Airflow Reliability (0.90 pts)</div>
      </div>

      <div class="grid-2" style="height: 68%;">
        <div class="card">
          <div class="card-header">
            <span class="card-title">⚡ Airflow 3.1.8 TaskFlow API</span>
            <span class="badge badge-cyan">airflow.sdk</span>
          </div>
          <div class="card-body">
            <div class="code-block" style="font-size: 0.74rem;">
<span class="code-keyword">from</span> airflow.sdk <span class="code-keyword">import</span> dag, task

<span class="code-accent">@dag</span>(dag_id=<span class="code-success">"reliable_music_pipeline"</span>, schedule=<span class="code-keyword">None</span>)
<span class="code-keyword">def</span> reliable_music_pipeline():
    s_raw = extract_spotify_task()
    s_val = validate_spotify_raw_task(s_raw)

    g_raw = extract_grammys_task()
    g_val = validate_grammys_raw_task(g_raw)

    prep = transform_and_integrate_task(s_val, g_val)
    prep_val = validate_prepared_task(prep)
    load_dw_task(prep_val)
            </div>
            <p style="margin-top: 10px; font-size: 0.8rem; color: var(--text-muted);">
              ✅ Pure reference-passing: only file paths and compact metadata dictionaries are passed through task interfaces.
            </p>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <span class="card-title">🎯 Selective Retry Policy</span>
            <span class="badge badge-purple">No Blanket Retries</span>
          </div>
          <div class="card-body">
            <table class="table-clean" style="font-size: 0.74rem;">
              <tr><th>Task</th><th>Failure Class</th><th>Retries</th><th>Reasoning</th></tr>
              <tr>
                <td><code>extract_spotify</code></td>
                <td>Transient I/O</td>
                <td><strong class="code-accent">2</strong></td>
                <td>Mount latency resolves on retry.</td>
              </tr>
              <tr>
                <td><code>extract_grammys</code></td>
                <td>Transient DB</td>
                <td><strong class="code-accent">2</strong></td>
                <td>PostgreSQL socket recovery.</td>
              </tr>
              <tr>
                <td><code>validate_*_raw</code></td>
                <td>Deterministic DQ</td>
                <td><strong class="code-fail">0</strong></td>
                <td>Corrupt data fails identically; stop immediately.</td>
              </tr>
              <tr>
                <td><code>validate_prepared</code></td>
                <td>Deterministic DQ</td>
                <td><strong class="code-fail">0</strong></td>
                <td>Prevents corrupt data entering DW.</td>
              </tr>
              <tr>
                <td><code>load_dw</code></td>
                <td>Transient Lock</td>
                <td><strong class="code-accent">1</strong></td>
                <td>Deadlock clear on second attempt.</td>
              </tr>
            </table>
          </div>
        </div>
      </div>
    </section>

    <!-- ============================================================== -->
    <!-- SLIDE 9: Reliability Test A — Successful Run                   -->
    <!-- ============================================================== -->
    <section class="slide" data-notes="
<p><strong>Script:</strong></p>
<p>'Now we present Test A: Successful Execution. Running the complete pipeline end-to-end under manual run ID 2026-10-07. All 7 tasks succeeded in 39.14 seconds. The Data Warehouse loaded 113,549 fact rows, 475 winners, 17,645 artists, and 89,740 tracks without a single error.'</p>
<div class='notes-section-title'>Key Execution Numbers</div>
<ul>
  <li>Runtime: 39.14 seconds.</li>
  <li>Referential Integrity: 100% resolved foreign keys with 0 orphaned records.</li>
  <li>Validation: Both raw gates and prepared gate evaluated and passed under documented policies.</li>
</ul>
">
      <div class="slide-header">
        <div>
          <div class="slide-tag">Section 7.1 • Reliability Test A</div>
          <h2 class="slide-title">Test A: Successful End-to-End Run</h2>
          <p class="slide-subtitle">Complete pipeline execution passing all raw and prepared validation gates in 39.1 seconds.</p>
        </div>
        <div class="rubric-pill">Rubric: Sec 10.2 Test Demo (0.30 pts)</div>
      </div>

      <div class="grid-2" style="height: 68%;">
        <div class="card">
          <div class="card-header">
            <span class="card-title">⏱️ Airflow Execution Timestamps</span>
            <span class="badge badge-emerald">State: SUCCESS (39.1s)</span>
          </div>
          <div class="card-body">
            <table class="table-clean" style="font-size: 0.74rem;">
              <tr><th>Task Instance</th><th>State</th><th>Duration</th></tr>
              <tr><td><code>extract_spotify</code></td><td><span class="badge badge-emerald">success</span></td><td>3.8s</td></tr>
              <tr><td><code>extract_grammys</code></td><td><span class="badge badge-emerald">success</span></td><td>3.4s</td></tr>
              <tr><td><code>validate_spotify_raw</code></td><td><span class="badge badge-emerald">success</span></td><td>9.6s</td></tr>
              <tr><td><code>validate_grammys_raw</code></td><td><span class="badge badge-emerald">success</span></td><td>9.1s</td></tr>
              <tr><td><code>transform_and_integrate</code></td><td><span class="badge badge-emerald">success</span></td><td>1.9s</td></tr>
              <tr><td><code>validate_prepared</code></td><td><span class="badge badge-emerald">success</span></td><td>5.7s</td></tr>
              <tr><td><code>load_dw</code></td><td><span class="badge badge-emerald">success</span></td><td>16.5s</td></tr>
            </table>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <span class="card-title">📦 Data Warehouse Loaded Metrics</span>
            <span class="badge badge-cyan">dw_music_analytics</span>
          </div>
          <div class="card-body">
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 12px;">
              <div class="metric-box">
                <span class="metric-value" style="color: var(--accent-emerald);">113,549</span>
                <span class="metric-label">Fact Rows Loaded</span>
              </div>
              <div class="metric-box">
                <span class="metric-value" style="color: var(--accent-cyan);">475</span>
                <span class="metric-label">Grammy Winning Tracks</span>
              </div>
              <div class="metric-box">
                <span class="metric-value">17,645</span>
                <span class="metric-label">Unique Artists</span>
              </div>
              <div class="metric-box">
                <span class="metric-value">89,740</span>
                <span class="metric-label">Unique Tracks</span>
              </div>
            </div>
            <p style="font-size: 0.8rem; color: #cbd5e1;">
              ✅ 100% referential integrity verified. All foreign keys resolved to dimensional surrogate keys without orphaned records.
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- ============================================================== -->
    <!-- SLIDE 10: Reliability Test B — Controlled Failure              -->
    <!-- ============================================================== -->
    <section class="slide" data-notes="
<p><strong>Script:</strong></p>
<p>'Test B proves controlled failure behavior. In Section 7.2, we intentionally injected year=1800 into the PostgreSQL Grammy source table. When the DAG ran, validate_grammys_raw failed immediately. As a result, transform_and_integrate, validate_prepared, and load_dw were automatically blocked with upstream_failed, protecting the Data Warehouse.'</p>
<div class='notes-section-title'>Key Evaluation Arguments</div>
<ul>
  <li>Immediate halt: Zero retries because this is a deterministic data error.</li>
  <li>Zero DW poisoning: The Data Warehouse was never touched by corrupt rows.</li>
  <li>Audit logs: Great Expectations output a full diagnostic JSON in <code>gx/results/</code>.</li>
</ul>
">
      <div class="slide-header">
        <div>
          <div class="slide-tag">Section 7.2 • Reliability Test B</div>
          <h2 class="slide-title">Test B: Controlled Critical Quality Failure</h2>
          <p class="slide-subtitle">Demonstrating automated failure isolation: halting execution and protecting the analytical store.</p>
        </div>
        <div class="rubric-pill">Rubric: Sec 10.2 Test Demo (0.30 pts)</div>
      </div>

      <div class="grid-2" style="height: 68%;">
        <div class="card">
          <div class="card-header">
            <span class="card-title">🛑 Airflow Task States: Downstream Block</span>
            <span class="badge badge-rose">Controlled Halt</span>
          </div>
          <div class="card-body">
            <table class="table-clean" style="font-size: 0.74rem;">
              <tr><th>Task ID</th><th>Observed State</th><th>Engineering Behavior</th></tr>
              <tr><td><code>extract_grammys</code></td><td><span class="badge badge-emerald">success</span></td><td>Extracted batch from PostgreSQL</td></tr>
              <tr><td><code>validate_grammys_raw</code></td><td><span class="badge badge-rose">failed</span></td><td><strong>DQ-RAW-GRM-01 Violated (Year=1800)</strong></td></tr>
              <tr><td><code>transform_and_integrate</code></td><td><span class="badge badge-amber">upstream_failed</span></td><td><strong>BLOCKED: Did not proceed</strong></td></tr>
              <tr><td><code>validate_prepared</code></td><td><span class="badge badge-amber">upstream_failed</span></td><td><strong>BLOCKED: Did not proceed</strong></td></tr>
              <tr><td><code>load_dw</code></td><td><span class="badge badge-amber">upstream_failed</span></td><td><strong>BLOCKED: DW Protected</strong></td></tr>
            </table>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <span class="card-title">📋 Great Expectations Audit Evidence</span>
            <span class="badge badge-cyan">grammys_raw_validation.json</span>
          </div>
          <div class="card-body">
            <div class="code-block" style="font-size: 0.7rem;">
{{
  <span class="code-keyword">"dataset"</span>: <span class="code-success">"grammys_raw"</span>,
  <span class="code-keyword">"success"</span>: <span class="code-fail">false</span>,
  <span class="code-keyword">"rules_evaluated"</span>: [{{
    <span class="code-keyword">"rule_description"</span>: <span class="code-fail">"DQ-RAW-GRM-01 [Critical]: Year must fall in [1958, 2026]."</span>,
    <span class="code-keyword">"success"</span>: <span class="code-fail">false</span>,
    <span class="code-keyword">"observed_value"</span>: {{
      <span class="code-keyword">"unexpected_count"</span>: 1,
      <span class="code-keyword">"partial_unexpected_list"</span>: [<span class="code-fail">1800</span>]
    }}
  }}]
}}
            </div>
            <p style="margin-top: 10px; font-size: 0.8rem; color: #cbd5e1;">
              ✅ Machine-readable diagnostic evidence preserved in <code>gx/results/</code>. Downstream load prevented.
            </p>
          </div>
        </div>
      </div>
    </section>

    <!-- ============================================================== -->
    <!-- SLIDE 11: Reliability Test C — Safe Rerun & Idempotency        -->
    <!-- ============================================================== -->
    <section class="slide" data-notes="
<p><strong>Script:</strong></p>
<p>'Test C satisfies Section 7.3: Repeatability and Safe Rerun. We ran the exact same batch twice. Before rerun: 113,549 rows. After rerun: exactly 113,549 rows. Popularity sum: 3,783,956 before and after; 0 inserted, 113,549 updated. This proves our composite grain unique constraint and ON CONFLICT DO UPDATE upsert completely prevents silent duplication.'</p>
<div class='notes-section-title'>Mathematical Verification</div>
<ul>
  <li>Fact table net discrepancy: exactly 0 rows.</li>
  <li>Popularity measure sum net discrepancy: exactly 0.0.</li>
  <li>Danceability mean net discrepancy: exactly 0.0.</li>
</ul>
">
      <div class="slide-header">
        <div>
          <div class="slide-tag">Section 7.3 • Reliability Test C</div>
          <h2 class="slide-title">Test C: Repeatability & Safe Rerun</h2>
          <p class="slide-subtitle">Empirical proof of 100% idempotency: repeated execution creates zero unintended duplicates.</p>
        </div>
        <div class="rubric-pill">Rubric: Sec 10.2 Test Demo (0.30 pts)</div>
      </div>

      <div class="grid-2" style="height: 68%;">
        <div class="card">
          <div class="card-header">
            <span class="card-title">🔁 Before vs. After Rerun Comparison</span>
            <span class="badge badge-emerald">0 Discrepancy</span>
          </div>
          <div class="card-body">
            <table class="table-clean" style="font-size: 0.74rem;">
              <tr><th>Target Metric</th><th>Run 1 Count</th><th>Rerun 2 Count</th><th>Net Discrepancy</th></tr>
              <tr><td><code>fact_music_performance</code></td><td>113,549</td><td>113,549</td><td><strong class="code-success">0 (Exact)</strong></td></tr>
              <tr><td>Awarded Tracks (Winners)</td><td>475</td><td>475</td><td><strong class="code-success">0 (Exact)</strong></td></tr>
              <tr><td><code>dim_artist</code> Records</td><td>17,645</td><td>17,645</td><td><strong class="code-success">0 (Exact)</strong></td></tr>
              <tr><td><code>dim_track</code> Records</td><td>89,740</td><td>89,740</td><td><strong class="code-success">0 (Exact)</strong></td></tr>
              <tr><td>Sum of <code>popularity</code></td><td>3,783,956</td><td>3,783,956</td><td><strong class="code-success">0.0 (Invariant)</strong></td></tr>
              <tr><td>Mean of <code>danceability</code></td><td>0.5670</td><td>0.5670</td><td><strong class="code-success">0.0 (Invariant)</strong></td></tr>
            </table>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <span class="card-title">🔒 Architectural Mechanism</span>
            <span class="badge badge-cyan">Atomic Upsert</span>
          </div>
          <div class="card-body">
            <div class="code-block" style="font-size: 0.7rem; margin-bottom: 8px;">
<span class="code-keyword">INSERT INTO</span> fact_music_performance (...)
<span class="code-keyword">SELECT</span> ... <span class="code-keyword">FROM</span> temp_prepared_staging
<span class="code-accent">ON CONFLICT</span> (track_sk, genre_sk, time_sk, category_sk) 
<span class="code-keyword">DO UPDATE SET</span>
  popularity = EXCLUDED.popularity,
  danceability = EXCLUDED.danceability,
  is_grammy_winner = EXCLUDED.is_grammy_winner,
  loaded_at = CURRENT_TIMESTAMP;
            </div>
            <ul>
              <li><strong>Atomic Rollback:</strong> Partial failures roll back cleanly in transaction blocks.</li>
              <li><strong>Zero Poisoning:</strong> Re-executing never inflates metrics or corrupts aggregations.</li>
            </ul>
          </div>
        </div>
      </div>
    </section>

    <!-- ============================================================== -->
    <!-- SLIDE 12: Business Intelligence & The 3 Visual KPIs            -->
    <!-- ============================================================== -->
    <section class="slide" data-notes="
<p><strong>Script:</strong></p>
<p>'Section 8.1 requires at least 3 KPIs and 3 visualizations querying the DW directly. Direct CSV connections were avoided. KPI 1 shows Grammy winners have higher Valence (0.53 vs 0.47) and +12.04 popularity points (282 distinct awarded tracks). KPI 2 shows Soul and Country have the highest popularity multiplier (+45.6 and +23.6 pts). KPI 3 shows explicit lyrics rose from 0% pre-1990 to 20.24% in the 2010s, with collaborations hitting 35.71%.'</p>
<div class='notes-section-title'>Key Analytical Insights</div>
<ul>
  <li>KPI 1: Winners are systematically more energetic, cheerful, and popular.</li>
  <li>KPI 2: Niche genres benefit most from institutional awards.</li>
  <li>KPI 3: Modern music production heavily shifts towards collaborative feature tracks.</li>
</ul>
">
      <div class="slide-header">
        <div>
          <div class="slide-tag">Section 8.1 • Business Intelligence</div>
          <h2 class="slide-title">Data Warehouse Analytics & Insights</h2>
          <p class="slide-subtitle">Three interactive visualizations querying the PostgreSQL DW answering RQ-01, RQ-02, and RQ-03.</p>
        </div>
        <div class="rubric-pill">Rubric: Sec 10.1 Analytics (0.40 pts)</div>
      </div>

      <div class="grid-3" style="height: 68%;">
        <div class="card" style="padding: 12px;">
          <div class="card-header" style="margin-bottom: 4px;">
            <span class="card-title" style="font-size: 0.88rem;">KPI 1: Audio Fingerprint</span>
            <span class="badge badge-cyan">RQ-01</span>
          </div>
          <div class="img-kpi-container">
            <img src="{kpi1_b64}" alt="KPI 1 Audio Profile">
          </div>
          <p style="font-size: 0.74rem; color: #cbd5e1; margin-top: 4px;">
            <strong>Insight:</strong> Winners feature higher <strong>Valence (0.53 vs 0.47)</strong>, lower <strong>Acousticness (0.26 vs 0.33)</strong>, and +12.04 popularity points (282 distinct awarded tracks).
          </p>
        </div>

        <div class="card" style="padding: 12px;">
          <div class="card-header" style="margin-bottom: 4px;">
            <span class="card-title" style="font-size: 0.88rem;">KPI 2: Genre Uplift</span>
            <span class="badge badge-purple">RQ-02</span>
          </div>
          <div class="img-kpi-container">
            <img src="{kpi2_b64}" alt="KPI 2 Genre Popularity">
          </div>
          <p style="font-size: 0.74rem; color: #cbd5e1; margin-top: 4px;">
            <strong>Insight:</strong> Highest popularity multipliers: <strong>Soul (+45.6 pts)</strong> and <strong>Country (+23.6 pts)</strong> post-Grammy acclaim.
          </p>
        </div>

        <div class="card" style="padding: 12px;">
          <div class="card-header" style="margin-bottom: 4px;">
            <span class="card-title" style="font-size: 0.88rem;">KPI 3: Lyrical & Feat. Trends</span>
            <span class="badge badge-emerald">RQ-03</span>
          </div>
          <div class="img-kpi-container">
            <img src="{kpi3_b64}" alt="KPI 3 Historical Trends">
          </div>
          <p style="font-size: 0.74rem; color: #cbd5e1; margin-top: 4px;">
            <strong>Insight:</strong> Explicit content in winning songs rose from 0% (pre-1990) to <strong>20.24%</strong> in the 2010s; collaborations reached <strong>35.71%</strong>.
          </p>
        </div>
      </div>
    </section>

    <!-- ============================================================== -->
    <!-- SLIDE 13: Evaluator Defense Cheatsheet & Trap Q&A              -->
    <!-- ============================================================== -->
    <section class="slide" data-notes="
<p><strong>Script:</strong></p>
<p>'Evaluators often test deep engineering understanding during Q&A. Here are our exact answers to the top 6 hardest questions about SQLite, retries, XCom, and idempotency.'</p>
<div class='notes-section-title'>How to Answer During Oral Defense</div>
<ul>
  <li>Keep answers concise, confident, and grounded in industry engineering standards.</li>
  <li>Refer to explicit schema constraints and Airflow execution logs.</li>
</ul>
">
      <div class="slide-header">
        <div>
          <div class="slide-tag">Section 10.2 • Technical Understanding</div>
          <h2 class="slide-title">Evaluator Defense Cheatsheet & Trap Q&A</h2>
          <p class="slide-subtitle">Interactive answers to the 6 most challenging questions evaluators ask during the defense.</p>
        </div>
        <div class="rubric-pill">Rubric: Sec 10.2 Q&A Defense (0.25 pts)</div>
      </div>

      <div class="qa-accordion">
        <div class="qa-card open" onclick="toggleQA(this)">
          <div class="qa-q">
            <span>1. Why is SQLite strictly prohibited and PostgreSQL required?</span>
            <span style="color: var(--accent-cyan);">▼</span>
          </div>
          <div class="qa-a">
            <strong>Answer:</strong> SQLite is an embedded file database lacking multi-user concurrent write locking, client-server isolation, and advanced ANSI SQL capabilities like concurrent upserts (<code>ON CONFLICT DO UPDATE</code> with partial indices). PostgreSQL provides true production-grade transactional integrity and ACID guarantees.
          </div>
        </div>

        <div class="qa-card" onclick="toggleQA(this)">
          <div class="qa-q">
            <span>2. Why did you assign retries=0 to data validation tasks?</span>
            <span style="color: var(--accent-cyan);">▼</span>
          </div>
          <div class="qa-a">
            <strong>Answer:</strong> Data quality violations are <em>deterministic</em>. If a dataset has an invalid year (1800), re-evaluating it 3 times without modifying the source will reproduce the exact same failure 3 times, wasting compute and delaying failure alerting. Only transient operational errors (network latency, socket disconnections) warrant retries.
          </div>
        </div>

        <div class="qa-card" onclick="toggleQA(this)">
          <div class="qa-q">
            <span>3. Why is passing Pandas DataFrames through Airflow XCom an anti-pattern?</span>
            <span style="color: var(--accent-cyan);">▼</span>
          </div>
          <div class="qa-a">
            <strong>Answer:</strong> Airflow XCom serializes data into the Airflow metadata database (PostgreSQL), which is designed for tiny coordination messages, not multi-megabyte datasets. Storing 114,000 rows in XCom causes metadata bloat, latency, and memory exhaustion. We pass Parquet file paths and lightweight metadata dictionaries.
          </div>
        </div>

        <div class="qa-card" onclick="toggleQA(this)">
          <div class="qa-q">
            <span>4. How does your pipeline guarantee 100% idempotency upon re-execution?</span>
            <span style="color: var(--accent-cyan);">▼</span>
          </div>
          <div class="qa-a">
            <strong>Answer:</strong> Idempotency is enforced by a composite natural grain constraint on the fact table <code>(track_sk, genre_sk, time_sk, category_sk)</code> paired with an atomic PostgreSQL <code>INSERT ... ON CONFLICT DO UPDATE</code>. Running the exact same batch 10 times results in zero duplicate rows and zero metric inflation.
          </div>
        </div>

        <div class="qa-card" onclick="toggleQA(this)">
          <div class="qa-q">
            <span>5. How did you reconcile multi-artist collaborations with Spotify track records?</span>
            <span style="color: var(--accent-cyan);">▼</span>
          </div>
          <div class="qa-a">
            <strong>Answer:</strong> We normalized artist credits by tokenizing on delimiters (<code>;</code> in Spotify; <code>featuring</code>, <code>&</code>, <code>with</code> in Grammys) to extract the primary canonical artist for cross-source matching, while preserving the full collaboration string in <code>dim_track</code>.
          </div>
        </div>

        <div class="qa-card" onclick="toggleQA(this)">
          <div class="qa-q">
            <span>6. What happened to the 99.5% of songs in Spotify that never won a Grammy?</span>
            <span style="color: var(--accent-cyan);">▼</span>
          </div>
          <div class="qa-a">
            <strong>Answer:</strong> They are preserved in the Data Warehouse via Left Outer Join semantics with <code>is_grammy_winner = FALSE</code> and foreign keys mapped to surrogate key 0 (<code>category_sk = 0</code>: "Not Applicable"). This allows analytical queries to compare winners against the baseline catalog.
          </div>
        </div>
      </div>
    </section>

    <!-- ============================================================== -->
    <!-- SLIDE 14: Conclusion & Defense Readiness Scorecard            -->
    <!-- ============================================================== -->
    <section class="slide" data-notes="
<p><strong>Closing Script:</strong></p>
<p>'In conclusion, our solution achieves 100% compliance across all 7 evaluation categories. We delivered a reproducible Docker environment with Airflow 3.1.8 and PostgreSQL, automated Great Expectations gates, an idempotent Star Schema DW, and direct DW analytics. Thank you, professors. I am now ready for your questions.'</p>
<div class='notes-section-title'>Final Defense Check</div>
<p>Stand tall, make eye contact, and invite the professors to examine any file in the GitHub repo or the Airflow UI.</p>
">
      <div class="slide-header">
        <div>
          <div class="slide-tag">Technical Defense Summary • 100% Compliance</div>
          <h2 class="slide-title">Conclusion & Defense Readiness</h2>
          <p class="slide-subtitle">A fully observable, auditable, and resilient data engineering system ready for technical defense.</p>
        </div>
        <div class="rubric-pill">Target Score: 5.0 / 5.0 (100%)</div>
      </div>

      <div class="grid-2" style="height: 68%;">
        <div class="card">
          <div class="card-header">
            <span class="card-title">✅ Deliverables & Rubric Compliance</span>
            <span class="badge badge-emerald">Score Target: 5.0 / 5.0</span>
          </div>
          <div class="card-body">
            <ul>
              <li><strong>Requirements & Architecture (0.40):</strong> RQ-01..03, full end-to-end traceability documented.</li>
              <li><strong>Data Profiling & Risks (0.60):</strong> 7 categories covered in reproducible notebook.</li>
              <li><strong>Transformation & Integration (0.60):</strong> Relational Grammy extraction & formal contract.</li>
              <li><strong>Great Expectations Validation (0.80):</strong> 18 rules, 3 gates (Suite + Validation Definition + Checkpoint), per-run JSON results.</li>
              <li><strong>Airflow 3.1.8 Orchestration (0.90):</strong> TaskFlow API, selective retries, Tests A, B, C and D (retry) verified.</li>
              <li><strong>Dimensional DW & Analytics (0.40):</strong> PostgreSQL Star Schema & 3 visual KPIs.</li>
              <li><strong>Repository & Documentation (0.30):</strong> All 16 README sections, zero secret leaks.</li>
            </ul>
          </div>
        </div>

        <div class="card">
          <div class="card-header">
            <span class="card-title">🎯 Summary of Engineering Value</span>
            <span class="badge badge-cyan">Defense Takeaways</span>
          </div>
          <div class="card-body">
            <div class="metric-box" style="margin-bottom: 10px;">
              <span class="metric-value" style="font-size: 1.15rem; color: var(--accent-cyan);">A System, Not a Script</span>
              <span class="metric-label" style="text-transform: none; color: #e2e8f0;">Decoupled modules under <code>src/</code> orchestrated cleanly by Airflow 3.1.8.</span>
            </div>
            <div class="metric-box" style="margin-bottom: 10px;">
              <span class="metric-value" style="font-size: 1.15rem; color: var(--accent-emerald);">Automated Quality Gates</span>
              <span class="metric-label" style="text-transform: none; color: #e2e8f0;">Great Expectations prevents bad data from ever entering the Data Warehouse.</span>
            </div>
            <div class="metric-box">
              <span class="metric-value" style="font-size: 1.15rem; color: var(--accent-purple);">100% Idempotent Repeatability</span>
              <span class="metric-label" style="text-transform: none; color: #e2e8f0;">Rerunning creates exactly zero duplicates and zero metric drift.</span>
            </div>
          </div>
        </div>
      </div>
    </section>

  </main>

  <!-- Slide Grid Overview Modal (G key) -->
  <div id="grid-overview-modal">
    <div class="grid-modal-header">
      <div>
        <h2 style="font-size: 1.5rem; color: #fff;">Slide Overview Grid</h2>
        <p style="font-size: 0.85rem; color: var(--text-muted);">Click any slide thumbnail to jump directly, or press <span class="key-hint">G</span> / <span class="key-hint">Esc</span> to close.</p>
      </div>
      <button class="btn-ctrl" onclick="toggleGridOverview()">✕ Close</button>
    </div>
    <div class="slide-grid-cards" id="grid-thumbs-container">
      <!-- Injected dynamically via JS -->
    </div>
  </div>

  <!-- Speaker Defense Notes Drawer (N key) -->
  <aside id="defense-notes-drawer">
    <div class="notes-title">
      <span>💬 Evaluator Defense Script</span>
      <span class="key-hint">Press N to Close</span>
    </div>
    <div id="notes-text" class="notes-content">
      Welcome professors. Press Left / Right Arrow keys to navigate slides.
    </div>
  </aside>

  <!-- Bottom Control Bar -->
  <footer>
    <div style="display: flex; gap: 8px; align-items: center;">
      <button class="btn-ctrl" onclick="prevSlide()" title="Previous Slide (Key: Left Arrow)">◀ Prev</button>
      <button class="btn-ctrl" onclick="nextSlide()" title="Next Slide (Key: Right Arrow)">Next ▶</button>
    </div>

    <div class="progress-bar-container">
      <div id="progress-fill" class="progress-bar-fill"></div>
    </div>

    <div style="display: flex; gap: 12px; align-items: center; color: var(--text-muted); font-size: 0.78rem;">
      <span>Nav: <span class="key-hint">←</span> <span class="key-hint">→</span> / <span class="key-hint">Space</span></span>
      <span>Grid: <span class="key-hint">G</span></span>
      <span>Notes: <span class="key-hint">N</span></span>
      <span>Timer: <span class="key-hint">T</span></span>
      <span>Fullscreen: <span class="key-hint">F</span></span>
    </div>
  </footer>

  <script>
    const slides = document.querySelectorAll('.slide');
    const slideNumDisplay = document.getElementById('current-slide-num');
    const progressFill = document.getElementById('progress-fill');
    const notesDrawer = document.getElementById('defense-notes-drawer');
    const notesText = document.getElementById('notes-text');
    const btnNotes = document.getElementById('btn-notes');
    const gridModal = document.getElementById('grid-overview-modal');
    const gridThumbsContainer = document.getElementById('grid-thumbs-container');
    const timerDisplay = document.getElementById('timer-display');

    let currentIndex = 0;
    let timerSeconds = 0;
    let timerInterval = null;
    let isTimerRunning = false;

    // Timer functions
    function toggleTimer() {{
      if (isTimerRunning) {{
        clearInterval(timerInterval);
        isTimerRunning = false;
        timerDisplay.style.color = 'var(--text-muted)';
      }} else {{
        isTimerRunning = true;
        timerDisplay.style.color = 'var(--accent-cyan)';
        timerInterval = setInterval(() => {{
          timerSeconds++;
          const mins = String(Math.floor(timerSeconds / 60)).padStart(2, '0');
          const secs = String(timerSeconds % 60).padStart(2, '0');
          timerDisplay.textContent = `${{mins}}:${{secs}}`;
        }}, 1000);
      }}
    }}

    function buildGridOverview() {{
      gridThumbsContainer.innerHTML = '';
      slides.forEach((slide, idx) => {{
        const titleEl = slide.querySelector('.slide-title');
        const tagEl = slide.querySelector('.slide-tag');
        const titleText = titleEl ? titleEl.textContent : `Slide ${{idx + 1}}`;
        const tagText = tagEl ? tagEl.textContent : '';

        const thumb = document.createElement('div');
        thumb.className = `grid-slide-thumb ${{idx === currentIndex ? 'active-thumb' : ''}}`;
        thumb.innerHTML = `
          <div style="font-size: 0.72rem; color: var(--accent-cyan); font-weight: 700;">#${{idx + 1}} • ${{tagText}}</div>
          <div style="font-size: 0.9rem; font-weight: 700; color: #fff;">${{titleText}}</div>
        `;
        thumb.onclick = () => {{
          updateSlide(idx);
          toggleGridOverview();
        }};
        gridThumbsContainer.appendChild(thumb);
      }});
    }}

    function toggleGridOverview() {{
      const isOpen = gridModal.classList.toggle('open');
      if (isOpen) {{
        buildGridOverview();
      }}
    }}

    function updateSlide(index) {{
      if (index < 0) index = 0;
      if (index >= slides.length) index = slides.length - 1;
      currentIndex = index;

      slides.forEach((slide, i) => {{
        if (i === currentIndex) {{
          slide.classList.add('active');
        }} else {{
          slide.classList.remove('active');
        }}
      }});

      // Update Header & Progress
      slideNumDisplay.textContent = `Slide ${{currentIndex + 1}} of ${{slides.length}}`;
      const progressPct = ((currentIndex + 1) / slides.length) * 100;
      progressFill.style.width = `${{progressPct}}%`;

      // Update Notes Drawer Content
      const activeSlide = slides[currentIndex];
      const note = activeSlide.getAttribute('data-notes') || 'No defense notes available for this slide.';
      notesText.innerHTML = note;
    }}

    function nextSlide() {{
      if (currentIndex < slides.length - 1) {{
        updateSlide(currentIndex + 1);
      }}
    }}

    function prevSlide() {{
      if (currentIndex > 0) {{
        updateSlide(currentIndex - 1);
      }}
    }}

    function toggleNotes() {{
      const isOpen = notesDrawer.classList.toggle('open');
      btnNotes.classList.toggle('active', isOpen);
    }}

    function toggleFullscreen() {{
      if (!document.fullscreenElement) {{
        document.documentElement.requestFullscreen().catch(err => {{
          console.error(`Error attempting to enable fullscreen: ${{err.message}}`);
        }});
      }} else {{
        if (document.exitFullscreen) {{
          document.exitFullscreen();
        }}
      }}
    }}

    function toggleQA(card) {{
      card.classList.toggle('open');
    }}

    // Keyboard Event Listener
    document.addEventListener('keydown', (e) => {{
      if (gridModal.classList.contains('open')) {{
        if (e.key === 'Escape' || e.key.toLowerCase() === 'g') {{
          e.preventDefault();
          toggleGridOverview();
        }}
        return;
      }}

      if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'PageDown') {{
        e.preventDefault();
        nextSlide();
      }} else if (e.key === 'ArrowLeft' || e.key === 'Backspace' || e.key === 'PageUp') {{
        e.preventDefault();
        prevSlide();
      }} else if (e.key.toLowerCase() === 'n') {{
        e.preventDefault();
        toggleNotes();
      }} else if (e.key.toLowerCase() === 'g') {{
        e.preventDefault();
        toggleGridOverview();
      }} else if (e.key.toLowerCase() === 't') {{
        e.preventDefault();
        toggleTimer();
      }} else if (e.key.toLowerCase() === 'f') {{
        e.preventDefault();
        toggleFullscreen();
      }} else if (e.key === 'Home') {{
        e.preventDefault();
        updateSlide(0);
      }} else if (e.key === 'End') {{
        e.preventDefault();
        updateSlide(slides.length - 1);
      }}
    }});

    // Auto-start timer on load
    toggleTimer();

    // Initialize first slide and notes
    updateSlide(0);
  </script>
</body>
</html>
"""

    docs_path = os.path.join(base_dir, "docs", "presentation.html")

    with open(docs_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"✅ Generated {docs_path} ({len(html_content)} bytes)")

if __name__ == "__main__":
    build_deck()
