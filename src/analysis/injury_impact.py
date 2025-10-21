import sys
import os
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.db_manager import DatabaseManager

class InjuryImpactAnalyzer:
    
    def __init__(self):
        self.db = DatabaseManager()
        self.MIN_SNAP_THRESHOLD = 0.0
        
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
            'Injured Reserve': 1.0,
            'Reserve-Ret': 1.0,
            'Doubtful': 0.8,
            'Questionable': 0.4,
            'PUP': 0.9,
            'NFI': 0.9,
        }
    
    def get_current_nfl_week(self):
        today = datetime.now().date()
        
        season_weeks = {
            1: ("2025-09-05", "2025-09-09"),
            2: ("2025-09-10", "2025-09-16"),
            3: ("2025-09-17", "2025-09-23"),
            4: ("2025-09-24", "2025-09-30"),
            5: ("2025-10-01", "2025-10-07"),
            6: ("2025-10-08", "2025-10-14"),
            7: ("2025-10-15", "2025-10-21"),
            8: ("2025-10-22", "2025-10-28"),
            9: ("2025-10-29", "2025-11-04"),
            10: ("2025-11-05", "2025-11-11"),
            11: ("2025-11-12", "2025-11-18"),
            12: ("2025-11-19", "2025-11-25"),
            13: ("2025-11-26", "2025-12-02"),
            14: ("2025-12-03", "2025-12-09"),
            15: ("2025-12-10", "2025-12-16"),
            16: ("2025-12-17", "2025-12-23"),
            17: ("2025-12-24", "2025-12-30"),
            18: ("2025-12-31", "2026-01-05"),
        }
        
        for week, (start_str, end_str) in season_weeks.items():
            start = datetime.strptime(start_str, "%Y-%m-%d").date()
            end = datetime.strptime(end_str, "%Y-%m-%d").date()
            
            if start <= today <= end:
                return week
        
        last_week_end = datetime.strptime(season_weeks[18][1], "%Y-%m-%d").date()
        if today > last_week_end:
            return 18
        
        return 1
    
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
            week = self.get_current_nfl_week()
            
        query = """
            SELECT i.*, p.name as player_name, ps.position, p.player_id
            FROM injuries i
            JOIN players p ON i.player_id = p.player_id
            JOIN player_seasons ps ON p.player_id = ps.player_id AND i.season = ps.season
            JOIN teams t ON ps.team_id = t.team_id
            INNER JOIN (
                SELECT player_id, MAX(week) as max_week
                FROM injuries
                WHERE season = %s AND week <= %s
                GROUP BY player_id
            ) latest ON i.player_id = latest.player_id AND i.week = latest.max_week
            WHERE t.abbreviation = %s
            AND i.season = %s
            AND i.injury_status IN ('Out', 'Doubtful', 'Questionable', 'Injured Reserve', 'Reserve-Ret', 'IR', 'PUP', 'NFI')
        """
        injuries = self.db.execute_query(query, (season, week, team_abbr, season))
        
        if not injuries:
            return {
                'team': team_abbr,
                'total_impact': 0,
                'injury_count': 0,
                'skipped_inactive': 0,
                'critical_injuries': [],
                'injuries': []
            }
        
        processed_injuries = []
        total_impact = 0
        skipped_count = 0
        critical_injuries = []
        
        for injury in injuries:
            player_id = injury['player_id']
            position = injury['position']
            status = injury['injury_status']
            player_name = injury['player_name']
            
            snap_query = """
                SELECT AVG(snap_percentage) as avg_snaps
                FROM depth_charts
                WHERE player_id = %s
                AND snap_percentage > 0
            """
            snap_result = self.db.execute_query(snap_query, (player_id,))
            
            if snap_result and snap_result[0]['avg_snaps']:
                avg_snaps = float(snap_result[0]['avg_snaps']) / 100.0
            else:
                avg_snaps = 0.0
            
            if avg_snaps < self.MIN_SNAP_THRESHOLD:
                skipped_count += 1
                continue
            
            impact_score = self.calculate_injury_impact(player_id, position, status)
            
            injury_data = {
                'player': player_name,
                'position': position,
                'status': status,
                'impact_score': impact_score,
                'snap_pct': avg_snaps,
                'week': injury.get('week', week)
            }
            
            processed_injuries.append(injury_data)
            total_impact += impact_score
            
            if impact_score >= 5.0:
                critical_injuries.append(injury_data)
        
        processed_injuries.sort(key=lambda x: x['impact_score'], reverse=True)
        
        return {
            'team': team_abbr,
            'total_impact': round(total_impact, 1),
            'injury_count': len(processed_injuries),
            'skipped_inactive': skipped_count,
            'critical_injuries': critical_injuries,
            'injuries': processed_injuries
        }
    
    def compare_matchup_injuries(self, home_team, away_team, season=2025, week=None):
        if week is None:
            week = self.get_current_nfl_week()
            
        print("="*70)
        print(f"HEAD-TO-HEAD INJURY COMPARISON - Week {week}, {season}")
        print(f"{away_team} @ {home_team}")
        print("="*70)
        
        home_impact = self.get_team_injury_impact(home_team, season, week)
        away_impact = self.get_team_injury_impact(away_team, season, week)
        
        print(f"\n{home_team} (Home):")
        print(f"  Total Impact: {home_impact['total_impact']:.1f}")
        print(f"  Injuries: {home_impact['injury_count']}")
        print(f"  Critical: {len(home_impact['critical_injuries'])}")
        if home_impact['injuries']:
            print(f"  Top Injuries:")
            for inj in home_impact['injuries'][:3]:
                print(f"    • {inj['position']:5} {inj['player']:25} {inj['status']:15} (Impact: {inj['impact_score']:.1f})")
        
        print(f"\n{away_team} (Away):")
        print(f"  Total Impact: {away_impact['total_impact']:.1f}")
        print(f"  Injuries: {away_impact['injury_count']}")
        print(f"  Critical: {len(away_impact['critical_injuries'])}")
        if away_impact['injuries']:
            print(f"  Top Injuries:")
            for inj in away_impact['injuries'][:3]:
                print(f"    • {inj['position']:5} {inj['player']:25} {inj['status']:15} (Impact: {inj['impact_score']:.1f})")
        
        advantage = home_impact['total_impact'] - away_impact['total_impact']
        print(f"\n{'='*70}")
        if abs(advantage) < 5:
            print(f"INJURY ADVANTAGE: Even (difference: {abs(advantage):.1f})")
        elif advantage > 0:
            print(f"INJURY ADVANTAGE: {away_team} by {abs(advantage):.1f} points")
        else:
            print(f"INJURY ADVANTAGE: {home_team} by {abs(advantage):.1f} points")
        print("="*70)
    
    def generate_weekly_injury_report(self, season=2025, week=None):
        if week is None:
            week = self.get_current_nfl_week()
            
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