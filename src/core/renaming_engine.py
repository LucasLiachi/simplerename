from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import re
import os
from datetime import datetime

class RenameRule(ABC):
    """Base class for rename rules"""
    @abstractmethod
    def apply(self, filename: str, context: Dict[str, Any] = None) -> str:
        pass

    def validate(self, filename: str) -> bool:
        """Optional validation method for rules"""
        return True

class PrefixRule(RenameRule):
    def __init__(self, prefix: str):
        self.prefix = prefix

    def apply(self, filename: str, context: Dict[str, Any] = None) -> str:
        name, ext = os.path.splitext(filename)
        return f"{self.prefix}{name}{ext}"

class SuffixRule(RenameRule):
    def __init__(self, suffix: str):
        self.suffix = suffix

    def apply(self, filename: str, context: Dict[str, Any] = None) -> str:
        name, ext = os.path.splitext(filename)
        return f"{name}{self.suffix}{ext}"

class RegexReplaceRule(RenameRule):
    def __init__(self, pattern: str, replacement: str):
        self.pattern = pattern
        self.replacement = replacement

    def apply(self, filename: str, context: Dict[str, Any] = None) -> str:
        name, ext = os.path.splitext(filename)
        return f"{re.sub(self.pattern, self.replacement, name)}{ext}"

class CaseRule(RenameRule):
    def __init__(self, case_type: str):
        self.case_type = case_type

    def apply(self, filename: str, context: Dict[str, Any] = None) -> str:
        name, ext = os.path.splitext(filename)
        if self.case_type == "UPPERCASE":
            name = name.upper()
        elif self.case_type == "lowercase":
            name = name.lower()
        elif self.case_type == "Title Case":
            name = name.title()
        return f"{name}{ext}"

class NumberingRule(RenameRule):
    def __init__(self, start: int = 1, padding: int = 1, separator: str = "_"):
        self.start = start
        self.padding = padding
        self.separator = separator
        self._counter = start

    def apply(self, filename: str, context: Dict[str, Any] = None) -> str:
        name, ext = os.path.splitext(filename)
        number = str(self._counter).zfill(self.padding)
        self._counter += 1
        return f"{name}{self.separator}{number}{ext}"

    def reset(self):
        self._counter = self.start

class DateTimeRule(RenameRule):
    def __init__(self, format_str: str = "%Y%m%d_%H%M%S", position: str = "prefix"):
        self.format_str = format_str
        self.position = position

    def apply(self, filename: str, context: Dict[str, Any] = None) -> str:
        name, ext = os.path.splitext(filename)
        date_str = datetime.now().strftime(self.format_str)
        
        if self.position == "prefix":
            return f"{date_str}_{name}{ext}"
        else:
            return f"{name}_{date_str}{ext}"

class TextTransformRule(RenameRule):
    def __init__(self, prefix: str = "", suffix: str = "", 
                 find: str = "", replace: str = ""):
        self.prefix = prefix
        self.suffix = suffix
        self.find = find
        self.replace = replace

    def apply(self, filename: str, context: Dict[str, Any] = None) -> str:
        name, ext = os.path.splitext(filename)
        if self.find:
            name = name.replace(self.find, self.replace)
        return f"{self.prefix}{name}{self.suffix}{ext}"

class RenameEngine:
    def __init__(self):
        self.rules: List[RenameRule] = []
        self.context: Dict[str, Any] = {}

    def add_rule(self, rule: RenameRule) -> None:
        self.rules.append(rule)

    def clear_rules(self) -> None:
        self.rules.clear()
        self.context.clear()

    def set_context(self, key: str, value: Any) -> None:
        self.context[key] = value

    def process_filename(self, filename: str, dry_run: bool = False) -> Optional[str]:
        try:
            result = filename
            for rule in self.rules:
                if not rule.validate(result):
                    raise ValueError(f"Validation failed for rule {rule.__class__.__name__}")
                if not dry_run:
                    result = rule.apply(result, self.context)
            return result
        except Exception as e:
            raise RuntimeError(f"Error processing {filename}: {str(e)}")

    def process_batch(self, filenames: List[str], 
                     dry_run: bool = False) -> Dict[str, str]:
        results = {}
        for filename in filenames:
            try:
                new_name = self.process_filename(filename, dry_run)
                results[filename] = new_name
            except Exception as e:
                results[filename] = str(e)
        
        # Reset stateful rules like NumberingRule
        for rule in self.rules:
            if hasattr(rule, 'reset'):
                rule.reset()
                
        return results

    def validate_batch(self, filenames: List[str]) -> List[str]:
        """Validate a batch of filenames without applying changes"""
        errors = []
        seen_names = set()
        
        for filename in filenames:
            try:
                new_name = self.process_filename(filename, dry_run=True)
                if new_name in seen_names:
                    errors.append(f"Duplicate result: {new_name}")
                seen_names.add(new_name)
            except Exception as e:
                errors.append(str(e))
        
        return errors
