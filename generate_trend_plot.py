"""Generate line graph of article counts over time."""

import polars as pl
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import random

# Load the Delta Lake table
table_path = "covid_nz_news_delta"
df = pl.scan_delta(table_path).collect()

print(f"Total articles: {len(df)}")

if len(df) == 0:
    print("No articles in database. Using demo data to showcase visualization.")
    print("Run build_database.py to collect real articles from Common Crawl.")
    
    # Generate 30 days of demo data
    dates = []
    counts = []
    base_date = datetime(2020, 3, 1)
    
    for i in range(30):
        date = base_date + timedelta(days=i)
        # Simulate COVID news trend (spike in March-April 2020)
        if i < 10:
            count = random.randint(5, 20)  # Early days
        elif i < 20:
            count = random.randint(30, 60)  # Peak
        else:
            count = random.randint(15, 35)  # Declining
        
        dates.append(date.strftime("%Y-%m-%d"))
        counts.append(count)
    
    daily_counts = pl.DataFrame({
        "publish_date": dates,
        "count": counts
    })
    is_demo = True
else:
    # Filter out empty publish dates
    df = df.filter(pl.col("publish_date").str.len_chars() > 0)
    print(f"Articles with publish_date: {len(df)}")
    
    if len(df) == 0:
        print("No articles with valid publish_date. Using demo data.")
        # Generate demo data
        dates = []
        counts = []
        base_date = datetime(2020, 3, 1)
        
        for i in range(30):
            date = base_date + timedelta(days=i)
            if i < 10:
                count = random.randint(5, 20)
            elif i < 20:
                count = random.randint(30, 60)
            else:
                count = random.randint(15, 35)
            
            dates.append(date.strftime("%Y-%m-%d"))
            counts.append(count)
        
        daily_counts = pl.DataFrame({
            "publish_date": dates,
            "count": counts
        })
        is_demo = True
    else:
        # Group by date and count
        daily_counts = (
            df
            .group_by("publish_date")
            .agg(pl.len().alias("count"))
            .sort("publish_date")
        )
        is_demo = False

print(f"\nDaily counts ({len(daily_counts)} days):")
print(daily_counts)

# Create the plot
plt.figure(figsize=(12, 6))
plt.plot(daily_counts["publish_date"], daily_counts["count"], marker='o', linewidth=2, markersize=6, color='#2196F3')

# Format the plot
plt.xlabel("Date", fontsize=12)
plt.ylabel("Number of Articles", fontsize=12)
plt.title("COVID-19 News Articles in New Zealand Media Over Time", fontsize=14, fontweight='bold')

# Format x-axis dates
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
plt.gca().xaxis.set_major_locator(mdates.AutoDateLocator())
plt.gcf().autofmt_xdate()

# Add grid
plt.grid(True, alpha=0.3)

# Add annotation if demo data
if is_demo:
    plt.annotate("Demo data - run build_database.py to collect real articles",
                xy=(0.02, 0.98), xycoords='axes fraction',
                fontsize=9, style='italic',
                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))

# Tight layout and save
plt.tight_layout()
plt.savefig("covid_news_trend.png", dpi=150, bbox_inches='tight')
print("\nSaved: covid_news_trend.png")
