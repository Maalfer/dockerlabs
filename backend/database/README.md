# Database Directory

This directory contains the SQLite database file for the application.

**File:** `dockerlabs.db`

## Contents

- All user data
- All machine data (both dockerlabs and bunkerlabs)
- Writeups, ratings, rankings
- BunkerLabs specific tables (access tokens, solves, logs, writeups)

## Important Notes

- The `.db`, `.db-wal`, and `.db-shm` files are excluded from git via `.gitignore`
- SQLite creates `-wal` and `-shm` files automatically for write-ahead logging
- Do not manually delete `.db-wal` or `.db-shm` files while the application is running
