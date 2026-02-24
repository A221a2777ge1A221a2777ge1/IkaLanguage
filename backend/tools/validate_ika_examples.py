#!/usr/bin/env python3
"""
Validation script for IKA grammar patterns.
Fails if patterns contain example_language or banned tokens in examples.
"""
import json
import sys
from pathlib import Path

# Banned tokens that must not appear in examples
BANNED_TOKENS = ["akwukwo", "anyi", "umunna", "ga eje", "ya mere", "mgbe"]


def validate_patterns_file(patterns_file: Path) -> list:
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
        
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON in patterns file: {e}")
    except Exception as e:
        errors.append(f"Error validating patterns file: {e}")
    
    return errors


def main():
    """Main validation function"""
    # Find patterns file
    script_dir = Path(__file__).parent
    patterns_file = script_dir.parent / "ika-backend" / "data" / "ika_grammar_patterns.json"
    
    if not patterns_file.exists():
        print(f"ERROR: Patterns file not found: {patterns_file}")
        sys.exit(1)
    
    errors = validate_patterns_file(patterns_file)
    
    if errors:
        print("VALIDATION FAILED:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)
    else:
        print("✓ Validation passed: No example_language fields or banned tokens found")
        sys.exit(0)


if __name__ == "__main__":
    main()
