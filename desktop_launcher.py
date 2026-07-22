import os
import sys
import time
import urllib.request
import subprocess

def is_server_running(url="http://localhost:8501"):
    try:
        response = urllib.request.urlopen(url, timeout=2)
        return response.status == 200
    except Exception:
        return False

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # 1. Start Streamlit server if not running
    if not is_server_running():
        print("Starting AI Resume Analyzer server...")
        subprocess.Popen(
            [sys.executable, "-m", "streamlit", "run", "app.py", "--server.headless=true"],
            cwd=script_dir,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        # Wait for server to launch
        for _ in range(15):
            time.sleep(1)
            if is_server_running():
                break

    # 2. Launch App Window using Edge in --app mode (Native Desktop Experience)
    app_url = "http://localhost:8501"
    edge_paths = [
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
    ]
    
    edge_bin = None
    for path in edge_paths:
        if os.path.exists(path):
            edge_bin = path
            break

    if edge_bin:
        print("Opening native app window...")
        subprocess.Popen([edge_bin, f"--app={app_url}", "--name=AI Resume Analyzer"])
    else:
        print("Opening default browser...")
        import webbrowser
        webbrowser.open(app_url)

if __name__ == "__main__":
    main()
