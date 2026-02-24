"""
Slot Filler - Fills pattern slots with words from lexicon
"""
import json
from pathlib import Path
from typing import Dict, List, Optional
import random
import logging
from app.lexicon_repo import LexiconRepository
from app.pattern_repo import PatternRepository
from app.rule_engine import RuleEngine

logger = logging.getLogger(__name__)


class SlotFiller:
    """Fills pattern slots with appropriate words from lexicon"""
    
    def __init__(
        self,
        lexicon_repo: LexiconRepository,
        pattern_repo: PatternRepository,
        rule_engine: RuleEngine
    ):
        self.lexicon_repo = lexicon_repo
        self.pattern_repo = pattern_repo
        self.rule_engine = rule_engine
        self.pronouns = self._load_pronouns()
        self.connectors = self._load_connectors()
    
    def _load_pronouns(self) -> Dict:
        """Load pronouns from pronouns.json"""
        try:
            app_dir = Path(__file__).parent
            pronouns_file = app_dir.parent / "data" / "pronouns.json"
            if pronouns_file.exists():
                with open(pronouns_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load pronouns: {e}")
        return {}
    
    def _load_connectors(self) -> Dict:
        """Load connectors from connectors.json"""
        try:
            app_dir = Path(__file__).parent
            connectors_file = app_dir.parent / "data" / "connectors.json"
            if connectors_file.exists():
                with open(connectors_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load connectors: {e}")
        return {}
    
    def fill_slot(
        self,
        slot_name: str,
        slot_constraints: Optional[Dict] = None,
        domain: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Fill a single slot with a word from lexicon.
        
        Args:
            slot_name: Name of the slot (e.g., "Subject", "Verb", "Object")
            slot_constraints: Constraints for the slot (pos, domain, etc.)
            domain: Optional domain filter
        
        Returns:
            Lexicon entry dict or None
        """
        # Check for pronouns first (for Subject/Object slots)
        if slot_name in ["Subject", "Object"]:
            pronoun = self._get_pronoun_for_slot(slot_name)
            if pronoun:
                return {
                    "source_text": pronoun.get("english", ""),
                    "target_text": pronoun.get("ika", ""),
                    "pos": "pronoun",
                    "source": "pronouns.json"
                }
        
        # Check for connectors
        if slot_name == "Connector":
            connector = self._get_connector()
            if connector:
                return {
                    "source_text": connector.get("english", ""),
                    "target_text": connector.get("ika", ""),
                    "pos": "connector",
                    "source": "connectors.json"
                }
        
        # Get POS from constraints or infer from slot name
        pos = None
        if slot_constraints:
            pos = slot_constraints.get("pos")
        
        if not pos:
            pos = self._infer_pos_from_slot_name(slot_name)
        
        # Look up in lexicon by POS
        if pos:
            candidates = self.lexicon_repo.find_by_pos(pos, domain=domain, limit=20)
            if candidates:
                return random.choice(candidates)
        
        # Fallback: search by domain only
        if domain:
            candidates = self.lexicon_repo.find_by_domain(domain, limit=20)
            if candidates:
                return random.choice(candidates)
        
        # Last resort: return None (slot will be empty)
        return None
    
    # Map ika_dictionary slot names to pronoun keys (Subject / Object)
    _SUBJECT_SLOTS = {"Subject", "SUBJ"}
    _OBJECT_SLOTS = {"Object", "OBJ_OR_COMP", "OBJ_OR_LOC"}

    def _get_pronoun_for_slot(self, slot_name: str) -> Optional[Dict]:
        """Get pronoun for Subject or Object slot"""
        if slot_name in self._SUBJECT_SLOTS:
            pronouns_list = self.pronouns.get("subject_pronouns", [])
        elif slot_name in self._OBJECT_SLOTS:
            pronouns_list = self.pronouns.get("object_pronouns", [])
        else:
            return None
        
        if pronouns_list:
            return random.choice(pronouns_list)
        return None
    
    def _get_connector(self) -> Optional[Dict]:
        """Get a random connector"""
        connectors_list = self.connectors.get("connectors", [])
        if connectors_list:
            return random.choice(connectors_list)
        return None
    
    def _infer_pos_from_slot_name(self, slot_name: str) -> Optional[str]:
        """Infer part of speech from slot name (supports ika_grammar_patterns and ika_dictionary slot names)"""
        slot_lower = slot_name.lower()
        if "verb" in slot_lower or slot_name in ("Verb", "VERB"):
            return "verb"
        if slot_name in ("Subject", "Object", "Noun", "SUBJ", "OBJ_OR_COMP", "OBJ_OR_LOC", "NP"):
            return "noun"
        if "noun" in slot_lower or "np" in slot_lower:
            return "noun"
        if "adj" in slot_lower or slot_name == "Adjective":
            return "adjective"
        if "adv" in slot_lower or slot_name == "Adverb":
            return "adverb"
        if slot_name in ("LOC", "PHRASE", "LEXEME_OR_PHRASE"):
            return "noun"
        return None
    
    def fill_pattern_slots(
        self,
        pattern: Dict,
        domain: Optional[str] = None
    ) -> Dict[str, Dict]:
        """
        Fill all slots in a pattern.
        
        Returns:
            Dict mapping slot_name -> lexicon_entry
        """
        filled_slots = {}
        slots = pattern.get("slots", [])
        
        for slot in slots:
            if isinstance(slot, str):
                slot_name = slot
                slot_constraints = {}
            elif isinstance(slot, dict):
                slot_name = slot.get("name", "")
                slot_constraints = slot
            else:
                continue
            
            if slot_name:
                filled = self.fill_slot(slot_name, slot_constraints, domain)
                if filled:
                    filled_slots[slot_name] = filled
        
        return filled_slots
