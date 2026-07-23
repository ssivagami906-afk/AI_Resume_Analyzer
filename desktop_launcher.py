import os
import sys
import time
import socket
import urllib.request
import subprocess

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def is_server_running(url="http://127.0.0.1:8501"):
    try:
        response = urllib.request.urlopen(url, timeout=2)
        return response.status in (200, 304, 404)
    except Exception:
        return False

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    local_ip = get_local_ip()
    print("=" * 65)
    print(" 👔 AI RESUME ANALYZER LAUNCHER")
    print("=" * 65)
    print(f" 💻 PC Local Browser URL:    http://localhost:8501")
    print(f" 📱 Mobile App Connection IP: http://{local_ip}:8501")
    print("=" * 65)
    print(" 📌 INSTRUCTIONS FOR MOBILE APP / மொபைல் ஆப் அறிவுறுத்தல்கள்:")
    print(f" 1. Open the App on Mobile.")
    print(f" 2. Enter this IP: http://{local_ip}:8501")
    print(f" 3. Click 'Connect / இணைக்கவும்'.")
    print("=" * 65)

    # 1. Start Streamlit server if not running
    if not is_server_running():
        print("Starting AI Resume Analyzer server (bound to 0.0.0.0:8501)...")
        subprocess.Popen(
            [
                sys.executable, "-m", "streamlit", "run", "app.py",
                "--server.headless=true",
                "--server.address=0.0.0.0",
                "--server.port=8501"
            ],
            cwd=script_dir,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
        # Wait for server to launch
        for _ in range(15):
            time.sleep(1)
            if is_server_running():
                print("Server is ready!")
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
