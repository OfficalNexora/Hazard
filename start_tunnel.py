import subprocess
import re
import time
import os
import json

def start_cloudflare_tunnel(port=8000):
    """
    Starts a Cloudflared Quick Tunnel and 'leaks' the URL to a local file.
    The ESP32 can then be provisioned with this URL.
    """
    print(f"[Tunnel] Starting Cloudflared tunnel on port {port}...")
    
    # Delete stale URL to prevent devices from using dead tunnels
    if os.path.exists("tunnel_url.txt"):
        os.remove("tunnel_url.txt")
    
    # Run cloudflared tunnel
    # Note: Requires cloudflared installed on the system
    try:
        process = subprocess.Popen(
            ["cloudflared", "tunnel", "--url", f"http://localhost:{port}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        
        tunnel_url = None
        for line in process.stdout:
            print(f"[Cloudflared] {line.strip()}")
            # Look for the .trycloudflare.com URL
            match = re.search(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com", line)
            if match:
                tunnel_url = match.group(0)
                print(f"\n[!!!] TUNNEL READY: {tunnel_url}")
                print(f"[!!!] USE THIS URL IN YOUR ESP32 PROVISIONING\n")
                
                # 'Leak' the URL to a file for the backend/frontend to pick up
                with open("tunnel_url.txt", "w") as f:
                    f.write(tunnel_url)
                
                # Also save to config.json if it exists
                if os.path.exists("config.json"):
                    try:
                        with open("config.json", "r") as f:
                            config = json.load(f)
                        config["public_url"] = tunnel_url
                        with open("config.json", "w") as f:
                            json.dump(config, f, indent=4)
                    except:
                        pass
                
        process.wait()
    except FileNotFoundError:
        print("[Error] 'cloudflared' not found. Please install it from https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/install-cloudflare-tunnel/")
    except KeyboardInterrupt:
        print("[Tunnel] Stopping...")

if __name__ == "__main__":
    start_cloudflare_tunnel()
