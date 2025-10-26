import os
import shutil

def clear_cache():
    print("=== Clearing Cache and Old Data ===")
    
    # Clear browser cache (if possible)
    print("1. Clearing browser cache...")
    print("   Please clear your browser cache manually:")
    print("   - Chrome: Ctrl+Shift+Delete")
    print("   - Firefox: Ctrl+Shift+Delete")
    print("   - Edge: Ctrl+Shift+Delete")
    
    # Clear static uploads (optional)
    uploads_dir = os.path.join('backend', 'static', 'uploads')
    if os.path.exists(uploads_dir):
        print(f"2. Found uploads directory: {uploads_dir}")
        files = os.listdir(uploads_dir)
        print(f"   Found {len(files)} files")
        
        # List files with inemi.id URLs
        old_files = []
        for file in files:
            if file.startswith(('fusigaya_', 'face_swap_')):
                old_files.append(file)
        
        if old_files:
            print(f"   Found {len(old_files)} old files:")
            for file in old_files:
                print(f"     - {file}")
            
            choice = input("   Delete old files? (y/n): ").lower()
            if choice == 'y':
                for file in old_files:
                    filepath = os.path.join(uploads_dir, file)
                    try:
                        os.remove(filepath)
                        print(f"     ✓ Deleted: {file}")
                    except Exception as e:
                        print(f"     ✗ Error deleting {file}: {e}")
        else:
            print("   No old files found")
    else:
        print("2. Uploads directory not found")
    
    print("\n3. Recommendations:")
    print("   - Restart Flask server")
    print("   - Clear browser cache")
    print("   - Upload new images (don't reuse old ones)")
    print("   - Check that new URLs use ngrok domain")

if __name__ == "__main__":
    clear_cache() 