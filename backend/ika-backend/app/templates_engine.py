"""
Templates Engine - Manages poem/story/lecture templates
"""
import json
from pathlib import Path
from typing import Dict, List, Optional
import random
import logging
from app.pattern_repo import PatternRepository
from app.slot_filler import SlotFiller
from app.rule_engine import RuleEngine

logger = logging.getLogger(__name__)


class TemplatesEngine:
    """Manages and applies templates for different generation kinds"""
    
    def __init__(
        self,
        pattern_repo: PatternRepository,
        slot_filler: SlotFiller,
        rule_engine: RuleEngine
    ):
        self.pattern_repo = pattern_repo
        self.slot_filler = slot_filler
        self.rule_engine = rule_engine
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict:
        """Load templates from templates.json"""
        try:
            app_dir = Path(__file__).parent
            templates_file = app_dir.parent / "data" / "templates.json"
            if templates_file.exists():
                with open(templates_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load templates: {e}")
        return {}
    
    def generate_poem(
        self,
        topic: str,
        tone: str = "neutral",
        length: str = "medium"
    ) -> List[Dict]:
        """
        Generate poem structure using templates.
        
        Returns:
            List of pattern applications with filled slots
        """
        poem_templates = self.templates.get("poem_templates", [])
        if not poem_templates:
            return []
        
        # Select template based on length
        length_map = {"short": 2, "medium": 4, "long": 6}
        num_lines = length_map.get(length, 4)
        
        # Select a template
        template = random.choice(poem_templates) if poem_templates else {}
        
        # Get pattern pool
        pattern_pool = template.get("pattern_pool", [])
        if not pattern_pool:
            # Fallback: use any available patterns
            all_patterns = list(self.pattern_repo.get_all_patterns().values())
            pattern_pool = [p.get("pattern_id") for p in all_patterns[:5]]
        
        # Generate lines
        lines = []
        for i in range(num_lines):
            pattern_id = random.choice(pattern_pool) if pattern_pool else None
            if pattern_id:
                pattern = self.pattern_repo.get_pattern(pattern_id)
                if pattern:
                    filled_slots = self.slot_filler.fill_pattern_slots(
                        pattern,
                        domain=None  # Could filter by topic domain
                    )
                    lines.append({
                        "pattern_id": pattern_id,
                        "slots": filled_slots
                    })
        
        return lines
    
    def generate_story(
        self,
        topic: str,
        tone: str = "neutral",
        length: str = "medium"
    ) -> List[Dict]:
        """Generate story structure using templates"""
        story_templates = self.templates.get("story_templates", [])
        if not story_templates:
            return []
        
        template = random.choice(story_templates) if story_templates else {}
        
        # Story sections: opening, conflict, resolution
        sections = []
        for section_name in ["opening", "conflict", "resolution"]:
            section_config = template.get(section_name, {})
            pattern_pool = section_config.get("pattern_pool", [])
            min_sentences = section_config.get("min_sentences", 1)
            max_sentences = section_config.get("max_sentences", 3)
            
            num_sentences = random.randint(min_sentences, max_sentences)
            
            for _ in range(num_sentences):
                if pattern_pool:
                    pattern_id = random.choice(pattern_pool)
                    pattern = self.pattern_repo.get_pattern(pattern_id)
                    if pattern:
                        filled_slots = self.slot_filler.fill_pattern_slots(pattern)
                        sections.append({
                            "section": section_name,
                            "pattern_id": pattern_id,
                            "slots": filled_slots
                        })
        
        return sections
    
    def generate_lecture(
        self,
        topic: str,
        tone: str = "neutral",
        length: str = "medium"
    ) -> List[Dict]:
        """Generate lecture structure using templates"""
        lecture_templates = self.templates.get("lecture_templates", [])
        if not lecture_templates:
            return []
        
        template = random.choice(lecture_templates) if lecture_templates else {}
        
        # Lecture sections: intro, explain, summary
        sections = []
        for section_name in ["intro", "explain", "summary"]:
            section_config = template.get(section_name, {})
            pattern_pool = section_config.get("pattern_pool", [])
            min_sentences = section_config.get("min_sentences", 2)
            max_sentences = section_config.get("max_sentences", 5)
            
            num_sentences = random.randint(min_sentences, max_sentences)
            
            for _ in range(num_sentences):
                if pattern_pool:
                    pattern_id = random.choice(pattern_pool)
                    pattern = self.pattern_repo.get_pattern(pattern_id)
                    if pattern:
                        filled_slots = self.slot_filler.fill_pattern_slots(pattern)
                        sections.append({
                            "section": section_name,
                            "pattern_id": pattern_id,
                            "slots": filled_slots
                        })
        
        return sections
