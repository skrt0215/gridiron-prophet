import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_manager import DatabaseManager

class InjuryImpactAnalyzer:
    
    def __init__(self):
        self.db = DatabaseManager()
        self.MIN_SNAP_THRESHOLD = 0.15
        
        self.position_weights = {
            'QB': 1.0,
            'WR': 0.6,
            'RB': 0.6,
            'TE': 0.5,
            'OT': 0.7,
            'OG': 0.5,
            'G': 0.5,
            'C': 0.6,
            'DE': 0.75,
            'DT': 0.65,
            'LB': 0.65,
            'CB': 0.75,
            'S': 0.6,
            'DB': 0.65,
            'DL': 0.7,
            'K': 0.2,
            'P': 0.1,
            'LS': 0.1,
            'FB': 0.3,
        }
        
        self.status_multipliers = {
            'Out': 1.0,
            'IR': 1.0,
            'Doubtful': 0.8,
            'Questionable': 0.4,
            'PUP': 0.9,
            'NFI': 0.9,
        }
    
    def get_player_importance(self, player_id):
        query = """
            SELECT AVG(snap_percentage) as avg_snaps, MIN(depth_order) as depth
            FROM depth_charts
            WHERE player_id = %s
            AND snap_percentage > 0
        """
        result = self.db.execute_query(query, (player_id,))
        
        if result and result[0]['avg_snaps']:
            avg_snaps = float(result[0]['avg_snaps'])
            depth = result[0]['depth']
            
            snap_factor = min(avg_snaps / 100.0, 1.0)
            
            depth_bonus = 0.0
            if depth and depth <= 5:
                depth_bonus = (6 - depth) * 0.1
            
            importance = min(snap_factor + depth_bonus, 1.0)
            return importance
        
        depth_query = """
            SELECT depth_order as depth, position
            FROM depth_charts
            WHERE player_id = %s
            ORDER BY depth_order ASC
            LIMIT 1
        """
        depth_result = self.db.execute_query(depth_query, (player_id,))
        
        if depth_result and depth_result[0]['depth']:
            depth = depth_result[0]['depth']
            position = depth_result[0]['position']
            
            if depth == 1:
                if position == 'QB':
                    return 1.0
                return 0.85
            elif depth == 2:
                return 0.7
            elif depth <= 5:
                return 0.5
            else:
                return 0.3
        
        return 0.3
    
    def calculate_injury_impact(self, player_id, position, injury_status):
        position_weight = self.position_weights.get(position, 0.5)
        severity = self.status_multipliers.get(injury_status, 0.5)
        player_importance = self.get_player_importance(player_id)
        impact = position_weight * severity * player_importance * 10
        return round(impact, 2)
    
    def get_team_injury_impact(self, team_abbr, season=2025, week=None):
        if week is None:
            query = """
                SELECT i.*, p.name as player_name, ps.position, p.player_id
                FROM injuries i
                JOIN players p ON i.player_id = p.player_id
                JOIN player_seasons ps ON p.player_id = ps.player_id AND i.season = ps.season
                JOIN teams t ON ps.team_id = t.team_id
                WHERE t.abbreviation = %s
                AND i.season = %s
                AND i.injury_status IN ('Out', 'Doubtful', 'Questionable', 'IR', 'PUP', 'NFI')
            """
            injuries = self.db.execute_query(query, (team_abbr, season))
        else:
            query = """
                SELECT i.*, p.name as player_name, ps.position, p.player_id
                FROM injuries i
                JOIN players p ON i.player_id = p.player_id
                JOIN player_seasons ps ON p.player_id = ps.player_id AND i.season = ps.season
                JOIN teams t ON ps.team_id = t.team_id
                WHERE t.abbreviation = %s
                AND i.season = %s
                AND i.week = %s
                AND i.injury_status IN ('Out', 'Doubtful', 'Questionable', 'IR', 'PUP', 'NFI')
            """
            injuries = self.db.execute_query(query, (team_abbr, season, week))
        
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
        skipped_count = 0
        
        for injury in injuries:
            player_importance = self.get_player_importance(injury['player_id'])

            if player_importance < self.MIN_SNAP_THRESHOLD:
                skipped_count += 1
                continue
            
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
                'body_part': injury.get('body_part', 'Unknown'),
                'impact_score': impact,
                'snap_importance': player_importance
            }
            
            injury_details.append(injury_info)
            
            if injury['position'] == 'QB' or impact >= 4.0:
                critical_injuries.append(injury_info)
        
        injury_details.sort(key=lambda x: x['impact_score'], reverse=True)
        
        return {
            'team': team_abbr,
            'total_impact': round(total_impact, 2),
            'injury_count': len(injury_details),
            'skipped_inactive': skipped_count,
            'critical_injuries': critical_injuries,
            'injuries': injury_details
        }
    
    def compare_matchup_injuries(self, home_team, away_team, season=2025, week=None):
        home_impact = self.get_team_injury_impact(home_team, season, week)
        away_impact = self.get_team_injury_impact(away_team, season, week)
        
        impact_diff = away_impact['total_impact'] - home_impact['total_impact']
        
        print("="*70)
        print(f"INJURY IMPACT ANALYSIS: {away_team} @ {home_team}")
        print("="*70)
        
        print(f"\n{home_team} Injuries (Total Impact: {home_impact['total_impact']})")
        if home_impact['skipped_inactive'] > 0:
            print(f"  (Skipped {home_impact['skipped_inactive']} inactive/emergency players)")
        print("-"*70)
        for inj in home_impact['injuries'][:10]:
            critical = "⚠️ CRITICAL" if inj in home_impact['critical_injuries'] else ""
            print(f"  {inj['position']:5} {inj['player']:25} {inj['status']:20} "
                  f"Impact: {inj['impact_score']:.1f} {critical}")
        
        print(f"\n{away_team} Injuries (Total Impact: {away_impact['total_impact']})")
        if away_impact['skipped_inactive'] > 0:
            print(f"  (Skipped {away_impact['skipped_inactive']} inactive/emergency players)")
        print("-"*70)
        for inj in away_impact['injuries'][:10]:
            critical = "⚠️ CRITICAL" if inj in away_impact['critical_injuries'] else ""
            print(f"  {inj['position']:5} {inj['player']:25} {inj['status']:20} "
                  f"Impact: {inj['impact_score']:.1f} {critical}")
        
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
        print("="*70)
        print(f"NFL INJURY IMPACT REPORT - Week {week}, {season}")
        print("="*70)
        
        teams = self.db.get_all_teams()
        
        team_impacts = []
        total_skipped = 0
        
        for team in teams:
            impact = self.get_team_injury_impact(team['abbreviation'], season, week)
            team_impacts.append(impact)
            total_skipped += impact.get('skipped_inactive', 0)
        
        team_impacts.sort(key=lambda x: x['total_impact'], reverse=True)
        
        print(f"\nFiltered out {total_skipped} inactive/emergency players across all teams")
        print("\nTEAMS BY INJURY SEVERITY:")
        print("-"*70)
        for idx, team in enumerate(team_impacts, 1):
            critical_count = len(team['critical_injuries'])
            critical_str = f"({critical_count} CRITICAL)" if critical_count > 0 else ""
            print(f"{idx:2}. {team['team']:5} - Impact: {team['total_impact']:6.1f} - "
                  f"{team['injury_count']} injuries {critical_str}")
        
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
    analyzer.generate_weekly_injury_report()
    print("\n\n")
    analyzer.compare_matchup_injuries('DEN', 'NYJ')