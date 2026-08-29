import re
import html
import unicodedata
import logging
from typing import List

try:
    import nltk
    from nltk.tokenize import word_tokenize
    from nltk.corpus import stopwords
    from nltk.stem import WordNetLemmatizer
except ImportError:
    nltk = None

try:
    from langdetect import detect
except ImportError:
    detect = None

logger = logging.getLogger(__name__)

CONTRACTION_MAP = {
    "ain't": "is not", "aren't": "are not", "can't": "cannot", "can't've": "cannot have",
    "'cause": "because", "could've": "could have", "couldn't": "could not",
    "couldn't've": "could not have", "didn't": "did not", "doesn't": "does not",
    "don't": "do not", "hadn't": "had not", "hadn't've": "had not have",
    "hasn't": "has not", "haven't": "have not", "he'd": "he would",
    "he'd've": "he would have", "he'll": "he will", "he'll've": "he will have",
    "he's": "he is", "how'd": "how did", "how'd'y": "how do you",
    "how'll": "how will", "how's": "how is", "I'd": "I would",
    "I'd've": "I would have", "I'll": "I will", "I'll've": "I will have",
    "I'm": "I am", "I've": "I have", "isn't": "is not", "it'd": "it would",
    "it'd've": "it would have", "it'll": "it will", "it'll've": "it will have",
    "it's": "it is", "let's": "let us", "ma'am": "madam", "mayn't": "may not",
    "might've": "might have", "mightn't": "might not", "mightn't've": "might not have",
    "must've": "must have", "mustn't": "must not", "mustn't've": "must not have",
    "needn't": "need not", "needn't've": "need not have", "o'clock": "of the clock",
    "oughtn't": "ought not", "oughtn't've": "ought not have", "shan't": "shall not",
    "sha'n't": "shall not", "shan't've": "shall not have", "she'd": "she would",
    "she'd've": "she would have", "she'll": "she will", "she'll've": "she will have",
    "she's": "she is", "should've": "should have", "shouldn't": "should not",
    "shouldn't've": "should not have", "so've": "so have", "so's": "so as",
    "that'd": "that would", "that'd've": "that would have", "that's": "that is",
    "there'd": "there would", "there'd've": "there would have", "there's": "there is",
    "they'd": "they would", "they'd've": "they would have", "they'll": "they will",
    "they'll've": "they will have", "they're": "they are", "they've": "they have",
    "to've": "to have", "wasn't": "was not", "we'd": "we would",
    "we'd've": "we would have", "we'll": "we will", "we'll've": "we will have",
    "we're": "we are", "we've": "we have", "weren't": "were not",
    "what'll": "what will", "what'll've": "what will have", "what're": "what are",
    "what's": "what is", "what've": "what have", "when's": "when is",
    "when've": "when have", "where'd": "where did", "where's": "where is",
    "where've": "where have", "who'll": "who will", "who'll've": "who will have",
    "who's": "who is", "who've": "who have", "why's": "why is",
    "why've": "why have", "will've": "will have", "won't": "will not",
    "won't've": "will not have", "would've": "would have", "wouldn't": "would not",
    "wouldn't've": "would not have", "y'all": "you all", "y'all'd": "you all would",
    "y'all'd've": "you all would have", "y'all're": "you all are",
    "y'all've": "you all have", "you'd": "you would", "you'd've": "you would have",
    "you'll": "you will", "you'll've": "you will have", "you're": "you are",
    "you've": "you have"
}

class TextPreprocessor:
    def __init__(self):
        self.lemmatizer = None
        self.stop_words = set()
        
        if nltk is not None:
            try:
                # Bypass SSL verification for NLTK downloads
                import ssl
                try:
                    _create_unverified_https_context = ssl._create_unverified_context
                except AttributeError:
                    pass
                else:
                    ssl._create_default_https_context = _create_unverified_https_context

                for pkg in ['punkt_tab', 'stopwords', 'wordnet', 'averaged_perceptron_tagger_eng']:
                    try:
                        nltk.data.find(f'tokenizers/{pkg}' if 'punkt' in pkg else f'corpora/{pkg}' if pkg in ('stopwords', 'wordnet') else f'taggers/{pkg}')
                    except LookupError:
                        nltk.download(pkg, quiet=True)

                self.lemmatizer = WordNetLemmatizer()
                self.stop_words = set(stopwords.words('english'))
                negations = {'not', 'no', 'never', 'nor', 'none', 'neither', 'cannot'}
                self.stop_words = self.stop_words - negations
            except Exception as e:
                logger.warning(f"NLTK partial init (some features may be limited): {e}")
        else:
            logger.warning("NLTK not installed. Preprocessor limited.")

    def normalize(self, text: str) -> str:
        text = html.unescape(str(text))
        text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8', 'ignore')
        return text.lower().strip()

    def expand_contractions(self, text: str) -> str:
        pattern = re.compile('({})'.format('|'.join(CONTRACTION_MAP.keys())), flags=re.IGNORECASE|re.DOTALL)
        def expand(match):
            m = match.group(0)
            expanded = CONTRACTION_MAP.get(m) or CONTRACTION_MAP.get(m.lower())
            if not expanded: return m
            return m[0] + expanded[1:]
        expanded_text = pattern.sub(expand, text)
        return re.sub("'", "", expanded_text)

    def remove_noise(self, text: str) -> str:
        text = re.sub(r'[^\w\s]', ' ', text)
        return re.sub(r'\s+', ' ', text).strip()

    def tokenize(self, text: str) -> List[str]:
        if nltk is not None:
            try:
                return word_tokenize(text)
            except Exception:
                return text.split()
        return text.split()

    def remove_stopwords(self, tokens: List[str]) -> List[str]:
        return [t for t in tokens if t.lower() not in self.stop_words]

    def lemmatize(self, tokens: List[str]) -> List[str]:
        if self.lemmatizer:
            return [self.lemmatizer.lemmatize(t) for t in tokens]
        return tokens

    def detect_language(self, text: str) -> str:
        if detect is not None:
            try:
                return detect(text)
            except Exception:
                return 'en'
        return 'en'

    def extract_emojis(self, text: str) -> List[str]:
        emoji_pattern = re.compile(
            "[\U0001f600-\U0001f64f\U0001f300-\U0001f5ff\U0001f680-\U0001f6ff\U0001f1e0-\U0001f1ff\U00002702-\U000027b0\U000024c2-\U0001f251]+", 
            flags=re.UNICODE)
        return emoji_pattern.findall(text)

    def full_preprocess(self, text: str) -> str:
        text = self.normalize(text)
        text = self.expand_contractions(text)
        text = self.remove_noise(text)
        tokens = self.tokenize(text)
        tokens = self.remove_stopwords(tokens)
        tokens = self.lemmatize(tokens)
        return " ".join(tokens)
