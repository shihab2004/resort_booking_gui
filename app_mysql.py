import os
from contextlib import contextmanager
from datetime import datetime
from tkinter import messagebox, ttk

import customtkinter as ctk
import mysql.connector
from mysql.connector import IntegrityError

MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "resort_booking"),
}


def get_connection():
    return mysql.connector.connect(**MYSQL_CONFIG)


@contextmanager
def get_db_connection():
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = DATABASE()
              AND table_name IN ('rooms', 'bookings')
            """
        )
        if cursor.fetchone()[0] != 2:
            raise RuntimeError(
                "Required MySQL tables not found. Please create 'rooms' and 'bookings' tables first."
            )


def add_room_record(room_name, capacity, price):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO rooms (room_name, capacity, price) VALUES (%s, %s, %s)",
            (room_name, capacity, price),
        )
        return cursor.lastrowid


def update_room_record(room_id, room_name, capacity, price):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE rooms
            SET room_name = %s, capacity = %s, price = %s
            WHERE id = %s
            """,
            (room_name, capacity, price, room_id),
        )
        return cursor.rowcount


def fetch_rooms():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, room_name, capacity, price FROM rooms ORDER BY id DESC")
        return cursor.fetchall()


def fetch_rooms_for_options():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, room_name, capacity, price FROM rooms ORDER BY room_name")
        return cursor.fetchall()


def delete_room_record(room_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM bookings WHERE room_id = %s", (room_id,))
        linked_count = cursor.fetchone()[0]

        if linked_count > 0:
            return 0, linked_count

        cursor.execute("DELETE FROM rooms WHERE id = %s", (room_id,))
        return cursor.rowcount, 0


def add_booking_record(name, phone, check_in, nights, guests, room_id, room_name):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO bookings
            (guest_name, phone, check_in, nights, guests, room_type, room_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (name, phone, check_in, nights, guests, room_name, room_id),
        )


def update_booking_record(
    booking_id, name, phone, check_in, nights, guests, room_id, room_name
):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE bookings
            SET guest_name = %s,
                phone = %s,
                check_in = %s,
                nights = %s,
                guests = %s,
                room_type = %s,
                room_id = %s
            WHERE id = %s
            """,
            (name, phone, check_in, nights, guests, room_name, room_id, booking_id),
        )
        return cursor.rowcount


def fetch_bookings():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT
                b.id,
                b.guest_name,
                b.phone,
                b.check_in,
                b.nights,
                b.guests,
                COALESCE(r.room_name, b.room_type) AS room_name,
                (b.nights * COALESCE(r.price, 0)) AS booking_amount,
                b.room_id
            FROM bookings b
            LEFT JOIN rooms r ON r.id = b.room_id
            ORDER BY b.id DESC
            """
        )
        return cursor.fetchall()


def delete_booking_record(booking_id):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bookings WHERE id = %s", (booking_id,))
        return cursor.rowcount


def get_total_booking_revenue():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT COALESCE(SUM(b.nights * COALESCE(r.price, 0)), 0)
            FROM bookings b
            LEFT JOIN rooms r ON r.id = b.room_id
            """
        )
        value = cursor.fetchone()[0]
        return float(value or 0)


class ResortBookingApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Resort Booking Manager")
        self.geometry("1180x720")
        self.minsize(1050, 680)

        self.name_var = ctk.StringVar()
        self.phone_var = ctk.StringVar()
        self.check_in_var = ctk.StringVar()
        self.nights_var = ctk.StringVar(value="1")
        self.guests_var = ctk.StringVar(value="2")
        self.booking_room_var = ctk.StringVar(value="No Rooms")
        self.booking_delete_id_var = ctk.StringVar()

        self.room_name_var = ctk.StringVar()
        self.room_capacity_var = ctk.StringVar(value="2")
        self.room_price_input_var = ctk.StringVar(value="120")
        self.room_delete_id_var = ctk.StringVar()

        self.selected_booking_id = None
        self.selected_room_id = None
        self.room_option_map = {}
        self.revenue_var = ctk.StringVar(value="Total Revenue: $0.00")

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._setup_table_style()
        self._build_header()
        self._build_tabs()
        self._build_footer()

        self.refresh_rooms(update_status=False)
        self.refresh_bookings(update_status=True)

    def _setup_table_style(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure(
            "App.Treeview",
            background="#111827",
            fieldbackground="#111827",
            foreground="#E5E7EB",
            borderwidth=0,
            rowheight=28,
        )
        style.map(
            "App.Treeview",
            background=[("selected", "#1D4ED8")],
            foreground=[("selected", "#FFFFFF")],
        )
        style.configure(
            "App.Treeview.Heading",
            background="#1F2937",
            foreground="#F3F4F6",
            relief="flat",
            borderwidth=0,
        )
        style.map("App.Treeview.Heading", background=[("active", "#374151")])

    def _build_header(self):
        header = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Resort Booking Manager",
            font=ctk.CTkFont(size=32, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            header,
            text="Booking and Room tabs with MySQL database",
            text_color="#9CA3AF",
            font=ctk.CTkFont(size=14),
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

    def _build_tabs(self):
        self.tabs = ctk.CTkTabview(self, corner_radius=16)
        self.tabs.grid(row=1, column=0, sticky="nsew", padx=20, pady=10)

        self.tabs.add("Booking")
        self.tabs.add("Room")

        self._build_booking_tab(self.tabs.tab("Booking"))
        self._build_room_tab(self.tabs.tab("Room"))

    def _build_booking_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=2)
        tab.grid_rowconfigure(0, weight=1)

        form_card = ctk.CTkScrollableFrame(tab, corner_radius=18)
        form_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12), pady=4)
        form_card.grid_columnconfigure((0, 1), weight=1)

        ctk.CTkLabel(
            form_card,
            text="Booking Form",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=20, pady=(20, 6))

        ctk.CTkLabel(
            form_card,
            text="Create / Update booking",
            text_color="#9CA3AF",
            font=ctk.CTkFont(size=13),
        ).grid(row=1, column=0, columnspan=2, sticky="w", padx=20, pady=(0, 12))

        ctk.CTkLabel(form_card, text="Guest Name", anchor="w").grid(
            row=2, column=0, columnspan=2, sticky="ew", padx=20, pady=(8, 4)
        )
        ctk.CTkEntry(
            form_card,
            textvariable=self.name_var,
            placeholder_text="John Carter",
            height=36,
        ).grid(row=3, column=0, columnspan=2, sticky="ew", padx=20)

        ctk.CTkLabel(form_card, text="Phone", anchor="w").grid(
            row=4, column=0, columnspan=2, sticky="ew", padx=20, pady=(8, 4)
        )
        ctk.CTkEntry(
            form_card,
            textvariable=self.phone_var,
            placeholder_text="+1 555 201 900",
            height=36,
        ).grid(row=5, column=0, columnspan=2, sticky="ew", padx=20)

        ctk.CTkLabel(form_card, text="Check-in (YYYY-MM-DD)", anchor="w").grid(
            row=6, column=0, columnspan=2, sticky="ew", padx=20, pady=(8, 4)
        )
        ctk.CTkEntry(
            form_card,
            textvariable=self.check_in_var,
            placeholder_text="2026-05-01",
            height=36,
        ).grid(row=7, column=0, columnspan=2, sticky="ew", padx=20)

        ctk.CTkLabel(form_card, text="Nights", anchor="w").grid(
            row=8, column=0, sticky="ew", padx=(20, 8), pady=(8, 4)
        )
        ctk.CTkLabel(form_card, text="Guests", anchor="w").grid(
            row=8, column=1, sticky="ew", padx=(8, 20), pady=(8, 4)
        )
        ctk.CTkEntry(
            form_card,
            textvariable=self.nights_var,
            placeholder_text="1",
            height=36,
        ).grid(row=9, column=0, sticky="ew", padx=(20, 8))
        ctk.CTkEntry(
            form_card,
            textvariable=self.guests_var,
            placeholder_text="2",
            height=36,
        ).grid(row=9, column=1, sticky="ew", padx=(8, 20))

        ctk.CTkLabel(form_card, text="Room", anchor="w").grid(
            row=10, column=0, columnspan=2, sticky="ew", padx=20, pady=(8, 4)
        )

        self.booking_room_menu = ctk.CTkOptionMenu(
            form_card,
            variable=self.booking_room_var,
            values=["No Rooms"],
            height=36,
        )
        self.booking_room_menu.grid(
            row=11, column=0, columnspan=2, sticky="ew", padx=20
        )

        btn_row = ctk.CTkFrame(form_card, fg_color="transparent")
        btn_row.grid(row=12, column=0, columnspan=2, sticky="ew", padx=20, pady=(18, 20))
        btn_row.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(
            btn_row,
            text="Save Booking",
            fg_color="#0EA5E9",
            hover_color="#0284C7",
            command=self.add_booking,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))

        ctk.CTkButton(
            btn_row,
            text="Update",
            fg_color="#F59E0B",
            hover_color="#D97706",
            command=self.update_booking,
        ).grid(row=0, column=1, sticky="ew", padx=6)

        ctk.CTkButton(
            btn_row,
            text="Clear",
            fg_color="#374151",
            hover_color="#1F2937",
            command=self.clear_booking_form,
        ).grid(row=0, column=2, sticky="ew", padx=(6, 0))

        list_card = ctk.CTkFrame(tab, corner_radius=18)
        list_card.grid(row=0, column=1, sticky="nsew", pady=4)
        list_card.grid_columnconfigure(0, weight=1)
        list_card.grid_rowconfigure(1, weight=1)

        top_bar = ctk.CTkFrame(list_card, fg_color="transparent")
        top_bar.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 8))
        top_bar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top_bar,
            text="Booking List",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            top_bar,
            text="Refresh",
            width=100,
            command=self.refresh_bookings,
        ).grid(row=0, column=1, sticky="e")

        ctk.CTkLabel(
            top_bar,
            textvariable=self.revenue_var,
            text_color="#34D399",
            font=ctk.CTkFont(size=15, weight="bold"),
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        table_wrap = ctk.CTkFrame(list_card, fg_color="transparent")
        table_wrap.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 10))
        table_wrap.grid_columnconfigure(0, weight=1)
        table_wrap.grid_rowconfigure(0, weight=1)

        columns = (
            "id",
            "name",
            "phone",
            "check_in",
            "nights",
            "guests",
            "room",
            "amount",
            "room_id",
        )
        self.booking_table = ttk.Treeview(
            table_wrap,
            columns=columns,
            show="headings",
            style="App.Treeview",
        )
        self.booking_table.grid(row=0, column=0, sticky="nsew")

        self.booking_table.heading("id", text="ID")
        self.booking_table.heading("name", text="Name")
        self.booking_table.heading("phone", text="Phone")
        self.booking_table.heading("check_in", text="Check-in")
        self.booking_table.heading("nights", text="Nights")
        self.booking_table.heading("guests", text="Guests")
        self.booking_table.heading("room", text="Room")
        self.booking_table.heading("amount", text="Amount")
        self.booking_table.heading("room_id", text="")

        self.booking_table.column("id", width=55, anchor="center", stretch=False)
        self.booking_table.column("name", width=150, anchor="w")
        self.booking_table.column("phone", width=120, anchor="w")
        self.booking_table.column("check_in", width=110, anchor="center")
        self.booking_table.column("nights", width=65, anchor="center", stretch=False)
        self.booking_table.column("guests", width=65, anchor="center", stretch=False)
        self.booking_table.column("room", width=120, anchor="w")
        self.booking_table.column("amount", width=95, anchor="e")
        self.booking_table.column("room_id", width=0, stretch=False)

        booking_scroll = ttk.Scrollbar(
            table_wrap, orient="vertical", command=self.booking_table.yview
        )
        booking_scroll.grid(row=0, column=1, sticky="ns")
        self.booking_table.configure(yscrollcommand=booking_scroll.set)
        self.booking_table.bind("<<TreeviewSelect>>", self.on_booking_table_select)

        delete_row = ctk.CTkFrame(list_card, fg_color="transparent")
        delete_row.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 16))
        delete_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(delete_row, text="Booking ID").grid(row=0, column=0, padx=(0, 8))
        ctk.CTkEntry(
            delete_row,
            textvariable=self.booking_delete_id_var,
            placeholder_text="Enter ID",
            height=34,
            width=130,
        ).grid(row=0, column=1, sticky="w")

        ctk.CTkButton(
            delete_row,
            text="Delete",
            fg_color="#DC2626",
            hover_color="#B91C1C",
            width=100,
            command=self.delete_booking,
        ).grid(row=0, column=2, padx=(10, 0), sticky="e")

    def _build_room_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_columnconfigure(1, weight=2)
        tab.grid_rowconfigure(0, weight=1)

        form_card = ctk.CTkFrame(tab, corner_radius=18)
        form_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12), pady=4)

        ctk.CTkLabel(
            form_card,
            text="Room Form",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=20, pady=(20, 6))

        ctk.CTkLabel(
            form_card,
            text="Create / Update room",
            text_color="#9CA3AF",
            font=ctk.CTkFont(size=13),
        ).grid(row=1, column=0, sticky="w", padx=20, pady=(0, 12))

        ctk.CTkLabel(form_card, text="Room Name", anchor="w").grid(
            row=2, column=0, sticky="ew", padx=20, pady=(8, 4)
        )
        ctk.CTkEntry(
            form_card,
            textvariable=self.room_name_var,
            placeholder_text="Deluxe Sea View",
            height=36,
        ).grid(row=3, column=0, sticky="ew", padx=20)

        ctk.CTkLabel(form_card, text="Capacity", anchor="w").grid(
            row=4, column=0, sticky="ew", padx=20, pady=(8, 4)
        )
        ctk.CTkEntry(
            form_card,
            textvariable=self.room_capacity_var,
            placeholder_text="2",
            height=36,
        ).grid(row=5, column=0, sticky="ew", padx=20)

        ctk.CTkLabel(form_card, text="Price (per night)", anchor="w").grid(
            row=6, column=0, sticky="ew", padx=20, pady=(8, 4)
        )
        ctk.CTkEntry(
            form_card,
            textvariable=self.room_price_input_var,
            placeholder_text="120",
            height=36,
        ).grid(row=7, column=0, sticky="ew", padx=20)

        btn_row = ctk.CTkFrame(form_card, fg_color="transparent")
        btn_row.grid(row=8, column=0, sticky="ew", padx=20, pady=(18, 20))
        btn_row.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(
            btn_row,
            text="Save Room",
            fg_color="#0EA5E9",
            hover_color="#0284C7",
            command=self.add_room,
        ).grid(row=0, column=0, sticky="ew", padx=(0, 6))

        ctk.CTkButton(
            btn_row,
            text="Update",
            fg_color="#F59E0B",
            hover_color="#D97706",
            command=self.update_room,
        ).grid(row=0, column=1, sticky="ew", padx=6)

        ctk.CTkButton(
            btn_row,
            text="Clear",
            fg_color="#374151",
            hover_color="#1F2937",
            command=self.clear_room_form,
        ).grid(row=0, column=2, sticky="ew", padx=(6, 0))

        list_card = ctk.CTkFrame(tab, corner_radius=18)
        list_card.grid(row=0, column=1, sticky="nsew", pady=4)
        list_card.grid_columnconfigure(0, weight=1)
        list_card.grid_rowconfigure(1, weight=1)

        top_bar = ctk.CTkFrame(list_card, fg_color="transparent")
        top_bar.grid(row=0, column=0, sticky="ew", padx=18, pady=(16, 8))
        top_bar.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            top_bar,
            text="Room List",
            font=ctk.CTkFont(size=22, weight="bold"),
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkButton(
            top_bar,
            text="Refresh",
            width=100,
            command=self.refresh_rooms,
        ).grid(row=0, column=1, sticky="e")

        table_wrap = ctk.CTkFrame(list_card, fg_color="transparent")
        table_wrap.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 10))
        table_wrap.grid_columnconfigure(0, weight=1)
        table_wrap.grid_rowconfigure(0, weight=1)

        room_columns = ("id", "room_name", "capacity", "price")
        self.room_table = ttk.Treeview(
            table_wrap,
            columns=room_columns,
            show="headings",
            style="App.Treeview",
        )
        self.room_table.grid(row=0, column=0, sticky="nsew")

        self.room_table.heading("id", text="ID")
        self.room_table.heading("room_name", text="Room Name")
        self.room_table.heading("capacity", text="Capacity")
        self.room_table.heading("price", text="Price")

        self.room_table.column("id", width=55, anchor="center", stretch=False)
        self.room_table.column("room_name", width=220, anchor="w")
        self.room_table.column("capacity", width=110, anchor="center")
        self.room_table.column("price", width=130, anchor="e")

        room_scroll = ttk.Scrollbar(table_wrap, orient="vertical", command=self.room_table.yview)
        room_scroll.grid(row=0, column=1, sticky="ns")
        self.room_table.configure(yscrollcommand=room_scroll.set)
        self.room_table.bind("<<TreeviewSelect>>", self.on_room_table_select)

        delete_row = ctk.CTkFrame(list_card, fg_color="transparent")
        delete_row.grid(row=2, column=0, sticky="ew", padx=18, pady=(0, 16))
        delete_row.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(delete_row, text="Room ID").grid(row=0, column=0, padx=(0, 8))
        ctk.CTkEntry(
            delete_row,
            textvariable=self.room_delete_id_var,
            placeholder_text="Enter ID",
            height=34,
            width=130,
        ).grid(row=0, column=1, sticky="w")

        ctk.CTkButton(
            delete_row,
            text="Delete",
            fg_color="#DC2626",
            hover_color="#B91C1C",
            width=100,
            command=self.delete_room,
        ).grid(row=0, column=2, padx=(10, 0), sticky="e")

    def _build_footer(self):
        footer = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=20, pady=(4, 14))

        self.status_label = ctk.CTkLabel(
            footer,
            text="Ready",
            text_color="#93C5FD",
            anchor="w",
            font=ctk.CTkFont(size=13),
        )
        self.status_label.pack(fill="x")

    def set_status(self, text, color="#93C5FD"):
        self.status_label.configure(text=text, text_color=color)

    def _collect_room_form_values(self):
        room_name = self.room_name_var.get().strip()
        cap_text = self.room_capacity_var.get().strip()
        price_text = self.room_price_input_var.get().strip()

        if not room_name:
            messagebox.showerror("Missing Data", "Room Name is required.")
            return None

        try:
            capacity = int(cap_text)
            if capacity <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Capacity", "Capacity must be a positive number.")
            return None

        try:
            price = float(price_text)
            if price < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Price", "Price must be a valid positive number.")
            return None

        return room_name, capacity, price

    def _collect_booking_form_values(self):
        name = self.name_var.get().strip()
        phone = self.phone_var.get().strip()
        check_in = self.check_in_var.get().strip()
        nights_text = self.nights_var.get().strip()
        guests_text = self.guests_var.get().strip()

        if not name or not phone or not check_in:
            messagebox.showerror("Missing Data", "Name, Phone and Check-in are required.")
            return None

        try:
            datetime.strptime(check_in, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Wrong Date", "Use date format YYYY-MM-DD.")
            return None

        try:
            nights = int(nights_text)
            guests = int(guests_text)
            if nights <= 0 or guests <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Wrong Number", "Nights and Guests must be positive numbers.")
            return None

        room_data = self.room_option_map.get(self.booking_room_var.get())
        if not room_data:
            messagebox.showerror("No Room", "Please add a room first in Room tab.")
            return None

        return (
            name,
            phone,
            check_in,
            nights,
            guests,
            room_data["id"],
            room_data["name"],
        )

    def clear_booking_form(self):
        self.name_var.set("")
        self.phone_var.set("")
        self.check_in_var.set("")
        self.nights_var.set("1")
        self.guests_var.set("2")
        self.booking_delete_id_var.set("")
        self.selected_booking_id = None

        if hasattr(self, "booking_table"):
            self.booking_table.selection_remove(self.booking_table.selection())

        if self.room_option_map:
            first_option = next(iter(self.room_option_map))
            self.booking_room_var.set(first_option)
        else:
            self.booking_room_var.set("No Rooms")

        self.set_status("Booking form cleared", "#9CA3AF")

    def clear_room_form(self):
        self.room_name_var.set("")
        self.room_capacity_var.set("2")
        self.room_price_input_var.set("120")
        self.room_delete_id_var.set("")
        self.selected_room_id = None

        if hasattr(self, "room_table"):
            self.room_table.selection_remove(self.room_table.selection())

        self.set_status("Room form cleared", "#9CA3AF")

    def _refresh_booking_room_options(self):
        rooms = fetch_rooms_for_options()
        self.room_option_map = {}
        options = []

        for room_id, room_name, capacity, _price in rooms:
            option_text = f"{room_name} (Cap {capacity})"
            options.append(option_text)
            self.room_option_map[option_text] = {
                "id": int(room_id),
                "name": room_name,
            }

        if not options:
            self.booking_room_menu.configure(values=["No Rooms"])
            self.booking_room_var.set("No Rooms")
            return

        current = self.booking_room_var.get()
        self.booking_room_menu.configure(values=options)

        if current not in self.room_option_map:
            current = options[0]
            self.booking_room_var.set(current)

    def select_booking_room_by_room_id(self, room_id):
        for option_text, room_data in self.room_option_map.items():
            if room_data["id"] == room_id:
                self.booking_room_var.set(option_text)
                return

        if self.room_option_map:
            first_option = next(iter(self.room_option_map))
            self.booking_room_var.set(first_option)
        else:
            self.booking_room_var.set("No Rooms")

    def select_booking_room_by_name(self, room_name):
        for option_text, room_data in self.room_option_map.items():
            if room_data["name"].lower() == str(room_name).lower():
                self.booking_room_var.set(option_text)
                return

        self.select_booking_room_by_room_id(-1)

    def add_booking(self):
        values = self._collect_booking_form_values()
        if not values:
            return

        add_booking_record(*values)
        self.clear_booking_form()
        self.refresh_bookings(update_status=False)
        self.set_status("Booking saved successfully", "#34D399")

    def update_booking(self):
        booking_id_text = self.booking_delete_id_var.get().strip()
        if not booking_id_text.isdigit():
            messagebox.showerror(
                "Invalid ID",
                "Select a booking row or enter a valid Booking ID.",
            )
            return

        values = self._collect_booking_form_values()
        if not values:
            return

        updated = update_booking_record(int(booking_id_text), *values)
        if updated == 0:
            self.set_status("Booking ID not found", "#F59E0B")
            return

        self.refresh_bookings(update_status=False)
        self.set_status("Booking updated", "#34D399")

    def delete_booking(self):
        booking_id_text = self.booking_delete_id_var.get().strip()
        if not booking_id_text.isdigit():
            messagebox.showerror("Invalid ID", "Please enter a valid numeric booking ID.")
            return

        deleted = delete_booking_record(int(booking_id_text))
        if deleted == 0:
            self.set_status("Booking ID not found", "#F59E0B")
            return

        self.clear_booking_form()
        self.refresh_bookings(update_status=False)
        self.set_status("Booking deleted", "#FCA5A5")

    def on_booking_table_select(self, _event=None):
        selected = self.booking_table.selection()
        if not selected:
            return

        values = self.booking_table.item(selected[0], "values")
        if not values:
            return

        booking_id = values[0]
        name = values[1]
        phone = values[2]
        check_in = values[3]
        nights = values[4]
        guests = values[5]
        room_name = values[6]
        room_id = values[8]

        self.selected_booking_id = int(booking_id)
        self.booking_delete_id_var.set(str(booking_id))
        self.name_var.set(name)
        self.phone_var.set(phone)
        self.check_in_var.set(check_in)
        self.nights_var.set(str(nights))
        self.guests_var.set(str(guests))

        if str(room_id).isdigit():
            self.select_booking_room_by_room_id(int(room_id))
        else:
            self.select_booking_room_by_name(room_name)

        self.set_status(f"Selected booking ID {booking_id}", "#93C5FD")

    def refresh_bookings(self, update_status=True):
        rows = fetch_bookings()

        for item in self.booking_table.get_children():
            self.booking_table.delete(item)

        for booking in rows:
            (
                booking_id,
                guest_name,
                phone,
                check_in,
                nights,
                guests,
                room_name,
                booking_amount,
                room_id,
            ) = booking

            self.booking_table.insert(
                "",
                "end",
                values=(
                    booking_id,
                    guest_name,
                    phone,
                    check_in,
                    nights,
                    guests,
                    room_name,
                    f"{float(booking_amount):.2f}",
                    room_id if room_id is not None else "",
                ),
            )

        total_revenue = get_total_booking_revenue()
        self.revenue_var.set(f"Total Revenue: ${total_revenue:.2f}")

        if update_status:
            self.set_status(f"Loaded {len(rows)} booking(s)")

    def add_room(self):
        values = self._collect_room_form_values()
        if not values:
            return

        try:
            add_room_record(*values)
        except IntegrityError:
            messagebox.showerror("Duplicate Room", "Room Name already exists.")
            return

        self.clear_room_form()
        self.refresh_rooms(update_status=False)
        self.refresh_bookings(update_status=False)
        self.set_status("Room saved successfully", "#34D399")

    def update_room(self):
        room_id_text = self.room_delete_id_var.get().strip()
        if room_id_text.isdigit():
            room_id = int(room_id_text)
        elif self.selected_room_id:
            room_id = self.selected_room_id
        else:
            messagebox.showerror("Invalid ID", "Select a room row or enter a valid Room ID.")
            return

        values = self._collect_room_form_values()
        if not values:
            return

        try:
            updated = update_room_record(room_id, *values)
        except IntegrityError:
            messagebox.showerror("Duplicate Room", "Room Name already exists.")
            return

        if updated == 0:
            self.set_status("Room ID not found", "#F59E0B")
            return

        self.refresh_rooms(update_status=False)
        self.refresh_bookings(update_status=False)
        self.set_status("Room updated", "#34D399")

    def delete_room(self):
        room_id_text = self.room_delete_id_var.get().strip()
        if not room_id_text.isdigit():
            messagebox.showerror("Invalid ID", "Please enter a valid numeric room ID.")
            return

        deleted, linked_count = delete_room_record(int(room_id_text))
        if linked_count > 0:
            messagebox.showerror(
                "Room In Use",
                f"Cannot delete. {linked_count} booking(s) are linked to this room.",
            )
            return

        if deleted == 0:
            self.set_status("Room ID not found", "#F59E0B")
            return

        self.clear_room_form()
        self.refresh_rooms(update_status=False)
        self.refresh_bookings(update_status=False)
        self.set_status("Room deleted", "#FCA5A5")

    def on_room_table_select(self, _event=None):
        selected = self.room_table.selection()
        if not selected:
            return

        values = self.room_table.item(selected[0], "values")
        if not values:
            return

        room_id, room_name, capacity, price = values
        self.selected_room_id = int(room_id)
        self.room_delete_id_var.set(str(room_id))
        self.room_name_var.set(room_name)
        self.room_capacity_var.set(str(capacity))
        self.room_price_input_var.set(str(price))
        self.set_status(f"Selected room ID {room_id}", "#93C5FD")

    def refresh_rooms(self, update_status=True):
        rows = fetch_rooms()

        for item in self.room_table.get_children():
            self.room_table.delete(item)

        for room in rows:
            room_id, room_name, capacity, price = room
            self.room_table.insert(
                "",
                "end",
                values=(room_id, room_name, capacity, f"{float(price):.2f}"),
            )

        self._refresh_booking_room_options()

        if update_status:
            self.set_status(f"Loaded {len(rows)} room(s)")


def main():
    init_db()
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")

    app = ResortBookingApp()
    app.mainloop()


if __name__ == "__main__":
    main()
