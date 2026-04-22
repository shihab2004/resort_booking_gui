# Resort Booking GUI

Simple desktop app for room and booking management using CustomTkinter + MySQL.

## Features
- Add, update, and delete rooms
- Add, update, and delete bookings
- Auto-calculate booking amount and total revenue
- MySQL database

## MySQL Setup
Create a database and required tables before running the app:

```sql
CREATE DATABASE resort_booking;
USE resort_booking;

CREATE TABLE rooms (
  id INT AUTO_INCREMENT PRIMARY KEY,
  room_name VARCHAR(255) NOT NULL UNIQUE,
  capacity INT NOT NULL,
  price DECIMAL(10,2) NOT NULL
);

CREATE TABLE bookings (
  id INT AUTO_INCREMENT PRIMARY KEY,
  guest_name VARCHAR(255) NOT NULL,
  phone VARCHAR(64) NOT NULL,
  check_in DATE NOT NULL,
  nights INT NOT NULL,
  guests INT NOT NULL,
  room_type VARCHAR(255) NOT NULL,
  room_id INT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (room_id) REFERENCES rooms(id)
);
```

Set environment variables as needed:
- `MYSQL_HOST` (default: `127.0.0.1`)
- `MYSQL_PORT` (default: `3306`)
- `MYSQL_USER` (default: `root`)
- `MYSQL_PASSWORD` (default: empty)
- `MYSQL_DATABASE` (default: `resort_booking`)

## Run
1. `pip install -r requirements.txt`
2. `python app.py`
