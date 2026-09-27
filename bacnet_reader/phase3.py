"""Presentation assets and future capabilities; no control implementation."""
from pathlib import Path

ZONE_CAPABILITIES = {
    name: {'monitoring': True, 'control_ready': name in ('Grande Salle', 'Petite Salle'),
           'control_enabled': False, 'write_enabled': False}
    for name in ('Grande Salle', 'Petite Salle', 'Communs', 'Bureaux administratifs',
                 'CTA', 'Chaufferie', 'ECS', 'Comptages')
}

# Exact allowlist: never interpret a URL as a filesystem path.
ASSETS = {
    '/': ('exploitation.html', 'text/html; charset=utf-8'),
    '/exploitation.html': ('exploitation.html', 'text/html; charset=utf-8'),
    '/technical': ('mct.html', 'text/html; charset=utf-8'),
    '/mct.html': ('mct.html', 'text/html; charset=utf-8'),
    '/exploitation.css': ('exploitation.css', 'text/css; charset=utf-8'),
    '/exploitation.js': ('exploitation.js', 'text/javascript; charset=utf-8'),
    '/presentation.js': ('presentation.js', 'text/javascript; charset=utf-8'),
    '/assets/MCT_Logo_Ver_Blanc.png': ('assets/MCT_Logo_Ver_Blanc.png', 'image/png'),
    '/assets/batiment.jpg': ('assets/batiment.jpg', 'image/jpeg'),
    '/assets/grande-salle.jpeg': ('assets/grande-salle.jpeg', 'image/jpeg'),
    '/assets/petite-salle.jpg': ('assets/petite-salle.jpg', 'image/jpeg'),
}

def asset(path):
    entry = ASSETS.get(path)
    if entry is None:
        return None
    filename, mime = entry
    return mime, Path(__file__).parent.joinpath(filename).read_bytes()
