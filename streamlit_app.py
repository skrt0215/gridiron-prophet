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
    components.html(vault.slate_html(hero_payload, hero_accuracy), height=860, scrolling=True)

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
    st.markdown("<div class='section-header'>HEAD-TO-HEAD MATCHUP</div>", unsafe_allow_html=True)
    
    analyzer = get_injury_analyzer()
    teams = analyzer.db.get_all_teams()
    team_abbrs = sorted([t['abbreviation'] for t in teams])
    
    col1, col2, col3 = st.columns([2, 1, 2])
    
    with col1:
        away_team = st.selectbox("Away Team", team_abbrs, key="matchup_away")
    
    with col2:
        st.markdown("<div style='text-align: center; padding-top: 30px; font-size: 2rem;'>@</div>", unsafe_allow_html=True)
    
    with col3:
        home_team = st.selectbox("Home Team", team_abbrs, key="matchup_home")
    
    if st.button("⚔️ ANALYZE MATCHUP", use_container_width=True):
        with st.spinner("Comparing teams..."):
            predictor = load_predictor()
            
            prediction = predictor.calculate_comprehensive_prediction(home_team, away_team, st.session_state.current_season, st.session_state.current_week)
            
            st.markdown(f"<div class='game-title' style='text-align: center; margin: 2rem 0;'>{away_team} @ {home_team}</div>", unsafe_allow_html=True)
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{home_team} {prediction['model_betting_line']:+.1f}</div>
                    <div class="metric-label">Model Spread</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{prediction['ml_home_win_probability']:.1%}</div>
                    <div class="metric-label">{home_team} Win Probability</div>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{prediction['confidence']}</div>
                    <div class="metric-label">Prediction Confidence</div>
                </div>
                """, unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            with st.expander("📊 PREDICTION BREAKDOWN", expanded=True):
                components_df = pd.DataFrame([
                    {"Factor": k.replace('_', ' ').title(), "Value": f"{v:+.2f}"}
                    for k, v in prediction['components'].items()
                ])
                st.dataframe(components_df, use_container_width=True, hide_index=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{prediction['injury_impact']['home']:.1f}</div>
                    <div class="metric-label">{home_team} Injury Impact</div>
                    <div style="color: #94a3b8; font-size: 0.85rem; margin-top: 0.5rem;">
                        {prediction['injury_impact']['critical_home']} critical injuries
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{prediction['injury_impact']['away']:.1f}</div>
                    <div class="metric-label">{away_team} Injury Impact</div>
                    <div style="color: #94a3b8; font-size: 0.85rem; margin-top: 0.5rem;">
                        {prediction['injury_impact']['critical_away']} critical injuries
                    </div>
                </div>
                """, unsafe_allow_html=True)

with tab4:
    st.markdown("<div class='section-header'>TEAM ROSTERS</div>", unsafe_allow_html=True)
    
    analyzer = get_injury_analyzer()
    teams = analyzer.db.get_all_teams()
    team_abbrs = sorted([t['abbreviation'] for t in teams])
    
    col1, col2 = st.columns([1, 2])
    
    with col1:
        selected_team = st.selectbox("Select Team", team_abbrs, key="roster_team")
    
    with col2:
        if st.button("📋 LOAD ROSTER", use_container_width=True):
            with st.spinner(f"Loading {selected_team} roster..."):
                query = """
                    SELECT DISTINCT
                        p.name as player_name,
                        ps.position,
                        ps.jersey_number,
                        ps.status,
                        p.height,
                        p.weight,
                        p.college,
                        ps.years_in_league,
                        ps.games_played,
                        ps.games_started
                    FROM player_seasons ps
                    JOIN players p ON ps.player_id = p.player_id
                    WHERE ps.team_id = (SELECT team_id FROM teams WHERE abbreviation = %s)
                    AND ps.season = %s
                    AND ps.roster_status = 'Active'
                    ORDER BY 
                        CASE ps.position
                            WHEN 'QB' THEN 1
                            WHEN 'RB' THEN 2
                            WHEN 'WR' THEN 3
                            WHEN 'TE' THEN 4
                            WHEN 'OL' THEN 5
                            WHEN 'DL' THEN 6
                            WHEN 'LB' THEN 7
                            WHEN 'DB' THEN 8
                            WHEN 'K' THEN 9
                            WHEN 'P' THEN 10
                            ELSE 11
                        END,
                        p.name
                """
                
                roster = analyzer.db.execute_query(query, (selected_team, st.session_state.current_season))
                
                if roster:
                    st.success(f"✅ {len(roster)} active players")
                    
                    df = pd.DataFrame(roster)
                    
                    tab_off, tab_def, tab_st = st.tabs(["🏈 Offense", "🛡️ Defense", "🎯 Special Teams"])
                    
                    with tab_off:
                        offense = df[df['position'].isin(['QB', 'RB', 'WR', 'TE', 'OL'])]
                        st.dataframe(offense, use_container_width=True, hide_index=True)
                    
                    with tab_def:
                        defense = df[df['position'].isin(['DL', 'LB', 'DB'])]
                        st.dataframe(defense, use_container_width=True, hide_index=True)
                    
                    with tab_st:
                        special = df[df['position'].isin(['K', 'P', 'LS'])]
                        st.dataframe(special, use_container_width=True, hide_index=True)
                else:
                    st.warning(f"No roster data for {selected_team}")

with tab5:
    st.markdown("<div class='section-header'>WEEKLY ACCURACY</div>", unsafe_allow_html=True)
    
    db = get_db()
    
    accuracy_data = db.execute_query("""
        SELECT 
            week,
            total_predictions,
            correct_predictions,
            accuracy_pct,
            spread_3pt_accuracy,
            spread_7pt_accuracy,
            avg_margin_error,
            high_conf_total,
            high_conf_correct,
            calculated_date
        FROM weekly_accuracy
        WHERE season = %s
        ORDER BY week
    """, (st.session_state.current_season,))
    
    if accuracy_data:
        df = pd.DataFrame(accuracy_data)
        
        df['high_conf_accuracy'] = df.apply(
            lambda row: (row['high_conf_correct'] / row['high_conf_total'] * 100) 
            if row['high_conf_total'] and row['high_conf_total'] > 0 else None,
            axis=1
        )
        
        col1, col2, col3, col4 = st.columns(4)
        
        total_correct = df['correct_predictions'].sum()
        total_games = df['total_predictions'].sum()
        overall_accuracy = (total_correct / total_games * 100) if total_games > 0 else 0
        
        with col1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{overall_accuracy:.1f}%</div>
                <div class="metric-label">Overall Accuracy</div>
                <div style="color: #94a3b8; font-size: 0.85rem; margin-top: 0.5rem;">
                    {total_correct}-{total_games - total_correct}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            avg_spread_3pt = df['spread_3pt_accuracy'].mean() if 'spread_3pt_accuracy' in df.columns else 0
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{avg_spread_3pt:.1f}%</div>
                <div class="metric-label">Avg Spread (±3pts)</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            avg_margin = df['avg_margin_error'].mean() if 'avg_margin_error' in df.columns else 0
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{avg_margin:.1f}</div>
                <div class="metric-label">Avg Margin Error</div>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            high_conf_total = df['high_conf_total'].sum()
            high_conf_correct = df['high_conf_correct'].sum()
            high_conf_acc = (high_conf_correct / high_conf_total * 100) if high_conf_total > 0 else 0
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{high_conf_acc:.1f}%</div>
                <div class="metric-label">High Confidence</div>
                <div style="color: #94a3b8; font-size: 0.85rem; margin-top: 0.5rem;">
                    {high_conf_correct}-{high_conf_total - high_conf_correct if high_conf_total > 0 else 0}
                </div>
            </div>
            """, unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)
        
        fig = go.Figure()
        
        fig.add_trace(go.Scatter(
            x=df['week'],
            y=df['accuracy_pct'],
            mode='lines+markers',
            name='Winner Accuracy',
            line=dict(color='#4ade80', width=3),
            marker=dict(size=10),
        ))
        
        if 'spread_3pt_accuracy' in df.columns:
            fig.add_trace(go.Scatter(
                x=df['week'],
                y=df['spread_3pt_accuracy'],
                mode='lines+markers',
                name='Spread (±3pts)',
                line=dict(color='#f59e0b', width=2),
                marker=dict(size=8),
            ))
        
        fig.add_hline(y=overall_accuracy, line_dash="dot", line_color="rgba(255,255,255,0.3)")
        
        fig.update_layout(
            title="Accuracy Trends",
            xaxis_title="Week",
            yaxis_title="Accuracy (%)",
            plot_bgcolor='rgba(0,0,0,0)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No accuracy data available yet")

with tab6:
    st.markdown("<div class='section-header'>HOW IT WORKS</div>", unsafe_allow_html=True)
    
    faq_tab1, faq_tab2, faq_tab3 = st.tabs(["📊 Model", "💰 Strategy", "🎯 Accuracy"])
    
    with faq_tab1:
        st.markdown(f"""
        ### Machine Learning Component
        - **Training Data**: 800+ NFL games (2022-2024)
        - **Algorithm**: Random Forest Classifier
        - **Current Accuracy**: {get_overall_accuracy_display()}
        - **Updates**: Every Tuesday with new results
        
        ### Key Factors Analyzed
        1. Team performance metrics (home/away splits)
        2. Injury impact scores (position-weighted)
        3. Historical matchups
        4. Home field advantage (2.5 pts)
        
        ### Output
        - Model Spread (our prediction)
        - Win Probability
        - Confidence Level (High/Medium/Low)
        - Edge vs Vegas
        """)
    
    with faq_tab2:
        st.markdown("""
        ### Understanding Edge
        **Edge = Model Line - Vegas Line**
        
        - **Negative Edge**: Model favors home team MORE than Vegas
        - **Positive Edge**: Model favors away team MORE than Vegas
        
        ### Edge Thresholds
        - 🔥 **≥10 pts**: Best opportunities
        - ⚡ **5-9 pts**: Good value
        - ⚠️ **3-4 pts**: Minimum threshold
        - ❌ **<3 pts**: Skip
        
        ### Bankroll Management
        - 1 unit = 1-2% of bankroll
        - HIGH confidence = 2-3 units
        - MEDIUM confidence = 1-2 units
        - LOW confidence = 0.5-1 unit
        
        **Never bet > 5% on single game**
        """)
    
    with faq_tab3:
        st.markdown(f"""
        ### Performance Metrics
        - **Model Accuracy**: {get_overall_accuracy_display()}
        - **Breakeven Rate**: 52.4% (at -110 odds)
        
        ### Weekly Updates
        1. Monday: Collect results
        2. Tuesday: Retrain model
        3. Wednesday: Update injuries
        4. Thursday: Generate predictions
        
        ### Limitations
        ⚠️ Past performance doesn't guarantee future results  
        ⚠️ Variance exists week-to-week (60-75% range)  
        ⚠️ Always bet responsibly  
        
        ### Data Sources
        - NFL official statistics
        - ESPN injury reports
        - DraftKings betting lines
        - 2022-2024 historical data
        """)

st.markdown("---")
st.markdown(f"""
<div style="text-align: center; color: #94a3b8; padding: 1rem;">
    <strong>Gridiron Prophet</strong> | Model Accuracy: {get_overall_accuracy_display()} | Created by Kurt<br>
    <span style="font-size: 0.85rem;">Bet responsibly. Past performance does not guarantee future results.</span>
</div>
""", unsafe_allow_html=True)