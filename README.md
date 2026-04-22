# Resort Booking GUI

Simple desktop app for room and booking management using CustomTkinter + MySQL.

## Features
- Add, update, and delete rooms
- Add, update, and delete bookings
- Auto-calculate booking amount and total revenue
- MySQL database

## MySQL Setup
Create database first (the app will auto-create `rooms` and `bookings` tables if missing):

```sql
CREATE DATABASE resort_booking;
USE resort_booking;

-- Tables are created automatically by the app.
```

Note: `price` is stored as `DECIMAL(10,2)` in MySQL and shown in the app as numeric text with 2 decimal places.

Set environment variables as needed:
- `MYSQL_HOST` (default: `127.0.0.1`)
- `MYSQL_PORT` (default: `3306`)
- `MYSQL_USER` (default: `root`)
- `MYSQL_PASSWORD` (default: empty)
- `MYSQL_DATABASE` (default: `resort_booking`)

## Run
1. `pip install -r requirements.txt`
2. `python app.py`
