import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from betting.odds_comparator import OddsComparator
from betting.roi_tracker import ROITracker
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

class WeeklyReportGenerator:
    """Generate automated weekly betting reports"""
    
    def __init__(self):
        self.comparator = OddsComparator()
        self.roi_tracker = ROITracker()
    
    def generate_text_report(self, season=2025, week=6):
        """Generate a text-based weekly report"""
        
        report = []
        report.append("=" * 70)
        report.append("GRIDIRON PROPHET - WEEKLY BETTING REPORT")
        report.append(f"Week {week}, {season} Season")
        report.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        report.append("=" * 70)
        
        odds_data = self.comparator.fetch_current_odds()
        
        if not odds_data:
            report.append("\n⚠️  Could not fetch current odds")
            return "\n".join(report)
        
        games = self.comparator.parse_odds_data(odds_data)
        predictions = self.comparator.generate_model_predictions(games, season, week)
        
        opportunities = [p for p in predictions if abs(p['edge']) >= 3.0]
        
        report.append(f"\n📊 WEEK {week} OVERVIEW")
        report.append(f"   Total Games: {len(predictions)}")
        report.append(f"   Betting Opportunities: {len(opportunities)}")
        
        if opportunities:
            report.append(f"\n🔥 TOP BETTING OPPORTUNITIES\n")
            
            for i, opp in enumerate(sorted(opportunities, key=lambda x: abs(x['edge']), reverse=True)[:5], 1):
                edge = opp['edge']
                confidence = opp['confidence']
                
                report.append(f"{i}. {opp['away_team']} @ {opp['home_team']}")
                report.append(f"   Vegas: {opp['vegas_spread']:+.1f} | Model: {opp['predicted_spread']:+.1f}")
                report.append(f"   Edge: {edge:+.1f} points | Confidence: {confidence}")
                
                if edge > 0:
                    report.append(f"   💰 BET: {opp['home_team']} to cover")
                else:
                    report.append(f"   💰 BET: {opp['away_team']} to cover")
                report.append("")
        else:
            report.append("\n   No strong edges found this week.")
        
        performance = self.roi_tracker.get_performance_report(season)
        
        if not performance.empty:
            report.append(f"\n📈 SEASON PERFORMANCE")
            total_bets = performance['total_bets'].sum()
            total_wins = performance['winning_bets'].sum()
            total_losses = performance['losing_bets'].sum()
            total_profit = performance['total_profit_loss'].sum()
            total_wagered = performance['total_wagered'].sum()
            
            if total_wagered > 0:
                roi = (total_profit / total_wagered * 100)
                win_rate = (total_wins / (total_wins + total_losses) * 100) if (total_wins + total_losses) > 0 else 0
                
                report.append(f"   Record: {total_wins}-{total_losses} ({win_rate:.1f}%)")
                report.append(f"   Total Wagered: ${total_wagered:,.2f}")
                report.append(f"   Profit/Loss: ${total_profit:+,.2f}")
                report.append(f"   ROI: {roi:+.1f}%")
        
        report.append("\n" + "=" * 70)
        report.append("Track results after games at: python3 src/betting/update_results.py")
        report.append("=" * 70)
        
        return "\n".join(report)
    
    def save_report(self, report_text, filename=None):
        """Save report to file"""
        if not filename:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M')
            filename = f"reports/week_report_{timestamp}.txt"
        
        os.makedirs('reports', exist_ok=True)
        
        with open(filename, 'w') as f:
            f.write(report_text)
        
        print(f"\n✓ Report saved to: {filename}")
        return filename
    
    def send_email_report(self, report_text, to_email, from_email, password):
        """Send report via email (optional - requires email setup)"""
        
        msg = MIMEMultipart()
        msg['From'] = from_email
        msg['To'] = to_email
        msg['Subject'] = f"Gridiron Prophet - Week {datetime.now().strftime('%U')} Report"
        
        msg.attach(MIMEText(report_text, 'plain'))
        
        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(from_email, password)
            server.send_message(msg)
            server.quit()
            
            print(f"✓ Report emailed to {to_email}")
            return True
            
        except Exception as e:
            print(f"✗ Email failed: {e}")
            return False

def main():
    generator = WeeklyReportGenerator()
    
    print("Generating weekly report...")
    report = generator.generate_text_report(season=2025, week=6)
    
    print("\n" + report)
    
    generator.save_report(report)
    
    print("\n💡 note: Set up a cron job to run this automatically every Tuesday")

if __name__ == "__main__":
    main()