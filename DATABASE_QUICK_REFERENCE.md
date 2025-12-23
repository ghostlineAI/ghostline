---
Last Updated: 2025-06-28 09:30:52 PDT
---

# GhostLine Database Quick Reference

## 🚀 Quick Commands

```bash
# Check status
./db_connect.sh status

# Connect to database
./db_connect.sh connect

# Start SSH tunnel
./db_connect.sh tunnel

# pgAdmin info
./db_connect.sh pgadmin
```

## 📊 Database Credentials

### PostgreSQL
- **Host**: localhost (through tunnel)
- **Port**: 5433
- **Database**: ghostline
- **Username**: ghostlineadmin
- **Password**: YO,_9~5]Vp}vrNGl

### Connection String
```
postgresql://ghostlineadmin:YO,_9~5]Vp}vrNGl@localhost:5433/ghostline
```

## 💰 Cost Saving

```bash
# Stop jump host when done
./db_connect.sh stop

# Start when needed
./db_connect.sh start
```

## 🔧 Troubleshooting

### Can't connect?
1. Check jump host is running: `./db_connect.sh status`
2. Kill old tunnels: `kill $(lsof -ti :5433)`
3. Restart tunnel: `./db_connect.sh tunnel`

### pgAdmin Setup
1. Host: `localhost`
2. Port: `5433`
3. Database: `ghostline`
4. Username: `ghostlineadmin`
5. Password: `YO,_9~5]Vp}vrNGl`

## 📝 Common SQL Commands

```sql
-- List tables
\dt

-- Describe table
\d users

-- Count records
SELECT COUNT(*) FROM users;

-- Exit
\q
``` 