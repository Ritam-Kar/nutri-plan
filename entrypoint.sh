#!/bin/bash
cd /app
exec adk web --host 0.0.0.0 --port 8080 --allow_origins="*" --session_service_uri memory:// --artifact_service_uri memory:// /app