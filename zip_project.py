import os
import zipfile
import datetime

# Exclude these bulky or unnecessary directories
EXCLUDE_DIRS = {
    '.venv', 
    'node_modules', 
    '__pycache__', 
    '.git', 
    '.vscode',
    'dist',
    'build',
    '.gemini'
}

# Exclude these file extensions or specific files
EXCLUDE_FILES = {
    '.DS_Store',
    'signbridge-v4-export.zip',
    'zip_project.py'
}

def create_zip():
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_filename = f"signbridge_v4_{timestamp}.zip"
    zip_path = os.path.join(project_root, zip_filename)
    
    print(f"Creating {zip_filename}...")
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(project_root):
            # Mutate the dirs list in-place to prevent os.walk from descending into excluded directories
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
            
            for file in files:
                if file in EXCLUDE_FILES or file.endswith('.zip'):
                    continue
                
                file_path = os.path.join(root, file)
                # Determine the relative path to preserve directory structure in the zip
                arcname = os.path.relpath(file_path, project_root)
                
                zipf.write(file_path, arcname)
                
    print(f"Done! Created: {zip_path}")
    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"Size: {size_mb:.2f} MB")

if __name__ == "__main__":
    create_zip()
