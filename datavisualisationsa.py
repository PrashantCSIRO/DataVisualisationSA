import streamlit as st
import pandas as pd
import numpy as np
import seaborn as sns
import plotly.express as px
from datetime import datetime

# Set the app configuration
st.set_page_config(layout="wide", page_title="Brine Data Visualiser")
st.title("Brine Data Visualiser")

# Add user instructions
st.sidebar.header("Instructions")
st.sidebar.markdown("""
### How to Use the App:
1. **Upload Your Data**:
   - Use the **"Upload spreadsheet"** button to upload your data file.
   - Supported file formats: `.csv`, `.xls`, `.xlsx`.
   - The data must be cleaned and formatted correctly for the app to work properly. 
   - The first column should contain the parameters, and the first row should contain the sampling dates.
   - The samples types are: Normal Grab Sample.
   - Fractions are: T - Total, D - Dissolved, N - Null.
   - The Parameter column has concatenated values contanining the parameter name, fraction and unit in parenthesis. The format is: Parameter - Fraction (Unit).
   - The cells with no values or < LOR have been replaced with 0.                      

2. **Scatter Plot**:
   - Select two parameters for the X-axis and Y-axis using the dropdown menus.
   - Use the **"Select sites for scatter plot"** option to filter data by specific sites.
   - The scatter plot will display the relationship between the selected parameters for the chosen sites.

3. **Time Series Plot**:
   - Select one or more parameters to visualize over time using the dropdown menu.
   - Use the **"Select sites for time series plot"** option to filter data by specific sites.
   - The time series plot will display the selected parameters as dots over time, color-coded by site.

4. **Ratio Time Series Plot**:
   - Select two parameters to calculate their ratio (A/B) using the dropdown menu.
   - Use the **"Select sites for ratio time series plot"** option to filter data by specific sites.
   - The ratio time series plot will display the calculated ratio over time, color-coded by site.

5. **Pairplot: Side-by-side Comparison**:
   - Select two sheets to compare using the dropdown menu.
   - The app will identify common parameters between the two sheets.
   - Use the **"Select parameters for pairplot"** option to choose specific parameters for comparison.
   - The pairplot will display scatter plots for all combinations of the selected parameters, color-coded by site.

6. **General Notes**:
   - Ensure that your data file has the correct format, with parameters in the first column and sampling dates in the first row.
   - If you encounter any issues, check the data format or refresh the app.
            
""")

# Function to read and clean each sheet
def process_sheet(df_raw, site_name):
    df = df_raw.copy()
    df.columns = df.iloc[0]
    df = df.drop(df.index[0])
    df = df.reset_index(drop=True)

    df.rename(columns={df.columns[0]: "PARAMETER"}, inplace=True)
    
    # Replace <x with 0, convert all to numeric
    for col in df.columns[1:]:
        df[col] = df[col].astype(str).replace(r"<\s*\d+\.?\d*", "0", regex=True)
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)

    # Melt the DataFrame to long format
    df_long = df.melt(id_vars=["PARAMETER"], var_name="Sampling Date", value_name="Value")
    df_long["Sampling Date"] = pd.to_datetime(df_long["Sampling Date"], errors="coerce")
    df_long = df_long.dropna(subset=["Sampling Date"])
    df_long["Date (MM-YY)"] = df_long["Sampling Date"].dt.strftime("%m-%y")
    df_long["Site"] = site_name

    return df_long

# File uploader
uploaded_file = st.file_uploader("Upload spreadsheet (csv, xls, xlsx)", type=['csv', 'xls', 'xlsx'])

if uploaded_file:
    if uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file, header=None)
        sheet_names = ["Sheet1"]
        sheets = {"Sheet1": df}
    else:
        xls = pd.ExcelFile(uploaded_file)
        sheet_names = xls.sheet_names[:4]
        sheets = {name: xls.parse(name, header=None) for name in sheet_names}

    processed_data = {}
    for name, df in sheets.items():
        processed_data[name] = process_sheet(df, name)

    all_data = pd.concat(processed_data.values(), ignore_index=True)
    parameters = all_data['PARAMETER'].unique().tolist()

    # SCATTER PLOT
    st.subheader("Scatter Plot")
    col1, col2 = st.columns(2)
    with col1:
        param_x = st.selectbox("X-axis parameter", parameters, key="scatter_x")
    with col2:
        param_y = st.selectbox("Y-axis parameter", parameters, key="scatter_y")

    # Add site selection for scatter plot
    scatter_sites = st.multiselect("Select sites for scatter plot", all_data["Site"].unique(), default=all_data["Site"].unique())
    scatter_df = all_data[(all_data['PARAMETER'].isin([param_x, param_y])) & (all_data["Site"].isin(scatter_sites))]
    pivot_df = scatter_df.pivot_table(index=["Sampling Date", "Site"], columns="PARAMETER", values="Value").dropna()

    fig_scatter = px.scatter(pivot_df, x=param_x, y=param_y, color=pivot_df.index.get_level_values("Site"),
                             title=f"{param_y} vs {param_x}")
    fig_scatter.update_layout(xaxis_title=param_x, yaxis_title=param_y)
    st.plotly_chart(fig_scatter, use_container_width=True)

    # TIME SERIES PLOT
    st.subheader("Time Series Plot")
    selected_ts_params = st.multiselect("Select parameters to plot over time", parameters, default=parameters[:2], key="ts")

    # Add site selection for time series plot
    ts_sites = st.multiselect("Select sites for time series plot", all_data["Site"].unique(), default=all_data["Site"].unique(), key="ts_sites")
    ts_df = all_data[(all_data['PARAMETER'].isin(selected_ts_params)) & (all_data["Site"].isin(ts_sites))]
    fig_ts = px.scatter(ts_df, x="Sampling Date", y="Value", color="Site", symbol="PARAMETER", title="Time Series of Parameters")
    fig_ts.update_layout(xaxis_title="Sampling Date", yaxis_title="Value", xaxis_tickangle=-90)
    st.plotly_chart(fig_ts, use_container_width=True)

    # RATIO PLOT
    st.subheader("Ratio Time Series Plot")
    ratio_params = st.multiselect("Select two parameters for ratio (A/B)", parameters, default=parameters[:2], key="ratio")

    # Add site selection for ratio time series plot
    ratio_sites = st.multiselect("Select sites for ratio time series plot", all_data["Site"].unique(), default=all_data["Site"].unique(), key="ratio_sites")

    if len(ratio_params) == 2:
        ratio_df = all_data[(all_data['PARAMETER'].isin(ratio_params)) & (all_data["Site"].isin(ratio_sites))]
        pivot_ratio = ratio_df.pivot_table(index=["Sampling Date", "Date (MM-YY)", "Site"], columns="PARAMETER", values="Value").dropna()
        pivot_ratio['Ratio'] = pivot_ratio[ratio_params[0]] / pivot_ratio[ratio_params[1]]

        fig_ratio = px.scatter(pivot_ratio.reset_index(), x="Date (MM-YY)", y="Ratio", color="Site",
                               title=f"Ratio of {ratio_params[0]} / {ratio_params[1]}")
        fig_ratio.update_layout(xaxis_title="Sampling Date", yaxis_title=f"{ratio_params[0]} / {ratio_params[1]}", xaxis_tickangle=-90)
        st.plotly_chart(fig_ratio, use_container_width=True)

    # SEABORN PAIRPLOT
    st.subheader("Pairplot: Side-by-side Comparison")
    sheet_pair = st.multiselect("Select two sheets to compare", sheet_names, default=sheet_names[:2], key="pairplot")

    if len(sheet_pair) == 2:
        pair1 = processed_data[sheet_pair[0]]
        pair2 = processed_data[sheet_pair[1]]
        merged_pair = pd.concat([pair1, pair2])

        # Allow users to select specific parameters for comparison
        common_params = list(set(pair1['PARAMETER']).intersection(pair2['PARAMETER']))
        common_params.sort()  # Sort parameters alphabetically
        selected_pair_params = st.multiselect("Select parameters for pairplot", common_params, default=common_params[:3])

        if selected_pair_params:
            # Filter data for selected parameters
            filtered_pair = merged_pair[merged_pair['PARAMETER'].isin(selected_pair_params)]
            pivot_pair = filtered_pair.pivot_table(index=["Sampling Date", "Site"], 
                                                   columns="PARAMETER", values="Value").dropna().reset_index()

            st.write("Generating pairplot (this may take a few seconds)...")
        
        # Reduce font size for axis numbers and labels
        sns.set_context("notebook", font_scale=0.5)  # Reduce font size to half for axis numbers and labels
        
        # Generate the pairplot
        fig_pair = sns.pairplot(pivot_pair, vars=selected_pair_params, hue="Site", corner=True, height=2.5)

        # Display the pairplot
        st.pyplot(fig_pair)
    else:
        st.warning("Please select at least one parameter for the pairplot.")
