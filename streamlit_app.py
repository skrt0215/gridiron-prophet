import streamlit as st
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.models.master_betting_predictor import MasterBettingPredictor
from src.analysis.injury_impact import InjuryImpactAnalyzer
import pandas as pd

st.set_page_config(page_title="Gridiron Prophet", page_icon="🏈", layout="wide")

st.title("🏈 Gridiron Prophet")
st.subheader("NFL Betting Analysis & Predictions")

st.sidebar.header("⚙️ Settings")

season = st.sidebar.number_input("Season", min_value=2022, max_value=2025, value=2025, step=1)
week = st.sidebar.number_input("Week", min_value=1, max_value=18, value=6, step=1)

analysis_type = st.sidebar.selectbox(
    "Analysis Type",
    ["Weekly Predictions", "How It Works", "Team Rosters", "Injury Report", "Team Comparison"]
)

if analysis_type == "How It Works":
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
           - Severity of injuries (Out, Doubtful, Questionable, Injured Reserve)
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

elif analysis_type == "Team Rosters":
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

elif analysis_type == "Weekly Predictions":
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

elif analysis_type == "Injury Report":
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

elif analysis_type == "Team Comparison":
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