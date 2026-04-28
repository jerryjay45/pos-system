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

## ⚙️ Setup

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd project
```

### 2. Create virtual environment (recommended)

```bash
python -m venv venv
source venv/bin/activate   # Arch/Linux
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

## ▶️ Running the App

```bash
python main.py
```

---

## 🔌 Database Configuration

Inside your config or connection file:

```python
get_connection("sqlite")     # Local mode
get_connection("postgres")   # External DB
```

---

## 🧠 Design Notes

* Products and barcodes are separated to allow multiple barcodes per item
* Case sizes are treated as variations of a product
* Discounts are applied dynamically based on quantity
* Stock is tracked per case variation
* All checkout operations should use database transactions

---

## 🔄 Future Improvements

* Sync system between SQLite and PostgreSQL
* GUI (Tkinter / PyQt / Web UI)
* Reporting dashboard
* Multi-terminal support
* Backup & restore tools

---

## ⚠️ Notes

* Ensure proper database backups when using PostgreSQL
* Receipt printer compatibility depends on ESC/POS support
* Windows support planned (currently developed on Arch Linux)

---

## 📄 License

MIT (or your preferred license)

---

# pos-system
# pos-system
# pos-system
# pos-system
