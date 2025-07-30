import streamlit as st
import pandas as pd
import os
import time

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Inventory & Refining",
    page_icon="🏭",
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

# --- DATA & CONSTANTS ---
OIL_DENSITIES = {
    "Crude Degummed Oil": 0.92, "Palm Oil": 0.915,
    "Palm Degummed": 0.918, "Crude Sunflower Oil": 0.922
}
OIL_TYPES = list(OIL_DENSITIES.keys())

# --- DATA FILE MANAGEMENT ---
DATA_DIR = "data"
INVENTORY_FILE = os.path.join(DATA_DIR, "inventory.csv")

# --- HELPER FUNCTIONS ---
def load_inventory():
    """Loads the inventory data from the CSV file."""
    return pd.read_csv(INVENTORY_FILE)

def save_inventory(inventory_df):
    """Saves the inventory DataFrame back to the CSV file."""
    inventory_df.to_csv(INVENTORY_FILE, index=False)

# --- PAGE UI ---
st.title("🏭 Inventory & Refining Management")
st.markdown("View your current stock levels and manage the oil refining process.")

inventory_df = load_inventory()

# --- REFINING MODULE ---
st.header("Refining Module")
col1, col2 = st.columns([1, 2]) # Give more space to the inventory tables

with col1:
    with st.form(key="refining_form"):
        st.subheader("Start a New Refining Batch")
        
        # Get current crude stock to display in the selectbox
        crude_inventory = inventory_df[inventory_df['InventoryType'] == 'Crude'].set_index('OilType')
        
        # Create labels with stock info
        oil_options_labels = [
            f"{oil_type} (Available: {crude_inventory.loc[oil_type, 'QuantityMT']:.2f} MT)"
            for oil_type in OIL_TYPES
        ]
        
        selected_label = st.selectbox("Select Oil to Refine", options=oil_options_labels)
        
        # Extract the oil type from the selected label
        oil_to_refine = selected_label.split(" (")[0]
        
        max_refine_qty = crude_inventory.loc[oil_to_refine, 'QuantityMT']
        
        quantity_to_refine = st.number_input(
            "Quantity to Refine (in MT)",
            min_value=0.0,
            max_value=float(max_refine_qty), # Ensure max value is a float
            step=0.1,
            format="%.2f"
        )
        
        submit_button = st.form_submit_button(label="Start Refining")

        if submit_button:
            if quantity_to_refine <= 0:
                st.warning("Please enter a quantity greater than zero.")
            elif quantity_to_refine > max_refine_qty:
                st.error(f"Cannot refine {quantity_to_refine} MT. Only {max_refine_qty:.2f} MT of {oil_to_refine} is available.")
            else:
                # Proceed with refining logic
                # Get index for crude oil
                crude_idx = inventory_df[(inventory_df['OilType'] == oil_to_refine) & (inventory_df['InventoryType'] == 'Crude')].index[0]
                # Get index for refined oil
                refined_idx = inventory_df[(inventory_df['OilType'] == oil_to_refine) & (inventory_df['InventoryType'] == 'Refined')].index[0]
                
                # Update quantities
                inventory_df.loc[crude_idx, 'QuantityMT'] -= quantity_to_refine
                inventory_df.loc[refined_idx, 'QuantityMT'] += quantity_to_refine
                
                save_inventory(inventory_df)
                
                st.success(f"Successfully refined {quantity_to_refine:.2f} MT of {oil_to_refine}. Inventory updated.")
                time.sleep(1) # Pause to let user read the message
                st.rerun()

with col2:
    # --- INVENTORY DISPLAY ---
    st.subheader("Current Stock Levels (MT)")
    
    # Pivot the table for a more readable side-by-side view
    inventory_pivot = inventory_df.pivot(index='OilType', columns='InventoryType', values='QuantityMT')
    inventory_pivot = inventory_pivot[['Crude', 'Refined']] # Ensure column order
    
    st.dataframe(
        inventory_pivot.style.format("{:.2f}").highlight_max(axis=0, color='#d4edda').highlight_min(axis=0, color='#f8d7da'),
        use_container_width=True
    )

st.markdown("<hr>", unsafe_allow_html=True)
st.info("The table on the right shows your current inventory. Use the module on the left to convert 'Crude' stock into 'Refined' stock.")

