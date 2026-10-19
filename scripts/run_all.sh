set -euo pipefail
cd "$(dirname "$0")/.."
(cd src && python -m geoasset.pipeline "$@")
echo "Peta: http://localhost:8000"
cd web && python -m http.server 8000
