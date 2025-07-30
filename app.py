import streamlit as st
import pandas as pd
import os
import time
from datetime import datetime

# --- APP CONFIGURATION ---
st.set_page_config(
    page_title="Oil Logistics Dashboard",
    page_icon="🛢️",
    layout="wide"
)

# --- MODERN UI STYLING ---
st.markdown("""
<style>
    /* Main app background */
    .stApp {
        background-color: #f0f2f6;
    }

    /* Card-like containers */
    .stMetric, .stDataFrame, [data-testid="stExpander"] {
        border-radius: 10px;
        padding: 20px !important;
        background-color: #ffffff;
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        border: 1px solid #e6e6e6;
    }

    [data-testid="stMetric"] {
        padding: 20px !important;
    }

    /* Metric label styling */
    [data-testid="stMetricLabel"] {
        font-size: 1.1rem;
        color: #4a4a4a;
        font-weight: 600;
    }
    
    /* Main titles */
    h1, h2 {
        color: #1a2a6c; /* A deep blue */
    }

    h3 {
        color: #333333;
    }

    /* Expander styling */
    [data-testid="stExpander"] {
        background-color: #fafafa;
    }
    [data-testid="stExpander"] > summary > div > p {
        font-weight: 600;
        color: #1a2a6c;
    }

</style>
""", unsafe_allow_html=True)


# --- CORE DATA & CONSTANTS ---
# Standard densities (kg/Litre) to convert MT to Litres. 1 MT = 1000kg.
OIL_DENSITIES = {
    "Crude Degummed Oil": 0.92,
    "Palm Oil": 0.915,
    "Palm Degummed": 0.918,
    "Crude Sunflower Oil": 0.922
}
OIL_TYPES = list(OIL_DENSITIES.keys())
TRANSPORT_COST_PER_KM = 12
IGST_RATE = 0.05 # 5%

# --- DATA FILE MANAGEMENT ---
DATA_DIR = "data"
PURCHASES_FILE = os.path.join(DATA_DIR, "purchases.csv")
SALES_FILE = os.path.join(DATA_DIR, "sales.csv")
INVENTORY_FILE = os.path.join(DATA_DIR, "inventory.csv")

def initialize_data_files():
    """Creates the data directory and necessary CSV files if they don't exist."""
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(PURCHASES_FILE):
        pd.DataFrame(columns=[
            "ShipmentID", "OilType", "QuantityMT", "PricePerMT", "TotalCost",
            "PurchaseDate", "Status", "Supplier"
        ]).to_csv(PURCHASES_FILE, index=False)
    if not os.path.exists(SALES_FILE):
        pd.DataFrame(columns=[
            "OrderID", "VendorName", "Destination", "DistanceKM", "OilType",
            "QuantityMT", "SalePrice", "OrderDate", "Status"
        ]).to_csv(SALES_FILE, index=False)
    if not os.path.exists(INVENTORY_FILE):
        inventory_df = pd.DataFrame({
            "OilType": [oil for oil in OIL_TYPES for _ in (0, 1)],
            "InventoryType": ["Crude", "Refined"] * len(OIL_TYPES),
            "QuantityMT": [0.0] * len(OIL_TYPES) * 2
        })
        inventory_df.to_csv(INVENTORY_FILE, index=False)

# --- HELPER FUNCTIONS (The Brains of the App) ---

def load_data():
    """Loads all data from CSV files into pandas DataFrames."""
    purchases_df = pd.read_csv(PURCHASES_FILE)
    sales_df = pd.read_csv(SALES_FILE)
    inventory_df = pd.read_csv(INVENTORY_FILE)
    return purchases_df, sales_df, inventory_df

def save_data(purchases_df=None, sales_df=None, inventory_df=None):
    """Saves updated DataFrames back to their CSV files."""
    if purchases_df is not None:
        purchases_df.to_csv(PURCHASES_FILE, index=False)
    if sales_df is not None:
        sales_df.to_csv(SALES_FILE, index=False)
    if inventory_df is not None:
        inventory_df.to_csv(INVENTORY_FILE, index=False)

def get_simulated_oil_prices():
    """
    Simulates current and previous day's crude oil prices per MT.
    In a real app, this would be an API call.
    """
    day_of_year = time.localtime().tm_yday
    base_price = 80000 + (day_of_year * 15)
    
    prices = {
        "Crude Degummed Oil": base_price,
        "Palm Oil": base_price - 5000,
        "Palm Degummed": base_price - 4500,
        "Crude Sunflower Oil": base_price + 3000
    }
    
    previous_day_prices = {k: v * 0.99 for k, v in prices.items()}
    return prices, previous_day_prices

def calculate_sale_price(oil_type, quantity_mt, distance_km):
    """
    Calculates the final sale price based on current market rates,
    transport, premium, and taxes.
    """
    if quantity_mt <= 0 or distance_km <= 0:
        return 0, 0

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

# --- MAIN APP UI ---

initialize_data_files()
purchases, sales, inventory = load_data()

st.title("🛢️ Crude Oil Logistics Dashboard")
st.markdown("Welcome to your central hub for managing oil purchases, inventory, and sales.")

# --- Live Price Ticker ---
st.header("📈 Live Market Prices")
current_prices, prev_prices = get_simulated_oil_prices()
price_cols = st.columns(len(OIL_TYPES))
for col, oil in zip(price_cols, OIL_TYPES):
    with col:
        delta = current_prices[oil] - prev_prices[oil]
        delta_color = "normal" if delta < 0 else "inverse"
        st.metric(
            label=f"Current {oil} (per MT)",
            value=f"₹{current_prices[oil]:,.2f}",
            delta=f"₹{delta:,.2f} vs yesterday",
            delta_color=delta_color
        )

st.markdown("<hr>", unsafe_allow_html=True)

# --- Key Metrics ---
st.header("📊 Operational Overview")
kpi_cols = st.columns(4)

total_crude_stock = inventory[inventory['InventoryType'] == 'Crude']['QuantityMT'].sum()
total_refined_stock = inventory[inventory['InventoryType'] == 'Refined']['QuantityMT'].sum()
active_shipments = purchases[purchases['Status'].isin(['In Transit', 'At Port'])].shape[0]
pending_sales = sales[sales['Status'].isin(['Under Process', 'Confirmed'])].shape[0]

kpi_cols[0].metric("📦 Total Crude Stock", f"{total_crude_stock:,.2f} MT")
kpi_cols[1].metric("✅ Total Refined Stock", f"{total_refined_stock:,.2f} MT")
kpi_cols[2].metric("🚢 Active Shipments", f"{active_shipments}")
kpi_cols[3].metric("📋 Pending Sales Orders", f"{pending_sales}")

st.markdown("<hr>", unsafe_allow_html=True)

# --- Inventory & Recent Activity ---
st.header("📒 Inventory & Recent Activity")
col1, col2 = st.columns(2)

with col1:
    st.subheader("Refined (Sellable) Inventory")
    refined_inventory = inventory[inventory['InventoryType'] == 'Refined'].set_index('OilType')
    st.dataframe(refined_inventory[['QuantityMT']], use_container_width=True)

with col2:
    st.subheader("Recent Sales Orders")
    st.dataframe(sales.tail(5), use_container_width=True)

st.subheader("Recent Purchases")
st.dataframe(purchases.tail(5), use_container_width=True)

# --- Data Upload Section ---
with st.expander("⬆️ Upload & Manage Data Files"):
    st.info("Upload your existing CSV files here. The app will use them as the data source.")
    
    uploaded_purchases = st.file_uploader("Upload purchases.csv", type="csv")
    if uploaded_purchases:
        df = pd.read_csv(uploaded_purchases)
        df.to_csv(PURCHASES_FILE, index=False)
        st.success("Purchases file updated!")
        st.rerun()

    uploaded_sales = st.file_uploader("Upload sales.csv", type="csv")
    if uploaded_sales:
        df = pd.read_csv(uploaded_sales)
        df.to_csv(SALES_FILE, index=False)
        st.success("Sales file updated!")
        st.rerun()

    uploaded_inventory = st.file_uploader("Upload inventory.csv", type="csv")
    if uploaded_inventory:
        df = pd.read_csv(uploaded_inventory)
        df.to_csv(INVENTORY_FILE, index=False)
        st.success("Inventory file updated!")
        st.rerun()

st.sidebar.success("Navigate to other pages using the menu above.")
