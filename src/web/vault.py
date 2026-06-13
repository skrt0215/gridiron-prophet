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
            edge_show = '—'
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
            'vegas': vegas if vegas else '—',
            'edge': edge_show, 'edge_val': edge if edge is not None else 0.0,
            'cls': edge_cls, 'flag': flag, 'conf': pred.get('confidence', '—'),
            'prob': f"{prob_team} {prob_show*100:.0f}%",
            'drivers': _driver_pills(pred['components']),
        })

    if any(r['edge'] != '—' for r in rows):
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


def slate_html(payload, accuracy_pct):
    data = json.dumps(payload['games'])
    label = payload['label']
    n = len(payload['games'])
    flagged = payload['flagged']
    acc = f"{accuracy_pct*100:.1f}%" if accuracy_pct else "—"
    offseason = payload['offseason']
    banner = ''
    if offseason:
        banner = (f'<div class="banner">offseason · no live odds — showing model projections '
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

<script>
  const GAMES = {data};
  const DEFAULT_VIEW = "{default_view}";
  const rowsEl = document.getElementById('rows');

  function flagged(g) {{ return g.flag === 'flag-hi' || g.flag === 'flag-md'; }}

  function render(view) {{
    rowsEl.innerHTML = '';
    let list = GAMES;
    if (view === 'edges') list = GAMES.filter(flagged);
    if (!list.length) {{
      rowsEl.innerHTML = '<div class="empty">no games with an edge ≥3 — switch to all games</div>';
      return;
    }}
    list.forEach(g => {{
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
      r.addEventListener('click', () => r.classList.toggle('open'));
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
  }}

  const segE = document.getElementById('seg-edges');
  const segA = document.getElementById('seg-all');
  segE.addEventListener('click', () => {{ segE.classList.add('on'); segA.classList.remove('on'); render('edges'); }});
  segA.addEventListener('click', () => {{ segA.classList.add('on'); segE.classList.remove('on'); render('all'); }});
  render(DEFAULT_VIEW);
</script>
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
