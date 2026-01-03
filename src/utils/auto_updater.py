import requests
import webbrowser
from packaging import version
from src.config.constants import CURRENT_VERSION, GITHUB_REPO_OWNER, GITHUB_REPO_NAME

class AutoUpdater:
    """Manejador de actualizaciones desde GitHub Releases"""
    
    def __init__(self):
        self.api_url = f"https://api.github.com/repos/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/releases/latest"

    def check_for_updates(self):
        """
        Consulta la API de GitHub para ver si hay una versión más reciente.
        Retorna: (hay_actualizacion: bool, info: dict/str)
        """
        try:
            response = requests.get(self.api_url, timeout=5)
            response.raise_for_status()
            
            data = response.json()
            latest_tag = data.get("tag_name", "v0.0.0")
            
            # Limpiar la 'v' si existe para comparar números puros si es necesario,
            # pero packaging.version maneja 'v1.4.0' correctamente.
            current_v = version.parse(CURRENT_VERSION)
            latest_v = version.parse(latest_tag)
            
            if latest_v > current_v:
                return True, {
                    "version": latest_tag,
                    "url": data.get("html_url", ""),
                    "body": data.get("body", "")
                }
            else:
                return False, CURRENT_VERSION
                
        except Exception as e:
            return False, str(e)

    def open_download_page(self, url):
        """Abre la página de la release en el navegador predeterminado"""
        if url:
            webbrowser.open(url)