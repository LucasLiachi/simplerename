import json
import csv
import os
from typing import Dict, List, Any
from datetime import datetime
from pathlib import Path

class ConfigManager:
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            config_dir = os.path.join(str(Path.home()), '.simplerename')
        self.config_dir = config_dir
        self.config_file = os.path.join(config_dir, 'config.json')
        self._ensure_config_dir()

    def _ensure_config_dir(self) -> None:
        """Create configuration directory if it doesn't exist"""
        if not os.path.exists(self.config_dir):
            os.makedirs(self.config_dir)

    def save_config(self, config: Dict[str, Any], name: str = "default") -> None:
        """Save a renaming configuration"""
        try:
            configs = self.load_all_configs()
            configs[name] = {
                'config': config,
                'timestamp': datetime.now().isoformat()
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(configs, f, indent=2)
        except Exception as e:
            raise RuntimeError(f"Failed to save configuration: {str(e)}")

    def load_config(self, name: str = "default") -> Dict[str, Any]:
        """Load a specific configuration by name"""
        configs = self.load_all_configs()
        if name in configs:
            return configs[name]['config']
        return {}

    def load_all_configs(self) -> Dict[str, Any]:
        """Load all saved configurations"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                return {}
        return {}

    def delete_config(self, name: str) -> bool:
        """Delete a specific configuration"""
        configs = self.load_all_configs()
        if name in configs:
            del configs[name]
            with open(self.config_file, 'w') as f:
                json.dump(configs, f, indent=2)
            return True
        return False

    def export_rename_list(self, rename_pairs: List[tuple], 
                          output_path: str = None) -> str:
        """Export list of renamed files to CSV"""
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(self.config_dir, f'rename_list_{timestamp}.csv')

        try:
            with open(output_path, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['Original Name', 'New Name'])
                writer.writerows(rename_pairs)
            return output_path
        except Exception as e:
            raise RuntimeError(f"Failed to export rename list: {str(e)}")

    def import_rename_list(self, file_path: str) -> List[tuple]:
        """Import list of renamed files from CSV"""
        try:
            with open(file_path, 'r', newline='') as f:
                reader = csv.reader(f)
                next(reader)  # Skip header row
                return list(reader)
        except Exception as e:
            raise RuntimeError(f"Failed to import rename list: {str(e)}")
