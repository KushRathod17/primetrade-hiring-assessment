import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

sns.set_style("darkgrid")
plt.rcParams['figure.dpi'] = 130

print("Loading data...")
trades     = pd.read_csv(r"C:\Users\Kush\Downloads\Projects\primetrade_task\trades.csv")
fear_greed = pd.read_csv(r"C:\Users\Kush\Downloads\Projects\primetrade_task\fear_greed_index.csv")

print("Trades columns    :", trades.columns.tolist())
print("Fear/Greed columns:", fear_greed.columns.tolist())
print("Trades shape      :", trades.shape)
print("Fear/Greed shape  :", fear_greed.shape)


trades['datetime'] = pd.to_datetime(trades['Timestamp IST'], format='%d-%m-%Y %H:%M')
trades['date'] = trades['datetime'].dt.strftime('%Y-%m-%d')

fear_greed['date'] = pd.to_datetime(fear_greed['date']).dt.strftime('%Y-%m-%d')
fear_greed = fear_greed.rename(columns={'classification': 'sentiment'})


for col in ['Closed PnL', 'Size USD', 'Fee']:
    if col in trades.columns:
        trades[col] = pd.to_numeric(trades[col], errors='coerce')

closed = trades.dropna(subset=['Closed PnL']).copy()
closed = closed.rename(columns={'Closed PnL': 'closedPnL'})
print(f"\nTotal trades: {len(trades)} | Closed trades: {len(closed)}")


merged = closed.merge(fear_greed[['date', 'sentiment']], on='date', how='left')
print("\nSentiment distribution:")
print(merged['sentiment'].value_counts())

merged['is_win'] = merged['closedPnL'] > 0

agg_dict = {
    'total_trades': ('closedPnL', 'count'),
    'win_rate':     ('is_win',    'mean'),
    'avg_pnl':      ('closedPnL', 'mean'),
    'median_pnl':   ('closedPnL', 'median'),
    'total_pnl':    ('closedPnL', 'sum'),
}
if 'leverage' in merged.columns:
    agg_dict['avg_leverage'] = ('leverage', 'mean')

sentiment_stats = merged.groupby('sentiment').agg(**agg_dict).round(4)

print("\n===== SENTIMENT PERFORMANCE =====")
print(sentiment_stats.to_string())

order = ['Extreme Fear', 'Fear', 'Neutral', 'Greed', 'Extreme Greed']
order = [s for s in order if s in sentiment_stats.index]
colors = ['#d62728', '#ff7f0e', '#7f7f7f', '#2ca02c', '#1f77b4'][:len(order)]

num_plots = 3 if 'avg_leverage' in sentiment_stats.columns else 2
fig, axes = plt.subplots(1, num_plots, figsize=(6 * num_plots, 5))
fig.suptitle("Trader Performance by Market Sentiment", fontsize=14, fontweight='bold')

sentiment_stats.loc[order, 'win_rate'].plot(kind='bar', ax=axes[0], color=colors)
axes[0].set_title('Win Rate by Sentiment')
axes[0].set_ylabel('Win Rate')
axes[0].set_ylim(0, 1)
axes[0].tick_params(axis='x', rotation=30)

sentiment_stats.loc[order, 'avg_pnl'].plot(kind='bar', ax=axes[1], color=colors)
axes[1].set_title('Avg PnL by Sentiment')
axes[1].set_ylabel('Avg Closed PnL')
axes[1].tick_params(axis='x', rotation=30)

if 'avg_leverage' in sentiment_stats.columns:
    sentiment_stats.loc[order, 'avg_leverage'].plot(kind='bar', ax=axes[2], color=colors)
    axes[2].set_title('Avg Leverage by Sentiment')
    axes[2].set_ylabel('Leverage')
    axes[2].tick_params(axis='x', rotation=30)

plt.tight_layout()
plt.savefig('plot1_sentiment_performance.png')
print("\n Saved: plot1_sentiment_performance.png")
plt.show()


if 'Side' in merged.columns:
    side_df = merged.groupby(['sentiment', 'Side'])['closedPnL'].agg(['count', 'mean']).reset_index()
    side_df.columns = ['sentiment', 'side', 'count', 'avg_pnl']

    pivot_count = side_df.pivot(index='sentiment', columns='side', values='count').fillna(0)
    pivot_count.plot(kind='bar', figsize=(10, 5), colormap='RdYlGn')
    plt.title('Long vs Short Trade Count by Market Sentiment')
    plt.ylabel('Number of Trades')
    plt.xticks(rotation=30)
    plt.tight_layout()
    plt.savefig('plot2_long_short_sentiment.png')
    print("✅ Saved: plot2_long_short_sentiment.png")
    

daily = merged.groupby('date').agg(
    total_pnl = ('closedPnL', 'sum'),
    sentiment = ('sentiment', 'first')
).reset_index()
daily['date'] = pd.to_datetime(daily['date'])
daily = daily.sort_values('date')

color_map = {
    'Extreme Fear':  '#d62728',
    'Fear':          '#ff7f0e',
    'Neutral':       '#7f7f7f',
    'Greed':         '#2ca02c',
    'Extreme Greed': '#1f77b4'
}

fig, ax = plt.subplots(figsize=(16, 6))
for _, row in daily.iterrows():
    c = color_map.get(str(row['sentiment']), 'gray')
    ax.bar(row['date'], row['total_pnl'], color=c, alpha=0.8, width=1)

from matplotlib.patches import Patch
legend_els = [Patch(facecolor=v, label=k) for k, v in color_map.items()]
ax.legend(handles=legend_els, loc='upper left')
ax.set_title('Daily Total PnL — Colored by Market Sentiment')
ax.set_xlabel('Date')
ax.set_ylabel('Total Closed PnL')
plt.tight_layout()
plt.savefig('plot3_daily_pnl_timeline.png')
print("✅ Saved: plot3_daily_pnl_timeline.png")
plt.show()

if 'account' in merged.columns:
    trader_stats = merged.groupby('account').agg(
        total_trades = ('closedPnL', 'count'),
        win_rate     = ('is_win',    'mean'),
        total_pnl    = ('closedPnL', 'sum'),
        avg_pnl      = ('closedPnL', 'mean'),
    ).reset_index().round(4)

    top10 = trader_stats[trader_stats['total_trades'] >= 10].nlargest(10, 'total_pnl')
    print("\n===== TOP 10 TRADERS =====")
    print(top10.to_string(index=False))
else:
    trader_stats = pd.DataFrame()
    top10 = pd.DataFrame()
    print("\n  No 'account' column found — skipping top traders.")

groups = [g['closedPnL'].dropna().values for _, g in merged.groupby('sentiment')]
if len(groups) >= 2:
    f, p = stats.f_oneway(*groups)
    print(f"\nANOVA — F={f:.4f}, p={p:.6f}")
    if p < 0.05:
        print(" Statistically significant difference in PnL across sentiment groups!")
    else:
        print(" No statistically significant difference found.")

with pd.ExcelWriter('primetrade_results.xlsx', engine='openpyxl') as writer:
    sentiment_stats.to_excel(writer, sheet_name='Sentiment Stats')
    if not top10.empty:
        top10.to_excel(writer, sheet_name='Top 10 Traders', index=False)
    daily.to_excel(writer, sheet_name='Daily PnL', index=False)

print("\n All results saved to: primetrade_results.xlsx")
print("\n Analysis complete!")
