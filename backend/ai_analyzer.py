from typing import List, Dict
from datetime import datetime
from anthropic import Anthropic
from config import settings

class AIAnalyzer:
    def __init__(self):
        self.client = Anthropic(api_key=settings.ANTHROPIC_API_KEY) if settings.ANTHROPIC_API_KEY else None
    
    def analyze_dates(self, results: List[Dict]) -> Dict:
        """Analyze extracted dates for anomalies and insights"""
        all_dates = []
        for file_result in results:
            if 'results' in file_result:
                all_dates.extend(file_result['results'])
        
        # Basic statistics
        total_dates = len(all_dates)
        expired_count = sum(1 for d in all_dates if d.get('is_expired') == True)
        valid_count = sum(1 for d in all_dates if d.get('is_expired') == False)
        expiring_soon = sum(1 for d in all_dates if d.get('days_until_expiration') is not None and 0 <= d.get('days_until_expiration', 999) < 30)
        
        # Detect anomalies
        anomalies = []
        for date_obj in all_dates:
            if date_obj.get('date_iso'):
                try:
                    date = datetime.fromisoformat(date_obj['date_iso'])
                    years_diff = (datetime.now() - date).days / 365.25
                    
                    if years_diff > 100:
                        anomalies.append({
                            "message": "Unusually old date detected (possible OCR error)",
                            "date": date_obj['date_raw'],
                            "severity": "medium"
                        })
                    
                    if years_diff < -50:
                        anomalies.append({
                            "message": "Date far in the future detected",
                            "date": date_obj['date_raw'],
                            "severity": "medium"
                        })
                    
                    # Check for impossible dates
                    if date.year < 1900 or date.year > 2100:
                        anomalies.append({
                            "message": "Impossible date detected",
                            "date": date_obj['date_raw'],
                            "severity": "high"
                        })
                except:
                    anomalies.append({
                        "message": "Invalid date format",
                        "date": date_obj['date_raw'],
                        "severity": "low"
                    })
        
        # Generate suggestions
        suggestions = []
        if expired_count > 0:
            suggestions.append(f"You have {expired_count} expired document(s) that may need renewal")
        
        if expiring_soon > 0:
            suggestions.append(f"{expiring_soon} document(s) will expire within 30 days - consider renewal soon")
        
        if total_dates == 0:
            suggestions.append("No dates detected. Ensure documents contain clear date information")
        
        # Check for duplicate dates
        date_counts = {}
        for d in all_dates:
            raw = d.get('date_raw', '')
            date_counts[raw] = date_counts.get(raw, 0) + 1
        
        duplicates = [date for date, count in date_counts.items() if count > 3]
        if duplicates:
            suggestions.append("Some dates appear multiple times - verify document quality")
        
        # Use AI for advanced analysis if API key is available
        ai_insights = None
        if self.client and total_dates > 0:
            try:
                ai_insights = self._get_ai_insights(all_dates, anomalies)
            except Exception as e:
                print(f"AI analysis failed: {e}")
        
        return {
            "total_dates": total_dates,
            "expired_count": expired_count,
            "valid_count": valid_count,
            "expiring_soon": expiring_soon,
            "anomalies": anomalies,
            "suggestions": suggestions,
            "ai_insights": ai_insights
        }
    
    def _get_ai_insights(self, dates: List[Dict], anomalies: List[Dict]) -> str:
        """Get AI-powered insights using Claude"""
        date_summary = f"Total dates: {len(dates)}\n"
        date_summary += "Sample dates:\n"
        for i, d in enumerate(dates[:10]):
            date_summary += f"- {d.get('date_raw', 'N/A')} (ISO: {d.get('date_iso', 'N/A')}, Expired: {d.get('is_expired', 'N/A')})\n"
        
        if anomalies:
            date_summary += f"\nAnomalies detected: {len(anomalies)}\n"
            for a in anomalies[:5]:
                date_summary += f"- {a['message']}: {a['date']}\n"
        
        prompt = f"""Analyze this document expiration data and provide actionable insights:

{date_summary}

Please provide:
1. Key patterns or trends you notice
2. Potential data quality issues
3. Recommendations for document management
4. Any critical items requiring immediate attention

Keep your response concise and actionable."""
        
        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        
        return message.content[0].text if message.content else None
