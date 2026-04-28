# This is a personal project i will not looking at commit or merge requests


# 🧾 POS Inventory & Checkout System

A standalone Point of Sale (POS) and inventory management system built with **Python**, designed to run locally with **SQLite** and optionally connect to a **PostgreSQL** server for scaling.

---

## 🚀 Features

### 🛍️ Product Management

* Products with:

  * Brand
  * Name
  * Description (shared across barcodes)
* Multiple barcodes per product
* Case variations (e.g. single, 12-pack, 32-case)
* Stock tracking (enable/disable per product)

### 💸 Pricing & Discounts

* Tiered discount levels based on quantity purchased
* Configurable discount percentages

### 👤 User Roles

* **Cashier**

  * Checkout dashboard
  * Order processing

* **Supervisor**

  * Add/Edit/Delete products
  * Refunds & void transactions
  * Reprint receipts
  * View cashier sales & logs

* **Manager**

  * User management
  * Business configuration:

    * Discount levels
    * Tax rates
  * Full system control

---

## 🧾 Checkout System

* Barcode scanning support
* Cart-based checkout
* Receipt generation
* Logs:

  * Date & time
  * Cashier responsible

---

## 🖨️ Printing

* Receipt printer support (ESC/POS)
* Standard printer support (via PDF)
* Label generation and printing

---

## 🗄️ Database Support

### Local (Default)

* SQLite
* Fast and works offline

### External (Optional)

* PostgreSQL
* For multi-terminal or remote database setups

---

## 📁 Project Structure

```
project/
│
├── db/                # Database connection and schema
├── services/          # Business logic (products, checkout, etc.)
├── ui/                # CLI or GUI interface
├── main.py            # Entry point
└── pos.db             # SQLite database (local)
```

---

## 📄 License

MIT (or your preferred license)

---
