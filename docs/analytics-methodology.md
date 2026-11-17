# BizBazaar analytics methodology

The local MVP uses deterministic calculations and explainable baselines. No trained model,
causal growth effect or official payment verification is implied.

## Records and dates

Canonical records are positive integer paise with a unique transaction ID within one merchant.
Only current SUCCESS records contribute to collections/count/average. PENDING, FAILED and
REFUNDED are excluded; refunds are not subtracted a second time. Changes to current statuses
can change historical reports; immutable settlement snapshots are not reconstructed.

Report start/end dates are inclusive in the merchant timezone. Inputs may include up to 90 days
of historical lookback before the report starts. Missing/partial coverage stays unknown. A complete
day explicitly declared with zero recorded transactions contributes a known zero. Current/future
days never train a baseline even if their coverage is incorrectly declared complete.

## Metrics and trends

Money sums are integer arithmetic. Positive averages are rounded half-up to the nearest paise.
Empty successful activity returns average=null. Daily points include observed records and declared
complete zero days; absent unknown days are omitted rather than inserted as zero.

Slow-weekday comparisons need at least three complete observations per eligible weekday and two
eligible weekdays to compare. Weekday indices use Monday=0 through Sunday=6. Below-mean weekday collections are descriptive, not a causal diagnosis.
Average-value change compares the latest two consecutive complete seven-calendar-day windows,
requiring at least five successful payments in each. The default alert threshold is 10%, configurable through the analytics API as a whole percentage from 1-100;
insufficient coverage produces no confident comparison. Unknown days are not skipped to manufacture
consecutive windows.

## Forecasting and evaluation

The forecast is the mean recorded collections of earlier complete days sharing the predicted
weekday. At least 28 complete training days and three observations for each predicted weekday
are required. Horizon is 1-14 days. Predictions are rounded to integer paise. No invented confidence
interval or annual seasonality is displayed.

Evaluation holds out the final seven consecutive complete calendar days. Both weekday and flat
mean baselines train strictly before the holdout. Returned dates, actuals, predictions, training
count, and MAE permit independent inspection. MAE is reported in paise to two decimals. Missing
holdout days or insufficient earlier training produce INSUFFICIENT_DATA, not an accuracy score.

## Recommendations and summaries

Suggestions copy the merchant's validated saved type, rule parameters, fixed reward cost, cap and
duration. Successful recorded activity and explicit settings are required. Sufficiency here means
that the configured rule can be proposed, not that effectiveness is statistically proven. The
backend still creates drafts and requires separate merchant approval and activation.

English/Hindi summaries render only calculated amounts, counts and dates. Optional external
style selection cannot supply arbitrary facts or amounts. Missing keys, invalid output and provider
errors preserve the deterministic fallback. No provider is configured or contacted by default.
