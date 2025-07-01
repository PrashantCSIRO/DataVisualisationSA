import streamlit as st                # Import Streamlit for building the web app
import pandas as pd                   # Import pandas for data manipulation
import numpy as np                    # Import numpy for numerical operations
import seaborn as sns                 # Import seaborn for statistical data visualization
import plotly.express as px           # Import plotly express for interactive plots
from datetime import datetime         # Import datetime for date operations

# Set the app configuration
st.set_page_config(layout="wide", page_title="Brine Data Visualiser")   # Set Streamlit app layout and title
st.title("Brine Data Visualiser")                                       # Display the main title on the app

# Add user instructions
st.sidebar.header("Instructions")                                       # Add a header in the sidebar for instructions
st.sidebar.markdown("""                                                 # Add markdown-formatted instructions in the sidebar
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
def process_sheet(df_raw, site_name):                       # Define a function to process each sheet of data
    df = df_raw.copy()                                      # Make a copy of the raw DataFrame
    df.columns = df.iloc[0]                                 # Set the first row as column headers
    df = df.drop(df.index[0])                               # Drop the first row (now used as headers)
    df = df.reset_index(drop=True)                          # Reset the index after dropping the row

    df.rename(columns={df.columns[0]: "PARAMETER"}, inplace=True)   # Rename the first column to "PARAMETER"
    
    # Replace <x with 0, convert all to numeric
    for col in df.columns[1:]:                              # Loop through all columns except "PARAMETER"
        df[col] = df[col].astype(str).replace(r"<\s*\d+\.?\d*", "0", regex=True)  # Replace values like "<5" with "0"
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)              # Convert to numeric, fill NaN with 0

    # Melt the DataFrame to long format
    df_long = df.melt(id_vars=["PARAMETER"], var_name="Sampling Date", value_name="Value")  # Convert to long format
    df_long["Sampling Date"] = pd.to_datetime(df_long["Sampling Date"], errors="coerce")    # Convert dates to datetime
    df_long = df_long.dropna(subset=["Sampling Date"])                                      # Drop rows with invalid dates
    df_long["Date (MM-YY)"] = df_long["Sampling Date"].dt.strftime("%m-%y")                 # Add formatted date column
    df_long["Site"] = site_name                                                             # Add site name column

    return df_long                                    # Return the cleaned and formatted DataFrame

# File uploader
uploaded_file = st.file_uploader("Upload spreadsheet (csv, xls, xlsx)", type=['csv', 'xls', 'xlsx'])  # File upload widget

if uploaded_file:                                     # If a file is uploaded
    if uploaded_file.name.endswith('.csv'):           # If the file is a CSV
        df = pd.read_csv(uploaded_file, header=None)  # Read CSV without headers
        sheet_names = ["Sheet1"]                      # Use a default sheet name
        sheets = {"Sheet1": df}                       # Store in a dictionary
    else:                                             # If the file is Excel
        xls = pd.ExcelFile(uploaded_file)             # Read the Excel file
        sheet_names = xls.sheet_names[:4]             # Get up to 4 sheet names
        sheets = {name: xls.parse(name, header=None) for name in sheet_names}  # Parse each sheet

    processed_data = {}                               # Dictionary to hold processed data
    for name, df in sheets.items():                   # Loop through each sheet
        processed_data[name] = process_sheet(df, name) # Process and store each sheet

    all_data = pd.concat(processed_data.values(), ignore_index=True)   # Combine all sheets into one DataFrame
    parameters = all_data['PARAMETER'].unique().tolist()               # Get unique parameter names

    # SCATTER PLOT
    st.subheader("Scatter Plot")                      # Add a subheader for scatter plot
    col1, col2 = st.columns(2)                       # Create two columns for parameter selection
    with col1:
        param_x = st.selectbox("X-axis parameter", parameters, key="scatter_x")   # Dropdown for X-axis parameter
    with col2:
        param_y = st.selectbox("Y-axis parameter", parameters, key="scatter_y")   # Dropdown for Y-axis parameter

    # Add site selection for scatter plot
    scatter_sites = st.multiselect("Select sites for scatter plot", all_data["Site"].unique(), default=all_data["Site"].unique())  # Site filter
    scatter_df = all_data[(all_data['PARAMETER'].isin([param_x, param_y])) & (all_data["Site"].isin(scatter_sites))]               # Filter data
    pivot_df = scatter_df.pivot_table(index=["Sampling Date", "Site"], columns="PARAMETER", values="Value").dropna()               # Pivot for plotting

    fig_scatter = px.scatter(
        pivot_df, x=param_x, y=param_y, color=pivot_df.index.get_level_values("Site"),
        title=f"{param_y} vs {param_x}"
    )                               # Create scatter plot

    # Update layout for axis lines, ticks, and bold fonts
    fig_scatter.update_layout(
        xaxis=dict(
            title=dict(text=param_x, font=dict(family="Arial", size=14, color="black", weight="bold")),
            showline=True, linewidth=2, linecolor='black',
            ticks="outside",
            tickfont=dict(family="Arial Black, Arial Bold, Arial, sans-serif", size=12, color="black")
        ),
        yaxis=dict(
            title=dict(text=param_y, font=dict(family="Arial", size=14, color="black", weight="bold")),
            showline=True, linewidth=2, linecolor='black',
            ticks="outside",
            tickfont=dict(family="Arial Black, Arial Bold, Arial, sans-serif", size=12, color="black")
        ),
        legend=dict(
            font=dict(family="Arial", size=12, color="black", weight="bold")
        ),
        title=dict(font=dict(family="Arial", size=16, color="black", weight="bold"))
    )
    st.plotly_chart(fig_scatter, use_container_width=True)                                  # Display plot in app

    # TIME SERIES PLOT
    st.subheader("Time Series Plot")                                                        # Add subheader for time series
    selected_ts_params = st.multiselect("Select parameters to plot over time", parameters, default=parameters[:2], key="ts")  # Parameter selection

    # Add site selection for time series plot
    ts_sites = st.multiselect("Select sites for time series plot", all_data["Site"].unique(), default=all_data["Site"].unique(), key="ts_sites")  # Site filter
    ts_df = all_data[(all_data['PARAMETER'].isin(selected_ts_params)) & (all_data["Site"].isin(ts_sites))]   # Filter data
    fig_ts = px.scatter(
        ts_df, x="Sampling Date", y="Value", color="Site", symbol="PARAMETER", title="Time Series of Parameters"
    )  # Create plot

    fig_ts.update_layout(
        xaxis=dict(
            title=dict(text="Sampling Date", font=dict(family="Arial", size=14, color="black", weight="bold")),
            showline=True, linewidth=2, linecolor='black',
            ticks="outside", tickfont=dict(family="Arial", size=12, color="black", weight="bold")
        ),
        yaxis=dict(
            title=dict(text="Value", font=dict(family="Arial", size=14, color="black", weight="bold")),
            showline=True, linewidth=2, linecolor='black',
            ticks="outside", tickfont=dict(family="Arial", size=12, color="black", weight="bold")
        ),
        legend=dict(
            font=dict(family="Arial", size=12, color="black", weight="bold")
        ),
        title=dict(font=dict(family="Arial", size=16, color="black", weight="bold"))
    )
    st.plotly_chart(fig_ts, use_container_width=True)                                                                             # Display plot

    # RATIO PLOT
    st.subheader("Ratio Time Series Plot")                                                  # Add subheader for ratio plot
    ratio_params = st.multiselect("Select two parameters for ratio (A/B)", parameters, default=parameters[:2], key="ratio")       # Parameter selection

    # Add site selection for ratio time series plot
    ratio_sites = st.multiselect("Select sites for ratio time series plot", all_data["Site"].unique(), default=all_data["Site"].unique(), key="ratio_sites")  # Site filter

    if len(ratio_params) == 2:                                                             # If two parameters are selected
        ratio_df = all_data[(all_data['PARAMETER'].isin(ratio_params)) & (all_data["Site"].isin(ratio_sites))]   # Filter data
        pivot_ratio = ratio_df.pivot_table(index=["Sampling Date", "Date (MM-YY)", "Site"], columns="PARAMETER", values="Value").dropna()  # Pivot data
        pivot_ratio['Ratio'] = pivot_ratio[ratio_params[0]] / pivot_ratio[ratio_params[1]]  # Calculate ratio

        fig_ratio = px.scatter(
            pivot_ratio.reset_index(), x="Date (MM-YY)", y="Ratio", color="Site",
            title=f"Ratio of {ratio_params[0]} / {ratio_params[1]}"
        )    # Create scatter plot for ratio

        fig_ratio.update_layout(
            xaxis=dict(
                title=dict(text="Sampling Date", font=dict(family="Arial", size=14, color="black", weight="bold")),
                showline=True, linewidth=2, linecolor='black',
                ticks="outside", tickfont=dict(family="Arial", size=12, color="black", weight="bold")
            ),
            yaxis=dict(
                title=dict(text=f"{ratio_params[0]} / {ratio_params[1]}", font=dict(family="Arial", size=14, color="black", weight="bold")),
                showline=True, linewidth=2, linecolor='black',
                ticks="outside", tickfont=dict(family="Arial", size=12, color="black", weight="bold")
            ),
            legend=dict(
                font=dict(family="Arial", size=12, color="black", weight="bold")
            ),
            title=dict(font=dict(family="Arial", size=16, color="black", weight="bold"))
        )
        st.plotly_chart(fig_ratio, use_container_width=True)                                # Display plot

    # SEABORN PAIRPLOT
    st.subheader("Pairplot: Side-by-side Comparison")                                       # Add subheader for pairplot
    sheet_pair = st.multiselect("Select two sheets to compare", sheet_names, default=sheet_names[:2], key="pairplot")  # Sheet selection

    if len(sheet_pair) == 2:                                                                # If two sheets are selected
        pair1 = processed_data[sheet_pair[0]]                                               # Get first sheet data
        pair2 = processed_data[sheet_pair[1]]                                               # Get second sheet data
        merged_pair = pd.concat([pair1, pair2])                                             # Merge both sheets

        # Allow users to select specific parameters for comparison
        common_params = list(set(pair1['PARAMETER']).intersection(pair2['PARAMETER']))      # Find common parameters
        common_params.sort()  # Sort parameters alphabetically
        selected_pair_params = st.multiselect("Select parameters for pairplot", common_params, default=common_params[:3])  # Parameter selection

        if selected_pair_params:                                                            # If parameters are selected
            # Filter data for selected parameters
            filtered_pair = merged_pair[merged_pair['PARAMETER'].isin(selected_pair_params)] # Filter merged data
            pivot_pair = filtered_pair.pivot_table(index=["Sampling Date", "Site"], 
                                                   columns="PARAMETER", values="Value").dropna().reset_index()  # Pivot data

            st.write("Generating pairplot (this may take a few seconds)...")                # Notify user
        
        # Reduce font size for axis numbers and labels
        sns.set_context("notebook", font_scale=0.5)  # Reduce font size to half for axis numbers and labels
        
        # Generate the pairplot
        fig_pair = sns.pairplot(pivot_pair, vars=selected_pair_params, hue="Site", corner=True, height=2.5)  # Create pairplot

        # Set y-axis label for the top-left subplot and ensure y-axis is visible
        if fig_pair.axes is not None:
            for i, param in enumerate(selected_pair_params):
                if fig_pair.axes[i, 0] is not None:
                    fig_pair.axes[i, 0].set_ylabel(param)  # Set y-axis label
                    fig_pair.axes[i, 0].get_yaxis().set_visible(True)  # Ensure y-axis is visible
                    fig_pair.axes[i, 0].spines['left'].set_visible(True)  # Ensure y-axis line is visible
                    fig_pair.axes[i, 0].spines['left'].set_linewidth(1)   # Set y-axis line width (optional)
                    fig_pair.axes[i, 0].spines['left'].set_color('black') # Set y-axis line color (optional)

        # Display the pairplot
        st.pyplot(fig_pair)                                                                # Show pairplot in app
    else:
        st.warning("Please select at least one parameter for the pairplot.")               # Warn if not
