#!/usr/bin/env python3
"""
Quick fix to comment out all User relationships causing circular import issues
"""
import os
from pathlib import Path

def fix_relationships():
    """Comment out User relationships in all model files"""
    model_files = [
        "app/models/ai_analysis.py",
        "app/models/performance_metric.py", 
        "app/models/approval_workflow.py",
        "app/models/quality_issue.py"
    ]
    
    for file_path in model_files:
        if os.path.exists(file_path):
            print(f"Fixing {file_path}...")
            
            with open(file_path, 'r') as f:
                content = f.read()
            
            # Comment out User relationships
            lines = content.split('\n')
            fixed_lines = []
            
            for line in lines:
                if 'relationship("User"' in line:
                    fixed_lines.append("    # " + line.strip() + "  # Disabled to avoid circular imports")
                else:
                    fixed_lines.append(line)
            
            with open(file_path, 'w') as f:
                f.write('\n'.join(fixed_lines))
            
            print(f"  ✅ Fixed {file_path}")
    
    print("✅ All relationship fixes applied!")

if __name__ == "__main__":
    fix_relationships()