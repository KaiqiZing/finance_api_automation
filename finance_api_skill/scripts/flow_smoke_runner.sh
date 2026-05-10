#!/usr/bin/env bash
set -euo pipefail

# Run the system business-flow smoke suite.
# Execute from the repository root:
#   bash finance_api_skill/scripts/flow_smoke_runner.sh

python3 run.py --env test --mark scenario -n 1
