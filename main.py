import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pymongo
from pymongo import MongoClient

# MongoDB connection
def get_mongodb_connection():
    # Get MongoDB connection string from Streamlit secrets
    
    mongo_uri = st.secrets["MONGO_URI"]
    try:
        client = MongoClient(mongo_uri)
        db = client["pvs_db"]
        st.write(db)
        collection = db["pvs_db"]
        return collection
    except Exception as e:
        st.error(f"Failed to connect to MongoDB: {e}")
        return None

# Get supply data from MongoDB
def get_supply_data():
    collection = get_mongodb_connection()
    if collection:
        data = list(collection.find({}, {"_id": 0, "timestamp": 1, "total_supply": 1}))
        if data:
            df = pd.DataFrame(data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df = df.sort_values('timestamp')
            return df
    return pd.DataFrame(columns=['timestamp', 'total_supply'])

# Add new supply data to MongoDB
def add_supply_data(timestamp, total_supply):
    collection = get_mongodb_connection()
    if collection:
        try:
            collection.insert_one({
                "timestamp": timestamp.isoformat(),
                "total_supply": total_supply
            })
            return True
        except Exception as e:
            st.error(f"Failed to add data: {e}")
    return False

# Calculate supply change metrics
def calculate_metrics(df):
    if df.empty or len(df) < 2:
        return {
            "24h": 0,
            "7d": 0,
            "30d": 0,
            "total": 0
        }
    
    latest = df.iloc[-1]
    latest_supply = latest['total_supply']
    latest_time = latest['timestamp']
    
    # 24h change
    day_ago = latest_time - timedelta(days=1)
    day_df = df[df['timestamp'] >= day_ago]
    day_change = 0
    if not day_df.empty and len(day_df) > 1:
        first_day = day_df.iloc[0]['total_supply']
        day_change = ((latest_supply - first_day) / first_day) * 100 if first_day != 0 else 0
    
    # 7d change
    week_ago = latest_time - timedelta(days=7)
    week_df = df[df['timestamp'] >= week_ago]
    week_change = 0
    if not week_df.empty and len(week_df) > 1:
        first_week = week_df.iloc[0]['total_supply']
        week_change = ((latest_supply - first_week) / first_week) * 100 if first_week != 0 else 0
    
    # 30d change
    month_ago = latest_time - timedelta(days=30)
    month_df = df[df['timestamp'] >= month_ago]
    month_change = 0
    if not month_df.empty and len(month_df) > 1:
        first_month = month_df.iloc[0]['total_supply']
        month_change = ((latest_supply - first_month) / first_month) * 100 if first_month != 0 else 0
    
    # Total change
    if len(df) > 1:
        first = df.iloc[0]['total_supply']
        total_change = ((latest_supply - first) / first) * 100 if first != 0 else 0
    else:
        total_change = 0
    
    return {
        "24h": day_change,
        "7d": week_change,
        "30d": month_change,
        "total": total_change
    }

# Create the supply chart
def create_supply_chart(df):
    if df.empty:
        return go.Figure()
    
    fig = px.line(
        df, 
        x='timestamp', 
        y='total_supply',
        title='PVS Total Supply Over Time',
        labels={'timestamp': 'Date', 'total_supply': 'Total Supply'}
    )
    
    # Add a note that downward trend is positive for the price
    fig.add_annotation(
        x=0.5,
        y=-0.15,
        xref="paper",
        yref="paper",
        text="Note: Decreasing total supply is generally positive for price",
        showarrow=False,
        font=dict(size=10, color="grey"),
        align="center",
    )
    
    return fig

# App main function
def main():
    st.set_page_config(
        page_title="PVS Crypto Dashboard",
        page_icon="📊",
        layout="wide"
    )
    
    # App title
    st.title("PVS Cryptocurrency Dashboard")
    st.write("Track price and supply metrics for PVS on Solana")
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["Dashboard", "Supply History", "Add Data"])
    
    # Get data
    #supply_df = get_supply_data()
    
    # Tab 1: Main Dashboard
    with tab1:
        st.header("PVS Price Chart")
        
        # Dextools iframe for price chart
        st.components.v1.iframe(
            "https://www.dextools.io/app/en/solana/pair-explorer/98nocLbiDi9ykAjwAUJW9fnYZsf4L4KLCfH7U2LFXDsv?t=1744397006636",
            height=600,
            scrolling=True
        )
        
        st.header("PVS Supply Metrics")
        
        if not supply_df.empty:
            # Calculate metrics
            metrics = calculate_metrics(supply_df)
            
            # Display metrics in columns
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "24h Supply Change", 
                    f"{metrics['24h']:.2f}%",
                    delta=f"{metrics['24h']:.2f}%" if metrics['24h'] < 0 else f"{metrics['24h']:.2f}%",
                    delta_color="normal" if metrics['24h'] >= 0 else "inverse"
                )
            
            with col2:
                st.metric(
                    "7d Supply Change", 
                    f"{metrics['7d']:.2f}%",
                    delta=f"{metrics['7d']:.2f}%" if metrics['7d'] < 0 else f"{metrics['7d']:.2f}%",
                    delta_color="normal" if metrics['7d'] >= 0 else "inverse"
                )
            
            with col3:
                st.metric(
                    "30d Supply Change", 
                    f"{metrics['30d']:.2f}%",
                    delta=f"{metrics['30d']:.2f}%" if metrics['30d'] < 0 else f"{metrics['30d']:.2f}%",
                    delta_color="normal" if metrics['30d'] >= 0 else "inverse"
                )
            
            with col4:
                st.metric(
                    "Total Supply Change", 
                    f"{metrics['total']:.2f}%",
                    delta=f"{metrics['total']:.2f}%" if metrics['total'] < 0 else f"{metrics['total']:.2f}%",
                    delta_color="normal" if metrics['total'] >= 0 else "inverse"
                )
            
            # Latest supply
            latest_supply = supply_df.iloc[-1]['total_supply'] if not supply_df.empty else 0
            st.metric("Current Total Supply", f"{latest_supply:,.0f}")
        
        else:
            st.warning("No supply data available. Please add data in the 'Add Data' tab.")
    
    # Tab 2: Supply History
    with tab2:
        st.header("PVS Total Supply History")
        
        if not supply_df.empty:
            # Show chart
            supply_chart = create_supply_chart(supply_df)
            st.plotly_chart(supply_chart, use_container_width=True)
            
            # Show data table
            st.subheader("Historical Data")
            display_df = supply_df.copy()
            display_df['timestamp'] = display_df['timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
            st.dataframe(display_df)
        else:
            st.warning("No supply data available. Please add data in the 'Add Data' tab.")
    
    # Tab 3: Add Data
    with tab3:
        st.header("Add New Supply Data")
        
        # Input form
        with st.form("supply_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                input_date = st.date_input("Date", datetime.now())
            
            with col2:
                input_time = st.time_input("Time", datetime.now().time())
            
            # Combine date and time
            timestamp = datetime.combine(input_date, input_time)
            
            total_supply = st.number_input("Total Supply", min_value=0.0, format="%.2f")
            
            submit = st.form_submit_button("Add Data")
            
            if submit:
                if add_supply_data(timestamp, total_supply):
                    st.success(f"Successfully added supply data: {total_supply} at {timestamp}")
                    st.experimental_rerun()
                else:
                    st.error("Failed to add data to MongoDB")

if __name__ == "__main__":
    main()
