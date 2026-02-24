"""
Validators - Validate data files on startup
"""
import json
from pathlib import Path
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

# Banned tokens that must not appear in examples
BANNED_TOKENS = ["akwukwo", "anyi", "umunna", "ga eje", "ya mere", "mgbe"]


def validate_grammar_patterns(patterns_file: Path) -> List[str]:
    """
    Validate grammar patterns file.
    Returns list of errors (empty if valid).
    """
    errors = []
    
    if not patterns_file.exists():
        errors.append(f"Grammar patterns file not found: {patterns_file}")
        return errors
    
    try:
        with open(patterns_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Extract patterns
        if isinstance(data, dict):
            patterns_list = data.get("patterns", [])
            if not patterns_list:
                patterns_list = [v for v in data.values() if isinstance(v, dict)]
        elif isinstance(data, list):
            patterns_list = data
        else:
            errors.append("Invalid patterns file format")
            return errors
        
        # Validate each pattern
        for pattern in patterns_list:
            if not isinstance(pattern, dict):
                continue
            
            pattern_id = pattern.get("pattern_id", "unknown")
            
            # Check for example_language (must not exist)
            if "example_language" in pattern:
                errors.append(
                    f"Pattern {pattern_id} contains 'example_language' field (not allowed)"
                )
            
            # Check example field for banned tokens
            example = pattern.get("example", "")
            if example:
                example_lower = example.lower()
                for banned in BANNED_TOKENS:
                    if banned in example_lower:
                        errors.append(
                            f"Pattern {pattern_id} example contains banned token: {banned}"
                        )
            
            # Validate pattern_id exists
            if not pattern.get("pattern_id"):
                errors.append("Pattern missing pattern_id")
        
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON in patterns file: {e}")
    except Exception as e:
        errors.append(f"Error validating patterns file: {e}")
    
    return errors


def validate_templates(templates_file: Path, pattern_repo) -> List[str]:
    """
    Validate templates file references valid pattern_ids.
    Returns list of errors (empty if valid).
    """
    errors = []
    
    if not templates_file.exists():
        # Templates are optional
        return errors
    
    try:
        with open(templates_file, 'r', encoding='utf-8') as f:
            templates = json.load(f)
        
        # Check all pattern references
        def check_pattern_pool(pattern_pool: List, context: str):
            for pattern_id in pattern_pool:
                if not pattern_repo.has_pattern(pattern_id):
                    errors.append(
                        f"Templates {context} references invalid pattern_id: {pattern_id}"
                    )
        
        # Check poem templates
        for template in templates.get("poem_templates", []):
            check_pattern_pool(
                template.get("pattern_pool", []),
                f"poem_templates[{templates.get('poem_templates', []).index(template)}]"
            )
        
        # Check story templates
        for template in templates.get("story_templates", []):
            for section in ["opening", "conflict", "resolution"]:
                section_config = template.get(section, {})
                check_pattern_pool(
                    section_config.get("pattern_pool", []),
                    f"story_templates[{templates.get('story_templates', []).index(template)}].{section}"
                )
        
        # Check lecture templates
        for template in templates.get("lecture_templates", []):
            for section in ["intro", "explain", "summary"]:
                section_config = template.get(section, {})
                check_pattern_pool(
                    section_config.get("pattern_pool", []),
                    f"lecture_templates[{templates.get('lecture_templates', []).index(template)}].{section}"
                )
        
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON in templates file: {e}")
    except Exception as e:
        errors.append(f"Error validating templates file: {e}")
    
    return errors


def validate_on_startup():
    """
    Run all validations on startup.
    Raises ValueError if validation fails.
    """
    app_dir = Path(__file__).parent
    data_dir = app_dir.parent / "data"
    
    all_errors = []
    
    # Validate grammar patterns
    patterns_file = data_dir / "ika_grammar_patterns.json"
    pattern_errors = validate_grammar_patterns(patterns_file)
    all_errors.extend(pattern_errors)
    
    # Validate templates (requires pattern_repo)
    try:
        # Import here to avoid circular imports
        from app.pattern_repo import PatternRepository
        pattern_repo = PatternRepository()
        
        templates_file = data_dir / "templates.json"
        template_errors = validate_templates(templates_file, pattern_repo)
        all_errors.extend(template_errors)
    except Exception as e:
        logger.warning(f"Could not validate templates: {e}")
        # Don't fail startup if template validation fails (templates are optional)
    
    if all_errors:
        error_msg = "Validation failed:\n" + "\n".join(f"  - {e}" for e in all_errors)
        raise ValueError(error_msg)
    
    logger.info("All validations passed")
