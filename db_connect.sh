#!/bin/bash

# GhostLine Database Connection Helper

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Database credentials
DB_HOST="localhost"
DB_PORT="5433"
DB_NAME="ghostline"
DB_USER="ghostlineadmin"
DB_PASS="YO,_9~5]Vp}vrNGl"

function show_help() {
    echo -e "${GREEN}GhostLine Database Connection Helper${NC}"
    echo ""
    echo "Usage: $0 [command]"
    echo ""
    echo "Commands:"
    echo "  tunnel    - Start SSH tunnel for database access"
    echo "  connect   - Connect to database via psql"
    echo "  status    - Check tunnel and jump host status"
    echo "  stop      - Stop the jump host (saves money)"
    echo "  start     - Start the jump host"
    echo "  pgadmin   - Show pgAdmin connection info"
    echo "  help      - Show this help message"
}

function start_tunnel() {
    echo -e "${YELLOW}Starting SSH tunnel...${NC}"
    
    # Check if tunnel is already running
    if lsof -i :5433 > /dev/null 2>&1; then
        echo -e "${YELLOW}Tunnel already running on port 5433${NC}"
        return 0
    fi
    
    # Start tunnel in background
    ssh -N -f ghostline-db
    
    # Wait a moment for tunnel to establish
    sleep 2
    
    if lsof -i :5433 > /dev/null 2>&1; then
        echo -e "${GREEN}✓ SSH tunnel established on port 5433${NC}"
    else
        echo -e "${RED}✗ Failed to establish SSH tunnel${NC}"
        return 1
    fi
}

function connect_db() {
    echo -e "${YELLOW}Connecting to database...${NC}"
    
    # Check if tunnel is running
    if ! lsof -i :5433 > /dev/null 2>&1; then
        echo -e "${YELLOW}Tunnel not running. Starting it first...${NC}"
        start_tunnel
    fi
    
    # Connect to database
    PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME"
}

function check_status() {
    echo -e "${GREEN}Checking status...${NC}"
    echo ""
    
    # Check jump host
    echo -e "${YELLOW}Jump Host Status:${NC}"
    INSTANCE_STATE=$(aws ec2 describe-instances --instance-ids i-0248957055ba45290 --query 'Reservations[0].Instances[0].State.Name' --output text 2>/dev/null)
    if [ $? -eq 0 ]; then
        echo -e "  Instance: i-0248957055ba45290"
        echo -e "  State: ${GREEN}$INSTANCE_STATE${NC}"
        echo -e "  IP: 44.236.39.246"
    else
        echo -e "  ${RED}Unable to check instance status${NC}"
    fi
    
    echo ""
    
    # Check SSH tunnel
    echo -e "${YELLOW}SSH Tunnel Status:${NC}"
    if lsof -i :5433 > /dev/null 2>&1; then
        echo -e "  Port 5433: ${GREEN}Active${NC}"
        TUNNEL_PID=$(lsof -ti :5433)
        echo -e "  Process ID: $TUNNEL_PID"
    else
        echo -e "  Port 5433: ${RED}Not running${NC}"
    fi
    
    echo ""
    
    # Test database connection
    echo -e "${YELLOW}Database Connection Test:${NC}"
    if lsof -i :5433 > /dev/null 2>&1; then
        if PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c "SELECT version();" > /dev/null 2>&1; then
            echo -e "  ${GREEN}✓ Database is accessible${NC}"
        else
            echo -e "  ${RED}✗ Database connection failed${NC}"
        fi
    else
        echo -e "  ${YELLOW}Cannot test - tunnel not running${NC}"
    fi
}

function stop_jump_host() {
    echo -e "${YELLOW}Stopping jump host to save costs...${NC}"
    aws ec2 stop-instances --instance-ids i-0b166378578083427
    echo -e "${GREEN}✓ Stop command sent. Instance will shut down shortly.${NC}"
}

function start_jump_host() {
    echo -e "${YELLOW}Starting jump host...${NC}"
    aws ec2 start-instances --instance-ids i-0b166378578083427
    echo -e "${GREEN}✓ Start command sent. Instance will be available in ~1 minute.${NC}"
    echo -e "${YELLOW}Run '$0 status' to check when it's ready.${NC}"
}

function show_pgadmin_info() {
    echo -e "${GREEN}pgAdmin Connection Information${NC}"
    echo ""
    echo -e "${YELLOW}Method 1: Manual SSH Tunnel${NC}"
    echo "1. Run: $0 tunnel"
    echo "2. In pgAdmin use:"
    echo "   Host: localhost"
    echo "   Port: 5433"
    echo "   Database: ghostline"
    echo "   Username: ghostlineadmin"
    echo "   Password: YO,_9~5]Vp}vrNGl"
    echo ""
    echo -e "${YELLOW}Method 2: pgAdmin SSH Tunnel${NC}"
    echo "Connection tab:"
    echo "   Host: ghostline-dev.cpygckmsmh2k.us-west-2.rds.amazonaws.com"
    echo "   Port: 5432"
    echo "   Database: ghostline"
    echo "   Username: ghostlineadmin"
    echo "   Password: YO,_9~5]Vp}vrNGl"
    echo ""
    echo "SSH Tunnel tab:"
    echo "   Tunnel host: 44.236.39.246"
    echo "   Tunnel port: 22"
    echo "   Username: ec2-user"
    echo "   Identity file: ~/.ssh/ghostline-jump-key.pem"
}

# Main script logic
case "$1" in
    tunnel)
        start_tunnel
        ;;
    connect)
        connect_db
        ;;
    status)
        check_status
        ;;
    stop)
        stop_jump_host
        ;;
    start)
        start_jump_host
        ;;
    pgadmin)
        show_pgadmin_info
        ;;
    help|"")
        show_help
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        show_help
        exit 1
        ;;
esac 