#!/bin/bash

# Clear current database
PGPASSWORD='YO,_9~5]Vp}vrNGl' psql -h 127.0.0.1 -p 5433 -U ghostlineadmin -d ghostline -c "TRUNCATE users, projects, source_materials, content_chunks, voice_profiles, book_outlines, chapters, chapter_revisions, generation_tasks, token_transactions, qa_findings, exported_books, notifications, api_keys CASCADE;"

# Dump from restored database
PGPASSWORD='YO,_9~5]Vp}vrNGl' pg_dump -h 127.0.0.1 -p 5434 -U ghostlineadmin -d ghostline --data-only > dump.sql

# Restore to current database
PGPASSWORD='YO,_9~5]Vp}vrNGl' psql -h 127.0.0.1 -p 5433 -U ghostlineadmin -d ghostline < dump.sql

# Verify
PGPASSWORD='YO,_9~5]Vp}vrNGl' psql -h 127.0.0.1 -p 5433 -U ghostlineadmin -d ghostline -c "SELECT email FROM users;" 