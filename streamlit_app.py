import streamlit as st
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

from src.models.master_betting_predictor import MasterBettingPredictor
from src.analysis.injury_impact import InjuryImpactAnalyzer
from src.database.db_manager import DatabaseManager
from src.config.season import CURRENT_SEASON
from src.web import vault
import streamlit.components.v1 as components
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Gridiron Prophet", page_icon="🏈", layout="wide", initial_sidebar_state="collapsed")

@st.cache_resource
def load_predictor():
    predictor = MasterBettingPredictor()
    predictor.train_ml_model()
    return predictor

@st.cache_resource
def get_db():
    return DatabaseManager()

@st.cache_resource
def get_injury_analyzer():
    return InjuryImpactAnalyzer()

@st.cache_data(ttl=3600)
def get_overall_accuracy_display():
    """Honest out-of-sample (holdout) accuracy from the trained model, or 'N/A'."""
    try:
        acc = load_predictor().holdout_accuracy
        if acc:
            return f"{acc * 100:.1f}%"
    except Exception:
        pass
    return "N/A"

@st.cache_data(ttl=900, show_spinner=False)
def get_hero():
    """Resolve the slate week and compute the Vault hero payload + accuracy."""
    predictor = load_predictor()
    db = get_db()
    season, week, offseason, label = vault.resolve_slate_week(db, CURRENT_SEASON)
    payload = vault.build_payload(predictor, db, season, week, offseason, label)
    accuracy = predictor.holdout_accuracy
    return payload, accuracy, season, week

@st.cache_data(ttl=900, show_spinner=False)
def get_team_injury(team, season, week):
    return get_injury_analyzer().get_team_injury_impact(team, season, week)

@st.cache_data(ttl=900, show_spinner=False)
def get_matchup(home, away, season, week):
    return load_predictor().calculate_comprehensive_prediction(home, away, season, week)

@st.cache_data(ttl=900, show_spinner=False)
def get_roster(team, season):
    return get_db().execute_query("""
        SELECT p.name AS player, ps.position AS pos,
               ps.jersey_number AS num, ps.years_in_league AS exp
        FROM player_seasons ps
        JOIN players p ON ps.player_id = p.player_id
        WHERE ps.team_id = (SELECT team_id FROM teams WHERE abbreviation = %s)
        AND ps.season = %s AND ps.roster_status = 'Active'
        ORDER BY CASE ps.position
            WHEN 'QB' THEN 1 WHEN 'RB' THEN 2 WHEN 'WR' THEN 3 WHEN 'TE' THEN 4
            WHEN 'OL' THEN 5 WHEN 'OT' THEN 5 WHEN 'OG' THEN 5 WHEN 'G' THEN 5 WHEN 'C' THEN 5
            WHEN 'DL' THEN 6 WHEN 'DE' THEN 6 WHEN 'DT' THEN 6 WHEN 'LB' THEN 7
            WHEN 'CB' THEN 8 WHEN 'S' THEN 8 WHEN 'DB' THEN 8
            WHEN 'K' THEN 9 WHEN 'P' THEN 10 ELSE 11 END, p.name
    """, (team, season))

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;700;900&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    .stApp {
        background: linear-gradient(135deg, #0a0e1a 0%, #1a1f35 100%);
    }
    
    .main-header {
        background: linear-gradient(90deg, #0B2265 0%, #1a3a8a 100%);
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(11, 34, 101, 0.4);
    }
    
    .main-title {
        font-size: 3.5rem;
        font-weight: 900;
        color: white;
        margin: 0;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
    }
    
    .main-subtitle {
        font-size: 1.2rem;
        color: #a8c5ff;
        margin-top: 0.5rem;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #1e2742 0%, #2a3654 100%);
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 4px solid #0B2265;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        transition: transform 0.2s;
    }
    
    .metric-card:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.4);
    }
    
    .metric-value {
        font-size: 2.5rem;
        font-weight: 900;
        color: #4ade80;
        line-height: 1;
    }
    
    .metric-label {
        font-size: 0.9rem;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 0.5rem;
    }
    
    .bet-card {
        background: linear-gradient(135deg, #1e2742 0%, #252d47 100%);
        border-radius: 15px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        border: 2px solid transparent;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        transition: all 0.3s;
    }
    
    .bet-card:hover {
        border-color: #0B2265;
        transform: scale(1.02);
        box-shadow: 0 8px 25px rgba(11, 34, 101, 0.3);
    }
    
    .bet-card-fire {
        border-left: 6px solid #ef4444;
        background: linear-gradient(135deg, #2d1e1e 0%, #3d2525 100%);
    }
    
    .bet-card-lightning {
        border-left: 6px solid #f59e0b;
        background: linear-gradient(135deg, #2d2516 0%, #3d3220 100%);
    }
    
    .bet-card-warning {
        border-left: 6px solid #eab308;
        background: linear-gradient(135deg, #2d2916 0%, #3d3620 100%);
    }
    
    .game-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: white;
        margin-bottom: 0.5rem;
    }
    
    .bet-recommendation {
        font-size: 1.5rem;
        font-weight: 900;
        color: #4ade80;
        padding: 0.8rem;
        background: rgba(74, 222, 128, 0.1);
        border-radius: 8px;
        text-align: center;
        margin: 1rem 0;
    }
    
    .confidence-bar {
        background: #1e293b;
        height: 30px;
        border-radius: 15px;
        overflow: hidden;
        margin: 1rem 0;
        position: relative;
    }
    
    .confidence-fill {
        height: 100%;
        background: linear-gradient(90deg, #10b981 0%, #059669 100%);
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        font-weight: 700;
        transition: width 0.5s;
    }
    
    .edge-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 700;
        font-size: 1.1rem;
    }
    
    .edge-fire {
        background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
        color: white;
    }
    
    .edge-lightning {
        background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
        color: white;
    }
    
    .edge-warning {
        background: linear-gradient(135deg, #eab308 0%, #ca8a04 100%);
        color: white;
    }
    
    .injury-critical {
        background: linear-gradient(135deg, #991b1b 0%, #7f1d1d 100%);
        border-left: 4px solid #ef4444;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    
    .injury-moderate {
        background: linear-gradient(135deg, #854d0e 0%, #713f12 100%);
        border-left: 4px solid #f59e0b;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    
    .injury-minor {
        background: linear-gradient(135deg, #14532d 0%, #166534 100%);
        border-left: 4px solid #22c55e;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
    }
    
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 1rem;
        margin: 1rem 0;
    }
    
    .stat-item {
        background: rgba(255, 255, 255, 0.05);
        padding: 1rem;
        border-radius: 8px;
        text-align: center;
    }
    
    .stat-value {
        font-size: 1.5rem;
        font-weight: 700;
        color: #4ade80;
    }
    
    .stat-label {
        font-size: 0.8rem;
        color: #94a3b8;
        margin-top: 0.3rem;
    }
    
    .section-header {
        font-size: 2rem;
        font-weight: 900;
        color: white;
        margin: 2rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 3px solid #0B2265;
    }
    
    div[data-testid="stExpander"] {
        background: linear-gradient(135deg, #1e2742 0%, #252d47 100%);
        border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background: transparent;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: linear-gradient(135deg, #1e2742 0%, #2a3654 100%);
        color: white;
        border-radius: 10px 10px 0 0;
        padding: 1rem 2rem;
        font-weight: 600;
        border: 2px solid transparent;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, #0B2265 0%, #1a3a8a 100%);
        border-color: #0B2265;
    }
    
    .stButton > button {
        background: linear-gradient(90deg, #0B2265 0%, #1a3a8a 100%);
        color: white;
        border: none;
        padding: 0.8rem 2rem;
        border-radius: 10px;
        font-weight: 700;
        font-size: 1.1rem;
        transition: all 0.3s;
        box-shadow: 0 4px 15px rgba(11, 34, 101, 0.4);
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(11, 34, 101, 0.6);
    }
    
    [data-testid="stSidebar"] {
        background: linear-gradient(135deg, #0f1419 0%, #1a1f2e 100%);
    }
</style>
""", unsafe_allow_html=True)

st.markdown(vault.shell_css(), unsafe_allow_html=True)

with st.spinner("training model & loading slate..."):
    hero_payload, hero_accuracy, slate_season, slate_week = get_hero()

components.html(vault.ticker_html(hero_payload), height=48)

if 'predictions_loaded' not in st.session_state:
    st.session_state.predictions_loaded = False
if 'recommendations' not in st.session_state:
    st.session_state.recommendations = []
if 'current_season' not in st.session_state:
    st.session_state.current_season = slate_season
if 'current_week' not in st.session_state:
    st.session_state.current_week = slate_week

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["THIS WEEK", "INJURIES", "MATCHUP", "ROSTERS", "PERFORMANCE", "MODEL"])

with tab1:
    components.html(vault.slate_html(hero_payload, hero_accuracy), height=vault.slate_height(hero_payload['offseason']), scrolling=False)

with tab2:
    st.markdown('<div class="vault-eyebrow">injury intelligence</div>', unsafe_allow_html=True)
    _inj_analyzer = get_injury_analyzer()
    _inj_teams = sorted(t['abbreviation'] for t in _inj_analyzer.db.get_all_teams())
    _c1, _c2 = st.columns([1, 3])
    with _c1:
        _inj_team = st.selectbox('team', _inj_teams, key='injury_team')
    _impact = get_team_injury(_inj_team, slate_season, slate_week)
    components.html(vault.injuries_html(_impact, hero_payload['label']), height=vault.injuries_height(), scrolling=False)

with tab3:
    st.markdown('<div class="vault-eyebrow">head-to-head</div>', unsafe_allow_html=True)
    _mu_teams = sorted(t['abbreviation'] for t in get_injury_analyzer().db.get_all_teams())
    _a, _mid, _b = st.columns([2, 1, 2])
    with _a:
        _away = st.selectbox('away', _mu_teams, index=0, key='matchup_away')
    with _mid:
        st.markdown("<div style='text-align:center;padding-top:30px;color:#5e636d;font-size:1.4rem'>@</div>", unsafe_allow_html=True)
    with _b:
        _home = st.selectbox('home', _mu_teams, index=min(1, len(_mu_teams)-1), key='matchup_home')
    if _away == _home:
        st.markdown("<div style='color:#9298a3;font-size:13px;padding:8px 2px'>pick two different teams</div>", unsafe_allow_html=True)
    else:
        _pred = get_matchup(_home, _away, slate_season, slate_week)
        components.html(vault.matchup_html(_pred, _home, _away, hero_payload['label']), height=vault.matchup_height(), scrolling=False)

with tab4:
    st.markdown('<div class="vault-eyebrow">rosters</div>', unsafe_allow_html=True)
    _r_teams = sorted(t['abbreviation'] for t in get_injury_analyzer().db.get_all_teams())
    _rc1, _rc2 = st.columns([1, 3])
    with _rc1:
        _r_team = st.selectbox('team', _r_teams, key='roster_team')
    _roster = get_roster(_r_team, CURRENT_SEASON)
    components.html(vault.roster_html(_roster, _r_team, f'{CURRENT_SEASON} active'), height=vault.roster_height(), scrolling=False)

with tab5:
    st.markdown('<div class="vault-eyebrow">performance</div>', unsafe_allow_html=True)
    _es = load_predictor().ml_predictor.eval_stats
    components.html(vault.performance_html(_es), height=vault.performance_height(), scrolling=False)

with tab6:
    components.html(vault.model_html(hero_accuracy, 'gridiron prophet'), height=vault.model_height(), scrolling=False)

st.markdown("---")
st.markdown(f"""
<div style="text-align: center; color: #94a3b8; padding: 1rem;">
    <strong>Gridiron Prophet</strong> | Model Accuracy: {get_overall_accuracy_display()} | Created by Kurt<br>
    <span style="font-size: 0.85rem;">Bet responsibly. Past performance does not guarantee future results.</span>
</div>
""", unsafe_allow_html=True)