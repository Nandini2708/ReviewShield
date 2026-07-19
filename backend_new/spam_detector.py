import re
from textblob import TextBlob
from typing import Dict, List, Tuple

class SpamDetector:
    def __init__(self):
        # Temporary email domains
        self.temp_domains = {
            'tempmail.com', '10minutemail.com', 'mailinator.com',
            'guerrillamail.com', 'yopmail.com', 'throwaway.com',
            'temp-mail.org', 'fakeinbox.com'
        }
        
        # Spam patterns
        self.spam_patterns = [
            (r'buy\s+now', 15), (r'click\s+here', 20), (r'free\s+shipping', 15),
            (r'discount|offer|promo', 10), (r'www\.|https?://', 20),
            (r'lottery|prize|won', 30), (r'bitcoin|crypto|investment', 25),
            (r'make\s+money|earn\s+cash', 25), (r'limited\s+time|act\s+now', 15)
        ]
        
        # Spam keywords
        self.spam_keywords = [
            'free', 'money', 'win', 'prize', 'lottery', 'bitcoin',
            'crypto', 'investment', 'click', 'subscribe', 'bonus',
            'cash', 'guaranteed', 'earn', 'income'
        ]
    
    def detect(self, review_text: str, email: str) -> Dict:
        spam_score = 0
        reasons = []
        
        # 1. Email domain check
        try:
            domain = email.split('@')[1].lower()
            if domain in self.temp_domains:
                spam_score += 40
                reasons.append(f"Temporary email: {domain}")
        except:
            pass
        
        # 2. Pattern check
        for pattern, weight in self.spam_patterns:
            if re.search(pattern, review_text.lower()):
                spam_score += weight
                reasons.append(f"Spam pattern detected")
                break
        
        # 3. Keyword check
        found = [kw for kw in self.spam_keywords if kw in review_text.lower()]
        if len(found) >= 3:
            spam_score += 25
            reasons.append(f"Multiple spam keywords: {', '.join(found[:3])}")
        elif len(found) >= 2:
            spam_score += 15
            reasons.append(f"Spam keywords detected")
        
        # 4. Length check
        if len(review_text.strip()) < 15:
            spam_score += 35
            reasons.append("Review too short (min 15 chars)")
        elif len(review_text.strip()) < 30:
            spam_score += 15
            reasons.append("Review unusually short")
        
        # 5. ALL CAPS check
        if len(review_text) > 20:
            caps_ratio = sum(1 for c in review_text if c.isupper()) / len(review_text)
            if caps_ratio > 0.7:
                spam_score += 20
                reasons.append("Excessive capitalization (SHOUTING)")
            elif caps_ratio > 0.5:
                spam_score += 10
                reasons.append("Unusual capitalization")
        
        # 6. Exclamation marks
        exc_count = review_text.count('!')
        if exc_count > 3:
            spam_score += min(exc_count * 3, 15)
            reasons.append(f"Too many exclamations ({exc_count})")
        
        # 7. Sentiment analysis
        try:
            blob = TextBlob(review_text)
            polarity = blob.sentiment.polarity
            sentiment = "positive" if polarity > 0.1 else "negative" if polarity < -0.1 else "neutral"
            
            if abs(polarity) > 0.8:
                spam_score += 15
                reasons.append("Extreme sentiment (possible fake)")
        except:
            sentiment = "neutral"
        
        # Normalize score
        spam_score = min(spam_score, 100)
        is_spam = spam_score >= 50
        
        # Recommendation
        if is_spam:
            if spam_score >= 80:
                recommendation = "Highly likely spam. Auto-reject."
            elif spam_score >= 60:
                recommendation = "Suspicious. Manual review needed."
            else:
                recommendation = "Potential spam. Flag for review."
        else:
            if spam_score <= 20:
                recommendation = "Authentic review. Auto-approve."
            else:
                recommendation = "Likely genuine. Publish with caution."
        
        return {
            'is_spam': is_spam,
            'spam_score': int(spam_score),
            'confidence': 100 - int(spam_score),
            'reasons': reasons[:5],
            'sentiment': sentiment,
            'recommendation': recommendation
        }

# Singleton
spam_detector = SpamDetector()