"""Vault front-end: near-black + gold sportsbook theme.

Renders the THIS WEEK hero (scrolling edge ticker + dense expandable slate) as
embedded HTML/CSS/JS for streamlit.components.v1.html(), wired to real data.
"""
import json

PALETTE = {
    'bg': '#0a0b0d', 'panel': '#121419', 'panel2': '#171a21', 'line': '#23262e',
    'txt': '#e8eaed', 'txt2': '#9298a3', 'txt3': '#5e636d',
    'accent': '#d4a437', 'accent_dim': '#8a6d22',
    'pos': '#3ecf8e', 'neg': '#e2554d', 'warn': '#e0a82e',
}

ROW_H = 47
SLATE_PAGE_SIZE = 8
INJURY_PAGE_SIZE = 9

_PAGER_CSS = """
  .pager { display:flex; align-items:center; justify-content:space-between; margin-top:12px; padding:0 2px; }
  .pager .info { font-size:11px; color:var(--txt3); letter-spacing:0.03em; }
  .pager .nav { display:flex; gap:6px; align-items:center; }
  .pager button { background:var(--panel); border:1px solid var(--line); color:var(--txt2); font-size:12px;
      padding:5px 12px; border-radius:6px; cursor:pointer; font-family:inherit; }
  .pager button:hover:not(:disabled) { border-color:var(--accent); color:var(--txt); }
  .pager button:disabled { opacity:0.35; cursor:default; }
  .pager .pg { font-family:var(--mono); font-size:12px; color:var(--txt2); min-width:54px; text-align:center; }
"""

DRIVER_LABELS = {
    'ml_model': 'ml model',
    'current_record': 'record',
    'historical_trend': 'trend',
    'offensive_power': 'offense',
    'defensive_strength': 'defense',
    'injury_impact': 'injury',
    'home_field': 'home field',
}

_VARS = """
  --bg:#0a0b0d; --panel:#121419; --panel2:#171a21; --line:#23262e;
  --txt:#e8eaed; --txt2:#9298a3; --txt3:#5e636d;
  --accent:#d4a437; --accent-dim:#8a6d22;
  --pos:#3ecf8e; --neg:#e2554d; --warn:#e0a82e;
  --mono:'SFMono-Regular',Menlo,Consolas,monospace;
  --sans:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
"""


def shell_css():
    """CSS that skins the Streamlit shell (background, tabs, fonts) to Vault."""
    return f"""
<style>
  :root {{{_VARS}}}
  .stApp {{ background:{PALETTE['bg']}; }}
  .block-container {{ padding-top:1rem; max-width:1120px; }}
  header[data-testid="stHeader"] {{ background:transparent; }}
  #MainMenu, footer {{ visibility:hidden; }}
  html, body, [class*="css"] {{ font-family:var(--sans); color:{PALETTE['txt']}; }}
  .stTabs [data-baseweb="tab-list"] {{ gap:2px; border-bottom:1px solid {PALETTE['line']}; background:transparent; }}
  .stTabs [data-baseweb="tab"] {{ background:transparent; color:{PALETTE['txt2']}; padding:10px 16px;
      font-size:13px; font-weight:500; border-bottom:2px solid transparent; }}
  .stTabs [aria-selected="true"] {{ color:{PALETTE['txt']}; border-bottom-color:{PALETTE['accent']}; }}
  .stTabs [data-baseweb="tab"]:hover {{ color:{PALETTE['txt']}; }}
  .vault-eyebrow {{ font-size:11px; color:{PALETTE['txt3']}; letter-spacing:0.07em;
      text-transform:lowercase; }}
  .stSelectbox label, .stNumberInput label {{ color:{PALETTE['txt2']}; font-size:12px;
      text-transform:lowercase; letter-spacing:0.04em; }}
  div[data-baseweb="select"] > div {{ background:{PALETTE['panel']}; border-color:{PALETTE['line']};
      color:{PALETTE['txt']}; }}
  div[data-baseweb="select"] svg {{ color:{PALETTE['accent']}; }}
  .stApp h1, .stApp h2, .stApp h3 {{ color:{PALETTE['txt']}; }}
</style>
"""


def _driver_pills(components):
    rows = []
    for key, val in components.items():
        label = DRIVER_LABELS.get(key, key.replace('_', ' '))
        if key == 'home_field':
            cls = 'x'
        elif val > 0.05:
            cls = 'p'
        elif val < -0.05:
            cls = 'n'
        else:
            cls = 'x'
        rows.append({'label': label, 'val': round(float(val), 1), 'cls': cls})
    rows.sort(key=lambda d: abs(d['val']), reverse=True)
    return rows[:4]


def _fmt_signed(v):
    return f"{v:+.1f}"


def build_payload(predictor, db, season, week, offseason, label):
    """Compute the slate for one week. Edges only when live odds are available."""
    odds_data = None
    try:
        odds_data = predictor.fetch_draftkings_lines()
    except Exception:
        odds_data = None

    games = db.execute_query(
        """
        SELECT ht.abbreviation AS home, at.abbreviation AS away
        FROM games g
        JOIN teams ht ON g.home_team_id = ht.team_id
        JOIN teams at ON g.away_team_id = at.team_id
        WHERE g.season = %s AND g.week = %s
        ORDER BY g.game_date, g.game_id
        """,
        (season, week),
    )

    rows = []
    flagged = 0
    for g in games:
        home, away = g['home'], g['away']
        try:
            pred = predictor.calculate_comprehensive_prediction(home, away, season, week)
        except Exception:
            continue

        line = float(pred['model_betting_line'])
        prob = float(pred['ml_home_win_probability'])
        prob_team = home if prob >= 0.5 else away
        prob_show = prob if prob >= 0.5 else 1 - prob

        edge = None
        vegas = None
        dk = predictor.parse_odds_for_game(odds_data, home, away) if odds_data else None
        if dk and dk.get('spread') is not None:
            dk_spread = float(dk['spread'])
            vegas = f"{home} {_fmt_signed(dk_spread)}"
            edge = round(line - dk_spread, 1)

        if edge is None:
            edge_cls, flag = 'fl', ''
            edge_show = '-'
        else:
            ae = abs(edge)
            edge_show = _fmt_signed(edge)
            if ae >= 5:
                edge_cls, flag = 'up', 'flag-hi'
                flagged += 1
            elif ae >= 3:
                edge_cls, flag = 'md', 'flag-md'
                flagged += 1
            elif ae >= 1:
                edge_cls, flag = 'fl', ''
            else:
                edge_cls, flag = 'fl', 'dim'

        rows.append({
            'away': away, 'home': home,
            'arec': pred.get('away_record', ''), 'hrec': pred.get('home_record', ''),
            'model': f"{home} {_fmt_signed(line)}",
            'vegas': vegas if vegas else '-',
            'edge': edge_show, 'edge_val': edge if edge is not None else 0.0,
            'cls': edge_cls, 'flag': flag, 'conf': pred.get('confidence', '-'),
            'prob': f"{prob_team} {prob_show*100:.0f}%",
            'drivers': _driver_pills(pred['components']),
        })

    if any(r['edge'] != '-' for r in rows):
        rows.sort(key=lambda r: abs(r['edge_val']), reverse=True)
    else:
        rows.sort(key=lambda r: abs(float(r['model'].split()[-1])), reverse=True)

    return {
        'label': label, 'season': season, 'week': week,
        'offseason': offseason, 'flagged': flagged, 'games': rows,
    }


def ticker_html(payload):
    games = payload['games']
    offseason = payload['offseason']
    tag = 'model lines' if offseason else 'live edges'
    items = []
    for g in (games + games):
        if offseason:
            val = g['model'].split()[-1]
            cls = 'fl'
        else:
            val = g['edge']
            cls = g['cls']
        items.append(
            f'<span class="tick"><span class="g">{g["away"]}@{g["home"]}</span>'
            f'<span class="e {cls}">{val}</span></span>'
        )
    track = ''.join(items) if items else '<span class="tick"><span class="g">no games</span></span>'
    return f"""
<style>
  :root {{{_VARS}}}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); font-family:var(--sans); overflow:hidden; }}
  .ticker {{ background:var(--panel); border:1px solid var(--line); border-radius:8px;
      height:38px; display:flex; align-items:center; overflow:hidden; }}
  .ticker-tag {{ flex:none; display:flex; align-items:center; gap:6px; padding:0 14px; height:100%;
      background:var(--accent); color:#0a0b0d; font-weight:700; font-size:11px;
      letter-spacing:0.06em; text-transform:uppercase; }}
  .ticker-tag .dot {{ width:6px; height:6px; border-radius:50%; background:#0a0b0d; animation:pulse 1.6s infinite; }}
  @keyframes pulse {{ 0%,100%{{opacity:1}} 50%{{opacity:0.35}} }}
  .ticker-track {{ display:flex; white-space:nowrap; animation:scroll 38s linear infinite; }}
  .ticker:hover .ticker-track {{ animation-play-state:paused; }}
  @keyframes scroll {{ from{{transform:translateX(0)}} to{{transform:translateX(-50%)}} }}
  .tick {{ display:inline-flex; align-items:center; gap:8px; padding:0 18px; font-size:12px; border-right:1px solid var(--line); }}
  .tick .g {{ color:var(--txt2); font-weight:500; }}
  .tick .e {{ font-family:var(--mono); font-variant-numeric:tabular-nums; font-weight:600; }}
  .tick .e.up {{ color:var(--accent); }} .tick .e.md {{ color:var(--pos); }} .tick .e.fl {{ color:var(--txt3); }}
</style>
<div class="ticker">
  <div class="ticker-tag"><span class="dot"></span>{tag}</div>
  <div class="ticker-track">{track}</div>
</div>
"""


def slate_height(offseason):
    """Fixed iframe height: a full page of rows + room for one open detail card."""
    base = 200 + (44 if offseason else 0)
    detail_reserve = 165
    pager = 54
    return base + SLATE_PAGE_SIZE * ROW_H + detail_reserve + pager


def slate_html(payload, accuracy_pct):
    data = json.dumps(payload['games'])
    label = payload['label']
    n = len(payload['games'])
    flagged = payload['flagged']
    acc = f"{accuracy_pct*100:.1f}%" if accuracy_pct else "-"
    offseason = payload['offseason']
    banner = ''
    if offseason:
        banner = (f'<div class="banner">offseason · no live odds. showing model projections '
                  f'and final results for {label}. gold edges activate when betting lines are live.</div>')
    default_view = 'all' if offseason else 'edges'
    return f"""
<style>
  :root {{{_VARS}}}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); color:var(--txt); font-family:var(--sans); font-size:14px; line-height:1.5; -webkit-font-smoothing:antialiased; }}
  .mono {{ font-family:var(--mono); font-variant-numeric:tabular-nums; }}
  .top {{ display:flex; align-items:center; justify-content:space-between; padding:4px 2px 16px; }}
  .brand {{ display:flex; align-items:center; gap:11px; }}
  .brand .mark {{ width:30px; height:30px; border-radius:7px; background:var(--accent); color:#0a0b0d;
      display:flex; align-items:center; justify-content:center; font-weight:800; font-size:15px; }}
  .brand h1 {{ font-size:17px; font-weight:700; letter-spacing:-0.01em; }}
  .brand .sub {{ font-size:11px; color:var(--txt3); letter-spacing:0.04em; text-transform:lowercase; }}
  .acc {{ font-size:12px; color:var(--txt2); display:flex; gap:18px; align-items:center; }}
  .acc b {{ color:var(--pos); font-family:var(--mono); font-variant-numeric:tabular-nums; }}
  .acc .lab {{ display:block; font-size:10px; color:var(--txt3); text-transform:lowercase; letter-spacing:0.04em; }}
  .banner {{ font-size:11.5px; color:var(--warn); background:rgba(224,168,46,0.07);
      border:1px solid rgba(224,168,46,0.25); border-radius:7px; padding:8px 12px; margin-bottom:14px; }}
  .slate-head {{ display:flex; align-items:baseline; justify-content:space-between; margin-bottom:14px; }}
  .slate-head .t {{ font-size:20px; font-weight:700; }}
  .slate-head .t span {{ color:var(--txt3); font-weight:400; font-size:14px; margin-left:8px; }}
  .seg {{ display:flex; gap:4px; }}
  .seg button {{ background:var(--panel); border:1px solid var(--line); color:var(--txt2); font-size:12px;
      padding:5px 12px; border-radius:6px; cursor:pointer; font-family:inherit; }}
  .seg button.on {{ background:var(--accent); border-color:var(--accent); color:#0a0b0d; font-weight:600; }}
  .cols {{ display:grid; grid-template-columns:1.6fr 1fr 1fr 0.8fr 0.7fr 24px; padding:0 16px 8px;
      font-size:10px; color:var(--txt3); text-transform:uppercase; letter-spacing:0.07em; border-bottom:1px solid var(--line); }}
  .cols span:nth-child(n+2) {{ text-align:right; }}
  .cols span:nth-child(2),.cols span:nth-child(3) {{ text-align:left; }}
  .row {{ display:grid; grid-template-columns:1.6fr 1fr 1fr 0.8fr 0.7fr 24px; padding:13px 16px; align-items:center;
      border-bottom:1px solid var(--line); cursor:pointer; border-left:2px solid transparent; transition:background .12s; }}
  .row:hover {{ background:var(--panel); }}
  .row.flag-hi {{ border-left-color:var(--accent); background:var(--panel); }}
  .row.flag-md {{ border-left-color:var(--pos); }}
  .row.dim {{ opacity:0.5; }}
  .mteam {{ font-weight:600; font-size:14.5px; }}
  .mrec {{ font-size:11px; color:var(--txt3); margin-top:1px; }}
  .ln {{ font-family:var(--mono); font-variant-numeric:tabular-nums; font-size:13px; text-align:right; }}
  .ln.v {{ color:var(--txt2); }}
  .ln.left {{ text-align:left; }}
  .edge {{ font-family:var(--mono); font-variant-numeric:tabular-nums; font-weight:700; text-align:right; }}
  .edge.up {{ color:var(--accent); }} .edge.md {{ color:var(--pos); }} .edge.fl {{ color:var(--txt3); font-weight:400; }}
  .conf {{ text-align:right; font-size:11px; color:var(--txt2); letter-spacing:0.03em; }}
  .chev {{ text-align:right; color:var(--txt3); transition:transform .15s; }}
  .row.open .chev {{ transform:rotate(90deg); color:var(--accent); }}
  .detail {{ display:none; padding:0 16px 18px; border-bottom:1px solid var(--line); background:var(--panel); }}
  .row.open + .detail {{ display:block; animation:fade .18s ease; }}
  @keyframes fade {{ from{{opacity:0;transform:translateY(-4px)}} to{{opacity:1;transform:none}} }}
  .dgrid {{ display:grid; grid-template-columns:repeat(4,1fr); gap:8px; padding-top:4px; }}
  .dcell {{ background:var(--panel2); border:1px solid var(--line); border-radius:8px; padding:10px 12px; }}
  .dcell .k {{ font-size:10px; color:var(--txt3); text-transform:uppercase; letter-spacing:0.05em; }}
  .dcell .val {{ font-family:var(--mono); font-variant-numeric:tabular-nums; font-size:16px; font-weight:600; margin-top:3px; }}
  .drivers {{ display:flex; gap:6px; margin-top:12px; flex-wrap:wrap; align-items:center; }}
  .drivers .lab {{ font-size:11px; color:var(--txt3); margin-right:2px; }}
  .pill {{ font-size:11px; font-family:var(--mono); font-variant-numeric:tabular-nums; padding:3px 9px;
      border-radius:5px; background:var(--panel2); border:1px solid var(--line); }}
  .pill.p {{ color:var(--pos); }} .pill.n {{ color:var(--neg); }} .pill.x {{ color:var(--txt2); }}
  .copybet {{ margin-top:12px; display:inline-flex; align-items:center; gap:7px; background:var(--accent);
      color:#0a0b0d; border:none; font-weight:700; font-size:12px; padding:8px 16px; border-radius:7px;
      cursor:pointer; font-family:inherit; letter-spacing:0.02em; }}
  .empty {{ padding:40px 16px; text-align:center; color:var(--txt3); font-size:13px; }}
{_PAGER_CSS}
</style>

<div class="top">
  <div class="brand">
    <div class="mark">GP</div>
    <div><h1>Gridiron Prophet</h1><div class="sub">edge intelligence · {label}</div></div>
  </div>
  <div class="acc">
    <span><span class="lab">model accuracy · out-of-sample</span><b>{acc}</b></span>
  </div>
</div>

{banner}

<div class="slate-head">
  <div class="t">{label} <span>{n} games · {flagged} flagged</span></div>
  <div class="seg">
    <button id="seg-edges" class="{ 'on' if default_view=='edges' else '' }">edges ≥3</button>
    <button id="seg-all" class="{ 'on' if default_view=='all' else '' }">all games</button>
  </div>
</div>

<div class="cols"><span>matchup</span><span>model</span><span>vegas</span><span>edge</span><span>conf</span><span></span></div>
<div id="rows"></div>
<div class="pager" id="pager" style="display:none">
  <div class="info" id="info"></div>
  <div class="nav"><button id="prev">‹ prev</button><span class="pg" id="pg"></span><button id="next">next ›</button></div>
</div>

<script>
  const GAMES = {data};
  const SIZE = {SLATE_PAGE_SIZE};
  let view = "{default_view}";
  let page = 0;
  const rowsEl = document.getElementById('rows');
  const pagerEl = document.getElementById('pager');
  const infoEl = document.getElementById('info');
  const pgEl = document.getElementById('pg');
  const prev = document.getElementById('prev');
  const next = document.getElementById('next');

  function flagged(g) {{ return g.flag === 'flag-hi' || g.flag === 'flag-md'; }}
  function list() {{ return view === 'edges' ? GAMES.filter(flagged) : GAMES; }}

  function render() {{
    rowsEl.innerHTML = '';
    const L = list();
    const pages = Math.max(1, Math.ceil(L.length / SIZE));
    if (page >= pages) page = pages - 1;
    if (!L.length) {{
      rowsEl.innerHTML = '<div class="empty">no games with an edge ≥3. switch to all games</div>';
      pagerEl.style.display = 'none';
      return;
    }}
    const start = page * SIZE;
    L.slice(start, start + SIZE).forEach(g => {{
      const r = document.createElement('div');
      r.className = 'row ' + (g.flag || '');
      r.innerHTML =
        '<div><div class="mteam">' + g.away + ' <span style="color:var(--txt3)">@</span> ' + g.home + '</div>' +
        '<div class="mrec">' + g.arec + ' · ' + g.hrec + '</div></div>' +
        '<div class="ln left">' + g.model + '</div>' +
        '<div class="ln v left">' + g.vegas + '</div>' +
        '<div class="edge ' + g.cls + '">' + g.edge + '</div>' +
        '<div class="conf">' + g.conf + '</div>' +
        '<div class="chev">›</div>';
      const d = document.createElement('div');
      d.className = 'detail';
      const pills = g.drivers.map(x => '<span class="pill ' + x.cls + '">' + x.label + ' ' +
        (x.val >= 0 ? '+' : '') + x.val + '</span>').join('');
      const copy = flagged(g) ? '<button class="copybet" data-bet="' + g.home + ' ' + g.edge + '">▸ copy bet · ' + g.home + '</button>' : '';
      d.innerHTML =
        '<div class="dgrid">' +
          '<div class="dcell"><div class="k">model line</div><div class="val">' + g.model + '</div></div>' +
          '<div class="dcell"><div class="k">vegas line</div><div class="val">' + g.vegas + '</div></div>' +
          '<div class="dcell"><div class="k">win prob</div><div class="val">' + g.prob + '</div></div>' +
          '<div class="dcell"><div class="k">edge</div><div class="val" style="color:var(--accent)">' + g.edge + '</div></div>' +
        '</div>' +
        '<div class="drivers"><span class="lab">drivers</span>' + pills + '</div>' + copy;
      r.addEventListener('click', () => {{
        const wasOpen = r.classList.contains('open');
        rowsEl.querySelectorAll('.row.open').forEach(o => o.classList.remove('open'));
        if (!wasOpen) r.classList.add('open');
      }});
      rowsEl.appendChild(r);
      rowsEl.appendChild(d);
    }});
    rowsEl.querySelectorAll('.copybet').forEach(b => {{
      b.addEventListener('click', e => {{
        e.stopPropagation();
        navigator.clipboard && navigator.clipboard.writeText(b.dataset.bet);
        const t = b.innerHTML; b.innerHTML = '✓ copied'; setTimeout(() => b.innerHTML = t, 1500);
      }});
    }});
    if (pages > 1) {{
      pagerEl.style.display = 'flex';
      infoEl.textContent = (start + 1) + '-' + Math.min(start + SIZE, L.length) + ' of ' + L.length;
      pgEl.textContent = (page + 1) + ' / ' + pages;
      prev.disabled = page === 0;
      next.disabled = page >= pages - 1;
    }} else {{
      pagerEl.style.display = 'none';
    }}
  }}

  prev.addEventListener('click', () => {{ if (page > 0) {{ page--; render(); }} }});
  next.addEventListener('click', () => {{ if (page < Math.ceil(list().length / SIZE) - 1) {{ page++; render(); }} }});

  const segE = document.getElementById('seg-edges');
  const segA = document.getElementById('seg-all');
  segE.addEventListener('click', () => {{ segE.classList.add('on'); segA.classList.remove('on'); view = 'edges'; page = 0; render(); }});
  segA.addEventListener('click', () => {{ segA.classList.add('on'); segE.classList.remove('on'); view = 'all'; page = 0; render(); }});
  render();
</script>
"""


def injuries_height():
    """Fixed iframe height so a full page fits with no inner scrollbar."""
    return 252 + INJURY_PAGE_SIZE * ROW_H + 54


def injuries_html(impact, label):
    """Vault-styled, paginated injury report panel for one team."""
    injuries = impact.get('injuries', [])
    crit = [x for x in injuries if x['impact_score'] >= 7]

    rows = []
    for x in injuries:
        score = x['impact_score']
        tone = 'crit' if score >= 7 else 'mod' if score >= 3 else 'min'
        rows.append({'pos': x['position'], 'player': x['player'],
                     'status': x['status'], 'impact': round(score, 1), 'tone': tone})

    total = impact.get('total_impact', 0)
    data = json.dumps(rows)
    return f"""
<style>
  :root {{{_VARS}}}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); color:var(--txt); font-family:var(--sans); font-size:14px; -webkit-font-smoothing:antialiased; }}
  .mono {{ font-family:var(--mono); font-variant-numeric:tabular-nums; }}
  .eyebrow {{ font-size:11px; color:var(--txt3); letter-spacing:0.07em; text-transform:lowercase; }}
  .team {{ font-size:22px; font-weight:700; margin-top:2px; }}
  .stats {{ display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin:14px 0 16px; }}
  .scell {{ background:var(--panel2); border:1px solid var(--line); border-radius:8px; padding:11px 13px; }}
  .scell .k {{ font-size:10px; color:var(--txt3); text-transform:lowercase; letter-spacing:0.05em; }}
  .scell .v {{ font-family:var(--mono); font-variant-numeric:tabular-nums; font-size:20px; font-weight:700; margin-top:3px; }}
  .irow {{ display:grid; grid-template-columns:54px 1fr auto 56px; gap:12px; align-items:center;
      padding:11px 14px; background:var(--panel); border:1px solid var(--line); border-left:2px solid var(--line);
      border-radius:7px; margin-bottom:5px; }}
  .irow.crit {{ border-left-color:var(--neg); }} .irow.mod {{ border-left-color:var(--warn); }} .irow.min {{ border-left-color:var(--pos); }}
  .pos {{ font-size:10px; font-weight:700; color:var(--txt2); text-align:center; background:var(--panel2);
      border:1px solid var(--line); border-radius:5px; padding:3px 0; letter-spacing:0.03em; }}
  .pname {{ font-weight:600; font-size:14px; }}
  .status {{ font-size:11.5px; color:var(--txt2); letter-spacing:0.02em; }}
  .impact {{ text-align:right; font-weight:700; font-size:14px; }}
  .irow.crit .impact {{ color:var(--neg); }} .irow.mod .impact {{ color:var(--warn); }} .irow.min .impact {{ color:var(--pos); }}
  .empty {{ padding:30px 14px; text-align:center; color:var(--txt3); font-size:13px; }}
{_PAGER_CSS}
</style>
<div class="eyebrow">injury report · {label}</div>
<div class="team">{impact['team']}</div>
<div class="stats">
  <div class="scell"><div class="k">total impact</div><div class="v">{total:.1f}</div></div>
  <div class="scell"><div class="k">injuries</div><div class="v">{impact.get('injury_count', 0)}</div></div>
  <div class="scell"><div class="k">critical</div><div class="v">{len(crit)}</div></div>
</div>
<div id="rows"></div>
<div class="pager" id="pager" style="display:none">
  <div class="info" id="info"></div>
  <div class="nav"><button id="prev">‹ prev</button><span class="pg" id="pg"></span><button id="next">next ›</button></div>
</div>

<script>
  const ROWS = {data};
  const SIZE = {INJURY_PAGE_SIZE};
  const pages = Math.max(1, Math.ceil(ROWS.length / SIZE));
  let page = 0;
  const rowsEl = document.getElementById('rows');
  const pagerEl = document.getElementById('pager');
  const infoEl = document.getElementById('info');
  const pgEl = document.getElementById('pg');
  const prev = document.getElementById('prev');
  const next = document.getElementById('next');

  function render() {{
    rowsEl.innerHTML = '';
    if (!ROWS.length) {{ rowsEl.innerHTML = '<div class="empty">no reported injuries</div>'; return; }}
    const start = page * SIZE;
    ROWS.slice(start, start + SIZE).forEach(x => {{
      const r = document.createElement('div');
      r.className = 'irow ' + x.tone;
      r.innerHTML = '<span class="pos">' + x.pos + '</span>' +
        '<span class="pname">' + x.player + '</span>' +
        '<span class="status">' + x.status + '</span>' +
        '<span class="impact mono">' + x.impact.toFixed(1) + '</span>';
      rowsEl.appendChild(r);
    }});
    if (pages > 1) {{
      pagerEl.style.display = 'flex';
      infoEl.textContent = (start + 1) + '-' + Math.min(start + SIZE, ROWS.length) + ' of ' + ROWS.length;
      pgEl.textContent = (page + 1) + ' / ' + pages;
      prev.disabled = page === 0;
      next.disabled = page >= pages - 1;
    }}
  }}
  prev.addEventListener('click', () => {{ if (page > 0) {{ page--; render(); }} }});
  next.addEventListener('click', () => {{ if (page < pages - 1) {{ page++; render(); }} }});
  render();
</script>
"""


FEATURE_LABELS = {
    'home_wins': 'home wins', 'home_losses': 'home losses', 'home_win_pct': 'home win %',
    'home_avg_points_scored': 'home pts for', 'home_avg_points_allowed': 'home pts against',
    'away_wins': 'away wins', 'away_losses': 'away losses', 'away_win_pct': 'away win %',
    'away_avg_points_scored': 'away pts for', 'away_avg_points_allowed': 'away pts against',
}


def performance_height():
    return 660


def performance_html(eval_stats):
    """Honest out-of-sample model performance: accuracy vs baseline, feature weights, confusion."""
    if not eval_stats:
        return (f'<style>:root{{{_VARS}}}body{{background:var(--bg);color:var(--txt3);'
                f'font-family:var(--sans);padding:30px;text-align:center}}</style>'
                f'<div>model evaluation unavailable. train the model first</div>')

    acc = eval_stats['accuracy'] * 100
    base = eval_stats['home_baseline'] * 100
    lift = acc - base
    feats = eval_stats['feature_importance'][:10]
    fmax = max((f['importance'] for f in feats), default=1) or 1
    bars = []
    for f in feats:
        pct = f['importance'] / fmax * 100
        bars.append(
            f'<div class="frow"><span class="flab">{FEATURE_LABELS.get(f["feature"], f["feature"])}</span>'
            f'<span class="ftrack"><span class="ffill" style="width:{pct:.0f}%"></span></span>'
            f'<span class="fval mono">{f["importance"]:.3f}</span></div>'
        )
    cm = eval_stats['confusion']
    return f"""
<style>
  :root {{{_VARS}}}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); color:var(--txt); font-family:var(--sans); font-size:14px; -webkit-font-smoothing:antialiased; }}
  .mono {{ font-family:var(--mono); font-variant-numeric:tabular-nums; }}
  .eyebrow {{ font-size:11px; color:var(--txt3); letter-spacing:0.07em; text-transform:lowercase; }}
  .title {{ font-size:20px; font-weight:700; margin-top:2px; }}
  .stats {{ display:grid; grid-template-columns:repeat(4,1fr); gap:8px; margin:14px 0 6px; }}
  .scell {{ background:var(--panel2); border:1px solid var(--line); border-radius:8px; padding:11px 13px; }}
  .scell .k {{ font-size:10px; color:var(--txt3); text-transform:lowercase; letter-spacing:0.05em; }}
  .scell .v {{ font-family:var(--mono); font-variant-numeric:tabular-nums; font-size:20px; font-weight:700; margin-top:3px; }}
  .scell .v.gold {{ color:var(--accent); }}
  .scell .sub {{ font-size:10px; color:var(--pos); margin-top:3px; }}
  .sectlab {{ font-size:11px; color:var(--txt3); text-transform:lowercase; letter-spacing:0.06em; margin:16px 0 8px; }}
  .frow {{ display:grid; grid-template-columns:120px 1fr 48px; gap:10px; align-items:center; margin-bottom:6px; }}
  .flab {{ font-size:11.5px; color:var(--txt2); }}
  .ftrack {{ height:8px; background:var(--panel2); border:1px solid var(--line); border-radius:4px; overflow:hidden; }}
  .ffill {{ display:block; height:100%; background:linear-gradient(90deg,var(--accent-dim),var(--accent)); }}
  .fval {{ font-size:11px; color:var(--txt2); text-align:right; }}
  .bottom {{ display:grid; grid-template-columns:auto 1fr; gap:18px; margin-top:16px; align-items:start; }}
  .cm {{ display:grid; grid-template-columns:auto auto auto; gap:4px; font-size:11px; }}
  .cm .cell {{ background:var(--panel2); border:1px solid var(--line); border-radius:6px; padding:8px 12px;
      font-family:var(--mono); font-variant-numeric:tabular-nums; text-align:center; min-width:54px; }}
  .cm .hd {{ background:transparent; border:none; color:var(--txt3); font-family:var(--sans); font-size:10px; }}
  .cm .diag {{ color:var(--pos); }}
  .note {{ font-size:11.5px; color:var(--txt3); line-height:1.6; }}
</style>
<div class="eyebrow">model performance · out-of-sample</div>
<div class="title">how the model holds up</div>
<div class="stats">
  <div class="scell"><div class="k">holdout accuracy</div><div class="v gold">{acc:.1f}%</div><div class="sub">+{lift:.1f} vs baseline</div></div>
  <div class="scell"><div class="k">home-field baseline</div><div class="v">{base:.1f}%</div></div>
  <div class="scell"><div class="k">test games</div><div class="v">{eval_stats['test_size']}</div></div>
  <div class="scell"><div class="k">training games</div><div class="v">{eval_stats['train_size']}</div></div>
</div>
<div class="sectlab">what the model weighs · feature importance</div>
{''.join(bars)}
<div class="bottom">
  <div>
    <div class="sectlab" style="margin-top:0">confusion · test set</div>
    <div class="cm">
      <span class="cell hd"></span><span class="cell hd">pred away</span><span class="cell hd">pred home</span>
      <span class="cell hd">actual away</span><span class="cell diag">{cm[0][0]}</span><span class="cell">{cm[0][1]}</span>
      <span class="cell hd">actual home</span><span class="cell">{cm[1][0]}</span><span class="cell diag">{cm[1][1]}</span>
    </div>
  </div>
  <div class="note">accuracy is measured on a held-out 20% of 2022-2025 games the model never trained on.
  the honest out-of-sample number, not an in-season grade. live weekly grading populates here as the 2026 season plays.</div>
</div>
"""


def model_height():
    return 560


def model_html(accuracy, label):
    """Vault methodology panel: how the model works, honest framing."""
    acc = f"{accuracy * 100:.1f}%" if accuracy else "-"
    cards = [
        ('machine learning',
         f'Random Forest win classifier trained on completed 2022-2025 games. '
         f'The betting line blends the model with team-form, injury, historical-trend and home-field components.'),
        ('what it weighs',
         'team form: records, points for / against · injuries: position-weighted, snap-aware · '
         'historical trend · home-field advantage'),
        ('reading the edge',
         'edge = model line - vegas line · 🔥 ≥10 best · ⚡ 5-9 value · ⚠️ 3-4 minimum · skip under 3'),
        ('bankroll',
         '1 unit = 1-2% of bankroll · high 2-3u · medium 1-2u · low 0.5-1u · never more than 5% on one game'),
        ('trust & limits',
         f'out-of-sample accuracy {acc} · breakeven 52.4% at -110 · weekly variance is real · '
         f'educational use only. bet responsibly'),
        ('data & cadence',
         'espn stats & injuries · the odds api (draftkings) · nflverse · retrained every tuesday'),
    ]
    body = ''.join(
        f'<div class="mcard"><div class="mt">{t}</div><div class="mb">{b}</div></div>' for t, b in cards
    )
    return f"""
<style>
  :root {{{_VARS}}}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); color:var(--txt); font-family:var(--sans); font-size:14px; -webkit-font-smoothing:antialiased; }}
  .eyebrow {{ font-size:11px; color:var(--txt3); letter-spacing:0.07em; text-transform:lowercase; }}
  .title {{ font-size:20px; font-weight:700; margin:2px 0 16px; }}
  .grid {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; }}
  .mcard {{ background:var(--panel); border:1px solid var(--line); border-radius:9px; padding:14px 16px; }}
  .mcard .mt {{ font-size:11px; color:var(--accent); text-transform:lowercase; letter-spacing:0.06em; font-weight:700; }}
  .mcard .mb {{ font-size:13px; color:var(--txt2); line-height:1.6; margin-top:7px; }}
</style>
<div class="eyebrow">the model · {label}</div>
<div class="title">how it works</div>
<div class="grid">{body}</div>
"""


ROSTER_PAGE_SIZE = 11


def roster_height():
    return 250 + ROSTER_PAGE_SIZE * 40 + 54


def roster_html(rows, team, label):
    """Vault roster table: position-group filter + pagination."""
    data = json.dumps(rows)
    return f"""
<style>
  :root {{{_VARS}}}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); color:var(--txt); font-family:var(--sans); font-size:14px; -webkit-font-smoothing:antialiased; }}
  .mono {{ font-family:var(--mono); font-variant-numeric:tabular-nums; }}
  .eyebrow {{ font-size:11px; color:var(--txt3); letter-spacing:0.07em; text-transform:lowercase; }}
  .team {{ font-size:22px; font-weight:700; margin-top:2px; }}
  .head {{ display:flex; align-items:center; justify-content:space-between; margin:10px 0 12px; }}
  .head .cnt {{ font-size:12px; color:var(--txt3); }}
  .seg {{ display:flex; gap:4px; }}
  .seg button {{ background:var(--panel); border:1px solid var(--line); color:var(--txt2); font-size:12px;
      padding:5px 12px; border-radius:6px; cursor:pointer; font-family:inherit; }}
  .seg button.on {{ background:var(--accent); border-color:var(--accent); color:#0a0b0d; font-weight:600; }}
  .cols {{ display:grid; grid-template-columns:54px 1fr 56px 70px; gap:12px; padding:0 14px 7px;
      font-size:10px; color:var(--txt3); text-transform:lowercase; letter-spacing:0.06em; border-bottom:1px solid var(--line); }}
  .cols span:nth-child(3), .cols span:nth-child(4) {{ text-align:right; }}
  .prow {{ display:grid; grid-template-columns:54px 1fr 56px 70px; gap:12px; align-items:center;
      padding:9px 14px; border-bottom:1px solid var(--line); }}
  .prow:hover {{ background:var(--panel); }}
  .pos {{ font-size:10px; font-weight:700; color:var(--txt2); text-align:center; background:var(--panel2);
      border:1px solid var(--line); border-radius:5px; padding:3px 0; letter-spacing:0.03em; }}
  .pname {{ font-weight:600; font-size:14px; }}
  .num {{ text-align:right; font-family:var(--mono); font-variant-numeric:tabular-nums; color:var(--txt2); font-size:13px; }}
  .exp {{ text-align:right; font-family:var(--mono); font-variant-numeric:tabular-nums; color:var(--txt2); font-size:13px; }}
  .empty {{ padding:30px 14px; text-align:center; color:var(--txt3); font-size:13px; }}
{_PAGER_CSS}
</style>
<div class="eyebrow">roster · {label}</div>
<div class="team">{team}</div>
<div class="head">
  <div class="cnt" id="cnt"></div>
  <div class="seg">
    <button id="s-all" class="on">all</button>
    <button id="s-off">offense</button>
    <button id="s-def">defense</button>
    <button id="s-st">special</button>
  </div>
</div>
<div class="cols"><span>pos</span><span>player</span><span>#</span><span>exp</span></div>
<div id="rows"></div>
<div class="pager" id="pager" style="display:none">
  <div class="info" id="info"></div>
  <div class="nav"><button id="prev">‹ prev</button><span class="pg" id="pg"></span><button id="next">next ›</button></div>
</div>

<script>
  const ALL = {data};
  const SIZE = {ROSTER_PAGE_SIZE};
  const OFF = ['QB','RB','WR','TE','OL','OT','OG','G','C','FB'];
  const DEF = ['DL','DE','DT','LB','CB','S','DB','EDGE','NT'];
  const ST = ['K','P','LS'];
  let view = 'all', page = 0;
  const rowsEl = document.getElementById('rows');
  const pagerEl = document.getElementById('pager');
  const cntEl = document.getElementById('cnt');
  const infoEl = document.getElementById('info');
  const pgEl = document.getElementById('pg');
  const prev = document.getElementById('prev');
  const next = document.getElementById('next');

  function list() {{
    if (view === 'off') return ALL.filter(p => OFF.includes(p.pos));
    if (view === 'def') return ALL.filter(p => DEF.includes(p.pos));
    if (view === 'st') return ALL.filter(p => ST.includes(p.pos));
    return ALL;
  }}
  function render() {{
    const L = list();
    const pages = Math.max(1, Math.ceil(L.length / SIZE));
    if (page >= pages) page = pages - 1;
    cntEl.textContent = L.length + ' players';
    rowsEl.innerHTML = '';
    if (!L.length) {{ rowsEl.innerHTML = '<div class="empty">no players</div>'; pagerEl.style.display='none'; return; }}
    const start = page * SIZE;
    L.slice(start, start + SIZE).forEach(p => {{
      const r = document.createElement('div');
      r.className = 'prow';
      r.innerHTML = '<span class="pos">' + p.pos + '</span>' +
        '<span class="pname">' + p.player + '</span>' +
        '<span class="num">' + (p.num != null ? p.num : '-') + '</span>' +
        '<span class="exp">' + (p.exp != null ? p.exp + 'y' : '-') + '</span>';
      rowsEl.appendChild(r);
    }});
    if (pages > 1) {{
      pagerEl.style.display = 'flex';
      infoEl.textContent = (start + 1) + '-' + Math.min(start + SIZE, L.length) + ' of ' + L.length;
      pgEl.textContent = (page + 1) + ' / ' + pages;
      prev.disabled = page === 0;
      next.disabled = page >= pages - 1;
    }} else {{ pagerEl.style.display = 'none'; }}
  }}
  prev.addEventListener('click', () => {{ if (page > 0) {{ page--; render(); }} }});
  next.addEventListener('click', () => {{ if (page < Math.ceil(list().length / SIZE) - 1) {{ page++; render(); }} }});
  [['s-all','all'],['s-off','off'],['s-def','def'],['s-st','st']].forEach(([id, v]) => {{
    document.getElementById(id).addEventListener('click', () => {{
      document.querySelectorAll('.seg button').forEach(b => b.classList.remove('on'));
      document.getElementById(id).classList.add('on');
      view = v; page = 0; render();
    }});
  }});
  render();
</script>
"""


def matchup_height():
    return 470


def matchup_html(prediction, home, away, label):
    """Vault head-to-head breakdown for a chosen matchup."""
    line = float(prediction['model_betting_line'])
    prob = float(prediction['ml_home_win_probability'])
    prob_team = home if prob >= 0.5 else away
    prob_show = prob if prob >= 0.5 else 1 - prob

    pills = []
    for key, val in sorted(prediction['components'].items(), key=lambda kv: abs(kv[1]), reverse=True):
        label_txt = DRIVER_LABELS.get(key, key.replace('_', ' '))
        cls = 'x' if key == 'home_field' else 'p' if val > 0.05 else 'n' if val < -0.05 else 'x'
        pills.append(f'<span class="pill {cls}">{label_txt} {val:+.1f}</span>')
    pills_html = ''.join(pills)

    inj = prediction['injury_impact']
    adv = float(inj['away']) - float(inj['home'])
    if abs(adv) < 3:
        health = 'health edge · even'
    else:
        healthier = home if adv > 0 else away
        health = f'health edge · {healthier} by {abs(adv):.1f}'

    return f"""
<style>
  :root {{{_VARS}}}
  * {{ box-sizing:border-box; margin:0; padding:0; }}
  body {{ background:var(--bg); color:var(--txt); font-family:var(--sans); font-size:14px; -webkit-font-smoothing:antialiased; }}
  .mono {{ font-family:var(--mono); font-variant-numeric:tabular-nums; }}
  .eyebrow {{ font-size:11px; color:var(--txt3); letter-spacing:0.07em; text-transform:lowercase; }}
  .vs {{ font-size:26px; font-weight:800; margin-top:3px; letter-spacing:-0.01em; }}
  .vs span {{ color:var(--txt3); font-weight:400; }}
  .recs {{ font-size:12px; color:var(--txt3); margin-top:2px; }}
  .dgrid {{ display:grid; grid-template-columns:repeat(3,1fr); gap:8px; margin:16px 0; }}
  .dcell {{ background:var(--panel2); border:1px solid var(--line); border-radius:8px; padding:12px 13px; }}
  .dcell .k {{ font-size:10px; color:var(--txt3); text-transform:lowercase; letter-spacing:0.05em; }}
  .dcell .val {{ font-family:var(--mono); font-variant-numeric:tabular-nums; font-size:20px; font-weight:700; margin-top:4px; }}
  .drivers {{ display:flex; gap:6px; flex-wrap:wrap; align-items:center; margin:4px 0 18px; }}
  .drivers .lab {{ font-size:11px; color:var(--txt3); margin-right:2px; }}
  .pill {{ font-size:11px; font-family:var(--mono); font-variant-numeric:tabular-nums; padding:3px 9px;
      border-radius:5px; background:var(--panel2); border:1px solid var(--line); }}
  .pill.p {{ color:var(--pos); }} .pill.n {{ color:var(--neg); }} .pill.x {{ color:var(--txt2); }}
  .inj {{ display:grid; grid-template-columns:1fr 1fr; gap:8px; }}
  .icard {{ background:var(--panel); border:1px solid var(--line); border-radius:8px; padding:12px 14px; }}
  .icard .team {{ font-weight:700; font-size:14px; }}
  .icard .big {{ font-family:var(--mono); font-variant-numeric:tabular-nums; font-size:22px; font-weight:700; margin-top:4px; }}
  .icard .crit {{ font-size:11px; color:var(--txt3); margin-top:3px; }}
  .health {{ margin-top:12px; font-size:12px; color:var(--accent); letter-spacing:0.03em; }}
</style>
<div class="eyebrow">head-to-head · {label}</div>
<div class="vs">{away} <span>@</span> {home}</div>
<div class="recs">{prediction.get('away_record','')} · {prediction.get('home_record','')}</div>
<div class="dgrid">
  <div class="dcell"><div class="k">model line</div><div class="val">{home} {line:+.1f}</div></div>
  <div class="dcell"><div class="k">{prob_team} win prob</div><div class="val">{prob_show*100:.0f}%</div></div>
  <div class="dcell"><div class="k">confidence</div><div class="val">{prediction.get('confidence','-')}</div></div>
</div>
<div class="drivers"><span class="lab">drivers</span>{pills_html}</div>
<div class="inj">
  <div class="icard"><div class="team">{home}</div><div class="big">{float(inj['home']):.1f}</div><div class="crit">{inj['critical_home']} critical · injury impact</div></div>
  <div class="icard"><div class="team">{away}</div><div class="big">{float(inj['away']):.1f}</div><div class="crit">{inj['critical_away']} critical · injury impact</div></div>
</div>
<div class="health">{health}</div>
"""


def resolve_slate_week(db, current_season):
    """Pick the week to show: current season's latest completed reg week, else
    the most recent season with completed regular-season games."""
    row = db.execute_query(
        "SELECT MAX(week) w FROM games WHERE season=%s AND week<=18 AND game_status='Final'",
        (current_season,),
    )
    if row and row[0]['w']:
        return current_season, int(row[0]['w']), False, f"week {int(row[0]['w'])} · {current_season}"

    row = db.execute_query(
        "SELECT season, MAX(week) w FROM games WHERE week<=18 AND game_status='Final' "
        "GROUP BY season ORDER BY season DESC LIMIT 1"
    )
    if row and row[0]['w']:
        s, w = int(row[0]['season']), int(row[0]['w'])
        return s, w, True, f"week {w} · {s} (final)"

    return current_season, 1, True, f"week 1 · {current_season}"
