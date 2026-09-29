"""
WSGI config for backend project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/wsgi/
"""

import os
import threading
import time
import logging

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')

application = get_wsgi_application()

logger = logging.getLogger('talentsift.keepalive')

# ---------------------------------------------------------------------------
# Self-ping keep-alive — prevents Render free-tier from spinning down.
# Only runs when the RENDER environment variable is set (i.e. on Render).
# Uses RENDER_EXTERNAL_URL which Render injects automatically, so no
# hard-coded URLs are needed.
# ---------------------------------------------------------------------------
_PING_INTERVAL_SECONDS = 14 * 60  # 14 minutes (Render spins down after 15 min)


def _keep_alive():
    """Daemon thread: ping our own health_check endpoint every 14 minutes."""
    import requests  # imported here so local dev without requests still works

    # Wait for the server to be fully up before the first ping
    time.sleep(30)

    base_url = os.environ.get('RENDER_EXTERNAL_URL', '').rstrip('/')
    if not base_url:
        logger.warning('[KeepAlive] RENDER_EXTERNAL_URL not set — keep-alive disabled.')
        return

    ping_url = f'{base_url}/health_check/'
    logger.info('[KeepAlive] Keep-alive started. Pinging %s every %d minutes.', ping_url, _PING_INTERVAL_SECONDS // 60)

    while True:
        try:
            resp = requests.get(ping_url, timeout=10)
            logger.info('[KeepAlive] Ping OK — status=%s body=%s', resp.status_code, resp.text[:120])
        except Exception as exc:
            logger.warning('[KeepAlive] Ping failed: %s', exc)
        time.sleep(_PING_INTERVAL_SECONDS)


# Only start the keep-alive thread on Render (RENDER env var is set by Render)
if os.environ.get('RENDER'):
    _t = threading.Thread(target=_keep_alive, name='talentsift-keepalive', daemon=True)
    _t.start()
    logger.info('[KeepAlive] Keep-alive thread launched.')

