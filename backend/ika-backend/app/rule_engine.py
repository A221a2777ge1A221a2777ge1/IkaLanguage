"""
Rule Engine - Applies grammar rules (tense, negation, questions, connectors)
"""
import json
from pathlib import Path
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


class RuleEngine:
    """Manages and applies grammar rules from grammar_rules.json"""
    
    def __init__(self, rules_file: Optional[str] = None):
        """
        Initialize rule engine and load rules.
        
        Args:
            rules_file: Path to grammar_rules.json. If None, looks in data directory.
        """
        if rules_file is None:
            app_dir = Path(__file__).parent
            rules_file = app_dir.parent / "data" / "grammar_rules.json"
        
        self.rules_file = Path(rules_file)
        self.rules = {}
        self.load_rules()
    
    def load_rules(self):
        """Load grammar rules from JSON file"""
        try:
            if not self.rules_file.exists():
                logger.warning(f"Grammar rules file not found: {self.rules_file}")
                self.rules = {}
                return
            
            with open(self.rules_file, 'r', encoding='utf-8') as f:
                self.rules = json.load(f)
            
            logger.info(f"Loaded grammar rules from {self.rules_file}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse grammar rules JSON: {e}")
            self.rules = {}
        except Exception as e:
            logger.error(f"Failed to load grammar rules: {e}", exc_info=True)
            self.rules = {}
    
    def get_tense_marker(self, tense: str) -> str:
        """
        Get tense marker for given tense.
        
        Args:
            tense: present|past|future|progressive
        
        Returns:
            Tense marker string (empty if not found)
        """
        tense_markers = self.rules.get("tense_markers", {})
        return tense_markers.get(tense, "")
    
    def apply_tense(self, text: str, tense: str) -> str:
        """Apply tense marker to text"""
        marker = self.get_tense_marker(tense)
        if marker:
            # Simple prefix strategy (adjust based on Ika grammar)
            return f"{marker} {text}".strip()
        return text
    
    def get_negation_marker(self) -> str:
        """Get negation marker"""
        return self.rules.get("negation", {}).get("marker", "")
    
    def apply_negation(self, text: str) -> str:
        """Apply negation to text"""
        marker = self.get_negation_marker()
        if marker:
            # Simple prefix strategy
            return f"{marker} {text}".strip()
        return text
    
    def get_question_marker(self) -> str:
        """Get question marker for yes/no questions"""
        return self.rules.get("questions", {}).get("yes_no_marker", "")
    
    def apply_question(self, text: str) -> str:
        """Apply question formation to text"""
        marker = self.get_question_marker()
        if marker:
            # Simple prefix strategy
            return f"{marker} {text}".strip()
        return text
