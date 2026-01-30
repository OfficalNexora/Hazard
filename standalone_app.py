import webview
import sys
import os

def launch():
    url = "http://localhost:3000"
    if len(sys.argv) > 1:
        url = sys.argv[1]
        
    print(f"Launching Standalone Mission Control at {url}")
    
    # Create window with optimized settings
    window = webview.create_window(
        'Nexora Mission Control', 
        url,
        width=1280,
        height=800,
        min_size=(1024, 768),
        background_color='#09090b' # Match zinc-950
    )
    
    # Start the engine
    # gui='edgechromium' ensures we use the modern Edge engine on Windows
    webview.start(gui='edgechromium', debug=False)

if __name__ == "__main__":
    launch()
