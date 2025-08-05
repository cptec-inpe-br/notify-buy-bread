#!/bin/bash
export PYTHONPATH=/app
exec supervisord -c /app/supervisord.conf