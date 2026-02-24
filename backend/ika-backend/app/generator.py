"""
Generator - Main rule-based generation engine
Combines lexicon, patterns, rules, and templates
"""
from typing import Dict, List, Optional
import logging
from app.lexicon_repo import LexiconRepository
from app.pattern_repo import PatternRepository
from app.rule_engine import RuleEngine
from app.slot_filler import SlotFiller
from app.templates_engine import TemplatesEngine

logger = logging.getLogger(__name__)


class Generator:
    """Main generator for Ika text using rule-based approach"""
    
    def __init__(
        self,
        lexicon_repo: LexiconRepository,
        pattern_repo: PatternRepository,
        rule_engine: RuleEngine,
        slot_filler: SlotFiller,
        templates_engine: TemplatesEngine
    ):
        self.lexicon_repo = lexicon_repo
        self.pattern_repo = pattern_repo
        self.rule_engine = rule_engine
        self.slot_filler = slot_filler
        self.templates_engine = templates_engine
    
    def translate(
        self,
        text: str,
        tense: str = "present",
        mode: str = "rule_based"
    ) -> Dict:
        """
        Translate English text to Ika using rule-based generation.
        
        Args:
            text: English input text
            tense: present|past|future|progressive
            mode: rule_based (only mode supported)
        
        Returns:
            {
                "text": "Ika output",
                "meta": {
                    "pattern_ids": [...],
                    "lexicon_entries": [...],
                    "tense": "..."
                }
            }
        """
        # Simple word-by-word translation for MVP
        # In full implementation, would parse sentence structure and apply patterns
        
        words = text.lower().split()
        translated_words = []
        lexicon_entries_used = []
        
        for word in words:
            # Look up in lexicon
            entry = self.lexicon_repo.find_by_source_text(word)
            if entry and entry.get("target_text"):
                translated_words.append(entry["target_text"])
                lexicon_entries_used.append({
                    "doc_id": entry.get("doc_id"),
                    "source": entry.get("source_text"),
                    "target": entry.get("target_text")
                })
            else:
                # Keep unknown words as-is
                translated_words.append(word)
        
        # Join words
        ika_text = " ".join(translated_words)
        
        # Apply tense
        if tense != "present":
            ika_text = self.rule_engine.apply_tense(ika_text, tense)
        
        return {
            "text": ika_text,
            "meta": {
                "pattern_ids": [],  # Would be populated in full pattern-based translation
                "lexicon_entries": lexicon_entries_used,
                "tense": tense,
                "mode": mode
            }
        }
    
    def generate(
        self,
        kind: str,
        topic: str,
        tone: str = "neutral",
        length: str = "medium"
    ) -> Dict:
        """
        Generate Ika text (poem/story/lecture) based on parameters.
        
        Args:
            kind: poem|story|lecture
            topic: Topic for generation
            tone: neutral|formal|poetic
            length: short|medium|long
        
        Returns:
            {
                "text": "Generated Ika text",
                "meta": {
                    "kind": "...",
                    "pattern_ids": [...],
                    "lexicon_entries": [...]
                }
            }
        """
        # Generate structure using templates
        if kind == "poem":
            structure = self.templates_engine.generate_poem(topic, tone, length)
        elif kind == "story":
            structure = self.templates_engine.generate_story(topic, tone, length)
        elif kind == "lecture":
            structure = self.templates_engine.generate_lecture(topic, tone, length)
        else:
            raise ValueError(f"Unknown generation kind: {kind}")
        
        # Convert structure to Ika text
        ika_sentences = []
        pattern_ids_used = []
        lexicon_entries_used = []
        
        for item in structure:
            pattern_id = item.get("pattern_id")
            if pattern_id:
                pattern_ids_used.append(pattern_id)
                pattern = self.pattern_repo.get_pattern(pattern_id)
                
                if pattern:
                    # Build sentence from pattern and filled slots
                    slots = item.get("slots", {})
                    sentence_parts = []
                    
                    # Simple pattern application: use target_text from slots
                    for slot_name, slot_entry in slots.items():
                        if slot_entry and slot_entry.get("target_text"):
                            sentence_parts.append(slot_entry["target_text"])
                            lexicon_entries_used.append({
                                "doc_id": slot_entry.get("doc_id"),
                                "source": slot_entry.get("source_text"),
                                "target": slot_entry.get("target_text"),
                                "slot": slot_name
                            })
                    
                    if sentence_parts:
                        sentence = " ".join(sentence_parts)
                        ika_sentences.append(sentence)
        
        # Join sentences
        ika_text = " ".join(ika_sentences)
        
        if not ika_text:
            # Fallback: simple generation
            ika_text = self._fallback_generation(topic, kind)
        
        return {
            "text": ika_text,
            "meta": {
                "kind": kind,
                "topic": topic,
                "tone": tone,
                "length": length,
                "pattern_ids": pattern_ids_used,
                "lexicon_entries": lexicon_entries_used
            }
        }
    
    def _fallback_generation(self, topic: str, kind: str) -> str:
        """Fallback simple generation if templates fail"""
        # Get some words from lexicon related to topic
        entries = self.lexicon_repo.find_by_domain("general", limit=5)
        if not entries:
            entries = self.lexicon_repo.get_all()[:5]
        
        words = [e.get("target_text", "") for e in entries if e.get("target_text")]
        return " ".join(words) if words else ""
