import os
import shutil
import logging
from typing import List, Tuple, Dict
from pathlib import Path

class FileOperationError(Exception):
    """Custom exception for file operation errors"""
    pass

def validate_new_names(files: List[str], new_names: List[str]) -> List[str]:
    """
    Validate new filenames for potential issues.
    Returns list of error messages (empty if all valid).
    """
    errors = []
    used_names = set()
    
    for original, new_name in zip(files, new_names):
        # Check for empty names
        if not new_name:
            errors.append(f"Empty filename for {original}")
            
        # Check for invalid characters
        invalid_chars = '<>:"/\\|?*'
        if any(char in new_name for char in invalid_chars):
            errors.append(f"Invalid characters in {new_name}")
            
        # Check for duplicates
        if new_name in used_names:
            errors.append(f"Duplicate filename: {new_name}")
        used_names.add(new_name)
        
        # Check if target exists (different from source)
        target_path = os.path.join(os.path.dirname(original), new_name)
        if os.path.exists(target_path) and target_path != original:
            errors.append(f"Target file already exists: {new_name}")
    
    return errors

def preview_renames(files: List[str], new_names: List[str]) -> List[Tuple[str, str]]:
    """
    Preview rename operations without executing them.
    Returns list of (source, destination) pairs.
    """
    operations = []
    for original, new_name in zip(files, new_names):
        source_dir = os.path.dirname(original)
        dest_path = os.path.join(source_dir, new_name)
        operations.append((original, dest_path))
    return operations

def rename_files(files: List[str], new_names: List[str], dry_run: bool = False) -> Dict[str, str]:
    """
    Rename files with error handling and logging.
    Returns dict of results with status messages.
    """
    results = {}
    
    # Validate before proceeding
    errors = validate_new_names(files, new_names)
    if errors:
        raise FileOperationError("\n".join(errors))

    operations = preview_renames(files, new_names)
    
    # Return preview if dry run
    if dry_run:
        return {src: f"Will rename to: {dst}" for src, dst in operations}

    # Perform actual renames
    for source, dest in operations:
        try:
            # Create backup name in case of conflicts
            backup_name = None
            if os.path.exists(dest):
                backup_name = dest + ".bak"
                shutil.move(dest, backup_name)
            
            # Perform rename
            shutil.move(source, dest)
            
            # Remove backup if everything succeeded
            if backup_name and os.path.exists(backup_name):
                os.remove(backup_name)
                
            results[source] = f"Successfully renamed to: {os.path.basename(dest)}"
            logging.info(f"Renamed: {source} -> {dest}")
            
        except Exception as e:
            # Restore from backup if available
            if backup_name and os.path.exists(backup_name):
                shutil.move(backup_name, dest)
            
            error_msg = f"Failed to rename: {str(e)}"
            results[source] = error_msg
            logging.error(f"Rename failed for {source}: {str(e)}")
            
    return results

def undo_rename(original_path: str, current_path: str) -> bool:
    """
    Attempt to undo a rename operation.
    Returns True if successful, False otherwise.
    """
    try:
        if os.path.exists(current_path) and not os.path.exists(original_path):
            shutil.move(current_path, original_path)
            logging.info(f"Undid rename: {current_path} -> {original_path}")
            return True
    except Exception as e:
        logging.error(f"Failed to undo rename: {str(e)}")
        return False
    return False

def get_safe_filename(filename: str) -> str:
    """
    Convert filename to a safe version by removing/replacing unsafe characters.
    """
    unsafe_chars = '<>:"/\\|?*'
    for char in unsafe_chars:
        filename = filename.replace(char, '_')
    return filename.strip()
