"""Celery settings for the MAAS project."""

# Broken connection information.
# Format: transport://userid:password@hostname:port/virtual_host
BROKER_URL = 'amqp://guest:guest@localhost:5672//'
