# Methodology

This document explains the design decisions behind the pipeline, how data quality is handled, how unusual jumps are detected, and how the forecasts were built and tested. For a quick overview and setup instructions, see the [README](../README.md).

## Contents

1. [Ingestion and loading](#1-ingestion-and-loading)
2. [Missing data](#2-missing-data)
3. [Data model](#3-data-model)
4. [Detecting unusual jumps](#4-detecting-unusual-jumps)
5. [Forecasting electricity access](#5-forecasting-electricity-access)
6. [Known limitations](#6-known-limitations)

## 1. Ingestion and loading

**Fetching.** One request per indicator covers all 16 countries, since the World Bank API accepts country codes joined with `;`. The script reads the page count from each response and keeps fetching until it has every page.

**Retries.** Each request is tried up to three times, waiting 5 then 10 seconds between attempts. This came straight from experience: the very first API call failed on a network blip, and on the first full run two requests timed out and succeeded on retry.

**Hidden errors.** The API sometimes returns an error message inside an otherwise normal response. The script checks for this and stops rather than saving bad data.

**Raw files are kept.** Every response is saved untouched in a folder named after the run date. Everything downstream can be rebuilt from these files without downloading again, and runs can be compared to see when the World Bank revises numbers.

**Safe reruns.** Before loading a run, the loader deletes any rows already loaded from that run date. Running it twice gives the same result instead of duplicates. Each row also records its run date, source file and load time, so any value can be traced back to the file it came from.

**Two refresh styles.** Indicator values keep the history of every run. Country details are small reference data, so that table is simply replaced on each run.

**Skipping when nothing changed.** Every API response includes a `lastupdated` date. A quick check asks for one row per indicator, compares those dates with the ones saved after the last successful run, and only runs the full pipeline if something changed. The dates are saved only after a successful build, so a failed run is retried the next month instead of being skipped.

## 2. Missing data

Every indicator returns 416 rows (16 countries × 26 years), but that count says nothing about completeness: the API returns a row even when the value is empty.

| Indicator | Missing values |
| --- | --- |
| Manufactured exports | 23.6% |
| Manufacturing value added | 6.7% |
| Access to electricity | 6.0% |
| Employment in industry, Industry value added, GDP | 0% |

The gaps fall into four patterns:

| Pattern | Examples | Meaning |
| --- | --- | --- |
| Latest year missing | 2025 electricity for all 16 countries | Reporting lag |
| Stopped reporting | Liberia manufacturing ends 2011 | Recent years will stay empty for a while |
| Late start | Liberia electricity begins 2007 | No early history to compare |
| Sparse throughout | Guinea-Bissau exports: 4 of 26 years | Too thin to use |

**Rules applied in the pipeline:**

1. **Missing values are never filled in.** Inventing values hides the problem.
2. **A year is provisional** when fewer than half of the 16 countries have reported it.
3. **A country and indicator pair has low coverage** when fewer than half its years have data.

These rules flagged exactly what the exploration predicted: low coverage for exports in Guinea-Bissau (15.4%), Sierra Leone and Liberia (26.9% each) and Guinea (46.2%), plus manufacturing in Liberia (46.2%). Electricity and exports are provisional for 2025.

**Complete isn't the same as measured.** Employment in industry has no gaps at all, even for the latest year. That points to modelled estimates rather than surveys.

## 3. Data model

The finished tables form a star schema:

- `fct_indicator_values`: one row per country, indicator and year, carrying the value and three flags (`is_provisional`, `is_low_coverage`, `is_ecowas_member`).
- `dim_country`: names, region, income level, coordinates and ECOWAS membership years.
- `dim_indicator`: short names, units and themes for chart labels.

**ECOWAS membership by year.** Membership is kept in a small hand-written file (a dbt seed), because it changes over time. A country counts as a member for a year if it was a member for most of that year. Mauritania left on 26 December 2000, so it counts as a member in 2000 but not from 2001. Burkina Faso, Mali and Niger left on 29 January 2025, so they count as members up to 2024.

**Income level is today's label.** The World Bank reviews income classifications every year, so applying the current label to earlier years is a simplification. This is noted in the model.

**Tests.** 24 tests run on every build. They check for one row per key, no empty keys, valid ranges, that every fact row links to a country and an indicator, and that every country and indicator has its seed entry. Adding a country or indicator without updating the seeds makes the build fail.

## 4. Detecting unusual jumps

### Why not a fixed cut-off

A rule like "flag any change over 10 points" doesn't work here. A 10-point rise is normal for a fast-growing country and enormous for a slow one, and GDP is measured in dollars, not points. So each change is judged against that country's own history instead.

### How the score works

For each country and indicator:

1. List every year-on-year change. For GDP, use percentage growth instead.
2. Find the **typical change**: sort the changes and take the middle one (the median).
3. Measure how far each year was from typical, ignoring direction.
4. Take the middle of those distances. This is the **median absolute deviation** (MAD).
5. Multiply by **1.4826** to put it on the standard scale (explained below). The result is the **normal wobble**.
6. **Safety rule:** if the country's wobble is smaller than the wobble across all 16 countries for that indicator, use the larger one.

The score is then:

```
score = (this year's change − typical change) ÷ normal wobble
```

A score of 5 means the change is five times bigger than that country's usual wobble.

**Everyday comparison:** if a commute is usually within 5 minutes of normal, arriving 25 minutes late is five times the normal wobble. Something clearly happened that day.

### Worked example: Benin's access to electricity

Simplified to 2011 to 2024 so the numbers are easy to follow (the pipeline uses every year from 2001).

1. **Yearly changes:** +2.7, +1.5, −3.7, −0.6, −4.5, +7.4, −2.5, +4.5, +1.0, +1.0, +1.0, **+14.5**, +0.5, +2.0
2. **Typical change** (the middle value when sorted): **+1.0** a year
3. **Distance of each year from +1.0:** 1.7, 0.5, 4.7, 1.6, 5.5, 6.4, 3.5, 3.5, 0, 0, 0, **13.5**, 0.5, 1.0
4. **Middle of those distances (MAD):** **1.65** points
5. **Normal wobble:** 1.65 × 1.4826 ≈ **2.4** points
6. **Score for 2022:** (14.5 − 1.0) ÷ 2.4 ≈ **5.6**

Using every year from 2001, Benin's earlier years were calmer, so its real wobble is about 1.3 points and its real score is **10.1**.

**Why medians:** the 13.5 sits at the end of the list in step 3. Because the middle value is taken, that one huge number barely changes the result. An average would be pulled up by it, inflating the wobble so that the jump partly hides itself.

### Where 1.4826 comes from

`1.4826` is a conversion factor. It turns the outlier-proof measure of spread into the standard unit everyone else uses.

**Two rulers for spread.** The **standard deviation (SD)** is the standard ruler, and most statistical rules of thumb are written in SD units, such as "more than 3 SDs from average is unusual". But it's built on averages, so one huge outlier stretches it. The **MAD** is built on middle values, so outliers barely affect it. But it sits on a different scale, so the familiar rules don't apply to it directly. It's like centimetres and inches: they need converting before they can be compared. 1.4826 is the exchange rate.

**Where the number comes from:**

1. By definition, the MAD is the distance that half of all years land within. Half are closer to typical, half are further away.
2. For a bell curve, half of all values fall within 0.6745 SDs of the middle.
3. So for bell-shaped data, MAD ≈ 0.6745 × SD.
4. To turn the MAD back into SD units, divide by 0.6745. And 1 ÷ 0.6745 = **1.4826**.

Multiplying by 1.4826 gives what the SD would be if there were no outliers distorting it.

**Commute example:** if half of all days end within 5 minutes of normal, that's the MAD. In SD units the spread is 5 × 1.4826 ≈ 7.4 minutes. Arriving 37 minutes late is 5 SDs away, a score of 5.

**Result:** the score reads like the familiar "how many standard deviations away" number, but isn't fooled by outliers. This is known as a **modified z-score**.

**Caveat:** the conversion assumes the wobbles are roughly bell-shaped. World Bank data isn't perfectly so, because of filled-in stretches, survey jumps and wars. The score is a good guide rather than an exact measure, which is why the cut-off was chosen by looking at what it actually flagged.

### Choosing the cut-off

**First attempt.** Using only each country's own wobble flagged 142 of 2,249 changes at 3.5, and Benin's known jump didn't even reach the top 15. Many series contain stretches of filled-in values that rise by exactly the same amount every year, which makes a country's wobble tiny. Then any ordinary movement scores enormously. Mauritania's manufactured exports had a typical change of 0.0, so a 3-point move scored 33. Adding the safety rule (step 6) fixed this.

**Second attempt:**

| Cut-off | Changes flagged | Share |
| --- | --- | --- |
| 3.5 | 84 | 3.7% |
| **5** | **36** | **1.6%** |

Benin's 2022 jump ranked **3rd of 2,249**, so the method catches a break already known to be real. A cut-off of **5** was chosen: every important case scores well above it, and 3.5 mostly adds ordinary noise.

### What the flags turned out to be

| Kind | Examples | Meaning |
| --- | --- | --- |
| Measurement breaks | Benin electricity 2022 (+14.5), Burkina Faso 2024 (+12.3), Mali 2018 (+16.1) | The level resets and stays there, likely after a new survey |
| Real shocks | Liberia GDP 2003 (−30%), Sierra Leone GDP 2002 (+26.5%) | Match the end of the civil wars in both countries |
| One-year spikes | Gambia manufactured exports 2012 (+33.8) then 2013 (−32.7) | Up and straight back down, most likely a data error |

An unusual jump isn't automatically wrong. Wars and new surveys are real. So jumps are flagged for a person to review, never rejected.

### Benin's 2022 break

Benin rose by exactly 1.0 point a year from 2019 to 2021, which looks like estimates filled in between surveys, then jumped 14.5 points in 2022. Neighbouring Togo rose 1.5 points that year and Nigeria 1.0. Benin carried out its national household survey (EHCVM) in two waves, in 2021 and 2022, and a new survey resetting the level fits the pattern. Real progress also played a part, since Benin has been expanding access with World Bank support since 2016. But a 14.5-point rise in a single year is far beyond what new connections alone could explain. The survey explanation is likely but not confirmed.

### In the pipeline

- `indicator_jumps` (dbt model) scores every change and keeps the `normal_wobble` used, so any score can be checked by hand.
- `reviewed_jumps.csv` (seed) lists jumps a person has already checked, each with a note.
- `warn_new_unusual_jumps` (dbt test) **warns**, without stopping the pipeline, when a jump in the latest three years scores above 5 and isn't on the reviewed list. Without the reviewed list, the same known jumps would warn every month, and warnings that never change get ignored. With it, a warning always means something new.

The cut-off and the three-year window are settings in `dbt_project.yml`.

## 5. Forecasting electricity access

### Setup

Access to electricity is forecast five years past each country's last known year, for every country that passes the coverage rule. Five years is as far as about 25 yearly data points can honestly support. Forecasts are kept between 0 and 100.

The models are written in plain Python with no extra libraries, so every line can be explained and the monthly cloud runs stay fast.

| Model | How it works |
| --- | --- |
| Naive | Repeats the last known value |
| Linear trend | Fits a straight line to the last 10 years and extends it |
| Damped Holt | Tracks a level and a trend; a damping factor makes the trend fade, so the forecast flattens. Settings are chosen by trying 270 combinations and keeping the best fit |
| Blend | The average of the linear trend and damped Holt |

**Why a damped trend:** the damping makes the forecast curve and flatten instead of shooting past 100%. That's realistic for electricity access, because growth slows as countries get closer to full coverage.

### Backtests

Each model was trained on earlier years and asked to forecast five hidden years. The table shows the average miss in percentage points (lower is better).

| Model | Hidden 2020 to 2024 | Hidden 2015 to 2019 |
| --- | --- | --- |
| Blend | 2.85 | **2.91** |
| Linear trend | **2.73** | 3.62 |
| Damped Holt | 3.36 | 3.26 |
| Naive | 5.43 | 4.03 |

The straight line won the first test but came fourth on the second. A single test period can mislead.

### Testing the "growth slows" idea

Splitting countries by access level at the start of each test showed a clear pattern:

| Test period | Damped beat linear, at 50% access or above | Linear beat damped, below 50% |
| --- | --- | --- |
| 2020 to 2024 | 5 of 7 countries | 8 of 9 countries |
| 2015 to 2019 (unseen when the idea was formed) | 5 of 6 countries | 6 of 9 countries |

So the reasoning holds, with a sharper scope: **growth slows as countries get closer to full coverage, so a damped trend suits countries above roughly 50% access, while a straight line suits countries still early in their rise.** The pattern was spotted in the 2020 to 2024 results and then confirmed on the earlier period.

### Choice of model

The **blend** was chosen. It was the most consistent across both periods, the best on the unseen period, and needed nothing tuned by hand. The 50% finding explains why it works: the damped half helps countries near full coverage, and the straight-line half keeps fast risers on track.

### Ranges

The ranges come from real mistakes, not a formula. The blend is rerun on both backtest periods, and its misses are recorded at 1, 2, 3, 4 and 5 years ahead. At each step, the range covers 80% of those past misses, and it never shrinks further ahead. The result runs from about ±2.4 points one year ahead to ±7.2 points five years ahead.

### 2029 forecasts

| Country | Forecast (% with electricity) | 80% range |
| --- | --- | --- |
| Cabo Verde | 100.0 | 92.8 to 100 |
| Ghana | 98.6 | 91.4 to 100 |
| Senegal | 84.8 | 77.6 to 92.0 |
| Cote d'Ivoire | 77.9 | 70.7 to 85.1 |
| Gambia | 74.4 | 67.2 to 81.6 |
| Benin | 71.0 | 63.8 to 78.2 |
| Togo | 69.0 | 61.8 to 76.2 |
| Nigeria | 64.7 | 57.5 to 71.9 |
| Guinea | 64.1 | 56.9 to 71.3 |
| Mali | 63.2 | 56.1 to 70.4 |
| Mauritania | 57.0 | 49.8 to 64.1 |
| Guinea-Bissau | 54.1 | 46.9 to 61.2 |
| Sierra Leone | 47.5 | 40.4 to 54.7 |
| Burkina Faso | 43.7 | 36.5 to 50.9 |
| Liberia | 43.2 | 36.0 to 50.4 |
| Niger | 22.6 | 15.5 to 29.8 |

These are produced fresh on every monthly run and saved to the `fct_indicator_forecasts` table, together with the model name and the last real year used.

## 6. Known limitations

- **Forecasts assume past trends continue.** A large grid project or a crisis would change things in ways no trend model can see.
- **Every country gets the same range width** for a given year ahead. Benin was much harder to predict than most, so its real uncertainty is probably wider than shown.
- **Measurement breaks feed into forecasts.** Benin's 2022 and Burkina Faso's 2024 jumps push their forecasts up, so those two should be read with extra caution.
- **Much of the source data is estimated.** Smooth stretches that rise by the same amount every year are filled in between surveys, not measured.
- **Income level is the current classification**, applied to all years.
- **The backtests are small:** 16 countries over two five-year periods, so small differences between models may be noise.