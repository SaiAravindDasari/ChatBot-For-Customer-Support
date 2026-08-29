import logging
from typing import Tuple, List

try:
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    import nltk
except ImportError:
    SentimentIntensityAnalyzer = None
    nltk = None

logger = logging.getLogger(__name__)

class SentimentAnalyzer:
    def __init__(self):
        self.analyzer = None
        if SentimentIntensityAnalyzer:
            try:
                import ssl
                try:
                    ssl._create_default_https_context = ssl._create_unverified_context
                except AttributeError:
                    pass
                try:
                    nltk.data.find('sentiment/vader_lexicon')
                except LookupError:
                    nltk.download('vader_lexicon', quiet=True)
                self.analyzer = SentimentIntensityAnalyzer()
                
                custom_lexicon = {
                    'broken': -2.5, 'scam': -3.0, 'worst': -2.8, 
                    'terrible': -2.5, 'useless': -2.0, 'frustrated': -2.0, 
                    'angry': -2.5, 'unacceptable': -2.5, 'amazing': 2.5, 
                    'excellent': 2.5, 'helpful': 2.0, 'resolved': 1.5, 
                    'thank': 1.5, 'appreciate': 2.0
                }
                self.analyzer.lexicon.update(custom_lexicon)
                logger.info("Initialized VADER sentiment analyzer with custom lexicon.")
            except Exception as e:
                logger.error(f"Failed to initialize VADER: {e}")
        else:
            logger.warning("VADER is not available. Sentiment analyzer will return neutral.")

    def analyze(self, text: str) -> Tuple[float, str]:
        if not self.analyzer:
            return (0.0, 'neutral')
            
        scores = self.analyzer.polarity_scores(text)
        compound = scores.get('compound', 0.0)
        
        if compound > 0.15:
            label = 'positive'
        elif compound < -0.15:
            label = 'negative'
        else:
            label = 'neutral'
            
        return (compound, label)

    def get_frustration_level(self, text: str) -> str:
        compound, _ = self.analyze(text)
        if compound < -0.5:
            return 'high'
        elif compound < -0.15:
            return 'medium'
        else:
            return 'low'

    def should_escalate(self, scores: List[float], threshold: float = -0.5) -> bool:
        if len(scores) < 3:
            return False
        recent = scores[-3:]
        avg = sum(recent) / len(recent)
        return avg < threshold

    def analyze_trajectory(self, scores: List[float]) -> str:
        if len(scores) < 2:
            return 'stable'
            
        recent = scores[-min(len(scores), 3):]
        if recent[-1] > recent[0] + 0.2:
            return 'improving'
        elif recent[-1] < recent[0] - 0.2:
            return 'worsening'
        else:
            return 'stable'
