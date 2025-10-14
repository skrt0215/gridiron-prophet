import streamlit as st
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.models.master_betting_predictor import MasterBettingPredictor
from src.analysis.injury_impact import InjuryImpactAnalyzer
from src.database.db_manager import DatabaseManager
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

st.set_page_config(page_title="Gridiron Prophet", page_icon="🏈", layout="wide")

st.title("🏈 Gridiron Prophet")
st.subheader("NFL Betting Analysis & Predictions")

st.sidebar.header("⚙️ Settings")

faq_option = st.sidebar.selectbox(
    "FAQ's",
    ["Select...", "How It Works"]
)

analysis_type = st.sidebar.selectbox(
    "Analysis Type",
    ["Weekly Predictions", "Team Rosters", "Injury Report", "Team Comparison"]
)

season = st.sidebar.number_input("Season", min_value=2022, max_value=2025, value=2025, step=1)
week = st.sidebar.number_input("Week", min_value=1, max_value=18, value=6, step=1)

st.sidebar.markdown("---")

if st.sidebar.button("📊 View Weekly Accuracy", use_container_width=True):
    st.session_state.show_accuracy = True
    st.session_state.faq_option = None
    st.session_state.analysis_type = None

if 'show_accuracy' not in st.session_state:
    st.session_state.show_accuracy = False

if 'prev_faq' not in st.session_state:
    st.session_state.prev_faq = "Select..."

if 'prev_analysis' not in st.session_state:
    st.session_state.prev_analysis = "Weekly Predictions"

if faq_option != st.session_state.prev_faq:
    if faq_option != "Select...":
        st.session_state.show_accuracy = False
        st.session_state.faq_option = faq_option
        st.session_state.analysis_type = None
    st.session_state.prev_faq = faq_option

if analysis_type != st.session_state.prev_analysis:
    st.session_state.show_accuracy = False
    st.session_state.analysis_type = analysis_type
    st.session_state.faq_option = None
    st.session_state.prev_analysis = analysis_type

if st.session_state.show_accuracy:
    st.header("📊 Weekly Accuracy Tracking")
    
    tab_help, tab_accuracy = st.tabs(["💡 How to Read This", "📈 Accuracy Data"])
    
    with tab_help:
        st.markdown("""
        ## Understanding The Model's Performance
        
        ### 📊 Key Metrics Explained
        
        **Winner Accuracy**
        - Did you correctly predict which team would win?
        - Target: 60%+
        
        **Spread Accuracy (±3 points)**
        - How close was your predicted point margin?
        - Target: 40%+
        
        **Spread Accuracy (±7 points)**
        - Were you in the general ballpark?
        - Target: 70%+
        
        **Average Margin Error**
        - Average difference between predicted and actual margins
        - Lower is better (Target: Under 7 points)
        
        **HIGH Confidence Accuracy**
        - Performance on your most confident picks
        - Target: 70%+
                    """)
    
    with tab_accuracy:
        db = DatabaseManager()
        
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
        """, (season,))
        
        if accuracy_data:
            df = pd.DataFrame(accuracy_data)
            
            df['high_conf_accuracy'] = df.apply(
                lambda row: (row['high_conf_correct'] / row['high_conf_total'] * 100) 
                if row['high_conf_total'] and row['high_conf_total'] > 0 else None,
                axis=1
            )
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_correct = df['correct_predictions'].sum()
                total_games = df['total_predictions'].sum()
                overall_accuracy = (total_correct / total_games * 100) if total_games > 0 else 0
                st.metric(
                    "Overall Winner Accuracy", 
                    f"{overall_accuracy:.1f}%", 
                    f"{total_correct}-{total_games - total_correct}"
                )
            
            with col2:
                avg_spread_3pt = df['spread_3pt_accuracy'].mean() if 'spread_3pt_accuracy' in df.columns else 0
                st.metric(
                    "Avg Spread Accuracy (±3pts)", 
                    f"{avg_spread_3pt:.1f}%" if avg_spread_3pt else "N/A"
                )
            
            with col3:
                avg_margin = df['avg_margin_error'].mean() if 'avg_margin_error' in df.columns else 0
                st.metric(
                    "Avg Point Margin Error", 
                    f"{avg_margin:.1f} pts" if avg_margin else "N/A"
                )
            
            with col4:
                high_conf_total = df['high_conf_total'].sum()
                high_conf_correct = df['high_conf_correct'].sum()
                high_conf_acc = (high_conf_correct / high_conf_total * 100) if high_conf_total > 0 else 0
                st.metric(
                    "HIGH Confidence Accuracy",
                    f"{high_conf_acc:.1f}%" if high_conf_total > 0 else "N/A",
                    f"{high_conf_correct}-{high_conf_total - high_conf_correct}" if high_conf_total > 0 else ""
                )
            
            tab1, tab2, tab3 = st.tabs(["📈 Accuracy Trends", "🎯 Performance Analysis", "📋 Detailed Results"])
            
            with tab1:
                st.subheader("Accuracy by Week")
                
                fig = go.Figure()
                
                fig.add_trace(go.Scatter(
                    x=df['week'],
                    y=df['accuracy_pct'],
                    mode='lines+markers',
                    name='Winner Accuracy',
                    line=dict(color='#1f77b4', width=3),
                    marker=dict(size=10),
                    hovertemplate='Week %{x}<br>Accuracy: %{y:.1f}%<extra></extra>'
                ))
                
                if 'spread_3pt_accuracy' in df.columns and df['spread_3pt_accuracy'].notna().any():
                    fig.add_trace(go.Scatter(
                        x=df['week'],
                        y=df['spread_3pt_accuracy'],
                        mode='lines+markers',
                        name='Spread Accuracy (±3pts)',
                        line=dict(color='#ff7f0e', width=2, dash='dash'),
                        marker=dict(size=8),
                        hovertemplate='Week %{x}<br>±3pts: %{y:.1f}%<extra></extra>'
                    ))
                
                high_conf_weeks = df[df['high_conf_accuracy'].notna()]
                if not high_conf_weeks.empty:
                    fig.add_trace(go.Scatter(
                        x=high_conf_weeks['week'],
                        y=high_conf_weeks['high_conf_accuracy'],
                        mode='lines+markers',
                        name='HIGH Confidence',
                        line=dict(color='#2ca02c', width=2),
                        marker=dict(size=8, symbol='star'),
                        hovertemplate='Week %{x}<br>HIGH Conf: %{y:.1f}%<extra></extra>'
                    ))
                
                fig.add_hline(
                    y=overall_accuracy, 
                    line_dash="dot", 
                    line_color="rgba(128,128,128,0.5)",
                    annotation_text=f"Season Avg: {overall_accuracy:.1f}%",
                    annotation_position="right"
                )
                
                fig.update_layout(
                    title=f"{season} Season Accuracy Trends",
                    xaxis_title="Week",
                    yaxis_title="Accuracy (%)",
                    hovermode='x unified',
                    height=500,
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    )
                )
                
                st.plotly_chart(fig, use_container_width=True)
            
            with tab2:
                st.subheader("Performance Breakdown")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    if df['high_conf_total'].sum() > 0:
                        high_conf_acc = (df['high_conf_correct'].sum() / df['high_conf_total'].sum() * 100)
                        
                        conf_data = pd.DataFrame({
                            'Confidence Level': ['HIGH Confidence', 'Overall'],
                            'Accuracy': [high_conf_acc, overall_accuracy],
                            'Games': [df['high_conf_total'].sum(), total_games]
                        })
                        
                        fig_conf = px.bar(
                            conf_data,
                            x='Confidence Level',
                            y='Accuracy',
                            text='Accuracy',
                            title='Accuracy by Confidence Level',
                            color='Confidence Level',
                            color_discrete_map={'HIGH Confidence': '#2ca02c', 'Overall': '#1f77b4'}
                        )
                        
                        fig_conf.update_traces(texttemplate='%{text:.1f}%', textposition='outside')
                        fig_conf.update_layout(showlegend=False, height=400)
                        
                        st.plotly_chart(fig_conf, use_container_width=True)
                
                with col2:
                    if 'avg_margin_error' in df.columns and df['avg_margin_error'].notna().any():
                        fig_margin = px.line(
                            df,
                            x='week',
                            y='avg_margin_error',
                            markers=True,
                            title='Average Point Margin Error',
                            labels={'week': 'Week', 'avg_margin_error': 'Avg Margin Error (pts)'}
                        )
                        
                        fig_margin.update_traces(line_color='#d62728', marker_size=10)
                        fig_margin.update_layout(height=400)
                        
                        st.plotly_chart(fig_margin, use_container_width=True)
                
                st.subheader("Weekly Win Distribution")
                
                weekly_wins = df['correct_predictions'].values
                
                win_counts = pd.Series(weekly_wins).value_counts().sort_index()
                
                fig_dist = px.bar(
                    x=win_counts.index,
                    y=win_counts.values,
                    labels={'x': 'Correct Predictions', 'y': 'Number of Weeks'},
                    title=f'Distribution of Weekly Performance',
                    text=win_counts.values
                )
                
                fig_dist.update_traces(textposition='outside', marker_color='#17becf')
                fig_dist.update_layout(height=400)
                
                st.plotly_chart(fig_dist, use_container_width=True)
            
            with tab3:
                st.subheader("Detailed Weekly Results")
                
                display_df = df.copy()
                display_df['record'] = display_df.apply(
                    lambda row: f"{row['correct_predictions']}-{row['total_predictions'] - row['correct_predictions']}", 
                    axis=1
                )
                
                display_cols = ['week', 'record', 'accuracy_pct']
                col_names = ['Week', 'Record (W-L)', 'Winner %']
                
                if 'spread_3pt_accuracy' in display_df.columns:
                    display_cols.append('spread_3pt_accuracy')
                    col_names.append('±3pts %')
                
                if 'spread_7pt_accuracy' in display_df.columns:
                    display_cols.append('spread_7pt_accuracy')
                    col_names.append('±7pts %')
                
                if 'avg_margin_error' in display_df.columns:
                    display_cols.append('avg_margin_error')
                    col_names.append('Avg Margin Error')
                
                if 'high_conf_accuracy' in display_df.columns:
                    high_conf_col = display_df.apply(
                        lambda row: f"{row['high_conf_accuracy']:.1f}% ({row['high_conf_correct']}/{row['high_conf_total']})" 
                        if row['high_conf_total'] and row['high_conf_total'] > 0 
                        else "N/A",
                        axis=1
                    )
                    display_df['high_conf_display'] = high_conf_col
                    display_cols.append('high_conf_display')
                    col_names.append('HIGH Conf')
                
                display_cols.append('calculated_date')
                col_names.append('Date')
                
                display_df = display_df[display_cols]
                
                for col in ['accuracy_pct', 'spread_3pt_accuracy', 'spread_7pt_accuracy']:
                    if col in display_df.columns:
                        display_df[col] = display_df[col].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A")
                
                if 'avg_margin_error' in display_df.columns:
                    display_df['avg_margin_error'] = display_df['avg_margin_error'].apply(
                        lambda x: f"{x:.1f} pts" if pd.notna(x) else "N/A"
                    )
                
                display_df.columns = col_names
                
                st.dataframe(display_df, use_container_width=True, hide_index=True)
                
                csv = display_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download Accuracy Data",
                    data=csv,
                    file_name=f"gridiron_prophet_accuracy_{season}.csv",
                    mime="text/csv"
                )
            
            st.subheader("📊 Season Highlights")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                best_week = df.loc[df['accuracy_pct'].idxmax()]
                st.success(f"**Best Week:** Week {best_week['week']}")
                st.write(f"✓ {best_week['correct_predictions']}/{best_week['total_predictions']} ({best_week['accuracy_pct']:.1f}%)")
            
            with col2:
                worst_week = df.loc[df['accuracy_pct'].idxmin()]
                st.error(f"**Toughest Week:** Week {worst_week['week']}")
                st.write(f"✓ {worst_week['correct_predictions']}/{worst_week['total_predictions']} ({worst_week['accuracy_pct']:.1f}%)")
            
            with col3:
                latest_week = df.iloc[-1]
                st.info(f"**Latest Week:** Week {latest_week['week']}")
                st.write(f"✓ {latest_week['correct_predictions']}/{latest_week['total_predictions']} ({latest_week['accuracy_pct']:.1f}%)")
            
        else:
            st.info(f"No accuracy data available for {season} season yet.")
            
elif st.session_state.get('faq_option') == "How It Works":
    st.header("📖 Understanding Gridiron Prophet")
    
    tab1, tab2, tab3 = st.tabs(["📊 Prediction Model", "💰 Betting Strategy", "🎯 Accuracy & Methodology"])
    
    with tab1:
        st.markdown("""
        ## How Our Prediction Model Works
        
        Gridiron Prophet uses a **multi-layered approach** combining machine learning with traditional sports analytics:
        
        ### 🤖 Machine Learning Component
        - **Training Data**: 800+ NFL games from 2022-2024 seasons
        - **Algorithm**: Random Forest trained on historical game outcomes, team statistics, performance metrics, snap count %'s and MUCH MORE
        - **Current Accuracy**: 68.87% win prediction rate (from the 2022-2024 season schedules)
        - **Updates**: Model retrains every Tuesday with new game results
        
        > **Note:** 68.87% is a strong accuracy rate for NFL predictions. Vegas lines are highly efficient, so any edge over 53% (breakeven after juice) represents potential value.
        
        ### 📈 Statistical Factors We Analyze
        
        Our model considers multiple factors to generate predictions:
        
        1. **Team Performance Metrics**
           - Win/loss records (home and away)
           - Point differential trends
           - Offensive and defensive rankings
           - Recent form (last 3-5 games)
        
        2. **Injury Impact Analysis**
           - Player importance by position
           - Severity of injuries (Out, Doubtful, Questionable)
           - Cumulative team injury impact score weighted by snap counts
        
        3. **Historical Matchups**
           - Head-to-head records
           - Division rivalry adjustments
           - Season-over-season trends
        
        4. **Home Field Advantage**
           - Standard 2.5 point adjustment
        
        ### 🔢 The Final Prediction
        
        All these factors are weighted and combined to produce:
        - **Model Spread**: Our predicted betting line
        - **Win Probability**: Likelihood of home team victory
        - **Confidence Level**: How certain we are (High/Medium/Low)
        - **Edge**: How much we disagree with Vegas
        """)
    
    with tab2:
        st.markdown("""
        ## 💰 Betting Strategy Guide
        
        ### Understanding Betting Lines
        
        **All spreads are shown in standard betting line format:**
        
        - **Negative number (-)** = Favorite (must win by MORE than this number)
          - Example: `BAL -7.5` means Baltimore must win by 8+ points to cover
          
        - **Positive number (+)** = Underdog (can lose by LESS than this number)
          - Example: `BAL +7.5` means Baltimore can lose by 7 or fewer (or win outright)
        
        ---
        
        ### What is "Edge"?
        
        **Edge = Our Model's Line - Vegas Line**
        
        This tells us when our model disagrees with Vegas:
        
        - **Negative Edge** = Our model thinks the home team is BETTER than Vegas thinks
        - **Positive Edge** = Our model thinks the away team is BETTER than Vegas thinks
        
        ### Real Example:
        
        ```
        LA @ BAL
        Model Line:  BAL -0.7  (we think BAL is slight favorite)
        Vegas Line:  BAL +7.5  (Vegas has BAL as 7.5 pt underdog)
        Edge:        -8.2 points
        
        RECOMMENDATION: Bet BAL +7.5
        
        Why? Our model thinks BAL should be favored, but Vegas 
        has them as a big underdog. We're getting 7.5 extra points 
        on a team we think is actually better!
        ```
        
        ---
        
        ### Edge Interpretation
        
        | Edge Value | Meaning | Action |
        |------------|---------|--------|
        | **≥ 10 points** | 🔥 Strong disagreement with Vegas | Best betting opportunities |
        | **7-9 points** | 🔥 Significant edge | Very good betting value |
        | **5-6 points** | ⚡ Moderate edge | Good betting value |
        | **3-4 points** | ⚠️ Slight edge | Minimum threshold for betting |
        | **< 3 points** | ❌ No significant edge | Skip this bet |
        
        ---
        
        ### Reading the Recommendations
        
        **Example Bet: "IND -7.5"**
        - Bet on Indianapolis (IND) as the favorite
        - They need to win by MORE than 7.5 points for you to win
        - If they win by exactly 7, you lose
        
        **Example Bet: "DEN +3.5"**
        - Bet on Denver (DEN) as the underdog
        - They can lose by up to 3 points and you still win
        - Or if they win outright, you win
        
        ---
        
        ### Confidence Levels
        
        **HIGH Confidence** 🟢
        - Multiple factors align (ML model, injuries, records all agree)
        - Edge typically ≥7 points
        - Historical accuracy > 70%
        - **Recommended for betting**
        
        **MEDIUM Confidence** 🟡
        - Some factors align, others conflict
        - Edge typically 5-6 points
        - Historical accuracy ~65%
        - **Bet with caution**
        
        **LOW Confidence** 🔴
        - Mixed signals across factors
        - Edge typically 3-4 points
        - Historical accuracy < 60%
        - **Minimum threshold - consider skipping**
        
        ---
        
        ### Recommended Betting Approach
        
        1. **Focus on HIGH confidence bets** with edge ≥ 7 points
        2. **Bet sizing**: Larger bets on higher edge/confidence combinations
        3. **Track your results**: Monitor your actual ROI
        4. **Weekly discipline**: Not every week will have good opportunities
        5. **Never chase losses**: Skip weeks with no strong edges
        
        ### Bankroll Management
        
        A suggested **unit system**:
        - **1 unit** = 1-2% of your total bankroll
        - **HIGH confidence** = 2-3 units
        - **MEDIUM confidence** = 1-2 units
        - **LOW confidence** = 0.5-1 unit (or skip entirely)
        
        ### Example Bankroll Strategy
        
        If your bankroll is **$1,000**:
        - 1 unit = $10-20
        - HIGH confidence bet = $20-60
        - MEDIUM confidence bet = $10-40
        - LOW confidence bet = $5-20 (or pass)
        
        **Never bet more than 5% of your bankroll on a single game, regardless of confidence.**
        """)
    
    with tab3:
        st.markdown("""
        ## 🎯 Accuracy & Methodology
        
        ### Current Performance Metrics
        
        - **Overall Win Prediction**: 68.87%
        - **Against the Spread (ATS)**: Tracking in progress
        - **ROI**: Calculated weekly based on recommendations
        
        ### What Does 68.87% Mean?
        
        To break even in sports betting at standard -110 odds, you need to win about **52.4%** of your bets.
        
        Our model's **68.87% accuracy** means:
        - Well above breakeven threshold
        - Represents significant edge over the market
        - However, variance exists week-to-week (typically 60-75% range)
        
        ### Training & Updates
        
        **Weekly Cycle:**
        1. **Monday**: Collect previous week's game results
        2. **Tuesday**: Retrain ML model with new data
        3. **Wednesday**: Update injury reports
        4. **Thursday**: Generate predictions for upcoming week
        5. **Weekend**: Track live betting opportunities
        
        ### Data Sources
        
        - **Game Statistics**: Official NFL data
        - **Injury Reports**: Updated daily from team reports
        - **Betting Lines**: DraftKings Sportsbook API
        - **Historical Data**: 2022-2024 seasons (800+ games)
        - **Player Data**: Snap counts, depth charts, performance metrics
        
        ### Limitations & Disclaimers
        
        ⚠️ **Important Notes:**
        
        - Past performance does not guarantee future results
        - No model is 100% accurate - variance is expected
        - Weather, late scratches, and other factors may affect outcomes
        - **Always bet responsibly and within your means**
        - Model accuracy varies week-to-week (typically 60-75% range)
        - Vegas lines are highly efficient - edges can be temporary
        
        ### Continuous Improvement
        
        We're constantly working to improve accuracy by:
        - Adding weather data integration
        - Incorporating advanced metrics (EPA, DVOA)
        - Tracking referee tendencies
        - Analyzing line movement patterns
        - Backtesting strategies across multiple seasons
        - Refining injury impact calculations
        
        ### Questions?
        
        If you have any detailed questions that this does not answer,
        or if you even have any recommendations for the program to analyze, let me know!
        
        ---
        
        **Responsible Gambling:**
        - Only bet what you can afford to lose
        - Set a budget and stick to it
        - Take breaks if you're on a losing streak
        - Never chase losses
        - This is entertainment, not income
        """)

elif st.session_state.get('analysis_type') == "Team Rosters":
    st.header("👥 Active Team Rosters")
    
    analyzer = InjuryImpactAnalyzer()
    teams = analyzer.db.get_all_teams()
    team_abbrs = sorted([t['abbreviation'] for t in teams])
    
    col1, col2 = st.columns([1, 3])
    
    with col1:
        selected_team = st.selectbox("Select Team", team_abbrs)
        
        team_info = next((t for t in teams if t['abbreviation'] == selected_team), None)
        if team_info:
            st.info(f"**{team_info['name']}**")
    
    with col2:
        if st.button("🔄 Load Roster", type="primary"):
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
                            WHEN 'C' THEN 5
                            WHEN 'G' THEN 5
                            WHEN 'T' THEN 5
                            WHEN 'DL' THEN 6
                            WHEN 'DE' THEN 6
                            WHEN 'DT' THEN 6
                            WHEN 'LB' THEN 7
                            WHEN 'DB' THEN 8
                            WHEN 'CB' THEN 8
                            WHEN 'S' THEN 8
                            WHEN 'K' THEN 9
                            WHEN 'P' THEN 10
                            WHEN 'LS' THEN 10
                            ELSE 11
                        END,
                        p.name
                """
                
                try:
                    roster = analyzer.db.execute_query(query, (selected_team, season))
                    
                    if roster:
                        st.success(f"✅ Found {len(roster)} players on {selected_team} roster")
                        
                        offense_positions = ['QB', 'RB', 'WR', 'TE', 'OL', 'C', 'G', 'T']
                        defense_positions = ['DL', 'DE', 'DT', 'LB', 'DB', 'CB', 'S']
                        special_positions = ['K', 'P', 'LS']
                        
                        tab1, tab2, tab3, tab4 = st.tabs(["🏈 Offense", "🛡️ Defense", "🎯 Special Teams", "📋 Full Roster"])
                        
                        with tab1:
                            offense_players = [p for p in roster if p['position'] in offense_positions]
                            if offense_players:
                                df_offense = pd.DataFrame(offense_players)
                                st.dataframe(df_offense, use_container_width=True, hide_index=True)
                            else:
                                st.info("No offensive players found")
                        
                        with tab2:
                            defense_players = [p for p in roster if p['position'] in defense_positions]
                            if defense_players:
                                df_defense = pd.DataFrame(defense_players)
                                st.dataframe(df_defense, use_container_width=True, hide_index=True)
                            else:
                                st.info("No defensive players found")
                        
                        with tab3:
                            special_players = [p for p in roster if p['position'] in special_positions]
                            if special_players:
                                df_special = pd.DataFrame(special_players)
                                st.dataframe(df_special, use_container_width=True, hide_index=True)
                            else:
                                st.info("No special teams players found")
                        
                        with tab4:
                            df_full = pd.DataFrame(roster)
                            
                            search = st.text_input("🔍 Search players", "")
                            if search:
                                df_filtered = df_full[df_full['player_name'].str.contains(search, case=False, na=False)]
                                st.dataframe(df_filtered, use_container_width=True, hide_index=True)
                            else:
                                st.dataframe(df_full, use_container_width=True, hide_index=True)
                            
                            csv = df_full.to_csv(index=False)
                            st.download_button(
                                label="📥 Download Roster CSV",
                                data=csv,
                                file_name=f"{selected_team}_roster_{season}.csv",
                                mime="text/csv"
                            )
                    else:
                        st.warning(f"⚠️ No roster data found for {selected_team}")
                        st.info("💡 Make sure player data has been collected for this season")
                
                except Exception as e:
                    st.error(f"❌ Error loading roster: {str(e)}")
                    st.info("Check that the database connection is working and player data exists")

elif st.session_state.get('analysis_type') == "Weekly Predictions":
    st.header(f"📊 Week {week} Predictions")
    
    with st.expander("💡 Quick Reference Guide", expanded=False):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("**🔥 Best Bets**\n- Edge ≥ 10 pts\n- HIGH confidence")
        with col2:
            st.markdown("**⚡ Good Value**\n- Edge 5-9 pts\n- MEDIUM+ confidence")
        with col3:
            st.markdown("**⚠️ Skip**\n- Edge < 3 pts\n- LOW confidence")
    
    if st.button("🔮 Generate Predictions", type="primary"):
        with st.spinner("Training ML model and analyzing games..."):
            predictor = MasterBettingPredictor()
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            status_text.text("Training ML model on 2022-2024 data...")
            progress_bar.progress(20)
            predictor.train_ml_model()
            
            status_text.text("Fetching DraftKings lines...")
            progress_bar.progress(40)
            odds_data = predictor.fetch_draftkings_lines()
            
            status_text.text("Analyzing games...")
            progress_bar.progress(60)
            
            query = """
                SELECT g.game_id, ht.abbreviation as home_team, at.abbreviation as away_team
                FROM games g
                JOIN teams ht ON g.home_team_id = ht.team_id
                JOIN teams at ON g.away_team_id = at.team_id
                WHERE g.season = %s AND g.week = %s
                ORDER BY g.game_date
            """
            
            games = predictor.db.execute_query(query, (season, week))
            
            if not games:
                st.error(f"No games found for Week {week}")
            else:
                recommendations = []
                
                for game in games:
                    home = game['home_team']
                    away = game['away_team']
                    
                    prediction = predictor.calculate_comprehensive_prediction(home, away, season, week)
                    dk_lines = predictor.parse_odds_for_game(odds_data, home, away) if odds_data else None
                    
                    if dk_lines and dk_lines['spread'] is not None:
                        dk_spread = dk_lines['spread']
                        
                        edge = prediction['model_betting_line'] - dk_spread
                        
                        if abs(edge) >= 3.0:
                            if edge < 0:
                                if dk_spread > 0:
                                    recommended_bet = f"{home} +{dk_spread}"
                                elif dk_spread < 0:
                                    recommended_bet = f"{home} {dk_spread}"
                                else:
                                    recommended_bet = f"{home} PK"
                            else:
                                if dk_spread < 0:
                                    recommended_bet = f"{away} +{abs(dk_spread)}"
                                elif dk_spread > 0:
                                    recommended_bet = f"{away} {-dk_spread}"
                                else:
                                    recommended_bet = f"{away} PK"
                            
                            recommendations.append({
                                'game': f"{away} @ {home}",
                                'bet': recommended_bet,
                                'edge': edge,
                                'confidence': prediction['confidence'],
                                'ml_prob': prediction['ml_home_win_probability'],
                                'model_betting_line': prediction['model_betting_line'],
                                'vegas_spread': dk_spread
                            })
                
                progress_bar.progress(100)
                status_text.text("Analysis complete!")
                
                if recommendations:
                    st.success(f"✅ Found {len(recommendations)} betting opportunities!")
                    
                    sorted_recs = sorted(recommendations, key=lambda x: abs(x['edge']), reverse=True)
                    
                    for i, rec in enumerate(sorted_recs, 1):
                        edge_indicator = "🔥" if abs(rec['edge']) >= 10 else "⚡" if abs(rec['edge']) >= 5 else "⚠️"
                        
                        with st.expander(f"{edge_indicator} #{i} - {rec['game']} - Edge: {rec['edge']:+.1f}"):
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                st.metric("Recommended Bet", rec['bet'])
                                st.metric("Confidence", rec['confidence'])
                            
                            with col2:
                                st.metric("Edge", f"{rec['edge']:+.1f} pts")
                                st.metric("ML Win Probability", f"{rec['ml_prob']:.1%}")
                            
                            with col3:
                                st.metric("Model Spread", f"{rec['model_betting_line']:+.1f}")
                                st.metric("Vegas Spread", f"{rec['vegas_spread']:+.1f}")
                    
                    df = pd.DataFrame(sorted_recs)
                    st.dataframe(df, use_container_width=True)
                    
                    predictor.save_weekly_report(season, week, recommendations)
                    st.info("💾 Report saved to reports/ folder")
                else:
                    st.warning("⚠️ No strong betting opportunities found this week")

elif st.session_state.get('analysis_type') == "Injury Report":
    st.header("🏥 Team Injury Analysis")
    
    analyzer = InjuryImpactAnalyzer()
    
    teams = analyzer.db.get_all_teams()
    team_abbrs = [t['abbreviation'] for t in teams]
    
    selected_team = st.selectbox("Select Team", team_abbrs)
    
    if st.button("Get Injury Report"):
        with st.spinner("Analyzing injuries..."):
            impact = analyzer.get_team_injury_impact(selected_team, season, week)
            
            st.metric("Total Injury Impact", f"{impact['total_impact']:.1f}")
            st.metric("Total Injuries", impact['injury_count'])
            st.metric("Critical Injuries", len(impact['critical_injuries']))
            
            if impact['critical_injuries']:
                st.subheader("⚠️ Critical Injuries")
                for inj in impact['critical_injuries']:
                    st.warning(f"{inj['player']} ({inj['position']}) - {inj['status']} - Impact: {inj['impact_score']:.1f}")
            
            if impact['injuries']:
                st.subheader("All Injuries")
                df = pd.DataFrame(impact['injuries'])
    
                df = df.rename(columns={'body_part': 'expected_return'})
                column_order = ['player', 'position', 'status', 'expected_return', 'impact_score']
                df = df[column_order]
    
                st.dataframe(df, use_container_width=True)

elif st.session_state.get('analysis_type') == "Team Comparison":
    st.header("⚔️ Head-to-Head Comparison")
    
    analyzer = InjuryImpactAnalyzer()
    teams = analyzer.db.get_all_teams()
    team_abbrs = [t['abbreviation'] for t in teams]
    
    col1, col2 = st.columns(2)
    
    with col1:
        home_team = st.selectbox("Home Team", team_abbrs, index=team_abbrs.index('KC') if 'KC' in team_abbrs else 0)
    
    with col2:
        away_team = st.selectbox("Away Team", team_abbrs, index=team_abbrs.index('BUF') if 'BUF' in team_abbrs else 1)
    
    if st.button("Compare Teams"):
        with st.spinner("Comparing teams..."):
            predictor = MasterBettingPredictor()
            predictor.train_ml_model()
            
            prediction = predictor.calculate_comprehensive_prediction(home_team, away_team, season, week)
            
            st.subheader(f"{away_team} @ {home_team}")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Model Spread", f"{home_team} {prediction['model_betting_line']:+.1f}")
            
            with col2:
                st.metric("ML Win Probability", f"{home_team} {prediction['ml_home_win_probability']:.1%}")
            
            with col3:
                st.metric("Confidence", prediction['confidence'])
            
            st.subheader("📊 Prediction Breakdown")
            
            components_df = pd.DataFrame([
                {"Factor": k.replace('_', ' ').title(), "Value": f"{v:+.2f}"}
                for k, v in prediction['components'].items()
            ])
            
            st.dataframe(components_df, use_container_width=True)
            
            st.subheader("🏥 Injury Comparison")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric(f"{home_team} Injury Impact", f"{prediction['injury_impact']['home']:.1f}")
                st.caption(f"{prediction['injury_impact']['critical_home']} critical injuries")
            
            with col2:
                st.metric(f"{away_team} Injury Impact", f"{prediction['injury_impact']['away']:.1f}")
                st.caption(f"{prediction['injury_impact']['critical_away']} critical injuries")

st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip:** See the How it works tab for FAQ's! ")
st.sidebar.caption("Model Accuracy: 68.87% (Subject to change during training)")
st.sidebar.caption("Created by yours truly. -Kurt")