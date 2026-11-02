# Malaysia Inflation by State: Power BI Dashboard

**Question:** Where in Malaysia are prices rising fastest, and which spending categories are driving it?

![Overview page](images/overview.png)

<!-- Live report: add your Publish-to-web link here -->

## Key findings (CPI, September 2026)
1. **National inflation is 1.8% YoY**, but the spread between states is wide: **from 0.5% in Sarawak to 2.4% in Negeri Sembilan and Labuan**.
2. **Since January 2020, prices in Putrajaya are up 19.3%** (the highest), followed by Selangor at 15.1%. Labuan (7.7%) and Kelantan (8.0%) rose least.
3. **The top drivers right now are alcohol & tobacco and personal care (2.8% each), then transport (2.5%)**. Clothing (0.2%) and furnishings (0.3%) are almost flat.
4. Since 2010, national inflation peaked at **4.9% in March 2017**, just above the 2022 post-pandemic peak of 4.7% (August 2022).

## Dashboard pages
| Page | Answers |
|---|---|
| Overview | Headline rate, highest-inflation state, state ranking against the national rate, trend over time |
| State comparison | Year-by-state heatmap, cumulative rise since 2020, gap vs national |
| Category drill-through | Which categories drive inflation in a chosen state |

## Data
[OpenDOSM](https://open.dosm.gov.my/) consumer price index by state and by COICOP division, monthly from 2010 to September 2026. The national series is included as a benchmark. 47,838 rows.

## Method
| Step | File | What it does |
|---|---|---|
| 1 | `prepare.py` | Merges the index and inflation files, adds national rows, builds a star schema (`fact_cpi`, `dim_state`, `dim_division`), and checks that DOSM's YoY figures match the index |
| 2 | `powerbi/power_query.m` | Loads the CSVs with explicit types, using a folder parameter |
| 3 | `powerbi/measures.dax` | Date table plus measures: YoY via `DATEADD`, state rank via `RANKX`, gap vs national, cumulative rise, top state via `TOPN` |
| 4 | `powerbi/BUILD_GUIDE.md` | Visual-by-visual build steps |

Power BI skills used: star schema modeling, Power Query (M), DAX time intelligence, `RANKX` / `TOPN`, drill-through, conditional formatting, dynamic titles.

## Run it
```bash
pip install pandas
python prepare.py
```
Then follow [`powerbi/BUILD_GUIDE.md`](powerbi/BUILD_GUIDE.md).

To refresh with new months, re-download the 4 CSVs from `https://storage.dosm.gov.my/cpi/` (`cpi_2d_state`, `cpi_2d_state_inflation`, `cpi_2d`, `cpi_2d_inflation`) into `data/raw/`, rerun `prepare.py`, and click **Refresh** in Power BI.
