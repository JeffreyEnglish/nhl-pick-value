import dash
import dash_bootstrap_components as dbc
from dash import dcc, html, dash_table, Input, Output
from dash.dash_table.Format import Format, Scheme
import plotly.express as px
import plotly.graph_objects as go
import json, copy
import pandas as pd

# Initialize the app with the dark theme
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY, "assets/styles.css"])

# Common layout properties for dark theme
common_layout = json.load(open("assets/layout.json","r"))

# Load data
data = pd.read_csv("data/player_seasons.csv", parse_dates=False)
data['Season'] = data['Season'].astype(str)
pick_data = pd.read_csv("data/pick_probabilities.csv", parse_dates=False)

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

# Probability of becoming an NHLer
top_right_legend = dict(xanchor='right',yanchor='top',bgcolor='rgba(0,0,0,0.05)')
fig5_data = pick_data.loc[pick_data['Years After Draft'].isin([0,1,3,7,10])]
fig5 = px.line(fig5_data,
               x='Pick', y='NHL Probability', color='Years After Draft',
               title="Probability of Playing 21 Games or More",
               color_discrete_sequence=px.colors.sequential.Emrld,
               )
fig5.update_layout(common_layout)
fig5.update_layout({'legend':top_right_legend})
fig5.update_yaxes(range=[0,1])

# Probability of becoming an NHLer
fig6 = px.line(fig5_data,
               x='Pick', y='Star Probability', color='Years After Draft',
               title="Probability of Having 6 PS or More in a Season",
               color_discrete_sequence=px.colors.sequential.Emrld,
               )
fig6.update_layout(common_layout)
fig6.update_layout({'legend':top_right_legend})
fig6.update_yaxes(range=[0,1])

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
                        ]),
                        dbc.Row([
                            dbc.Col(dcc.Graph(figure=fig5), md=4),
                            dbc.Col(dcc.Graph(figure=fig6), md=4),
                            dbc.Col(dcc.Markdown("This shows the probability of a pick resulting in an NHL player (defined as someone who plays 21 games or more in a season) and a star player (defined as someone with 6 point shares or more in a season - roughly 20 players a year meet this criteria) for each pick. \n\nLate first round picks have only a ~50% of being a regular player during their RFA period. Star player probabilities drop more sharply and are less than 50% outside the top 3 picks."), md=3),
                        ]),                        
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

                # Tab explaining the content
                dbc.Tab(
                    [
                        dbc.Row([
                            dbc.Col([
                                dcc.Markdown("""This dashboard shows statistics related to the expected value of skaters drafted into the NHL. 
                                             Source data is taken from Atathead and includes every skater drafted since 2007 that played at least one NHL game. 
                                             I'd like to go back further but lately Stathead has had errors when including draft status in a search.\n\n"""),
                                dcc.Markdown("""For now it does not include goalies or skaters that never played an NHL game. These picks are given zero value
                                             in the estimations. This isn't completely accurate, but the number of goalies drafted is low enough to not have a huge impact.
                                             It does mean we can't use this data to make inferences on which teams draft and develop well so I will work on adding the missing data in a future update.\n\n"""),
                                dcc.Markdown("""Expected pick value is estimated using a multiple kernel regression model smoothing over pick number and years since drafted. 
                                             This smoothing avoid spikiness caused by individual standout players, particularly in later rounds.
                                             For high draft picks I use a Gaussian kernel with a bandwidth of 3 picks and 1 year, for low draft picks the kernel is Gaussian with a bandwidth of 32 picks and 1 year.
                                             The two estimates are interpolated between the 1st and 64th overall picks such that the 32nd overall pick is halfway between the two predictions."""), 
                                dcc.Markdown("""This site was made using Plotly Dash hosted on AWS Elastic Beanstalk. Analysis was performed using the Python packages *statsmodels* and *scikit-learn*."""), 

                                ],
                                md=7)
                            ], 
                            justify="center",
                            )
                    ],
                    label="About",
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

server = app.server
if __name__ == "__main__":
    app.run_server(debug=True, host='0.0.0.0')
