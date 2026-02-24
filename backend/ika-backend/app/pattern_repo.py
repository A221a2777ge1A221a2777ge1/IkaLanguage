"""
Pattern Repository - Loads and manages Ika grammar patterns
"""
import json
from pathlib import Path
from typing import Dict, Optional, List
import logging

logger = logging.getLogger(__name__)


class PatternRepository:
    """Manages Ika grammar patterns loaded from ika_grammar_patterns.json"""
    
    def __init__(self, patterns_file: Optional[str] = None):
        """
        Initialize pattern repository and load patterns.
        
        Args:
            patterns_file: Path to ika_grammar_patterns.json. If None, looks in data directory.
        """
        if patterns_file is None:
            # Look for file in data directory relative to app
            app_dir = Path(__file__).parent
            patterns_file = app_dir.parent / "data" / "ika_grammar_patterns.json"
        
        self.patterns_file = Path(patterns_file)
        self.patterns = {}
        self.pattern_index = {}  # Index by pattern_id
        self.load_patterns()
    
    def load_patterns(self):
        """Load grammar patterns from JSON file"""
        try:
            if not self.patterns_file.exists():
                logger.error(f"Grammar patterns file not found: {self.patterns_file}")
                raise FileNotFoundError(f"Grammar patterns file not found: {self.patterns_file}")
            
            with open(self.patterns_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract patterns (could be in 'patterns' key or root)
            if isinstance(data, dict):
                if "patterns" in data:
                    patterns_list = data["patterns"]
                else:
                    # Assume root is a dict of pattern_id -> pattern
                    patterns_list = data
            elif isinstance(data, list):
                patterns_list = data
            else:
                raise ValueError("Invalid patterns file format")
            
            # Build index
            for pattern in patterns_list:
                if isinstance(pattern, dict) and "pattern_id" in pattern:
                    pattern_id = pattern["pattern_id"]
                    self.pattern_index[pattern_id] = pattern
                    self.patterns[pattern_id] = pattern
            
            logger.info(f"Loaded {len(self.pattern_index)} grammar patterns from {self.patterns_file}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse grammar patterns JSON: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load grammar patterns: {e}", exc_info=True)
            raise
    
    def get_pattern(self, pattern_id: str) -> Optional[Dict]:
        """Get a pattern by ID"""
        return self.pattern_index.get(pattern_id)
    
    def get_all_patterns(self) -> Dict[str, Dict]:
        """Get all patterns"""
        return self.pattern_index.copy()
    
    def get_patterns_by_category(self, category: str) -> List[Dict]:
        """Get patterns by category (if category field exists)"""
        return [
            pattern for pattern in self.pattern_index.values()
            if pattern.get("category") == category
        ]
    
    def has_pattern(self, pattern_id: str) -> bool:
        """Check if pattern exists"""
        return pattern_id in self.pattern_index
