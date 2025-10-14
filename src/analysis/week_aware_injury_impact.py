import sys
from pathlib import Path
from typing import Dict, List
from datetime import datetime

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.database.db_manager import DatabaseManager

POSITION_WEIGHTS = {
    'QB': 1.0,
    'RB': 0.7,
    'WR': 0.6,
    'TE': 0.5,
    'OL': 0.6,
    'DL': 0.6,
    'LB': 0.5,
    'DB': 0.4,
    'K': 0.2,
    'P': 0.1,
    'LS': 0.1
}

INJURY_STATUS_MULTIPLIERS = {
    'Out': 1.0,
    'IR': 1.0,
    'PUP': 0.9,
    'Questionable': 0.4
}


class InjuryImpactCalculator:
    def __init__(self, db: DatabaseManager):
        self.db = db
        
    def get_current_week_injuries(self, team: str, week: int, season: int = 2025) -> List[Dict]:
        injuries = self.db.execute_query("""
            SELECT 
                p.name as player_name,
                ps.position,
                i.injury_status,
                COALESCE(i.body_part, 'Unspecified') as injury_description
            FROM injuries i
            JOIN players p ON i.player_id = p.player_id
            JOIN player_seasons ps ON i.player_id = ps.player_id AND i.season = ps.season
            JOIN teams t ON ps.team_id = t.team_id
            WHERE t.abbreviation = %s
            AND i.season = %s
            AND i.week = %s
        """, (team, season, week))
        
        return [
            {
                'player': row['player_name'] if isinstance(row, dict) else row[0],
                'position': row['position'] if isinstance(row, dict) else row[1],
                'status': row['injury_status'] if isinstance(row, dict) else row[2],
                'description': row['injury_description'] if isinstance(row, dict) else (row[3] or 'N/A'),
                'snap_pct': 65.0
            }
            for row in injuries
        ]
    
    def calculate_impact_score(self, team: str, week: int, season: int = 2025) -> Dict[str, float]:
        injuries = self.get_current_week_injuries(team, week, season)
        
        if not injuries:
            return {
                'total_impact': 0.0,
                'qb_impact': 0.0,
                'skill_impact': 0.0,
                'defense_impact': 0.0,
                'oline_impact': 0.0,
                'injury_count': 0,
                'critical_injuries': []
            }
        
        total_impact = 0.0
        qb_impact = 0.0
        skill_impact = 0.0
        defense_impact = 0.0
        oline_impact = 0.0
        critical_injuries = []
        
        for injury in injuries:
            position = injury['position']
            status = injury['status']
            snap_pct = injury['snap_pct']
            
            pos_weight = POSITION_WEIGHTS.get(position, 0.3)
            status_mult = INJURY_STATUS_MULTIPLIERS.get(status, 0.5)
            snap_factor = snap_pct / 100.0
            
            impact = pos_weight * status_mult * snap_factor
            total_impact += impact
            
            if position == 'QB':
                qb_impact += impact
                if status in ['Out', 'IR', 'PUP']:
                    critical_injuries.append(f"{injury['player']} (QB - {status})")
            
            elif position in ['RB', 'WR', 'TE']:
                skill_impact += impact
                if status in ['Out', 'IR'] and snap_pct > 50:
                    critical_injuries.append(f"{injury['player']} ({position} - {status})")
            
            elif position in ['DL', 'LB', 'DB']:
                defense_impact += impact
                if status in ['Out', 'IR'] and snap_pct > 60:
                    critical_injuries.append(f"{injury['player']} ({position} - {status})")
            
            elif position == 'OL':
                oline_impact += impact
                if status in ['Out', 'IR']:
                    critical_injuries.append(f"{injury['player']} ({position} - {status})")
        
        return {
            'total_impact': round(total_impact, 3),
            'qb_impact': round(qb_impact, 3),
            'skill_impact': round(skill_impact, 3),
            'defense_impact': round(defense_impact, 3),
            'oline_impact': round(oline_impact, 3),
            'injury_count': len(injuries),
            'critical_injuries': critical_injuries
        }
    
    def compare_team_injuries(self, home_team: str, away_team: str, week: int, season: int = 2025) -> Dict:
        home_impact = self.calculate_impact_score(home_team, week, season)
        away_impact = self.calculate_impact_score(away_team, week, season)
        
        injury_advantage = away_impact['total_impact'] - home_impact['total_impact']
        
        severity_rating = "Low"
        if abs(injury_advantage) > 1.5:
            severity_rating = "High"
        elif abs(injury_advantage) > 0.75:
            severity_rating = "Medium"
        
        favored_team = home_team if injury_advantage > 0 else away_team
        
        return {
            'home_impact': home_impact,
            'away_impact': away_impact,
            'injury_advantage': round(injury_advantage, 3),
            'favored_team': favored_team,
            'severity': severity_rating,
            'spread_adjustment': round(injury_advantage * 2.5, 1)
        }
    
    def get_injury_report(self, team: str, week: int, season: int = 2025) -> str:
        injuries = self.get_current_week_injuries(team, week, season)
        
        if not injuries:
            return f"✅ {team}: No reported injuries"
        
        report_lines = [f"\n🏥 {team} Injury Report (Week {week}):"]
        report_lines.append("-" * 50)
        
        status_groups = {'Out': [], 'IR': [], 'PUP': [], 'Questionable': []}
        
        for injury in injuries:
            status = injury['status']
            if status in status_groups:
                status_groups[status].append(injury)
        
        for status, group in status_groups.items():
            if group:
                report_lines.append(f"\n{status}:")
                for inj in group:
                    report_lines.append(
                        f"  • {inj['player']} ({inj['position']}) - "
                        f"{inj['description']} [~{inj['snap_pct']:.0f}% snaps]"
                    )
        
        impact = self.calculate_impact_score(team, week, season)
        report_lines.append(f"\n📊 Total Impact Score: {impact['total_impact']:.2f}")
        
        if impact['critical_injuries']:
            report_lines.append("\n⚠️  Critical Injuries:")
            for crit in impact['critical_injuries']:
                report_lines.append(f"  • {crit}")
        
        return "\n".join(report_lines)


def main():
    db = DatabaseManager()
    calc = InjuryImpactCalculator(db)
    
    try:
        print("\n" + "="*60)
        print("🏥 WEEK-AWARE INJURY IMPACT ANALYSIS")
        print("="*60)
        
        current_week = 7
        
        print(f"\n📅 Analyzing Week {current_week} Injuries\n")
        
        teams = db.execute_query("""
            SELECT DISTINCT t.abbreviation
            FROM injuries i
            JOIN player_seasons ps ON i.player_id = ps.player_id AND i.season = ps.season
            JOIN teams t ON ps.team_id = t.team_id
            WHERE i.season = 2025
            AND i.week = %s
            ORDER BY t.abbreviation
        """, (current_week,))
        
        team_impacts = []
        
        for team_row in teams:
            team = team_row['abbreviation'] if isinstance(team_row, dict) else team_row[0]
            impact = calc.calculate_impact_score(team, current_week)
            team_impacts.append((team, impact['total_impact'], impact['injury_count']))
            
            print(calc.get_injury_report(team, current_week))
            print()
        
        print("\n" + "="*60)
        print("📊 TEAMS RANKED BY INJURY IMPACT:")
        print("="*60)
        
        team_impacts.sort(key=lambda x: x[1], reverse=True)
        
        for rank, (team, impact, count) in enumerate(team_impacts, 1):
            bar = "█" * int(impact * 10)
            print(f"{rank:2d}. {team:20s} Impact: {impact:5.2f} {bar} ({count} injuries)")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()