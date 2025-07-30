import streamlit as st
import pandas as pd
import time
from datetime import datetime
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Purchase Management",
    page_icon="🚢",
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
    h1, h2 {
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
</style>
""", unsafe_allow_html=True)


# --- DATA & CONSTANTS (Copied from app.py for consistency) ---
OIL_DENSITIES = {
    "Crude Degummed Oil": 0.92, "Palm Oil": 0.915,
    "Palm Degummed": 0.918, "Crude Sunflower Oil": 0.922
}
OIL_TYPES = list(OIL_DENSITIES.keys())
SHIPMENT_STATUSES = ["In Transit", "At Port", "Reached Factory"]

# --- DATA FILE MANAGEMENT ---
DATA_DIR = "data"
PURCHASES_FILE = os.path.join(DATA_DIR, "purchases.csv")
INVENTORY_FILE = os.path.join(DATA_DIR, "inventory.csv")

# --- HELPER FUNCTIONS (from app.py) ---
def load_data():
    purchases_df = pd.read_csv(PURCHASES_FILE)
    inventory_df = pd.read_csv(INVENTORY_FILE)
    return purchases_df, inventory_df

def save_data(purchases_df=None, inventory_df=None):
    if purchases_df is not None:
        purchases_df.to_csv(PURCHASES_FILE, index=False)
    if inventory_df is not None:
        inventory_df.to_csv(INVENTORY_FILE, index=False)

def get_simulated_oil_prices():
    day_of_year = time.localtime().tm_yday
    base_price = 80000 + (day_of_year * 15)
    prices = {
        "Crude Degummed Oil": base_price, "Palm Oil": base_price - 5000,
        "Palm Degummed": base_price - 4500, "Crude Sunflower Oil": base_price + 3000
    }
    previous_day_prices = {k: v * 0.99 for k, v in prices.items()}
    return prices, previous_day_prices

# --- PAGE UI ---
st.title("🚢 Purchase & Shipment Management")
st.markdown("Log new crude oil purchases and track their status until they arrive at the factory.")

# Load data
purchases, inventory = load_data()
_, prev_prices = get_simulated_oil_prices()

# --- FORM TO ADD NEW PURCHASE ---
st.header("Log a New Purchase")
with st.form(key="new_purchase_form", clear_on_submit=True):
    st.subheader("Enter Shipment Details")
    
    col1, col2 = st.columns(2)
    with col1:
        supplier = st.text_input("Supplier Name", placeholder="e.g., Global Oil Traders")
        oil_type = st.selectbox("Type of Oil", options=OIL_TYPES)
        quantity_mt = st.number_input("Quantity (in Metric Tonnes)", min_value=0.1, step=0.1, format="%.2f")
    
    with col2:
        price_per_mt = st.number_input(
            f"Purchase Price per MT (Yesterday's Price: ₹{prev_prices[oil_type]:,.2f})",
            value=prev_prices[oil_type],
            step=100.0
        )
        purchase_date = st.date_input("Purchase Date", datetime.now())
    
    submit_button = st.form_submit_button(label="Log Purchase")

    if submit_button:
        if not supplier or quantity_mt <= 0:
            st.warning("Please fill in all required fields (Supplier, Quantity > 0).")
        else:
            total_cost = quantity_mt * price_per_mt
            shipment_id = f"SHP-{int(time.time())}" # Unique ID based on timestamp
            
            new_purchase = pd.DataFrame([{
                "ShipmentID": shipment_id,
                "OilType": oil_type,
                "QuantityMT": quantity_mt,
                "PricePerMT": price_per_mt,
                "TotalCost": total_cost,
                "PurchaseDate": purchase_date.strftime("%Y-%m-%d"),
                "Status": "In Transit", # Default status
                "Supplier": supplier
            }])
            
            purchases = pd.concat([purchases, new_purchase], ignore_index=True)
            save_data(purchases_df=purchases)
            st.success(f"Successfully logged new shipment {shipment_id} from {supplier}.")


st.markdown("<hr>", unsafe_allow_html=True)

# --- DISPLAY AND MANAGE SHIPMENTS ---
st.header("Current Shipments")

if purchases.empty:
    st.info("No purchases logged yet. Use the form above to add your first shipment.")
else:
    # Create an editable copy of the dataframe for status updates
    editable_purchases = purchases.copy()
    
    # Use st.data_editor to make the status column selectable
    edited_df = st.data_editor(
        editable_purchases,
        column_config={
            "Status": st.column_config.SelectboxColumn(
                "Shipment Status",
                options=SHIPMENT_STATUSES,
                required=True,
            ),
            "TotalCost": st.column_config.NumberColumn(
                "Total Cost (INR)",
                format="₹%,.2f"
            ),
            "PricePerMT": st.column_config.NumberColumn(
                "Price per MT (INR)",
                format="₹%,.2f"
            )
        },
        disabled=["ShipmentID", "OilType", "QuantityMT", "PricePerMT", "TotalCost", "PurchaseDate", "Supplier"],
        use_container_width=True,
        key="purchase_editor"
    )

    # Check for changes in the status
    if not edited_df.equals(purchases):
        # Find which rows were changed
        for index, row in edited_df.iterrows():
            original_status = purchases.at[index, 'Status']
            new_status = row['Status']
            
            if original_status != new_status:
                # Special logic for "Reached Factory"
                if new_status == "Reached Factory" and original_status != "Reached Factory":
                    oil_type = row['OilType']
                    quantity = row['QuantityMT']
                    
                    # Update inventory
                    inv_index = inventory.index[(inventory['OilType'] == oil_type) & (inventory['InventoryType'] == 'Crude')].tolist()
                    if inv_index:
                        inventory.loc[inv_index[0], 'QuantityMT'] += quantity
                        st.success(f"Shipment {row['ShipmentID']}: Status updated. Added {quantity} MT of {oil_type} to Crude Inventory.")
                    
        # Save both dataframes
        save_data(purchases_df=edited_df, inventory_df=inventory)
        st.info("Changes saved! Refreshing...")
        time.sleep(1) # Give user time to read the message
        st.rerun()

