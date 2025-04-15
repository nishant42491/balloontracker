import requests
import pandas as pd
import plotly.express as px
from dash import Dash, dcc, html, Input, Output
import datetime
import json
import plotly.graph_objects as go

app = Dash(__name__)
server = app.server

def fetch_balloon_data():
    records = []
    for hour in range(24):
        try:
            url = f"https://a.windbornesystems.com/treasure/{hour:02d}.json"
            r = requests.get(url, timeout=5)
            if r.status_code != 200:
                continue
            data = r.json()
            for i, point in enumerate(data):
                if not isinstance(point, list) or len(point) != 3:
                    continue
                lat, lon, alt = point
                records.append({
                    "time_hour_ago": hour,
                    "lat": lat,
                    "lon": lon,
                    "alt": alt,
                    "id": i
                })
        except (requests.RequestException, json.JSONDecodeError):
            continue

    df = pd.DataFrame(records)
    if df.empty:
        return df

    df["timestamp"] = datetime.datetime.now(datetime.timezone.utc) - pd.to_timedelta(df["time_hour_ago"], unit="h")
    df.sort_values(["id", "time_hour_ago"], inplace=True)
    df["vertical_speed"] = df.groupby("id")["alt"].diff(-1)
    return df

df = fetch_balloon_data()

app.layout = html.Div([
    html.H1("🌍 Windborne Balloon Tracker (Live Last 24H)", style={"textAlign": "center"}),

    html.Div([
        html.Label("Select Hour:", style={"fontWeight": "bold"}),
        dcc.Dropdown(
            id="hour-dropdown",
            options=[{"label": f"{h} hours ago", "value": h} for h in sorted(df["time_hour_ago"].unique())],
            value=0,
            clearable=False
        ),

        html.Br(),

        html.Label("Color By:", style={"fontWeight": "bold"}),
        dcc.RadioItems(
            id="color-toggle",
            options=[
                {"label": "Altitude (km)", "value": "alt"},
                {"label": "Vertical Speed (km/h)", "value": "vertical_speed"}
            ],
            value="alt",
            inline=True
        ),
    ], style={"width": "60%", "margin": "auto"}),

    html.Br(),

    html.Div([
        dcc.Graph(id="map-current", style={"height": "500px"})
    ], style={"width": "100%", "maxWidth": "900px", "margin": "auto"}),

    html.Br(),

    html.Div([
        html.Label("Track Individual Balloon:", style={"fontWeight": "bold"}),
        dcc.Dropdown(
            id="balloon-id-dropdown",
            options=[{"label": f"Balloon {i}", "value": i} for i in sorted(df["id"].unique())],
            value=None,
            placeholder="Select a balloon ID to view its path",
            clearable=True
        ),
    ], style={"width": "60%", "margin": "auto"}),

    html.Br(),

    html.Div([
        dcc.Graph(id="map-trajectory", style={"height": "500px"})
    ], style={"width": "100%", "maxWidth": "900px", "margin": "auto"}),

    html.P("Data from Windborne Systems • Updates every run", style={"textAlign": "center", "marginTop": "2em"})
])


@app.callback(
    Output("map-current", "figure"),
    Output("map-trajectory", "figure"),
    Input("hour-dropdown", "value"),
    Input("color-toggle", "value"),
    Input("balloon-id-dropdown", "value")
)
def update_maps(selected_hour, color_by, selected_balloon_id):
    # --- CURRENT POSITIONS MAP ---
    filtered_df = df[df["time_hour_ago"] == selected_hour]
    if len(filtered_df) > 1000:
        filtered_df = filtered_df.sample(n=1000, random_state=42)

    fig_current = px.scatter_geo(
        filtered_df,
        lat="lat",
        lon="lon",
        color=color_by,
        hover_name="id",
        color_continuous_scale="Viridis",
        projection="natural earth",
        title=f"Balloon Positions - {selected_hour} Hours Ago"
    )
    fig_current.update_layout(margin=dict(r=0, t=40, l=0, b=0))

    # --- TRAJECTORY MAP ---
    if selected_balloon_id is not None:
        balloon_df = df[df["id"] == selected_balloon_id].sort_values("time_hour_ago")

        fig_traj = go.Figure()
        fig_traj.add_trace(go.Scattergeo(
            lat=balloon_df["lat"],
            lon=balloon_df["lon"],
            mode="lines+markers",
            marker=dict(
                size=6,
                color=balloon_df[color_by],
                colorscale="Viridis",
                colorbar=dict(title=color_by),
            ),
            line=dict(width=2, color="gray"),
            text=[f"{h} hours ago" for h in balloon_df["time_hour_ago"]],
            name=f"Balloon {selected_balloon_id}"
        ))
        fig_traj.update_layout(
            geo=dict(projection_type="natural earth"),
            title=f"Trajectory of Balloon {selected_balloon_id} (Last 24H)",
            margin=dict(r=0, t=40, l=0, b=0)
        )
    else:
        fig_traj = go.Figure()
        fig_traj.update_layout(
            geo=dict(projection_type="natural earth"),
            title="No Balloon Selected",
            margin=dict(r=0, t=40, l=0, b=0)
        )

    return fig_current, fig_traj


if __name__ == "__main__":
    app.run(debug=True)
