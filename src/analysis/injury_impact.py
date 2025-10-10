import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_manager import DatabaseManager

class InjuryImpactAnalyzer:
    """Calculate injury impact scores for teams and games"""
    
    def __init__(self):
        self.db = DatabaseManager()
        
        # Position importance weights (0-1 scale)
        self.position_weights = {
            'QB': 1.0,      # Quarterback - most critical
            'WR': 0.6,      # Wide Receiver
            'RB': 0.6,      # Running Back
            'TE': 0.5,      # Tight End
            'OT': 0.7,      # Offensive Tackle - protects QB
            'OG': 0.5,      # Offensive Guard
            'G': 0.5,       # Guard (alternate notation)
            'C': 0.6,       # Center
            'DE': 0.75,     # Defensive End - elite pass rush critical
            'DT': 0.65,     # Defensive Tackle - disrupts run game
            'LB': 0.65,     # Linebacker - defensive QB
            'CB': 0.75,     # Cornerback - elite CBs shut down top WRs
            'S': 0.6,       # Safety - key for coverage
            'DB': 0.65,     # Defensive Back (general)
            'DL': 0.7,      # Defensive Line (general)
            'K': 0.2,       # Kicker
            'P': 0.1,       # Punter
            'LS': 0.1,      # Long Snapper
            'FB': 0.3,      # Fullback
        }
        
        # Injury status severity multipliers
        self.status_multipliers = {
            'Out': 1.0,              # Definitely not playing
            'Injured Reserve': 1.0,  # Out for extended period
            'Doubtful': 0.8,         # Very unlikely to play
            'Questionable': 0.4,     # 50/50 chance
        }
    
    def get_player_importance(self, player_id):
        """
        Calculate player importance based on snap counts
        Returns value 0-1 (1 = starter with high snap count)
        """
        query = """
            SELECT AVG(snap_percentage) as avg_snaps, MIN(depth_order) as depth
            FROM depth_charts
            WHERE player_id = %s
            AND snap_percentage > 0
        """
        result = self.db.execute_query(query, (player_id,))
        
        if not result or not result[0]['avg_snaps']:
            # No snap data = never played, minimal importance
            return 0.1
        
        avg_snaps = float(result[0]['avg_snaps'])
        depth = result[0]['depth']
        
        # Snap count factor
        snap_factor = min(avg_snaps, 1.0)
        
        # Bonus for being listed higher on depth chart
        depth_bonus = 0.0
        if depth and depth <= 5:
            depth_bonus = (6 - depth) * 0.1  # First 5 positions get bonus
        
        importance = min(snap_factor + depth_bonus, 1.0)
        return importance
    
    def calculate_injury_impact(self, player_id, position, injury_status):
        """
        Calculate impact score for a single injured player
        Returns float representing impact (0-10 scale)
        """
        # Get position weight (default to 0.5 if position not in map)
        position_weight = self.position_weights.get(position, 0.5)
        
        # Get injury severity
        severity = self.status_multipliers.get(injury_status, 0.5)
        
        # Get player importance (starter vs backup)
        player_importance = self.get_player_importance(player_id)
        
        # Calculate total impact (scale to 10)
        impact = position_weight * severity * player_importance * 10
        
        return round(impact, 2)
    
    def get_team_injury_impact(self, team_abbr, season=2025, week=None):
        """
        Calculate total injury impact for a team
        Returns dict with total score and breakdown
        """
        query = """
            SELECT i.*, p.name as player_name, p.position, p.player_id
            FROM injuries i
            JOIN players p ON i.player_id = p.player_id
            JOIN teams t ON p.team_id = t.team_id
            WHERE t.abbreviation = %s
            AND i.injury_status IN ('Out', 'Doubtful', 'Questionable', 'Injured Reserve')
        """
        
        injuries = self.db.execute_query(query, (team_abbr,))
        
        if not injuries:
            return {
                'team': team_abbr,
                'total_impact': 0,
                'injury_count': 0,
                'critical_injuries': [],
                'injuries': []
            }
        
        total_impact = 0
        critical_injuries = []
        injury_details = []
        
        for injury in injuries:
            impact = self.calculate_injury_impact(
                injury['player_id'],
                injury['position'],
                injury['injury_status']
            )
            
            total_impact += impact
            
            injury_info = {
                'player': injury['player_name'],
                'position': injury['position'],
                'status': injury['injury_status'],
                'body_part': injury['body_part'],
                'impact_score': impact
            }
            
            injury_details.append(injury_info)
            
            # Flag critical injuries (QB or high impact score)
            if injury['position'] == 'QB' or impact >= 4.0:  # Lower threshold
                critical_injuries.append(injury_info)
        
        # Sort injuries by impact
        injury_details.sort(key=lambda x: x['impact_score'], reverse=True)
        
        return {
            'team': team_abbr,
            'total_impact': round(total_impact, 2),
            'injury_count': len(injuries),
            'critical_injuries': critical_injuries,
            'injuries': injury_details
        }
    
    def compare_matchup_injuries(self, home_team, away_team):
        """
        Compare injury impact between two teams for a matchup
        Returns advantage analysis
        """
        home_impact = self.get_team_injury_impact(home_team)
        away_impact = self.get_team_injury_impact(away_team)
        
        impact_diff = away_impact['total_impact'] - home_impact['total_impact']
        
        print("="*70)
        print(f"INJURY IMPACT ANALYSIS: {away_team} @ {home_team}")
        print("="*70)
        
        # Home team injuries
        print(f"\n{home_team} Injuries (Total Impact: {home_impact['total_impact']})")
        print("-"*70)
        for inj in home_impact['injuries'][:10]:  # Top 10
            critical = "⚠️ CRITICAL" if inj in home_impact['critical_injuries'] else ""
            print(f"  {inj['position']:5} {inj['player']:25} {inj['status']:20} "
                  f"Impact: {inj['impact_score']:.1f} {critical}")
        
        # Away team injuries
        print(f"\n{away_team} Injuries (Total Impact: {away_impact['total_impact']})")
        print("-"*70)
        for inj in away_impact['injuries'][:10]:  # Top 10
            critical = "⚠️ CRITICAL" if inj in away_impact['critical_injuries'] else ""
            print(f"  {inj['position']:5} {inj['player']:25} {inj['status']:20} "
                  f"Impact: {inj['impact_score']:.1f} {critical}")
        
        # Advantage analysis
        print("\n" + "="*70)
        print("INJURY ADVANTAGE ANALYSIS")
        print("="*70)
        
        if abs(impact_diff) < 3:
            advantage = "NEUTRAL - Both teams similarly affected by injuries"
        elif impact_diff > 0:
            advantage = f"{home_team} has ADVANTAGE - {away_team} more impacted by injuries ({abs(impact_diff):.1f} points)"
        else:
            advantage = f"{away_team} has ADVANTAGE - {home_team} more impacted by injuries ({abs(impact_diff):.1f} points)"
        
        print(f"\n{advantage}")
        
        # Suggested spread adjustment
        # Rule of thumb: 1 point of impact difference ≈ 0.25 points on spread
        spread_adjustment = impact_diff * 0.25
        print(f"\nSuggested spread adjustment: {spread_adjustment:+.1f} points toward {home_team if spread_adjustment > 0 else away_team}")
        
        print("\n" + "="*70)
        
        return {
            'home_impact': home_impact,
            'away_impact': away_impact,
            'advantage': advantage,
            'spread_adjustment': spread_adjustment
        }
    
    def generate_weekly_injury_report(self, season=2025, week=6):
        """Generate injury report for all teams"""
        print("="*70)
        print(f"NFL INJURY IMPACT REPORT - Week {week}, {season}")
        print("="*70)
        
        # Get all teams
        teams = self.db.get_all_teams()
        
        team_impacts = []
        for team in teams:
            impact = self.get_team_injury_impact(team['abbreviation'])
            team_impacts.append(impact)
        
        # Sort by total impact (most impacted first)
        team_impacts.sort(key=lambda x: x['total_impact'], reverse=True)
        
        print("\nTEAMS BY INJURY SEVERITY:")
        print("-"*70)
        for idx, team in enumerate(team_impacts, 1):
            critical_count = len(team['critical_injuries'])
            critical_str = f"({critical_count} CRITICAL)" if critical_count > 0 else ""
            print(f"{idx:2}. {team['team']:5} - Impact: {team['total_impact']:6.1f} - "
                  f"{team['injury_count']} injuries {critical_str}")
        
        # Highlight most impacted teams
        print("\n" + "="*70)
        print("TOP 5 MOST IMPACTED TEAMS:")
        print("="*70)
        for team in team_impacts[:5]:
            print(f"\n{team['team']} - Total Impact: {team['total_impact']}")
            for inj in team['injuries'][:5]:
                print(f"  • {inj['position']:5} {inj['player']:25} {inj['status']:15} "
                      f"(Impact: {inj['impact_score']:.1f})")

if __name__ == "__main__":
    analyzer = InjuryImpactAnalyzer()
    
    # Generate weekly report
    analyzer.generate_weekly_injury_report()
    
    # Example matchup analysis
    print("\n\n")
    analyzer.compare_matchup_injuries('DEN', 'NYJ')