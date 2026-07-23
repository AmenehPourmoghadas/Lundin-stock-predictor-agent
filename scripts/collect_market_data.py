name: Collect Market Data

on:
  workflow_dispatch:
  schedule:
    - cron: "0 7 * * *"

permissions:
  contents: write

jobs:
  collect-market-data:
    name: Collect market data and send chart
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          ref: main
          fetch-depth: 0

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip

      - name: Install dependencies
        shell: bash
        run: |
          set -euo pipefail
          python -m pip install --upgrade pip
          python -m pip install -r requirements.txt

      - name: Collect market data and generate chart
        shell: bash
        run: |
          set -euo pipefail
          python scripts/collect_market_data.py

      - name: Validate generated files
        shell: bash
        run: |
          set -euo pipefail

          test -s data/market_data.json
          test -s data/market_data.png

          echo "Generated files:"
          ls -lh data/market_data.json data/market_data.png

      - name: Commit and push generated files
        id: commit
        shell: bash
        run: |
          set -euo pipefail

          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

          git add data/market_data.json data/market_data.png

          if git diff --cached --quiet; then
            echo "No market-data changes to commit."
            echo "committed=false" >> "${GITHUB_OUTPUT}"
          else
            git commit -m "data: update market snapshot"
            git push origin HEAD:main
            echo "committed=true" >> "${GITHUB_OUTPUT}"
          fi

      - name: Send chart link by WhatsApp
        shell: bash
        env:
          WHATSAPP_PHONE: ${{ secrets.WHATSAPP_PHONE }}
          CALLMEBOT_API_KEY: ${{ secrets.CALLMEBOT_API_KEY }}
          CHART_URL: https://raw.githubusercontent.com/${{ github.repository }}/main/data/market_data.png
        run: |
          set -euo pipefail

          python - <<'PY'
          import os

          from lundin_agent.whatsapp import send_callmebot

          phone = os.environ["WHATSAPP_PHONE"]
          api_key = os.environ["CALLMEBOT_API_KEY"]
          chart_url = os.environ["CHART_URL"]

          message = f"Lundin market chart:\n{chart_url}"

          send_callmebot(
              message=message,
              phone=phone,
              api_key=api_key,
          )
          PY