import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Sales Management",
    page_icon="📈",
    layout="wide"
)

# --- MODERN UI STYLING (from app.py) ---
st.markdown("""
<style>
    .stApp {
        background-color: #f0f2f6;
    }
    .stMetric, .stDataFrame, [data-testid="stExpander"], [data-testid="stForm"] {
        border-radius: 10px;
        padding: 20px !important;
        background-color: #ffffff;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        border: 1px solid #e6e6e6;
    }
    h1, h2, h3 {
        color: #1a2a6c;
    }
    .stButton>button {
        background-color: #1a2a6c;
        color: white;
        border-radius: 5px;
        padding: 10px 20px;
        border: none;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #293d8b;
    }
    .price-display {
        background-color: #e6f7ff;
        border-left: 5px solid #1a2a6c;
        padding: 15px;
        border-radius: 5px;
        margin-top: 10px;
    }
</style>
""", unsafe_allow_html=True)


# --- DATA & CONSTANTS ---
OIL_DENSITIES = {
    "Crude Degummed Oil": 0.92, "Palm Oil": 0.915,
    "Palm Degummed": 0.918, "Crude Sunflower Oil": 0.922
}
OIL_TYPES = list(OIL_DENSITIES.keys())
TRANSPORT_COST_PER_KM = 12
IGST_RATE = 0.05 # 5%
ORDER_STATUSES = ["Under Process", "Confirmed", "Dispatched", "Fulfilled"]


# --- DATA FILE MANAGEMENT ---
DATA_DIR = "data"
SALES_FILE = os.path.join(DATA_DIR, "sales.csv")
INVENTORY_FILE = os.path.join(DATA_DIR, "inventory.csv")

# --- HELPER FUNCTIONS ---
def load_data():
    sales_df = pd.read_csv(SALES_FILE)
    inventory_df = pd.read_csv(INVENTORY_FILE)
    return sales_df, inventory_df

def save_data(sales_df=None, inventory_df=None):
    if sales_df is not None:
        sales_df.to_csv(SALES_FILE, index=False)
    if inventory_df is not None:
        inventory_df.to_csv(INVENTORY_FILE, index=False)

def get_simulated_oil_prices():
    day_of_year = time.localtime().tm_yday
    base_price = 80000 + (day_of_year * 15)
    prices = {
        "Crude Degummed Oil": base_price, "Palm Oil": base_price - 5000,
        "Palm Degummed": base_price - 4500, "Crude Sunflower Oil": base_price + 3000
    }
    return prices, {k: v * 0.99 for k, v in prices.items()}

def calculate_sale_price(oil_type, quantity_mt, distance_km):
    if quantity_mt <= 0: return 0, 0
    current_prices, _ = get_simulated_oil_prices()
    density = OIL_DENSITIES[oil_type]
    base_oil_price = current_prices[oil_type] * quantity_mt
    quantity_litres = (quantity_mt * 1000) / density
    premium_cost = quantity_litres * 10
    transport_cost = distance_km * TRANSPORT_COST_PER_KM
    sub_total = base_oil_price + premium_cost + transport_cost
    gst_amount = sub_total * IGST_RATE
    total_price = sub_total + gst_amount
    final_price = round(total_price)
    price_per_lt = round(final_price / quantity_litres, 2) if quantity_litres > 0 else 0
    return final_price, price_per_lt


# --- PAGE UI ---
st.title("📈 Sales & Order Management")
st.markdown("Create new sales orders and track their fulfillment status.")

sales, inventory = load_data()

# --- FORM TO CREATE NEW SALE ---
st.header("Create a New Sales Order")

with st.form(key="new_sale_form"):
    col1, col2 = st.columns(2)
    with col1:
        vendor_name = st.text_input("Vendor Name", placeholder="e.g., National Retailers")
        destination = st.text_input("Destination", placeholder="e.g., Mumbai Warehouse")
        distance_km = st.number_input("Distance to Destination (KM)", min_value=0, step=10)

    with col2:
        refined_inventory = inventory[inventory['InventoryType'] == 'Refined'].set_index('OilType')
        oil_options_labels = [
            f"{oil_type} (Available: {refined_inventory.loc[oil_type, 'QuantityMT']:.2f} MT)"
            for oil_type in OIL_TYPES
        ]
        selected_label = st.selectbox("Select Oil Type", options=oil_options_labels)
        oil_type = selected_label.split(" (")[0]
        
        quantity_mt = st.number_input("Quantity to Sell (MT)", min_value=0.1, step=0.1, format="%.2f")
        order_date = st.date_input("Order Date", datetime.now())

    # --- DYNAMIC PRICE PREVIEW ---
    final_price, price_per_lt = calculate_sale_price(oil_type, quantity_mt, distance_km)
    st.markdown("### Price Calculation Preview")
    st.markdown(
        f"""
        <div class="price-display">
            <strong>Total Sale Price:</strong> ₹ {final_price:,.2f}<br>
            <strong>Price per Litre:</strong> ₹ {price_per_lt:,.2f}
        </div>
        """, unsafe_allow_html=True)
    
    submit_button = st.form_submit_button(label="Book Order")

    if submit_button:
        if not vendor_name or not destination or quantity_mt <= 0 or distance_km <= 0:
            st.warning("Please fill in all fields with valid values.")
        else:
            available_stock = refined_inventory.loc[oil_type, 'QuantityMT']
            order_id = f"ORD-{int(time.time())}"
            
            if quantity_mt > available_stock:
                # Not enough stock, order is under process
                status = "Under Process"
                st.warning(f"⚠️ Order booked as 'Under Process'. Not enough refined stock ({available_stock:.2f} MT) for {oil_type}. Please refine more.")
            else:
                # Enough stock, confirm the order and deduct from inventory
                status = "Confirmed"
                refined_idx = inventory[(inventory['OilType'] == oil_type) & (inventory['InventoryType'] == 'Refined')].index[0]
                inventory.loc[refined_idx, 'QuantityMT'] -= quantity_mt
                save_data(inventory_df=inventory)
                st.success(f"✅ Order {order_id} Confirmed! {quantity_mt:.2f} MT of {oil_type} deducted from refined inventory.")

            new_sale = pd.DataFrame([{
                "OrderID": order_id, "VendorName": vendor_name, "Destination": destination,
                "DistanceKM": distance_km, "OilType": oil_type, "QuantityMT": quantity_mt,
                "SalePrice": final_price, "OrderDate": order_date.strftime("%Y-%m-%d"), "Status": status
            }])
            
            sales = pd.concat([sales, new_sale], ignore_index=True)
            save_data(sales_df=sales)
            time.sleep(2)
            st.rerun()

st.markdown("<hr>", unsafe_allow_html=True)

# --- DISPLAY AND MANAGE SALES ORDERS ---
st.header("All Sales Orders")
if sales.empty:
    st.info("No sales orders yet. Use the form above to create one.")
else:
    edited_sales = st.data_editor(
        sales,
        column_config={
            "Status": st.column_config.SelectboxColumn("Order Status", options=ORDER_STATUSES, required=True),
            "SalePrice": st.column_config.NumberColumn("Total Sale Price (INR)", format="₹%,.2f")
        },
        disabled=list(sales.columns.drop("Status")),
        use_container_width=True,
        key="sales_editor"
    )
    
    if not edited_sales.equals(sales):
        save_data(sales_df=edited_sales)
        st.toast("Order status updated!")
        time.sleep(1)
        st.rerun()
