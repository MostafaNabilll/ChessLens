"""
ChessLens Dashboard
Personal chess analytics powered by DuckDB and dbt.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import duckdb


conn = duckdb.connect('./data/chesslens.duckdb', read_only=True)

def run_query(query: str) -> pd.DataFrame:
  return conn.execute(query).fetchdf()

st.set_page_config(page_title="ChessLens", page_icon="♟️", layout="wide")


st.markdown("""
    <style>
        .block-container { padding-top: 2rem; padding-bottom: 2rem; }
        [data-testid="stSidebar"] { min-width: 220px; max-width: 230px; }
        [data-testid="stMetricValue"], 
            [data-testid="stMetricDelta"] {white-space: nowrap;}
        [data-testid="stMetric"] { 
            background-color: rgba(128, 128, 128, 0.1); 
            padding: 15px; 
            border-radius: 10px;
            min-height: 120px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
    </style>
""", unsafe_allow_html=True)

st.sidebar.title("ChessLens")
st.sidebar.caption("Your chess patterns, revealed.")
st.sidebar.divider()
page = st.sidebar.radio("Navigate", ["Overview", "Tilt Tracker", "When To Play", "Opening Lab", "Know Your Opponent", "Session Insights"])





if page == "Overview":
  st.header("Overview")
  st.write("Quick snapshot of your chess performance across all time controls.")
  
  df = run_query("SELECT * FROM main_gold.gold_time_control_comparison")
  
  # Rating cards
  cols = st.columns(len(df))
  for i, row in df.iterrows():
      with cols[i]:
          peak_diff = row['current_rating'] - row['peak_rating']
          if peak_diff >= 0:
              delta_val = "At Peak!"
          else:
              delta_val = f"{int(peak_diff)} from peak"
          st.metric(
              label=f'{row["time_class"].title()} Rating',
              value=int(row['current_rating']),
              delta=delta_val,
              delta_color="normal"
          )
  
  total = df['total_games'].sum()
  overall_wr = (df['win_rate'] * df['total_games']).sum() / total
  
  cols = st.columns([1, 1, 1])

  with cols[0]:
    st.metric(label="Total Games", value=total, delta=f"{overall_wr:.1%} win rate")


  with cols[1]:
      longest_win = run_query("""
          SELECT MAX(streak) as longest FROM (
              SELECT COUNT(*) as streak
              FROM (
                  SELECT result,
                      SUM(CASE WHEN result != 'win' THEN 1 ELSE 0 END) 
                      OVER (ORDER BY end_at) as grp
                  FROM main_silver.silver_games
              )
              WHERE result = 'win'
              GROUP BY grp
          )
      """)['longest'].iloc[0]
      st.metric("Longest Win Streak", f"{int(longest_win)} games", delta=f"{int(longest_win)} in a row")


  with cols[2]:
      longest_loss = run_query("""
          SELECT MAX(streak) as longest FROM (
              SELECT COUNT(*) as streak
              FROM (
                  SELECT result,
                      SUM(CASE WHEN result != 'loss' THEN 1 ELSE 0 END) 
                      OVER (ORDER BY end_at) as grp
                  FROM main_silver.silver_games
              )
              WHERE result = 'loss'
              GROUP BY grp
          )
      """)['longest'].iloc[0]
      st.metric("Longest Loss Streak", f"{int(longest_loss)} games", delta=f"-{int(longest_loss)} in a row")

  
  st.divider()
  
  st.subheader("Rating Progression")

  rating_tc = st.selectbox("Time Control", 
      run_query("SELECT DISTINCT time_class FROM main_silver.silver_games")['time_class'].tolist(),
      key="rating_tc")

  df_rating = run_query(f"""
      SELECT end_at, player_rating 
      FROM main_silver.silver_games 
      WHERE time_class = '{rating_tc}'
      ORDER BY end_at
  """)

  fig = px.line(df_rating, x='end_at', y='player_rating',
                labels={'end_at': 'Date', 'player_rating': 'Rating'})
  fig.update_layout(
      plot_bgcolor='rgba(0,0,0,0)',
      paper_bgcolor='rgba(0,0,0,0)',
      height=400,
      yaxis=dict(gridcolor='rgba(128,128,128,0.2)'),
      margin=dict(t=30, b=50),
      font=dict(size=13)
  )
  st.plotly_chart(fig, width='stretch')
  
  st.divider()

  # Games distribution chart
  st.subheader("Games by Time Control")
  fig = px.bar(df, x='time_class', y='total_games',
              text='total_games',
              labels={'time_class': 'Time Control', 'total_games': 'Games Played'},
              color_discrete_sequence=['#4C78A8'])  
  fig.update_traces(textposition='outside', marker_line_width=0)
  fig.update_layout(
      plot_bgcolor='rgba(0,0,0,0)',
      paper_bgcolor='rgba(0,0,0,0)',
      height=400,
      coloraxis_showscale=False,
      yaxis=dict(gridcolor='rgba(128,128,128,0.2)'),
      margin=dict(t=30, b=50),
      font=dict(size=13)
  )
  st.plotly_chart(fig, use_container_width=True)
  
  # Timeout rate comparison
  st.subheader("Timeout Loss Rate")
  fig2 = px.bar(df, x='time_class', y='timeout_loss_rate',
                text=df['timeout_loss_rate'].apply(lambda x: f"{x:.1%}"),
                labels={'time_class': 'Time Control', 'timeout_loss_rate': 'Timeout Loss Rate'},
                color_discrete_sequence=['#ff6b6b'])
  fig2.update_traces(textposition='outside')
  fig2.update_layout(
      plot_bgcolor='rgba(0,0,0,0)',
      paper_bgcolor='rgba(0,0,0,0)',
      height=350,
      yaxis_tickformat='.0%',
      yaxis=dict(gridcolor='rgba(128,128,128,0.2)'),
      margin=dict(t=30, b=50),
      font=dict(size=13)
  )
  st.plotly_chart(fig2, use_container_width=True)
  




elif page == "Tilt Tracker":
  st.header("Tilt Tracker")
  st.write("Does losing make you lose more? This page tracks how consecutive losses affect your next game.")

  df1 = run_query ("""
      SELECT
        is_tilted,
        COUNT(*) AS games,
        AVG(CASE WHEN result ='win' THEN 1 ELSE 0 END) as win_rate
      FROM main_gold.gold_tilt_analysis
      GROUP BY 1
  """)
  cols = st.columns(len(df1))
  for i, row in df1.iterrows():
    with cols[i]:
      st.metric(
        label="Tilted" if row['is_tilted'] else "Not Tilted",
        value= f"{row['games']} games",
        delta = f"Win Rate: {row['win_rate']:.1%}",
        delta_color="off"
      )
  
  st.divider()

  st.subheader("Win Rate by Loss Streak")
  st.write("Each bar shows your win rate after N consecutive losses. Does your performance drop?")
  
  df2 = run_query("""
    SELECT
        consecutive_losses_before,
        COUNT(*) AS games,
        AVG(CASE WHEN result = 'win' THEN 1 ELSE 0 END) AS win_rate
    FROM main_gold.gold_tilt_analysis
    GROUP BY 1
    ORDER BY 1
  """)

  fig = px.bar(df2, x='consecutive_losses_before', y='win_rate',
              text=df2.apply(lambda x: f"{x['win_rate']:.0%} ({int(x['games'])} game(s))", axis=1),
              labels={'consecutive_losses_before': 'Consecutive Losses Before Game', 'win_rate': 'Win Rate'},
              color='win_rate',
              color_continuous_scale='RdYlGn')

  fig.update_traces(
      textposition='outside',
      marker_line_width=0
  )

  fig.update_layout(
      yaxis_tickformat='.0%',
      plot_bgcolor='rgba(0,0,0,0)',
      paper_bgcolor='rgba(0,0,0,0)',
      height=450,
      showlegend=False,
      coloraxis_showscale=False,
      xaxis=dict(dtick=1, title_font_size=14),
      yaxis=dict(title_font_size=14, gridcolor='rgba(128,128,128,0.2)'),
      margin=dict(t=30, b=50),
      font=dict(size=13)
  )

  st.plotly_chart(fig, use_container_width=True)
  tilted_wr = df1[df1['is_tilted'] == True]['win_rate'].values
  normal_wr = df1[df1['is_tilted'] == False]['win_rate'].values
  if len(tilted_wr) > 0 and len(normal_wr) > 0:
      diff = tilted_wr[0] - normal_wr[0]
      if diff > 0:
          st.success(f"You actually play **better** after losing streaks ({diff:+.1%}). No tilt detected!")
      else:
          st.warning(f"Your win rate drops by **{abs(diff):.1%}** when tilted. Consider taking breaks after 3 losses.")





elif page == "When To Play":
  st.header("When To Play")
  st.write("Discover when you play your best chess based on time of day and day of week.")
  
  df = run_query("SELECT * FROM main_gold.gold_time_of_day")
  
  # Time class filter
  time_classes = df['time_class'].unique().tolist()
  selected_tc = st.selectbox("Time Control", ["All"] + time_classes)
  
  if selected_tc != "All":
      df = df[df['time_class'] == selected_tc]
  
  st.divider()
  
  # Heatmap: day of week vs hour bucket
  heatmap_data = df.groupby(['day_of_week', 'hour_bucket']).agg(
      win_rate=('win_rate', 'mean'),
      games=('games_played', 'sum')
  ).reset_index()
  
  day_names = {0: 'Sunday', 1: 'Monday', 2: 'Tuesday', 3: 'Wednesday', 4: 'Thursday', 5: 'Friday', 6: 'Saturday'}
  heatmap_data['day_name'] = heatmap_data['day_of_week'].map(day_names)
  
  bucket_order = ['morning', 'afternoon', 'evening', 'night']
  day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
  
  pivot = heatmap_data.pivot_table(index='day_name', columns='hour_bucket', values='win_rate')
  pivot = pivot.reindex(index=day_order, columns=bucket_order)
  
  st.subheader("Win Rate Heatmap")
  fig = px.imshow(pivot,
                  color_continuous_scale='RdYlGn',
                  text_auto='.0%',
                  labels={'color': 'Win Rate'},
                  aspect='auto')
  fig.update_layout(
      height=400,
      margin=dict(t=30, b=30),
      font=dict(size=13),
      xaxis_title="Time of Day",
      yaxis_title=""
  )
  st.plotly_chart(fig, use_container_width=True)
  
  # Best and worst times
  st.divider()
  best = heatmap_data.loc[heatmap_data['win_rate'].idxmax()]
  worst = heatmap_data.loc[heatmap_data['win_rate'].idxmin()]
  
  cols = st.columns(2)
  with cols[0]:
      st.success(f"Best: {best['day_name']} {best['hour_bucket']} ({best['win_rate']:.0%} over {int(best['games'])} games)")
  with cols[1]:
      st.error(f"Worst: {worst['day_name']} {worst['hour_bucket']} ({worst['win_rate']:.0%} over {int(worst['games'])} games)")





elif page == "Opening Lab":
  st.header("Opening Lab")
  st.write("Track how your openings perform over time and spot what's improving or declining.")
  
  df = run_query("SELECT * FROM main_gold.gold_opening_trends")
  
  # Filters
  col1, col2 = st.columns(2)
  with col1:
      time_classes = df['time_class'].unique().tolist()
      selected_tc = st.selectbox("Time Control", time_classes, key="opening_tc")
  with col2:
      trend_filter = st.selectbox("Trend", ["All", "improving", "declining", "stable"], key="opening_trend")
  
  # Filter time class for everything
  df = df[df['time_class'] == selected_tc]
  df = df[df['trend'] != 'new']

  
  st.divider()
  
  # Filter openings by trend
  if trend_filter != "All":
      latest_month = df['month'].max()
      trending_openings = df[(df['month'] == latest_month) & (df['trend'] == trend_filter)]['opening_family'].unique().tolist()
      df_chart = df[df['opening_family'].isin(trending_openings)]
  else:
      df_chart = df

  all_openings = df_chart.groupby('opening_family')['games_played'].sum().sort_values(ascending=False).index.tolist()
  selected_openings = st.multiselect("Select Openings", all_openings, default=all_openings[:5])
  df_top = df_chart[df_chart['opening_family'].isin(selected_openings)]

  st.subheader("Win Rate Over Time")
  if not df_top.empty:
      fig = px.line(df_top, x='month', y='win_rate', color='opening_family',
                    markers=True,
                    labels={'month': 'Month', 'win_rate': 'Win Rate', 'opening_family': 'Opening'})
      fig.update_layout(
          yaxis_tickformat='.0%',
          plot_bgcolor='rgba(0,0,0,0)',
          paper_bgcolor='rgba(0,0,0,0)',
          height=450,
          yaxis=dict(gridcolor='rgba(128,128,128,0.2)'),
          margin=dict(t=30, b=50),
          font=dict(size=13),
          legend=dict(orientation='h', yanchor='bottom', y=-0.3)
      )
      st.plotly_chart(fig, use_container_width=True)
  else:
      st.info("No data for the selected filters.")
  
  st.divider()
  
  # Table uses trend filter
  st.subheader("Opening Trends")
  latest_month = df['month'].max()
  df_latest = df[df['month'] == latest_month].sort_values('games_played', ascending=False)
  
  if trend_filter != "All":
      df_latest = df_latest[df_latest['trend'] == trend_filter]
  
  if not df_latest.empty:
      display_df = df_latest[['opening_family', 'games_played', 'win_rate', 'avg_opponent_rating', 'trend']].copy()
      display_df['win_rate'] = display_df['win_rate'].apply(lambda x: f"{x:.0%}")
      display_df['avg_opponent_rating'] = display_df['avg_opponent_rating'].apply(lambda x: f"{x:.0f}")
      display_df.columns = ['Opening', 'Games', 'Win Rate', 'Avg Opponent', 'Trend']
      st.dataframe(display_df, use_container_width=True, hide_index=True)
  else:
      st.info("No openings match this trend filter.")

  # Takeaway
  improving = df_latest[df_latest['trend'] == 'improving'] if 'trend' in df_latest.columns else []
  declining = df_latest[df_latest['trend'] == 'declining'] if 'trend' in df_latest.columns else []
  if len(improving) > 0:
      st.success(f"{len(improving)} opening(s) improving this month")
  if len(declining) > 0:
      st.warning(f"{len(declining)} opening(s) declining this month")





elif page == "Know Your Opponent":
  st.header("Know Your Opponent")
  st.write("How do you perform against different strength opponents?")
  
  df = run_query("SELECT * FROM main_gold.gold_opponent_analysis")
  
  # Filter
  time_classes = df['time_class'].unique().tolist()
  selected_tc = st.selectbox("Time Control", time_classes, key="opponent_tc")
  df = df[df['time_class'] == selected_tc]
  
  st.divider()
  
  # Order buckets logically
  bucket_order = ['much_lower', 'lower', 'equal', 'higher', 'much_higher']
  df['rating_bucket'] = pd.Categorical(df['rating_bucket'], categories=bucket_order, ordered=True)
  df = df.sort_values('rating_bucket')
  
  # Win rate by rating bucket
  st.subheader("Win Rate by Opponent Strength")
  fig = px.bar(df, x='rating_bucket', y='win_rate',
                text=df.apply(lambda x: f"{x['win_rate']:.0%} ({int(x['games_played'])} games(s))", axis=1),
                color='win_rate',
                color_continuous_scale='RdYlGn',
                labels={'rating_bucket': 'Opponent Strength', 'win_rate': 'Win Rate'})
  fig.update_traces(textposition='outside', marker_line_width=0)
  fig.update_layout(
      yaxis_tickformat='.0%',
      plot_bgcolor='rgba(0,0,0,0)',
      paper_bgcolor='rgba(0,0,0,0)',
      height=450,
      coloraxis_showscale=False,
      yaxis=dict(gridcolor='rgba(128,128,128,0.2)'),
      margin=dict(t=30, b=50),
      font=dict(size=13)
  )
  st.plotly_chart(fig, width='stretch')
  
  st.divider()
  
  # Upset stats
  st.subheader("Upset Wins")
  total_upsets = int(df['upset_wins'].sum())
  higher_games = df[df['rating_bucket'].isin(['higher', 'much_higher'])]['games_played'].sum()
  
  cols = st.columns(2)
  with cols[0]:
      st.metric("Total Upset Wins", total_upsets)
  with cols[1]:
      higher_df = df[df['rating_bucket'].isin(['higher', 'much_higher'])]
      higher_upsets = int(higher_df['upset_wins'].sum())
      higher_games = int(higher_df['games_played'].sum())
      if higher_games > 0:
          overall_upset_rate = higher_upsets / higher_games
          st.metric("Upset Rate vs Stronger Opponents", f"{overall_upset_rate:.0%}")
  
  # Takeaway
  if not df.empty:
      best_bucket = df.loc[df['win_rate'].idxmax()]
      worst_bucket = df.loc[df['win_rate'].idxmin()]
      st.success(f"Strongest against **{best_bucket['rating_bucket']}** rated opponents ({best_bucket['win_rate']:.0%} win rate)")
      st.error(f"Weakest against **{worst_bucket['rating_bucket']}** rated opponents ({worst_bucket['win_rate']:.0%} win rate)")





elif page == "Session Insights":
  st.header("Session Insights")
  st.write("How does session length affect your performance? Should you stop after a few games or keep grinding?")
  
  df = run_query("SELECT * FROM main_gold.gold_sessions")
  
  # Filter
  time_classes = df['time_class'].unique().tolist()
  selected_tc = st.selectbox("Time Control", time_classes, key="session_tc")
  df = df[df['time_class'] == selected_tc]
  
  st.divider()
  
  # Key metrics
  cols = st.columns(4)
  with cols[0]:
      st.metric("Total Sessions", len(df))
  with cols[1]:
      avg_games = df['games_played'].mean()
      st.metric("Avg Games/Session", f"{avg_games:.1f}")
  with cols[2]:
      avg_delta = df['rating_delta'].mean()
      st.metric("Avg Rating Change", f"{avg_delta:+.0f}", delta_color="normal")
  with cols[3]:
      positive_sessions = (df['rating_delta'] > 0).sum() / len(df) if len(df) > 0 else 0
      st.metric("Profitable Sessions", f"{positive_sessions:.0%}")
  
  st.divider()
  
  # Win rate by session length
  st.subheader("Win Rate by Session Length")
  df['win_rate'] = df['wins'] / df['games_played']
  df['length_bucket'] = pd.cut(df['games_played'], 
                                bins=[0, 2, 5, 10, 20, 100], 
                                labels=['1-2', '3-5', '6-10', '11-20', '20+'])
  
  session_stats = df.groupby('length_bucket', observed=True).agg(
      sessions=('session_id', 'count'),
      avg_win_rate=('win_rate', 'mean'),
      avg_rating_delta=('rating_delta', 'mean')
  ).reset_index()
  
  fig = px.bar(session_stats, x='length_bucket', y='avg_win_rate',
                text=session_stats.apply(lambda x: f"{x['avg_win_rate']:.0%} ({int(x['sessions'])}s)", axis=1),
                color='avg_win_rate',
                color_continuous_scale='RdYlGn',
                labels={'length_bucket': 'Games per Session', 'avg_win_rate': 'Avg Win Rate'})
  fig.update_traces(textposition='outside', marker_line_width=0)
  fig.update_layout(
      yaxis_tickformat='.0%',
      plot_bgcolor='rgba(0,0,0,0)',
      paper_bgcolor='rgba(0,0,0,0)',
      height=400,
      coloraxis_showscale=False,
      yaxis=dict(gridcolor='rgba(128,128,128,0.2)'),
      margin=dict(t=30, b=50),
      font=dict(size=13)
  )
  st.plotly_chart(fig, width='stretch')
  
  st.divider()
  
  # Rating change by session length
  st.subheader("Avg Rating Change by Session Length")
  fig2 = px.bar(session_stats, x='length_bucket', y='avg_rating_delta',
                text=session_stats['avg_rating_delta'].apply(lambda x: f"{x:+.0f}"),
                color=session_stats['avg_rating_delta'].apply(lambda x: 'positive' if x >= 0 else 'negative'),
                color_discrete_map={'positive': '#2ecc71', 'negative': '#e74c3c'},
                labels={'length_bucket': 'Games per Session', 'avg_rating_delta': 'Avg Rating Change'})
  fig2.update_traces(textposition='outside', marker_line_width=0)
  fig2.update_layout(
      plot_bgcolor='rgba(0,0,0,0)',
      paper_bgcolor='rgba(0,0,0,0)',
      height=400,
      showlegend=False,
      yaxis=dict(gridcolor='rgba(128,128,128,0.2)'),
      margin=dict(t=30, b=50),
      font=dict(size=13)
  )
  st.plotly_chart(fig2, width='stretch')
  
  # Takeaway
  best_length = session_stats.loc[session_stats['avg_rating_delta'].idxmax()]
  worst_length = session_stats.loc[session_stats['avg_rating_delta'].idxmin()]
  st.success(f"Best session length: **{best_length['length_bucket']}** games (avg {best_length['avg_rating_delta']:+.0f} rating)")
  st.warning(f"Worst session length: **{worst_length['length_bucket']}** games (avg {worst_length['avg_rating_delta']:+.0f} rating)")