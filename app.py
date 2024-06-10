import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, dash_table, Input, Output
from dash.dash_table.Format import Format, Scheme
import plotly.express as px
import plotly.graph_objects as go
import json, copy
import pandas as pd

# Initialize the app with the dark theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY])

# Common layout properties for dark theme
common_layout = json.load(open("assets/layout.json","r"))

# Load data
data = pd.read_csv("data/player_seasons.csv", parse_dates=False)
data['Season'] = data['Season'].astype(str)

# === Create figures
# == Pick value summation
fig1_data = data.loc[data['Season_Start'] < (data['Draft_Year']+7)]
fig1_data = fig1_data.groupby(['Pick','Years_After_Draft'])['Prediction'].mean().reset_index()
fig1_data = fig1_data.groupby(['Pick'])['Prediction'].sum().reset_index()

fig1 = px.line(fig1_data,
               x='Pick', 
               y='Prediction', 
               labels=dict(Pick="Pick", Prediction="Predicted PS Over RFA Period"),
               color_discrete_sequence=px.colors.sequential.Emrld,
               title="Predicted Pick Value before UFA")
fig1.update_layout(common_layout)
fig1.update_yaxes(range=[-1, 40])

# Pick value by round & year
fig2_data = data.groupby(['Years_After_Draft','Round'])['Prediction'].mean().reset_index()
fig2 = px.line(fig2_data,
               x='Years_After_Draft', 
               y='Prediction',
               color='Round',
               labels=dict(Years_After_Draft="Years After Draft", Prediction="Predicted PS", Round='Draft Round'),
               title="Pick Value by Year",
               color_discrete_sequence=px.colors.sequential.Emrld,)
fig2.update_layout(common_layout)

# Table of value vs expected
fig3_data = data.loc[:,['Player','Draft_Year','Pick','Season','Prediction','PS','Draft_Team']]
fig3_data['Residual'] = fig3_data['PS'] - fig3_data['Prediction']
fig3_data = fig3_data.groupby("Player").agg({"Pick":"first",
                                             "Draft_Year":"first",
                                             "Draft_Team":"first",
                                             "Prediction":"sum",
                                             "PS":'sum',
                                             "Residual":"sum"}).reset_index().sort_values(by='PS', ascending=False)
fig3_columns = [
    {"name": "Player", "id": "Player"},
    {"name": "Draft Team", "id": "Draft_Team"},
    {"name": "Draft Year", "id": "Draft_Year"},
    {"name": "Pick", "id": "Pick"},
    {"name": "Predicted PS", "id": "Prediction", 'type':'numeric', 'format':Format(precision=1, scheme=Scheme.fixed)},
    {"name": "Actual PS", "id": "PS", 'type':'numeric', 'format':Format(precision=1, scheme=Scheme.fixed)},
    {"name": "Over-Performance", "id": "Residual", 'type':'numeric', 'format':Format(precision=1, scheme=Scheme.fixed)}
    ]
fig3 = dash_table.DataTable(data=fig3_data.to_dict('records'),
                            columns=fig3_columns,
                            style_table={'height':'80vh', 'min-height':'400px', 'overflowY': 'auto'},
                            style_header={'backgroundColor': '#303030', 'color': 'white'},
                            style_cell={'backgroundColor': '#303030', 'color': 'white'},
                            sort_action='native',
                            sort_mode="multi",
                            id='player_summary_table',
                )

# Player annual performance vs expected
fig4_data = pd.melt(data[['Player','Season_Start','Prediction','PS']], id_vars=['Player','Season_Start'])
fig4 = px.line(fig4_data,
               x='Season_Start', 
               y='value',
               color='variable',
               labels=dict(Season_Start="Season", value="PS", variable='Variable'),
               title="Pick Value vs. Predicted",
               #color_discrete_sequence=px.colors.Viridis,
               )
fig4.update_layout(common_layout)

# Define the layout with Tabs
app.layout = dbc.Container(
    [
        dbc.Tabs(
            [
                # Tab for overview of pick value
                dbc.Tab(
                    [
                        dbc.Row([
                            dbc.Col(dcc.Graph(figure=fig1), md=8),
                            dbc.Col(dcc.Markdown("This shows the value of each pick over the first seven years post draft. This translates to the RFA period for players that sign their ELC immediately. \n\nExpected point shares are calculated through a kernel regression for all draft picks since 2007 in which higher draft picks use a smaller kernel (*i.e.* are smoothed less) than later draft picks."), md=4),
                        ]),
                        dbc.Row([
                            dbc.Col(dcc.Markdown("This figure shows the average expected value for a pick in each round by year after the draft. First round picks peak in year 6 while later picks can take longer."), md=4),
                            dbc.Col(dcc.Graph(figure=fig2), md=8),
                        ])
                    ],
                    label="Pick Value",
                    ),

                # Tab for overview of players
                dbc.Tab(
                    [
                        dbc.Row([
                            dbc.Col([
                                html.H4("Player Name"),
                                dcc.Input(
                                    id="table_name_filter",
                                    type='text',
                                    placeholder=" ",
                                ),
                                html.H4(""),
                                html.H4("Draft Year"),
                                dcc.RangeSlider(min=2007, max=2023, step=1, 
                                                value=[2007, 2023], 
                                                marks={y:str(y) for y in range(2007,2024) if y%2==1},
                                                id='table_draft_range_slider'),
                                dcc.Markdown("\n\nLook up players cumulative point shares since their draft year. Can filter by name, draft year, or both."), 
                                ],
                                md=3),
                            dbc.Col(fig3, md=9),                            
                        ],
                        className='table-container-row')
                    ],
                    label="Player Summaries",
                ),

                # Tab for individual player plots
                dbc.Tab(
                    [
                        dbc.Row([
                            dbc.Col([
                                html.H4("Player Name 1"),
                                dcc.Dropdown(
                                    id="lookup_name_filter_1",
                                    options=data['Player'].unique(),
                                    value="Patrick Kane",
                                    multi=False,
                                    searchable=True,
                                    clearable=False,
                                    className='form-control'
                                ),
                                html.H4("Player Name 2"),
                                dcc.Dropdown(
                                    id="lookup_name_filter_2",
                                    options=data['Player'].unique(),
                                    value="Steven Stamkos",
                                    multi=False,
                                    searchable=True,
                                    clearable=False,
                                    className='form-control'
                                ),
                                dcc.Markdown("Compare actual and expected point shares between two players."), 
                                ],
                                md=3),
                            dbc.Col([
                                    dcc.Graph(id='player_comparison', figure=fig4),
                                ])
                            ]),  
                    ],
                    label="Player Comparison",
                ),
            ]
        )
    ],
    fluid=True,
    className="custom-container",
)

# Callback to update the player summary table
@app.callback(
    Output('player_summary_table', 'data'),
    [
        Input('table_name_filter', 'value'),
        Input('table_draft_range_slider', 'value')
    ]
)
def update_player_summary_table(name_filter, draft_year_range):
    filtered_df = fig3_data[
        (fig3_data['Draft_Year'] >= draft_year_range[0]) &
        (fig3_data['Draft_Year'] <= draft_year_range[1])
    ]
    if (name_filter != None) and (name_filter != ""):
        filtered_df = filtered_df[filtered_df['Player'].str.contains(name_filter, case=False, na=False)]

    return filtered_df.to_dict('records')

# Callback to update the player comparison chart
@app.callback(
    Output('player_comparison', 'figure'),
    [
        Input('lookup_name_filter_1', 'value'),
        Input('lookup_name_filter_2', 'value')
    ]
)
def update_player_comparison_figure(player_a, player_b):
    filtered_df = fig4_data[
        (fig4_data['Player']==player_a) | (fig4_data['Player']==player_b)
    ].iloc[::-1]
    fig = px.line(filtered_df,
                   x='Season_Start', 
                   y='value',
                   color='Player',
                   line_dash='variable',
                   labels=dict(Season_Start="Season", value="Point Shares", variable='Variable'),
                   title="Pick Value vs. Predicted",
                   #color_discrete_sequence=px.colors.Viridis,
                   )
    fig.update_layout(common_layout)
    return fig

if __name__ == "__main__":
    app.run_server(debug=True)
