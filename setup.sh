#!/usr/bin/env bash
# Set up the Alcohol Briefing environment.
set -e

cd "$(dirname "$0")"

echo "==> Creating virtualenv (.venv)"
python3 -m venv .venv
source .venv/bin/activate

echo "==> Upgrading pip"
pip install --upgrade pip >/dev/null

echo "==> Installing requirements"
pip install -r requirements.txt

if [ ! -f .env ]; then
  echo "==> Creating .env from template"
  cp .env.example .env
  echo "    Edit .env and add your API keys."
fi

mkdir -p assets output

echo ""
echo "Setup complete. Next:"
echo "  1) edit .env with your keys"
echo "  2) cp your-logo.png assets/logo.png   (optional)"
echo "  3) source .venv/bin/activate && python main.py"
