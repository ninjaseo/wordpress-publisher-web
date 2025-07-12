#!/usr/bin/env python3
"""
WordPress Publisher - Improved Native macOS Application
Separates server and webview to prevent threading issues
"""
import webview
import threading
import subprocess
import sys
import os
import time
import signal
import psutil
import socket
from pathlib import Path
import atexit

class WordPressPublisherApp:
    def __init__(self):
        self.server_process = None
        self.server_port = 8001
        self.max_retries = 30
        self.backend_dir = Path(__file__).parent / "backend"
        
    def find_free_port(self):
        """Find a free port to avoid conflicts"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port
    
    def is_server_running(self):
        """Check if server is responding"""
        try:
            import urllib.request
            response = urllib.request.urlopen(f"http://127.0.0.1:{self.server_port}/api/health", timeout=2)
            return response.status == 200
        except:
            return False
    
    def start_server_process(self):
        """Start FastAPI server as separate process"""
        try:
            # Find a free port
            self.server_port = self.find_free_port()
            
            print(f"🚀 Starting server on port {self.server_port}...")
            
            # Prepare server command
            python_exe = sys.executable
            server_script = self.backend_dir / "main.py"
            
            # Create startup script
            startup_code = f'''
import sys
import os
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent
sys.path.insert(0, str(backend_dir))
os.chdir(backend_dir)

# Start server
import uvicorn
uvicorn.run(
    "main:app",
    host="127.0.0.1",
    port={self.server_port},
    log_level="error",
    access_log=False
)
'''
            
            # Write temporary server launcher
            temp_server = self.backend_dir / "temp_server.py"
            with open(temp_server, 'w') as f:
                f.write(startup_code)
            
            # Start server process
            self.server_process = subprocess.Popen(
                [python_exe, str(temp_server)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid  # Create new process group
            )
            
            # Wait for server to start
            print("⏳ Waiting for server to start...")
            for attempt in range(self.max_retries):
                if self.is_server_running():
                    print("✅ Server started successfully!")
                    return True
                time.sleep(0.5)
            
            print("❌ Server failed to start")
            return False
            
        except Exception as e:
            print(f"❌ Error starting server: {e}")
            return False
    
    def stop_server_process(self):
        """Stop the server process cleanly"""
        if self.server_process:
            try:
                # Terminate the entire process group
                os.killpg(os.getpgid(self.server_process.pid), signal.SIGTERM)
                self.server_process.wait(timeout=5)
            except:
                try:
                    # Force kill if needed
                    os.killpg(os.getpgid(self.server_process.pid), signal.SIGKILL)
                except:
                    pass
            
            self.server_process = None
            
        # Clean up temp file
        temp_file = self.backend_dir / "temp_server.py"
        if temp_file.exists():
            temp_file.unlink()
    
    def create_webview_api(self):
        """Create API functions for webview"""
        def select_directory():
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
        
        # Return API object
        class WebViewAPI:
            def __init__(self):
                self.select_directory = select_directory
        
        return WebViewAPI()
    
    def inject_native_functionality(self):
        """Inject native functionality into the web page"""
        js_code = """
        // Wait for app to be ready
        function waitForApp() {
            if (typeof app !== 'undefined' && app.changeDirectory) {
                // Override the web app's directory change function
                app.changeDirectoryNative = function() {
                    pywebview.api.select_directory().then(function(result) {
                        if (result) {
                            // Update the backend with the new directory
                            fetch('/api/set-directory', {
                                method: 'POST',
                                headers: {'Content-Type': 'application/json'},
                                body: JSON.stringify({directory: result})
                            }).then(function(response) {
                                return response.json();
                            }).then(function(data) {
                                if (data.success) {
                                    app.loadCurrentDirectory();
                                    app.loadFiles();
                                    app.showToast('Carpeta cambiada a: ' + result, 'success');
                                }
                            }).catch(function(error) {
                                console.error('Error setting directory:', error);
                                app.showToast('Error cambiando carpeta', 'error');
                            });
                        }
                    }).catch(function(error) {
                        console.error('Error selecting directory:', error);
                    });
                };
                
                // Override the original change directory button
                const changeDirBtn = document.getElementById('change-directory-btn');
                if (changeDirBtn) {
                    changeDirBtn.onclick = function() {
                        app.changeDirectoryNative();
                    };
                }
                
                console.log('✅ Native functionality injected');
            } else {
                // Retry after a short delay
                setTimeout(waitForApp, 500);
            }
        }
        
        // Start waiting for app
        waitForApp();
        """
        
        return js_code
    
    def run(self):
        """Run the native application"""
        print("🚀 Starting WordPress Publisher Native App...")
        
        # Register cleanup function
        atexit.register(self.stop_server_process)
        
        # Start server in separate process
        if not self.start_server_process():
            print("❌ Failed to start server. Exiting.")
            return
        
        try:
            # Create webview window
            print("🖥️  Creating native window...")
            
            # Create API for webview
            api = self.create_webview_api()
            
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
                js_api=api
            )
            
            # Start webview with injected functionality
            webview.start(
                func=self.inject_native_functionality,
                debug=False  # Set to True for development
            )
            
        except Exception as e:
            print(f"❌ Error running app: {e}")
        finally:
            # Ensure server is stopped
            self.stop_server_process()

def main():
    """Main entry point"""
    app = WordPressPublisherApp()
    
    # Handle graceful shutdown
    def signal_handler(sig, frame):
        print("\n🛑 Shutting down...")
        app.stop_server_process()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        app.run()
    except KeyboardInterrupt:
        print("\n🛑 Application closed by user")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        app.stop_server_process()

if __name__ == "__main__":
    main()