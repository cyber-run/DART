import plotly.graph_objects as go
import pandas as pd
import os

# Define the folder containing the CSV files
folder_path = "curve_data"

# Create an empty figure
fig = go.Figure()

# Iterate over the CSV files in the folder
for file_name in os.listdir(folder_path):
    if file_name.endswith(".csv"):
        # Read the CSV file
        file_path = os.path.join(folder_path, file_name)
        df = pd.read_csv(file_path)
        
        # Extract column 1 -> object distance (m)
        object_distances = df.iloc[:, 0]
        
        # Extract column 2 -> best focus position
        best_focus_positions = df.iloc[:, 1]
        
        # Extract zoom position from the file name
        zoom_position = file_name.split("_")[-1].split(".")[0]
        
        # Add a trace for each CSV file
        fig.add_trace(go.Scatter(x=object_distances, y=best_focus_positions, mode='lines', name=f"{zoom_position}"))

# Update the layout
fig.update_layout(
    title="Lens tracking curves",
    xaxis_title="Object Distance (m)",
    yaxis_title="Best Focus Position (step)",
    legend_title="Zoom Positions (step):",
    template="plotly_dark"
)

# Display the graph
fig.show()