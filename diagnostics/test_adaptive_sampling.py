"""
Diagnostic: Check adaptive sampling for the Word Quiz.

Steps:
  1. Load the full word dictionary.
  2. Inspect columns and weight distribution.
  3. Run N simulations of 20-word quizzes with adaptive_sampling=True.
  4. Aggregate selection counts per word.
  5. Chi-square goodness-of-fit test (uniform vs. actual) and a weighted test.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

import numpy as np
import pandas as pd
from scipy.stats import chisquare, chi2
from collections import Counter

from main.quiz import QuizGenerator, calculate_adaptive_weights

# ── 1. Load data ──────────────────────────────────────────────────────────────
print("=" * 65)
print("STEP 1 — Load dataset")
print("=" * 65)
qg = QuizGenerator()
df = qg.dict_df.copy()
print(f"Total words in dictionary: {len(df)}")
print(f"Columns available: {list(df.columns)}\n")

# ── 2. Check which adaptive-weight columns are present ────────────────────────
print("=" * 65)
print("STEP 2 — Check adaptive-sampling column availability")
print("=" * 65)
required_wrong   = ['Num Pinyin Wrong', 'Num Meaning Wrong']
required_correct = ['Num Pinyin Correct', 'Num Meaning Correct']
required_all     = required_wrong + required_correct

missing = [c for c in required_all if c not in df.columns]
if missing:
    print(f"  *** PROBLEM: missing columns → {missing}")
    print("  → The guard in generate_pinyin_and_meaning_quiz will fall back")
    print("    to UNIFORM sampling every time.  Adaptive sampling is INACTIVE.\n")
    adaptive_possible = False
else:
    print("  All required columns present — adaptive sampling CAN fire.")
    adaptive_possible = True

# Show whatever perf columns do exist
perf_cols = [c for c in df.columns if any(k in c for k in ['Pinyin', 'Meaning', 'Quiz', 'Correct', 'Wrong'])]
print(f"\n  Performance columns found: {perf_cols}")
if perf_cols:
    print(df[perf_cols].describe().to_string())
print()

# ── 3. Compute expected weights ───────────────────────────────────────────────
print("=" * 65)
print("STEP 3 — Expected per-word selection probability")
print("=" * 65)

if adaptive_possible:
    weights = calculate_adaptive_weights(df)
    df['_weight'] = weights
    print(f"  Weight min={weights.min():.6f}  max={weights.max():.6f}  "
          f"mean={weights.mean():.6f}  std={weights.std():.6f}")
    top10 = df.nlargest(10, '_weight')[['Word', '_weight'] + perf_cols]
    print(f"\n  Top-10 highest-weight words:\n{top10.to_string(index=False)}\n")
    uniform_p = np.ones(len(df)) / len(df)
    expected_p = weights
else:
    print("  Using uniform weights (adaptive sampling inactive).")
    df['_weight'] = 1.0 / len(df)
    expected_p = df['_weight'].values
    uniform_p  = expected_p

# ── 4. Simulate N quizzes ─────────────────────────────────────────────────────
N_SIMS    = 200
NUM_WORDS = 20
print("=" * 65)
print(f"STEP 4 — Simulate {N_SIMS} × {NUM_WORDS}-word quizzes")
print("=" * 65)

selection_counter = Counter()
for i in range(N_SIMS):
    quiz_df = qg.generate_pinyin_and_meaning_quiz(num_words=NUM_WORDS, adaptive_sampling=True)
    for word_id in quiz_df['Word Id'].values:
        selection_counter[word_id] += 1

total_selections = sum(selection_counter.values())
print(f"  Total word-selections across all sims: {total_selections}")
print(f"  Unique words selected: {len(selection_counter)} / {len(df)}\n")

# ── 5. Build observed / expected arrays ───────────────────────────────────────
# Align to full dictionary order
observed_counts = np.array([selection_counter.get(wid, 0) for wid in df['Word Id']])

# Expected under UNIFORM sampling
uniform_expected = np.full(len(df), total_selections / len(df))

# Expected under ADAPTIVE sampling (only if columns exist)
adaptive_expected = expected_p * total_selections

# ── 6 & 7. Chi-square tests using weight-quintile buckets ────────────────────
# With ~3273 words and 4000 total selections, per-word expected counts (~1.2)
# are far too small for a cell-level chi-square. Instead, aggregate into
# weight-quintile buckets so every cell has adequate expected counts.

N_BUCKETS = 10
df['_obs_count'] = observed_counts  # needed for bucketing below

print("=" * 65)
print("STEP 5 — Chi-square test (10 weight-quintile buckets): observed vs UNIFORM null")
print("=" * 65)

df['_bucket'] = pd.qcut(df['_weight'], q=N_BUCKETS, labels=False, duplicates='drop')
bucket_obs      = df.groupby('_bucket')['_obs_count'].sum().values
bucket_size     = df.groupby('_bucket').size().values
uniform_bucket_exp = bucket_size * (total_selections / len(df))

chi2_stat_u, p_u = chisquare(f_obs=bucket_obs, f_exp=uniform_bucket_exp)
print(f"  Buckets: {len(bucket_obs)}")
print(f"  Observed counts per bucket:  {bucket_obs.tolist()}")
print(f"  Expected (uniform) per bucket: {np.round(uniform_bucket_exp, 1).tolist()}")
print(f"  chi2 statistic = {chi2_stat_u:.2f}")
print(f"  degrees of freedom = {len(bucket_obs) - 1}")
print(f"  p-value = {p_u:.4e}")
if p_u < 0.05:
    print("  → REJECT uniform null (p < 0.05): distribution is NOT uniform.")
else:
    print("  → FAIL TO REJECT uniform null: no evidence of non-uniform sampling.")
print()

if adaptive_possible:
    print("=" * 65)
    print("STEP 6 — Chi-square test (10 weight-quintile buckets): observed vs ADAPTIVE expected")
    print("=" * 65)
    adaptive_bucket_exp = df.groupby('_bucket')['_weight'].sum().values * total_selections
    chi2_stat_a, p_a = chisquare(f_obs=bucket_obs, f_exp=adaptive_bucket_exp)
    print(f"  Buckets: {len(bucket_obs)}")
    print(f"  Observed counts per bucket:  {bucket_obs.tolist()}")
    print(f"  Expected (adaptive) per bucket: {np.round(adaptive_bucket_exp, 1).tolist()}")
    print(f"  chi2 statistic = {chi2_stat_a:.2f}")
    print(f"  degrees of freedom = {len(bucket_obs) - 1}")
    print(f"  p-value = {p_a:.4e}")
    if p_a < 0.05:
        print("  → REJECT adaptive null: observed distribution DIFFERS from")
        print("    what the weight formula predicts (possible bug or drift).")
    else:
        print("  → FAIL TO REJECT adaptive null: observed frequencies are")
        print("    consistent with the adaptive weight formula.")

# ── 8. Summary table: most / least sampled words ─────────────────────────────
print()
print("=" * 65)
print("STEP 7 — Top-20 most-selected words in simulations")
print("=" * 65)
df['_obs_freq']  = observed_counts / total_selections
show_cols = ['Word', '_obs_count', '_obs_freq', '_weight'] + \
            [c for c in perf_cols if c in df.columns]
top20 = df.nlargest(20, '_obs_count')[show_cols]
print(top20.to_string(index=False))

print()
print("=" * 65)
print("STEP 8 — Bottom-20 least-selected (never or rarely seen) words")
print("=" * 65)
bot20 = df.nsmallest(20, '_obs_count')[show_cols]
print(bot20.to_string(index=False))

print()
print("=" * 65)
print("STEP 9 — Words NEVER selected in any simulation")
print("=" * 65)
never = df[df['_obs_count'] == 0]
print(f"  Count: {len(never)}")
if len(never) > 0 and len(never) <= 30:
    print(never[['Word', '_weight'] + perf_cols[:4]].to_string(index=False))
elif len(never) > 30:
    print(f"  (showing first 30 of {len(never)})")
    print(never[['Word', '_weight'] + perf_cols[:4]].head(30).to_string(index=False))

print("\nDone.")
