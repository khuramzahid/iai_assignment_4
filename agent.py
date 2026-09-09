"""
A tool-using e-commerce agent.
    python agent.py
        answer the sample questions using tools
    python agent.py --naive
        answer the sample questions without tools
    python agent.py --ask "..."
        ask your own question
    python agent.py --approve
        auto-approve the irreversible dispatch action (for testing)
The model asks for a tool.
This script decides whether to run it.
"""
# pyrefly: ignore [missing-import]
from langsmith import traceable

import argparse
import json
import re
import sqlite3
import requests


MODEL = "granite4.1:3b"
OLLAMA = "http://localhost:11434/v1/chat/completions"

# Some questions may require several tool calls.
MAX_STEPS = 8

# ============================================================
# 1. Data
# ============================================================
#
# Sample e-commerce database.
#
# Tables:
#   suppliers
#   categories
#   products
#   customers
#   orders
#   order_items
#
# All data is fictional.
# ============================================================

DB = sqlite3.connect(
    ":memory:",
    check_same_thread=False
)
DB.row_factory = sqlite3.Row
DB.executescript("""
PRAGMA foreign_keys = ON;

-- ==========================================================
-- SUPPLIERS
-- ==========================================================

CREATE TABLE suppliers (
    supplier_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    city TEXT NOT NULL,
    email TEXT UNIQUE
);

-- ==========================================================
-- CATEGORIES
-- ==========================================================

CREATE TABLE categories (
    category_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL UNIQUE
);

-- ==========================================================
-- PRODUCTS
-- ==========================================================

CREATE TABLE products (
    product_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category_id INTEGER NOT NULL,
    supplier_id INTEGER NOT NULL,
    price REAL NOT NULL CHECK (price >= 0),
    stock INTEGER NOT NULL DEFAULT 0 CHECK (stock >= 0),
    FOREIGN KEY (category_id)
        REFERENCES categories(category_id),
    FOREIGN KEY (supplier_id)
        REFERENCES suppliers(supplier_id)
);

-- ==========================================================
-- CUSTOMERS
-- ==========================================================

CREATE TABLE customers (
    customer_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    city TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- ==========================================================
-- ORDERS
-- ==========================================================

CREATE TABLE orders (
    order_id INTEGER PRIMARY KEY,
    customer_id INTEGER NOT NULL,
    order_date TEXT NOT NULL,
    status TEXT NOT NULL
        CHECK (
            status IN (
                'Pending',
                'Shipped',
                'Delivered',
                'Cancelled'
            )
        ),
    FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id)
);

-- ==========================================================
-- ORDER ITEMS
-- ==========================================================

CREATE TABLE order_items (
    order_item_id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL CHECK (quantity > 0),
    unit_price REAL NOT NULL CHECK (unit_price >= 0),
    FOREIGN KEY (order_id)
        REFERENCES orders(order_id),
    FOREIGN KEY (product_id)
        REFERENCES products(product_id)
);

-- ==========================================================
-- SAMPLE DATA
-- ==========================================================

INSERT INTO suppliers
    (supplier_id, name, city, email)
VALUES
    (1, 'TechSource Pakistan', 'Lahore',
        'sales@techsource.pk'),
    (2, 'Digital Traders', 'Karachi',
        'info@digitaltraders.pk'),
    (3, 'Smart Devices Ltd', 'Islamabad',
        'contact@smartdevices.pk');

INSERT INTO categories
    (category_id, name)
VALUES
    (1, 'Laptops'),
    (2, 'Accessories'),
    (3, 'Networking'),
    (4, 'Smart Home');

INSERT INTO products
    (
        product_id,
        name,
        category_id,
        supplier_id,
        price,
        stock
    )
VALUES
    (1, 'Lenovo ThinkPad E14', 1, 1, 185000, 12),
    (2, 'Dell Latitude 5440', 1, 1, 210000, 8),
    (3, 'Logitech MX Master 3S', 2, 2, 28500, 25),
    (4, 'Mechanical Keyboard', 2, 2, 12500, 40),
    (5, 'TP-Link WiFi 6 Router', 3, 2, 18500, 18),
    (6, 'ESP32 Development Board', 4, 3, 2500, 60),
    (7, 'Smart WiFi Plug', 4, 3, 4500, 35),
    (8, 'USB-C Docking Station', 2, 1, 22000, 15);

INSERT INTO customers
    (
        customer_id,
        name,
        email,
        city,
        created_at
    )
VALUES
    (1, 'Ali Raza', 'ali@example.com',
        'Lahore', '2026-01-15'),
    (2, 'Sara Khan', 'sara@example.com',
        'Islamabad', '2026-02-03'),
    (3, 'Usman Ahmed', 'usman@example.com',
        'Karachi', '2026-02-20'),
    (4, 'Ayesha Malik', 'ayesha@example.com',
        'Lahore', '2026-03-11'),
    (5, 'Hamza Iqbal', 'hamza@example.com',
        'Rawalpindi', '2026-04-07'),
    (6, 'Fatima Noor', 'fatima@example.com',
        'Lahore', '2026-05-19');

INSERT INTO orders
    (
        order_id,
        customer_id,
        order_date,
        status
    )
VALUES
    (1, 1, '2026-06-01', 'Delivered'),
    (2, 2, '2026-06-04', 'Shipped'),
    (3, 3, '2026-06-08', 'Delivered'),
    (4, 1, '2026-06-15', 'Pending'),
    (5, 4, '2026-06-18', 'Delivered'),
    (6, 5, '2026-06-22', 'Cancelled'),
    (7, 6, '2026-07-01', 'Shipped'),
    (8, 3, '2026-07-05', 'Delivered');

INSERT INTO order_items
    (
        order_item_id,
        order_id,
        product_id,
        quantity,
        unit_price
    )
VALUES
    (1,  1, 1, 1, 185000),
    (2,  1, 3, 1, 28500),
    (3,  2, 2, 1, 210000),
    (4,  2, 4, 2, 12500),
    (5,  3, 5, 1, 18500),
    (6,  3, 7, 3, 4500),
    (7,  4, 6, 5, 2500),
    (8,  4, 8, 1, 22000),
    (9,  5, 1, 1, 185000),
    (10, 5, 7, 2, 4500),
    (11, 6, 3, 1, 28500),
    (12, 7, 4, 1, 12500),
    (13, 7, 6, 4, 2500),
    (14, 8, 5, 2, 18500),
    (15, 8, 3, 1, 28500);
""")

# ============================================================
# 2. Tools
# ============================================================

def get_order(order_id):
    """
    Get basic order and customer information.
    """
    row = DB.execute(
        """
        SELECT
            o.order_id,
            o.order_date,
            o.status,
            c.customer_id,
            c.name AS customer_name,
            c.email AS customer_email,
            c.city AS customer_city
        FROM orders o
        JOIN customers c
            ON o.customer_id = c.customer_id
        WHERE o.order_id = ?
        """,
        (order_id,)
    ).fetchone()

    if not row:
        return {
            "error": f"no order {order_id}"
        }

    return dict(row)


def get_order_items(order_id):
    """
    Get all products contained in an order.
    """
    rows = DB.execute(
        """
        SELECT
            oi.order_item_id,
            oi.order_id,
            oi.product_id,
            p.name AS product_name,
            oi.quantity,
            oi.unit_price,
            (oi.quantity * oi.unit_price) AS line_total
        FROM order_items oi
        JOIN products p
            ON oi.product_id = p.product_id
        WHERE oi.order_id = ?
        ORDER BY oi.order_item_id
        """,
        (order_id,)
    ).fetchall()

    return {
        "order_id": order_id,
        "items": [dict(row) for row in rows]
    }


def get_product_stock(product_id):
    """
    Check the current stock for a product.
    """
    row = DB.execute(
        """
        SELECT
            product_id,
            name,
            price,
            stock
        FROM products
        WHERE product_id = ?
        """,
        (product_id,)
    ).fetchone()

    if not row:
        return {
            "product_id": product_id,
            "error": "product not found"
        }

    return dict(row)

def dispatch(order_id):
    """
    Irreversible action.
    The actual function only simulates dispatching.
    """
    return {
        "order_id": order_id,
        "dispatched": True,
        "message": f"Order {order_id} has been dispatched"
    }

# ============================================================
# Freely usable tools
# ============================================================

TOOLS = {
    "get_order": get_order,
    "get_order_items": get_order_items,
    "get_product_stock": get_product_stock,
}

# ============================================================
# Tools that require human approval
# ============================================================

NEEDS_HUMAN = {
    "dispatch": dispatch
}

# ============================================================
# 3. Model
# ============================================================

@traceable
def ask(system, user):
    try:
        response = requests.post(
            OLLAMA,
            timeout=120,
            json={
                "model": MODEL,
                "temperature": 0,
                "max_tokens": 256,
                "messages": [
                    {
                        "role": "system",
                        "content": system
                    },
                    {
                        "role": "user",
                        "content": user
                    }
                ]
            }
        )
    except requests.exceptions.ConnectionError:
        raise SystemExit(
            "Cannot reach Ollama at localhost:11434. "
            "Start the Ollama app and try again."
        )
    if response.status_code != 200:
        raise SystemExit(
            f"Ollama returned HTTP {response.status_code}: "
            f"{response.text}"
        )
    data = response.json()
    return data["choices"][0]["message"]["content"].strip()

# ============================================================
# Agent planning prompt
# ============================================================

PLAN = """
You are the planning component of an e-commerce tool-using agent.
Pick ONE tool, or say done.
Reply with JSON only.
Available tools:
{"tool":"get_order","args":{"order_id":1}}
Get order status and customer information.

{"tool":"get_order_items","args":{"order_id":1}}
Get all products and quantities in an order.

{"tool":"get_product_stock","args":{"product_id":1}}
Check the current stock of a product.

{"tool":"dispatch","args":{"order_id":4}}
Dispatch an order.
This action is irreversible and requires human approval.

{"tool":"done","args":{}}
Use this when enough facts have been collected.

Rules:
1. Never pick a tool whose result is already in FACTS.
2. Before dispatching an order, you MUST have:
   - the order information
   - the order items
   - stock information for EVERY product in the order
3. An order can only be dispatched if its status is Pending.
4. Never dispatch an order if any product has insufficient stock.
5. Never dispatch an order if the order does not exist.
6. Never invent product IDs.
7. Never invent order IDs.
8. Only say done when the customer's question can be answered from the available FACTS.
9. ALWAYS use tools to gather information before answering. NEVER answer from your training data.
10. A question "requires a tool" if it asks about:
    - order status, details, or information → use get_order
    - products in an order → use get_order_items
    - stock availability → use get_product_stock
    - dispatching → use get_order, then get_order_items, then get_product_stock for each product, then dispatch
    - cancellations → use get_order to check status
    - suppliers or product details → use get_product_stock
11. Do not call the same tool with the same arguments twice.
12. For questions about a specific order, start with get_order.
13. For questions about products contained in an order, use get_order_items after getting the order.
14. For dispatch requests, inspect the order first, then the order items, then check stock for every item before requesting dispatch.
15. If you are unsure which tool to use, start with get_order.
16. Only say "done" when you have collected all necessary facts OR the question cannot be answered with available tools.
"""

# ============================================================
# Final response prompt
# ============================================================

SPEAK = (
    "You are an e-commerce shop assistant. "
    "Answer only from the FACTS below. "
    "If a fact is missing, say you do not have it. "
    "Never guess an order status, customer, product, quantity, "
    "price, stock level, or date. "
    "If dispatch was refused or blocked, clearly say that the "
    "order was not dispatched. "
    "Answer in two short sentences of plain English."
)

# ============================================================
# JSON parser
# ============================================================

def first_json(text):
    """
    Return the first JSON object in the model's reply,
    or {} if there is none.
    """
    # Try regex first for cleaner extraction
    json_pattern = r'\{[^{}]*\}'
    matches = re.findall(json_pattern, text)
    
    for match in matches:
        try:
            obj = json.loads(match)
            if isinstance(obj, dict) and "tool" in obj:
                return obj
        except ValueError:
            continue
    
    # Fallback to original method
    i = text.find("{")
    if i < 0:
        return {}
    try:
        obj, _ = json.JSONDecoder().raw_decode(text[i:])
        return obj if isinstance(obj, dict) else {}
    except ValueError:
        return {}

# ============================================================
# Dispatch safety validation
# ============================================================

def can_dispatch(order_id, facts):
    """
    Deterministic safety check.
    Do NOT rely on the LLM to decide whether an order
    is safe to dispatch.
    """
    # --------------------------------------------------------
    # Find order information
    # --------------------------------------------------------

    order_fact = next(
        (
            fact["get_order"]
            for fact in facts
            if "get_order" in fact
        ),
        None
    )
    if not order_fact:
        return False, "order information is missing"
    if "error" in order_fact:
        return False, "order does not exist"

    # --------------------------------------------------------
    # Verify the requested order
    # --------------------------------------------------------

    if order_fact.get("order_id") != order_id:
        return False, "facts belong to a different order"

    # --------------------------------------------------------
    # Only Pending orders can be dispatched
    # --------------------------------------------------------

    if order_fact.get("status") != "Pending":
        return (
            False,
            f"order status is {order_fact.get('status')}; "
            "only Pending orders can be dispatched"
        )

    # --------------------------------------------------------
    # Find order items
    # --------------------------------------------------------

    items_fact = next(
        (
            fact["get_order_items"]
            for fact in facts
            if "get_order_items" in fact
        ),
        None
    )

    if not items_fact:
        return False, "order items have not been checked"

    if items_fact.get("order_id") != order_id:
        return False, "order items belong to a different order"

    items = items_fact.get("items", [])
    if not items:
        return False, "order contains no items"

    # --------------------------------------------------------
    # Collect required quantities
    # --------------------------------------------------------

    required_products = {
        item["product_id"]: item["quantity"]
        for item in items
    }

    # --------------------------------------------------------
    # Collect stock checks
    # --------------------------------------------------------

    stock_facts = {
        fact["get_product_stock"]["product_id"]:
        fact["get_product_stock"]
        for fact in facts
        if "get_product_stock" in fact
    }

    # --------------------------------------------------------
    # Every product must have been checked
    # --------------------------------------------------------

    missing_products = [
        product_id
        for product_id in required_products
        if product_id not in stock_facts
    ]

    if missing_products:
        return (
            False,
            f"stock has not been checked for products "
            f"{missing_products}"
        )

    # --------------------------------------------------------
    # Check stock levels
    # --------------------------------------------------------

    insufficient = []
    for product_id, required_quantity in required_products.items():
        stock_info = stock_facts[product_id]
        if "error" in stock_info:
            return (
                False,
                f"product {product_id} could not be found"
            )

        available = stock_info.get("stock")
        if available < required_quantity:
            insufficient.append(
                {
                    "product_id": product_id,
                    "product": stock_info.get("name"),
                    "required": required_quantity,
                    "available": available
                }
            )

    if insufficient:
        return (
            False,
            f"insufficient stock: {insufficient}"
        )

    # --------------------------------------------------------
    # Everything looks safe
    # --------------------------------------------------------

    return True, "all dispatch requirements satisfied"

# ============================================================
# 4. Agent loop
# ============================================================

def extract_order_id(q):
    """Extract order ID from question text."""
    match = re.search(r'order\s*(\d+)', q.lower())
    if match:
        return int(match.group(1))
    return None

def extract_product_id(q):
    """Extract product ID from question text."""
    # Map product names to IDs
    product_map = {
        'esp32': 6,
        'lenovo': 1,
        'thinkpad': 1,
        'dell': 2,
        'latitude': 2,
        'logitech': 3,
        'mx master': 3,
        'keyboard': 4,
        'mechanical': 4,
        'tplink': 5,
        'router': 5,
        'wifi 6': 5,
        'smart plug': 7,
        'docking station': 8,
        'usb-c': 8,
    }
    q_lower = q.lower()
    for name, pid in product_map.items():
        if name in q_lower:
            return pid
    match = re.search(r'product\s*(\d+)', q_lower)
    if match:
        return int(match.group(1))
    return None

def needs_tools(q):
    """Check if a question likely requires tools."""
    q_lower = q.lower()
    # These keywords strongly suggest tool usage
    tool_keywords = [
        'order', 'status', 'dispatch', 'cancel', 'return',
        'stock', 'product', 'supplier', 'deliver', 'ship',
        'item', 'price', 'quantity', 'customer'
    ]
    return any(kw in q_lower for kw in tool_keywords)

def suggest_tool(q, facts):
    """Suggest a tool based on question and current facts."""
    q_lower = q.lower()
    
    # Dispatch requests
    if 'dispatch' in q_lower or 'ship' in q_lower:
        order_id = extract_order_id(q)
        if order_id is not None:
            # Check if we already have order info
            has_order = any(
                'get_order' in fact and fact['get_order'].get('order_id') == order_id
                for fact in facts
            )
            if not has_order:
                return {"tool": "get_order", "args": {"order_id": order_id}}
            
            # Check if we already have order items
            has_items = any(
                'get_order_items' in fact and fact['get_order_items'].get('order_id') == order_id
                for fact in facts
            )
            if not has_items:
                return {"tool": "get_order_items", "args": {"order_id": order_id}}
            
            # Check if any product stock is missing
            items_fact = next(
                (fact['get_order_items'] for fact in facts if 'get_order_items' in fact),
                None
            )
            if items_fact:
                for item in items_fact.get('items', []):
                    pid = item['product_id']
                    has_stock = any(
                        'get_product_stock' in fact and fact['get_product_stock'].get('product_id') == pid
                        for fact in facts
                    )
                    if not has_stock:
                        return {"tool": "get_product_stock", "args": {"product_id": pid}}
            
            # If all checks pass, suggest dispatch
            return {"tool": "dispatch", "args": {"order_id": order_id}}
    
    # Order-related questions
    if 'order' in q_lower:
        order_id = extract_order_id(q)
        if order_id is not None:
            # Check if we already have order info
            has_order = any(
                'get_order' in fact and fact['get_order'].get('order_id') == order_id
                for fact in facts
            )
            if not has_order:
                return {"tool": "get_order", "args": {"order_id": order_id}}
            
            # If question is about products in the order
            if 'product' in q_lower or 'item' in q_lower:
                has_items = any(
                    'get_order_items' in fact and fact['get_order_items'].get('order_id') == order_id
                    for fact in facts
                )
                if not has_items:
                    return {"tool": "get_order_items", "args": {"order_id": order_id}}
    
    # Product/supplier questions
    if 'supplier' in q_lower or 'stock' in q_lower:
        product_id = extract_product_id(q)
        if product_id is not None:
            has_stock = any(
                'get_product_stock' in fact and fact['get_product_stock'].get('product_id') == product_id
                for fact in facts
            )
            if not has_stock:
                return {"tool": "get_product_stock", "args": {"product_id": product_id}}
    
    # Cancel/return questions - need order info first
    if 'cancel' in q_lower or 'return' in q_lower:
        order_id = extract_order_id(q)
        if order_id is not None:
            has_order = any(
                'get_order' in fact and fact['get_order'].get('order_id') == order_id
                for fact in facts
            )
            if not has_order:
                return {"tool": "get_order", "args": {"order_id": order_id}}
    
    return None

@traceable
def run(question, approve=None, quiet=False):
    facts = []
    trail = []
    blocked_action = None
    
    for step in range(MAX_STEPS):
        raw = ask(
            PLAN,
            (
                f"QUESTION: {question}\n"
                f"FACTS SO FAR: {json.dumps(facts)}"
            )
        )

        want = first_json(raw)
        name = want.get("tool")
        args = want.get("args", {})

        # ----------------------------------------------------
        # Force tool usage if model says done too early
        # ----------------------------------------------------

        if name == "done" or not name:
            if needs_tools(question):
                suggested = suggest_tool(question, facts)
                if suggested:
                    if not quiet:
                        print(f"  [forcing] model said done but question needs more info")
                        print(f"  [forcing] using {suggested['tool']}")
                    name = suggested["tool"]
                    args = suggested["args"]
                    want = {"tool": name, "args": args}
                else:
                    break
            else:
                break

        # ----------------------------------------------------
        # Human approval tools
        # ----------------------------------------------------

        if name in NEEDS_HUMAN:
            if name == "dispatch":
                order_id = args.get("order_id")
                if order_id is None:
                    blocked_action = (
                        "Dispatch was blocked because no order ID "
                        "was provided."
                    )
                    if not quiet:
                        print(
                            "  [blocked] dispatch requires order_id"
                        )
                    break

                # --------------------------------------------
                # Deterministic dispatch safety check
                # --------------------------------------------

                safe, reason = can_dispatch(
                    order_id,
                    facts
                )

                if not safe:
                    blocked_action = (
                        f"Dispatch was blocked: {reason}."
                    )
                    if not quiet:
                        print(
                            f"  [blocked] dispatch: {reason}"
                        )
                    break

            # ------------------------------------------------
            # Human approval
            # ------------------------------------------------

            if approve is None:
                ok = (
                    input(
                        f"  approve {name}({args})? [y/N] "
                    )
                    .strip()
                    .lower()
                    == "y"
                )
            else:
                ok = approve

            trail.append(
                f"{name}:{'approved' if ok else 'REFUSED'}"
            )

            if not quiet:
                print(
                    f"  [gate] {name} "
                    f"{'approved' if ok else 'REFUSED, nothing sent'}"
                )

            # ------------------------------------------------
            # Execute irreversible action only if approved
            # ------------------------------------------------

            if ok:
                result = NEEDS_HUMAN[name](**args)

            else:
                result = "refused by human"

            facts.append({
                name: result
            })

            continue

        # ----------------------------------------------------
        # Unknown tool
        # ----------------------------------------------------

        if name not in TOOLS:
            if not quiet:
                print(
                    f"  [blocked] {name} is not a tool"
                )
            break

        # ----------------------------------------------------
        # Prevent repeated tool call
        # ----------------------------------------------------

        tool_signature = (
            name,
            json.dumps(
                args,
                sort_keys=True
            )
        )

        if tool_signature in trail:
            if not quiet:
                print(
                    f"  [blocked] repeated tool call: "
                    f"{name}({args})"
                )
            break

        # ----------------------------------------------------
        # Execute normal tool
        # ----------------------------------------------------

        result = TOOLS[name](**args)
        trail.append(tool_signature)
        facts.append({
            name: result
        })

        if not quiet:
            print(
                f"  [tool] {name}({args}) -> {result}"
            )

    # ========================================================
    # Generate final customer response
    # ========================================================

    if blocked_action:
        answer = blocked_action

    else:
        answer = ask(
            SPEAK,
            (
                f"FACTS: {json.dumps(facts)}\n"
                f"CUSTOMER: {question}"
            )
        )

    return {
        "answer": answer,
        "trail": trail,
        "facts": facts
    }

# ============================================================
# Naive agent
# ============================================================

def naive(question):
    return ask(
        (
            "You are a shop assistant. "
            "Reply in two short sentences. "
            "Do not use tools."
        ),
        question
    )

# ============================================================
# 5. Run it
# ============================================================

SAMPLE_QUESTIONS = [
    "What is the status of order 1?",
    "What products are in order 1?",
    "Is there enough stock to dispatch order 4?",
    "Dispatch order 4",
]

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--naive",
        action="store_true"
    )
    parser.add_argument(
        "--ask"
    )
    parser.add_argument(
        "--approve",
        action="store_true"
    )
    args = parser.parse_args()
    questions = (
        [args.ask]
        if args.ask
        else SAMPLE_QUESTIONS
    )
    for question in questions:
        print(
            f"\nCUSTOMER: {question}"
        )

        if args.naive:
            print(
                f"     BOT: {naive(question)}"
            )
        else:
            output = run(
                question,
                approve=args.approve or None
            )
            print(
                f"     BOT: {output['answer']}"
            )
            print(
                "   tools: "
                f"{' -> '.join(map(str, output['trail'])) or 'none'}"
            )