#!/bin/bash
# ═══════════════════════════════════════════════════════
#  FetchBot — EC2 Production Deploy Script
#  Run on a fresh Ubuntu 22.04 EC2 instance
# ═══════════════════════════════════════════════════════

set -euo pipefail

BLUE='\033[0;34m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'
BOLD='\033[1m'

echo ""
echo -e "${BLUE}${BOLD}  ╔══════════════════════════════════════╗${NC}"
echo -e "${BLUE}${BOLD}  ║     🤖 FetchBot Production Deploy    ║${NC}"
echo -e "${BLUE}${BOLD}  ╚══════════════════════════════════════╝${NC}"
echo ""

APP_DIR="/opt/fetchbot"
REPO_URL="${REPO_URL:-}"

# ── Step 1: System updates ──
echo -e "${YELLOW}▸ [1/7] Updating system...${NC}"
sudo apt-get update -qq
sudo apt-get upgrade -y -qq

# ── Step 2: Create swap (critical for t3.small) ──
echo -e "${YELLOW}▸ [2/7] Setting up swap space...${NC}"
if [ ! -f /swapfile ]; then
    sudo fallocate -l 2G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab > /dev/null
    # Optimize swap behavior for low-memory servers
    echo 'vm.swappiness=10' | sudo tee -a /etc/sysctl.conf > /dev/null
    sudo sysctl -p > /dev/null
    echo -e "${GREEN}  ✓ 2GB swap created (swappiness=10)${NC}"
else
    echo -e "${GREEN}  ✓ Swap already exists${NC}"
fi

# ── Step 3: Install Docker ──
echo -e "${YELLOW}▸ [3/7] Installing Docker...${NC}"
if ! command -v docker &>/dev/null; then
    curl -fsSL https://get.docker.com | sudo sh
    sudo usermod -aG docker "$USER"
    echo -e "${GREEN}  ✓ Docker installed${NC}"
    echo -e "${YELLOW}    NOTE: You may need to log out and back in for docker group${NC}"
else
    echo -e "${GREEN}  ✓ Docker already installed${NC}"
fi

# ── Step 4: Clone or pull repo ──
echo -e "${YELLOW}▸ [4/7] Setting up application...${NC}"
if [ -d "$APP_DIR" ]; then
    cd "$APP_DIR/ftb-api-26"
    git pull origin main
    echo -e "${GREEN}  ✓ Pulled latest code${NC}"
else
    if [ -z "$REPO_URL" ]; then
        echo -e "${RED}  ✗ REPO_URL not set. Run with: REPO_URL=git@github.com:you/repo.git bash deploy.sh${NC}"
        exit 1
    fi
    sudo mkdir -p "$APP_DIR"
    sudo chown "$USER:$USER" "$APP_DIR"
    git clone "$REPO_URL" "$APP_DIR"
    cd "$APP_DIR/ftb-api-26"
    echo -e "${GREEN}  ✓ Repository cloned${NC}"
fi

# ── Step 5: Check .env.prod ──
echo -e "${YELLOW}▸ [5/7] Checking environment config...${NC}"
if [ ! -f .env.prod ]; then
    cp .env.prod.example .env.prod
    echo -e "${RED}  ⚠ Created .env.prod from template — EDIT IT NOW before continuing!${NC}"
    echo -e "${RED}    nano $APP_DIR/ftb-api-26/.env.prod${NC}"
    echo -e "${RED}    Then re-run this script.${NC}"
    exit 1
else
    echo -e "${GREEN}  ✓ .env.prod found${NC}"
fi

# ── Step 6: Build and start containers ──
echo -e "${YELLOW}▸ [6/7] Building and starting containers...${NC}"
cd "$APP_DIR/ftb-api-26"
docker compose -f docker/docker-compose.prod.yml down 2>/dev/null || true
docker compose -f docker/docker-compose.prod.yml up -d --build

# Wait for DB to be ready
echo -e "  Waiting for database..."
sleep 10

# ── Step 7: Run migrations and collect static ──
echo -e "${YELLOW}▸ [7/7] Running migrations...${NC}"
docker compose -f docker/docker-compose.prod.yml exec -T web python manage.py migrate --noinput
docker compose -f docker/docker-compose.prod.yml exec -T web python manage.py collectstatic --noinput 2>/dev/null || true
echo -e "${GREEN}  ✓ Migrations applied${NC}"

# ── Done! ──
echo ""
echo -e "${GREEN}${BOLD}  ══════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}  ✓ FetchBot is deployed!${NC}"
echo -e "${GREEN}${BOLD}  ══════════════════════════════════════════${NC}"
echo ""

# Show container status
echo -e "${BLUE}Container status:${NC}"
docker compose -f docker/docker-compose.prod.yml ps
echo ""

# Health check
echo -e "${BLUE}Health check:${NC}"
if curl -s -o /dev/null -w "%{http_code}" http://localhost/health/ | grep -q "200"; then
    echo -e "${GREEN}  ✓ API is healthy (HTTP 200)${NC}"
else
    echo -e "${YELLOW}  ⚠ Health check pending — containers may still be starting${NC}"
fi

echo ""
echo -e "  ${BOLD}Next steps:${NC}"
echo -e "  1. Point fetchbot.ai A record to this server's IP: $(curl -s ifconfig.me)"
echo -e "  2. Set Cloudflare SSL to Full (Strict)"
echo -e "  3. Visit https://fetchbot.ai"
echo ""
