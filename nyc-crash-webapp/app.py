import dash
from dash import dcc, html, Input, Output, State
import pandas as pd
import plotly.express as px
from dash.exceptions import PreventUpdate

# ------------------------
# Load and Prepare Data
# ------------------------
df = pd.read_csv('data/integrated.csv')

df['crash_date_crash'] = pd.to_datetime(df['crash_date_crash'], errors='coerce')
df['year'] = df['crash_date_crash'].dt.year

df['borough'] = df['borough'].astype(str).str.strip().str.upper()
df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')

# ------------------------
# Initialize Dash app
# ------------------------
app = dash.Dash(__name__)
server = app.server 
app.title = "NYC Collisions Dashboard"

# ------------------------
# Layout
# ------------------------
app.layout = html.Div([
    html.H1("NYC Motor Vehicle Collisions Dashboard", style={'textAlign': 'center'}),

    html.Div([
        html.Label('Select Borough:'),
        dcc.Dropdown(sorted(df['borough'].dropna().unique()), id='borough-filter', placeholder="Choose Borough"),

        html.Label('Select Year:'),
        dcc.Dropdown(sorted(df['year'].dropna().unique()), id='year-filter', placeholder="Choose Year"),

        html.Label('Search (e.g. Brooklyn 2020 pedestrian):'),
        dcc.Input(id='search-box', type='text', placeholder='Enter search term...'),

        html.Button("Generate Report", id="generate-btn", n_clicks=0),
    ], style={
        'width': '80%',
        'margin': 'auto',
        'display': 'grid',
        'gridTemplateColumns': 'repeat(4, 1fr)',
        'gap': '10px',
        'textAlign': 'center'
    }),

    html.Br(),

    # ORIGINAL CHARTS
    html.Div([
        html.H3("Top Vehicle Types Involved", style={'textAlign': 'center'}),
        dcc.Graph(id='bar-chart')
    ]),

    html.Div([
        html.H3("Injuries vs Fatalities", style={'textAlign': 'center'}),
        dcc.Graph(id='pie-chart')
    ]),

    html.Div([
        html.H3("Crash Locations by Borough", style={'textAlign': 'center'}),
        dcc.Graph(id='map-chart')
    ]),

    # NEW 5 CHARTS
    html.Div([
        html.H3("Crashes Over the Years", style={'textAlign': 'center'}),
        dcc.Graph(id='line-chart')
    ]),

    html.Div([
        html.H3("Heatmap: Injuries by Borough & Year", style={'textAlign': 'center'}),
        dcc.Graph(id='heatmap-chart')
    ]),

    html.Div([
        html.H3("Injury Count Distribution", style={'textAlign': 'center'}),
        dcc.Graph(id='hist-chart')
    ]),

    html.Div([
        html.H3("Scatter Plot: Injuries vs Fatalities", style={'textAlign': 'center'}),
        dcc.Graph(id='scatter-chart')
    ]),

    html.Div([
        html.H3("Sunburst: Borough → Vehicle Type → Injuries", style={'textAlign': 'center'}),
        dcc.Graph(id='sunburst-chart')
    ]),
])

# ------------------------
# Callback
# ------------------------
@app.callback(
    [
        Output('bar-chart', 'figure'),
        Output('pie-chart', 'figure'),
        Output('map-chart', 'figure'),
        Output('line-chart', 'figure'),
        Output('heatmap-chart', 'figure'),
        Output('hist-chart', 'figure'),
        Output('scatter-chart', 'figure'),
        Output('sunburst-chart', 'figure'),
    ],
    Input('generate-btn', 'n_clicks'),
    [
        State('borough-filter', 'value'),
        State('year-filter', 'value'),
        State('search-box', 'value')
    ]
)
def update_charts(n_clicks, borough, year, search_term):
    if not n_clicks:
        raise PreventUpdate

    dff = df.copy()

    # ---------------- SEARCH LOGIC ----------------
    if search_term:
        term = search_term.lower()
        for b in df['borough'].dropna().unique():
            if b.lower() in term:
                dff = dff[dff['borough'].str.lower() == b.lower()]
        for y in df['year'].dropna().unique():
            if str(int(y)) in term:
                dff = dff[dff['year'] == y]
        if 'pedestrian' in term and 'contributing_factor_vehicle_1' in dff:
            dff = dff[dff['contributing_factor_vehicle_1']
                      .str.contains('pedestrian', case=False, na=False)]

    # ---------------- DROPDOWNS ----------------
    if borough:
        dff = dff[dff['borough'] == borough.upper()]
    if year:
        dff = dff[dff['year'] == year]

    # EMPTY DATA CHECK
    if dff.empty:
        empty = px.scatter(title="⚠ No data available for the selected filters.")
        return empty, empty, empty, empty, empty, empty, empty, empty

    # ---------------- 1. BAR CHART ----------------
    bar = px.bar(
        dff['vehicle_type_code1'].value_counts().nlargest(10),
        title="Top 10 Vehicle Types",
        labels={'index': 'Vehicle Type', 'value': 'Count'}
    )

    # ---------------- 2. PIE CHART ----------------
    pie = px.pie(
        names=['Injured', 'Killed'],
        values=[dff['number_of_persons_injured'].sum(),
                dff['number_of_persons_killed'].sum()],
        title="Injuries vs Fatalities"
    )

    # ---------------- 3. MAP (FIXED) ----------------
    map_data = dff.dropna(subset=['latitude', 'longitude'])

    if map_data.empty:
        map_fig = px.scatter_mapbox(
            lat=[40.7128],
            lon=[-74.0060],
            zoom=9,
            text=["⚠ No location data for this selection"],
            title="⚠ No location data available for this selection.",
            mapbox_style="open-street-map"
        )
    else:
        map_fig = px.scatter_mapbox(
            map_data,
            lat='latitude',
            lon='longitude',
            color='borough',
            zoom=10,
            mapbox_style="open-street-map",
            title="Crash Locations"
        )

    # ---------------- 4. LINE CHART ----------------
    line_data = dff.groupby('year').size().reset_index(name='num')
    line = px.line(
        line_data,
        x='year',
        y='num',
        markers=True,
        title="Crashes Over the Years"
    )

    # ---------------- 5. HEATMAP ----------------
    pivot = dff.pivot_table(
        values='number_of_persons_injured',
        index='borough',
        columns='year',
        aggfunc='sum',
        fill_value=0
    )
    heat = px.imshow(
        pivot,
        title="Injuries Heatmap (Borough × Year)",
        labels=dict(x="Year", y="Borough", color="Injuries")
    )

    # ---------------- 6. HISTOGRAM ----------------
    hist = px.histogram(
        dff,
        x='number_of_persons_injured',
        nbins=20,
        title="Distribution of Injuries Per Crash"
    )

    # ---------------- 7. SCATTER ----------------
    scatter = px.scatter(
        dff,
        x='number_of_persons_injured',
        y='number_of_persons_killed',
        color='borough',
        title="Scatter: Injuries vs Fatalities"
    )

    # ---------------- 8. SUNBURST (FIXED) ----------------
    sunburst_df = dff.copy()
    sunburst_df['vehicle_type_code1'] = sunburst_df['vehicle_type_code1'].fillna('UNKNOWN')
    sb_group = sunburst_df.groupby(
        ['borough', 'vehicle_type_code1'],
        as_index=False
    )['number_of_persons_injured'].sum()
    sb_group['number_of_persons_injured'] = sb_group['number_of_persons_injured'].replace(0, 1)

    sunburst = px.sunburst(
        sb_group,
        path=['borough', 'vehicle_type_code1'],
        values='number_of_persons_injured',
        title="Sunburst: Borough → Vehicle Type → Injuries"
    )

    return bar, pie, map_fig, line, heat, hist, scatter, sunburst


# ------------------------
# Run App
# ------------------------
if __name__ == '__main__':
    app.run(debug=True)

