import json

data = json.load(open('master_stocks_dataset.json', 'r', encoding='utf-8'))
disc = json.load(open('host_invested_disclosures.json', 'r', encoding='utf-8'))

print("=== AKSHAT SHRIVASTAVA COMPREHENSIVE INTELLIGENCE DATASET ===")
print(f"Total Evaluated Stock Recommendations/Analyses: {len(data)}")
print(f"Unique Listed Corporate Entities Analyzed: {len(set(d['company'] for d in data))}")
print(f"Total Distinct YouTube Episodes Analyzed: {len(set(d['video_id'] for d in data))}")

pos = sum(1 for d in data if d.get('view') == 'Positive')
neut = sum(1 for d in data if d.get('view') == 'Neutral')
neg = sum(1 for d in data if d.get('view') == 'Negative')
print(f"Sentiment Breakdown: Positive: {pos} ({pos/len(data)*100:.1f}%), Neutral: {neut} ({neut/len(data)*100:.1f}%), Negative: {neg} ({neg/len(data)*100:.1f}%)")

host_inv = sum(1 for d in data if d.get('host_disclosed_holding'))
print(f"Host Personally Disclosed Holdings: {host_inv}")
print(f"Disclosures Audited & Timestamped to Exact Seconds: {sum(len(v) for v in disc.values())}")

# Calculate performance metrics
valid_perf = [float(str(d['change']).replace('%','').replace('+','')) for d in data if d.get('change') and d.get('change') != 'N/A']
valid_alpha = [float(d['alpha_pct']) for d in data if d.get('alpha_pct') is not None]
if valid_perf:
    print(f"Average Stock Return across all recommendations: {sum(valid_perf)/len(valid_perf):+.2f}% (from {len(valid_perf)} price-tracked stocks)")
if valid_alpha:
    print(f"Average Alpha over Nifty 50: {sum(valid_alpha)/len(valid_alpha):+.2f}%")

# Top repeatedly discussed stocks
from collections import Counter
counts = Counter(d['company'] for d in data)
print("\nTop 10 Most Frequently Discussed Stocks:")
for comp, cnt in counts.most_common(10):
    print(f"  - {comp}: {cnt} episodes")
