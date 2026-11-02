# Build guide: Power BI report

Takes about 2–3 hours the first time. Run `python prepare.py` first so `data/clean/` exists.

## 1. Load data (Power Query)
1. Open Power BI Desktop, then go to **Transform data**.
2. Create the `DataFolder` parameter and the 3 queries from [`power_query.m`](power_query.m).
3. **Close & Apply**.

> Check: in the `fact_cpi` table, `division_code` should show `01`, not `1`. If it shows `1`, the type step is missing.

## 2. Model
1. **Modeling > New table**: paste the `Date` table from [`measures.dax`](measures.dax). Then **Mark as date table** using `Date[Date]`.
2. In Model view, create these relationships (all many-to-one, single direction):
   - `fact_cpi[date]` → `Date[Date]`
   - `fact_cpi[state]` → `dim_state[state]`
   - `fact_cpi[division_code]` → `dim_division[division_code]`
3. Sort `dim_division[division]` by `sort_order`, and `Date[Month]` by `Month No`.
4. **Enter data** to create an empty table named `_Measures`, then add every measure from `measures.dax`.
   - Format the `%` measures as **Percentage, 1 decimal**.
5. Hide the foreign-key columns on `fact_cpi` (`state`, `date`, `division_code`) so report users pick from the dimension tables.

## 3. Pages

**Every page gets a page-level filter `dim_state[is_state] = True`**, except where a step says otherwise.

### Page 1: Overview
| Visual | Fields |
|---|---|
| Text box or card | `Overview Title` |
| Card | `National YoY Latest %` |
| Card | `Highest Inflation State` |
| Card | `Price Rise Since 2020 %`, with a visual-level filter `dim_state[state] = Malaysia` (remove the page filter on this visual) |
| Slicer (dropdown, single select) | `dim_division[division]`, default **Overall** |
| Slicer (between) | `Date[Date]` |
| Clustered bar | Y: `dim_state[state]`, X: `YoY Latest %`, sorted descending. Add a **constant line** at the national rate. |
| Line chart | X: `Date[Date]`, Y: `YoY Inflation %`, Legend: `dim_state[state]`. Use a visual filter to show Malaysia plus up to 3 states (no `is_state` filter on this visual). |

### Page 2: State comparison
| Visual | Fields |
|---|---|
| Matrix (heatmap) | Rows: `dim_state[state]`, Columns: `Date[Year]`, Values: `YoY Inflation %`. Apply **conditional formatting > background color** with a single-hue gradient (light = low, dark = high). |
| Bar | `dim_state[state]` × `Price Rise Since 2020 %` |
| Table | state, `YoY Latest %`, `Gap vs National (pp)`, `State Rank` |
| Map (optional) | Location: `dim_state[map_location]`, bubble size: `YoY Latest %` |

### Page 3: Category drill-through
1. Add `dim_state[state]` to the **Drill-through** well.
2. Bar chart: `dim_division[division]` × `YoY Latest %`. Add a visual filter that excludes Overall.
3. Line chart: `Date[Date]` × `YoY Inflation %`, Legend: `dim_division[division]`. Show the top 4 categories.
4. Back on Page 1, right-click a state bar and choose **Drill through** to this page.

## 4. Polish (this is what makes it look professional)
- Use one accent color for single-series visuals. Use grey for "national" reference lines.
- Give every visual a title that states the insight, e.g. "Negeri Sembilan and Labuan lead at 2.4%". A label like "YoY by state" says much less.
- Add alt text to each visual (Format > General > Alt text).
- Add a footer: *Source: OpenDOSM (DOSM), CPI by state, 2010–2026.*
- Verify the numbers: `YoY Inflation % (calc)` should match `YoY Inflation %` within ±0.2 pp.

## 5. Publish
1. Save as `malaysia_inflation.pbix`.
2. Publish to the Power BI Service. Use **Publish to web** to get a public link (it needs a free work or school account).
3. Take screenshots of each page and save them to `images/`. The README already links to them.
