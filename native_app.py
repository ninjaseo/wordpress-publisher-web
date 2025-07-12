#!/usr/bin/env python3
"""
WordPress Publisher - Native macOS Application
Uses webview to create a native app wrapper around the web interface
"""
import webview
import threading
import sys
import os
import subprocess
import time
import signal
import tempfile
from pathlib import Path

class WordPressPublisherApp:
    def __init__(self):
        self.server_process = None
        self.server_port = 8001  # Use different port to avoid conflicts
        
    def start_server(self):
        """Start the FastAPI server in background"""
        try:
            # Change to backend directory
            backend_dir = Path(__file__).parent / "backend"
            os.chdir(backend_dir)
            
            # Add backend to Python path
            sys.path.insert(0, str(backend_dir))
            
            # Start uvicorn server
            import uvicorn
            uvicorn.run(
                "main:app",
                host="127.0.0.1",
                port=self.server_port,
                log_level="error",  # Reduce log noise
                access_log=False
            )
        except Exception as e:
            print(f"Error starting server: {e}")
    
    def create_native_file_dialog(self):
        """Add native file dialog functionality"""
        return """
        // Override the web app's directory change function
        if (typeof app !== 'undefined') {
            app.changeDirectoryNative = function() {
                pywebview.api.select_directory().then(function(result) {
                    if (result) {
                        // Update the backend with the new directory
                        fetch('/api/set-directory', {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({directory: result})
                        }).then(function() {
                            app.loadCurrentDirectory();
                            app.loadFiles();
                            app.showToast('Carpeta cambiada a: ' + result, 'success');
                        });
                    }
                });
            };
            
            // Override the original change directory function
            document.getElementById('change-directory-btn').onclick = function() {
                app.changeDirectoryNative();
            };
        }
        """
    
    def select_directory(self):
        """Native directory selection dialog"""
        try:
            result = webview.windows[0].create_file_dialog(
                webview.FOLDER_DIALOG,
                directory=str(Path.home() / "Documents"),
            )
            if result:
                return result[0]
            return None
        except Exception as e:
            print(f"Error in file dialog: {e}")
            return None
    
    def run(self):
        """Run the native application"""
        print("🚀 Starting WordPress Publisher...")
        
        # Start server in background thread
        server_thread = threading.Thread(target=self.start_server, daemon=True)
        server_thread.start()
        
        # Wait for server to start
        time.sleep(3)
        
        # Create webview window
        window = webview.create_window(
            title="WordPress Publisher",
            url=f"http://127.0.0.1:{self.server_port}",
            width=1200,
            height=800,
            min_size=(900, 600),
            resizable=True,
            maximized=False,
            on_top=False,
            shadow=True,
            js_api=self  # Expose Python methods to JavaScript
        )
        
        # Add native functionality
        webview.start(
            func=self.create_native_file_dialog,
            debug=False  # Set to True for development
        )

def main():
    """Main entry point"""
    app = WordPressPublisherApp()
    
    # Handle graceful shutdown
    def signal_handler(sig, frame):
        print("\n🛑 Shutting down...")
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n🛑 Application closed by user")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()