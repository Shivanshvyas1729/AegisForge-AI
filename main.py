import os
import sys
import webview

# Ensure pywebview is installed. If not, this will fail.
try:
    import webview
except ImportError:
    print("Error: pywebview is not installed. Please install it with 'pip install pywebview'.")
    sys.exit(1)

from api_bridge import APIBridge

def main():
    api = APIBridge()
    
    # Path to the frontend html
    html_path = os.path.join(os.path.dirname(__file__), 'frontend', 'index.html')
    
    # Create the window
    window = webview.create_window(
        title='AegisForge AI Agent',
        url=f'file://{os.path.abspath(html_path)}',
        js_api=api,
        width=1000,
        height=700,
        min_size=(800, 600),
        background_color='#0f172a'
    )
    
    # Pass the window instance to the API bridge so it can call JS functions
    api.set_window(window)
    
    # Start the application loop
    webview.start(debug=True)

if __name__ == '__main__':
    main()
