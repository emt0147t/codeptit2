import subprocess
import sys
import time
import os

def start_server_and_tunnel():
    print("Khởi động Online Judge System...")
    
    # Start the web server in the background
    server_process = subprocess.Popen(
        [sys.executable, "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    
    print(" Đang chạy server nội bộ (chờ 3 giây)...")
    time.sleep(3) # Wait a bit for server to start
    
    # Check if server is running
    if server_process.poll() is not None:
        print(" Lỗi: Không thể khởi động server.")
        return
        
    print(" Đã khởi động server thành công.")
    print("Khởi động Cloudflare Tunnel...")
    
    try:
        # Run the tunnel process and attach to current console
        tunnel_process = subprocess.Popen(
            [sys.executable, "tunnel.py"]
        )
        tunnel_process.wait()
    except KeyboardInterrupt:
        print("\n Đang tắt hệ thống...")
    finally:
        # Ensure we kill the server when tunnel exits
        print(" Đang dừng server nội bộ...")
        server_process.terminate()
        server_process.wait()
        print(" Hệ thống đã tắt hoàn toàn.")

if __name__ == "__main__":
    start_server_and_tunnel()
