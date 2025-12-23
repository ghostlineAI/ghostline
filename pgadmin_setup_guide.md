---
Last Updated: 2025-06-28 09:29:55 PDT
---

# pgAdmin Setup Guide for GhostLine Database

## Prerequisites
- pgAdmin installed on your Mac (download from https://www.pgadmin.org/download/pgadmin-4-macos/)
- SSH key file: `~/.ssh/ghostline-jump-key.pem`
- Jump host running at: `18.236.96.88`

## Database Connection Details
- **RDS Host**: ghostline-dev.cpygckmsmh2k.us-west-2.rds.amazonaws.com
- **Port**: 5432
- **Database**: ghostline
- **Username**: ghostlineadmin
- **Password**: YO,_9~5]Vp}vrNGl

## Method 1: Using SSH Tunnel (Recommended)

### Step 1: Set up SSH Tunnel
```bash
# Open a terminal and run:
ssh -N -L 5433:ghostline-dev.cpygckmsmh2k.us-west-2.rds.amazonaws.com:5432 ec2-user@18.236.96.88 -i ~/.ssh/ghostline-jump-key.pem
```

Keep this terminal open while using pgAdmin.

### Step 2: Configure pgAdmin
1. Open pgAdmin
2. Right-click on "Servers" → "Register" → "Server"
3. In the "General" tab:
   - Name: `GhostLine Dev DB`
4. In the "Connection" tab:
   - Host: `localhost`
   - Port: `5433`
   - Database: `ghostline`
   - Username: `ghostlineadmin`
   - Password: `YO,_9~5]Vp}vrNGl`
5. Click "Save"

## Method 2: Using pgAdmin's Built-in SSH Tunnel

### Configure pgAdmin with SSH Tunnel
1. Open pgAdmin
2. Right-click on "Servers" → "Register" → "Server"
3. In the "General" tab:
   - Name: `GhostLine Dev DB (SSH)`
4. In the "Connection" tab:
   - Host: `ghostline-dev.cpygckmsmh2k.us-west-2.rds.amazonaws.com`
   - Port: `5432`
   - Database: `ghostline`
   - Username: `ghostlineadmin`
   - Password: `YO,_9~5]Vp}vrNGl`
5. In the "SSH Tunnel" tab:
   - Use SSH tunneling: ✓ (check this)
   - Tunnel host: `18.236.96.88`
   - Tunnel port: `22`
   - Username: `ec2-user`
   - Authentication: Identity file
   - Identity file: Browse to `~/.ssh/ghostline-jump-key.pem`
6. Click "Save"

## Troubleshooting

### "Connection refused" error
- Make sure the SSH tunnel is running
- Check that you're using port 5433 for localhost connection
- Verify the jump host is still running: `aws ec2 describe-instances --instance-ids i-0b166378578083427`

### "Authentication failed" error
- Double-check the password (note the underscore: `YO,_9~5]Vp}vrNGl`)
- Ensure you're using the correct username: `ghostlineadmin`

### "Host key verification failed"
- Add to known hosts: `ssh-keyscan -H 18.236.96.88 >> ~/.ssh/known_hosts`

## Alternative: TablePlus (Simpler UI)
If you prefer TablePlus (https://tableplus.com/):
1. Create new connection → PostgreSQL
2. Name: `GhostLine Dev`
3. Host: `localhost`
4. Port: `5433`
5. User: `ghostlineadmin`
6. Password: `YO,_9~5]Vp}vrNGl`
7. Database: `ghostline`
8. Enable "Use SSH" and configure:
   - SSH Host: `18.236.96.88`
   - SSH User: `ec2-user`
   - SSH Key: Select `~/.ssh/ghostline-jump-key.pem`

## Managing the Jump Host

### Check if jump host is running:
```bash
aws ec2 describe-instances --instance-ids i-0b166378578083427 --query 'Reservations[0].Instances[0].State.Name' --output text
```

### Stop the jump host (when not needed):
```bash
aws ec2 stop-instances --instance-ids i-0b166378578083427
```

### Start the jump host (when needed):
```bash
aws ec2 start-instances --instance-ids i-0b166378578083427
```

### Terminate the jump host (permanent):
```bash
aws ec2 terminate-instances --instance-ids i-0b166378578083427
``` 