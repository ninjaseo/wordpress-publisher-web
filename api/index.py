"""
Vercel entry point for WordPress Publisher - Simplified version
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import os

# Create FastAPI app
app = FastAPI(title="WordPress Publisher")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get base directory
base_dir = Path(__file__).parent.parent

# Mount static files if they exist
static_path = base_dir / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Basic HTML template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WordPress Publisher</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            background: white;
            padding: 40px;
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2d3748;
            margin-bottom: 20px;
        }
        .status {
            background: #48bb78;
            color: white;
            padding: 10px 20px;
            border-radius: 8px;
            margin: 20px 0;
        }
        .info {
            background: #f7fafc;
            padding: 20px;
            border-radius: 8px;
            border-left: 4px solid #667eea;
            margin: 20px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🚀 WordPress Publisher</h1>
        <div class="status">✅ Aplicación desplegada exitosamente en Vercel</div>
        
        <div class="info">
            <h3>📁 Próximos pasos:</h3>
            <p>Esta es la versión web simplificada de WordPress Publisher.</p>
            <p>Para usar la aplicación completa, ejecuta el código localmente:</p>
            <pre>cd web-app/backend && python main.py</pre>
        </div>
        
        <div class="info">
            <h3>🔗 Enlaces útiles:</h3>
            <ul>
                <li><a href="/api/health">Health Check</a></li>
                <li><a href="https://github.com/ninjaseo/wordpress-publisher-web">Código en GitHub</a></li>
            </ul>
        </div>
    </div>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Serve the main application page"""
    return HTMLResponse(content=HTML_TEMPLATE)

@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse({
        "status": "ok",
        "message": "WordPress Publisher API is running",
        "version": "1.0.0",
        "deployment": "vercel"
    })

@app.get("/api/info")
async def info():
    """App information"""
    return JSONResponse({
        "app": "WordPress Publisher",
        "status": "deployed",
        "platform": "vercel",
        "note": "This is a simplified web version. For full functionality, run locally."
    })

# Export app for Vercel
handler = app