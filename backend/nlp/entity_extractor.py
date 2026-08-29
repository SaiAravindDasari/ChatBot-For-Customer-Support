import json
import logging
import re
from typing import Dict, List, Any

try:
    import spacy
except ImportError:
    spacy = None

try:
    from dateutil import parser as date_parser
except ImportError:
    date_parser = None

from pathlib import Path

logger = logging.getLogger(__name__)

class EntityExtractor:
    def __init__(self, entities_path: Optional[str] = None):
        if not entities_path:
            entities_path = str(Path(__file__).parent.parent / "data" / "entities.json")
        self.nlp = None
        if spacy:
            try:
                self.nlp = spacy.load('en_core_web_sm')
                logger.info("Loaded SpaCy en_core_web_sm model.")
            except Exception as e:
                logger.warning(f"Could not load SpaCy model en_core_web_sm: {e}")
        else:
            logger.warning("SpaCy is not installed. NER will be limited to regex.")
            
        self.custom_patterns = self._load_patterns(entities_path)

    def _load_patterns(self, path: str) -> Dict[str, str]:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Handle nested format: {"entities": [{"name": "...", "patterns": ["...", ...]}]}
            patterns = {}
            entities_list = data.get("entities", []) if isinstance(data, dict) else data
            for entity in entities_list:
                if isinstance(entity, dict):
                    name = entity.get("name", "").upper()
                    entity_patterns = entity.get("patterns", [])
                    if name and entity_patterns:
                        # Combine all patterns for this entity with OR
                        combined = "|".join(f"(?:{p})" for p in entity_patterns)
                        patterns[name] = combined
                elif isinstance(entity, str):
                    # Flat format: {"ENTITY_NAME": "regex"}
                    patterns[entity] = data[entity]

            if patterns:
                logger.info(f"Loaded {len(patterns)} custom entity patterns")
                return patterns

            # If parsing failed, use defaults
            raise ValueError("No valid patterns parsed")
        except Exception as e:
            logger.warning(f"Using default entity patterns ({e})")
            return {
                "ORDER_ID": r"#?(?:QD|ORD|order)[-_ ]?\d{4,8}",
                "EMAIL": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
                "PHONE": r"\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
                "TRANSACTION_ID": r"\b(?:TXN|TRX)[-]?[A-Z0-9]{8,15}\b"
            }

    def extract(self, text: str) -> Dict[str, List[str]]:
        return self.extract_all(text)

    def _extract_regex(self, text: str, patterns: Dict[str, str]) -> Dict[str, List[str]]:
        results = {}
        for entity_type, pattern in patterns.items():
            matches = re.findall(pattern, text, flags=re.IGNORECASE)
            if matches:
                results[entity_type] = list(set(matches))
        return results

    def _extract_spacy(self, text: str) -> Dict[str, List[str]]:
        results = {}
        if not self.nlp:
            return results
            
        doc = self.nlp(text)
        allowed_labels = {'DATE', 'TIME', 'MONEY', 'PERSON', 'ORG', 'GPE'}
        
        for ent in doc.ents:
            if ent.label_ in allowed_labels:
                val = ent.text
                if ent.label_ == 'DATE' and date_parser:
                    try:
                        parsed = date_parser.parse(val, fuzzy=True)
                        val = parsed.strftime("%Y-%m-%d")
                    except Exception:
                        pass
                
                if ent.label_ not in results:
                    results[ent.label_] = []
                if val not in results[ent.label_]:
                    results[ent.label_].append(val)
                    
        return results

    def extract_all(self, text: str) -> Dict[str, List[str]]:
        results = {}
        
        regex_entities = self._extract_regex(text, self.custom_patterns)
        for k, v in regex_entities.items():
            results[k] = v
            
        spacy_entities = self._extract_spacy(text)
        for k, v in spacy_entities.items():
            if k not in results:
                results[k] = []
            for item in v:
                if item not in results[k]:
                    results[k].append(item)
                    
        return results
