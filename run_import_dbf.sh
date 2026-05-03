#!/usr/bin/env bash
# =============================================================================
# run_import_dbf.sh
# Standalone launcher for import_stock_dbf.py
#
# Usage:
#   ./run_import_dbf.sh STOCK.DBF
#   ./run_import_dbf.sh STOCK.DBF --db /path/to/products.db
#
# Run this independently of the main POS application.
# The POS app must have been started at least once so that
# storedata/products.db exists before running this.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMPORT_SCRIPT="$SCRIPT_DIR/import_stock_dbf.py"
DEFAULT_DB="$SCRIPT_DIR/storedata/products.db"

# Colour output
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; NC='\033[0m'

echo -e "${CYAN}"
echo "  ┌─────────────────────────────────────────┐"
echo "  │   Merchant POS — DBF Stock Importer     │"
echo "  └─────────────────────────────────────────┘"
echo -e "${NC}"

# Check Python
if ! command -v python3 &>/dev/null; then
    echo -e "${RED}Error: python3 not found. Install Python 3.9+${NC}"
    exit 1
fi

# Check import script exists
if [ ! -f "$IMPORT_SCRIPT" ]; then
    echo -e "${RED}Error: import_stock_dbf.py not found at $IMPORT_SCRIPT${NC}"
    exit 1
fi

# Show help if no args
if [ $# -eq 0 ]; then
    echo -e "${YELLOW}Usage:${NC}"
    echo "  $0 STOCK.DBF"
    echo "  $0 STOCK.DBF --db /path/to/storedata/products.db"
    echo ""
    echo -e "${YELLOW}Default DB path:${NC} $DEFAULT_DB"
    echo ""
    echo "The POS system must have been launched at least once"
    echo "to create the products.db database before importing."
    exit 0
fi

DBF_FILE="$1"
shift

# Check DBF file exists
if [ ! -f "$DBF_FILE" ]; then
    echo -e "${RED}Error: DBF file not found: $DBF_FILE${NC}"
    exit 1
fi

# Check products.db exists (unless --db override given)
DB_OVERRIDE=""
for arg in "$@"; do
    case "$arg" in
        --db) DB_OVERRIDE="next" ;;
        *)    [ "$DB_OVERRIDE" = "next" ] && DB_OVERRIDE="$arg" ;;
    esac
done

if [ -z "$DB_OVERRIDE" ]; then
    if [ ! -f "$DEFAULT_DB" ]; then
        echo -e "${RED}Error: products.db not found at $DEFAULT_DB${NC}"
        echo ""
        echo "Please launch the POS system at least once to create the"
        echo "database, then run this import script."
        exit 1
    fi
fi

echo -e "${GREEN}Starting import...${NC}"
echo ""

# Run the importer
python3 "$IMPORT_SCRIPT" "$DBF_FILE" "$@"

EXIT_CODE=$?
if [ $EXIT_CODE -eq 0 ]; then
    echo -e "\n${GREEN}Import completed successfully.${NC}"
else
    echo -e "\n${RED}Import failed with exit code $EXIT_CODE.${NC}"
fi
exit $EXIT_CODE
