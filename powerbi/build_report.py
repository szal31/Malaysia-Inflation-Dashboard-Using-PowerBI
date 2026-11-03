"""Generate the report pages of Malaysia-inflation.pbip (PBIR format) from code.

Rewrites Malaysia-inflation.Report/definition/pages/ with three pages:
Overview, State comparison and a Category drill-through, and installs theme.json as the report theme.
The semantic model is left untouched.
Close Power BI Desktop before running, then reopen the .pbip.

Usage:  python build_report.py
"""
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
PAGES = ROOT / "Malaysia-inflation.Report" / "definition" / "pages"
MODEL = ROOT / "Malaysia-inflation.SemanticModel" / "definition" / "tables"
SCHEMA = "https://developer.microsoft.com/json-schemas/fabric/item/report/definition"
M = "_Measure"
ACCENT, SLATE = "#0369A1", "#64748B"  # same accent as theme.json dataColors[0]
AI_APP = "https://malaysia-economic-ai-assistant.streamlit.app/"  # companion chatbot (project 06)
REPORT = ROOT / "Malaysia-inflation.Report"
THEME_NAME = "MalaysiaInflation.json"
DIVISIONS = ["Food & Non-Alcoholic Beverages", "Alcoholic Beverages & Tobacco", "Clothing & Footwear",
             "Housing, Water, Electricity & Gas", "Furnishings & Household Maintenance", "Health", "Transport",
             "Information & Communication", "Recreation, Sport & Culture", "Education",
             "Restaurants & Accommodation", "Insurance & Financial Services", "Personal Care & Misc."]
used_fields = set()


# ---------- query building blocks ----------
def col(entity, prop):
    used_fields.add((entity, prop))
    return {"Column": {"Expression": {"SourceRef": {"Entity": entity}}, "Property": prop}}


def meas(prop):
    used_fields.add((M, prop))
    return {"Measure": {"Expression": {"SourceRef": {"Entity": M}}, "Property": prop}}


def minimum(entity, prop):
    return {"Aggregation": {"Expression": col(entity, prop), "Function": 3}}


def ref(field):
    if "Aggregation" in field:
        inner = field["Aggregation"]["Expression"]["Column"]
        return f"Min({inner['Expression']['SourceRef']['Entity']}.{inner['Property']})", f"First {inner['Property']}"
    kind = "Column" if "Column" in field else "Measure"
    entity, prop = field[kind]["Expression"]["SourceRef"]["Entity"], field[kind]["Property"]
    return f"{entity}.{prop}", prop


def proj(field, name=None):
    query_ref, native = ref(field)
    p = {"field": field, "queryRef": query_ref, "nativeQueryRef": native}
    if name:
        p["displayName"] = name
    return p


def lit(value):
    return {"expr": {"Literal": {"Value": value}}}


def text(s):
    return lit("'" + s.replace("'", "''") + "'")


def where_in(entity, prop, values, alias="t"):
    """Filter body: entity[prop] IN values. Strings are quoted, booleans/ints passed through as literals."""
    def literal(v):
        if isinstance(v, bool):
            return "true" if v else "false"
        if isinstance(v, int):
            return f"{v}L"
        return "'" + v.replace("'", "''") + "'"
    return {"Version": 2, "From": [{"Name": alias, "Entity": entity, "Type": 0}],
            "Where": [{"Condition": {"In": {
                "Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": alias}}, "Property": prop}}],
                "Values": [[{"Literal": {"Value": literal(v)}}] for v in values]}}}]}


def where_gte(entity, prop, value, alias="t"):
    return {"Version": 2, "From": [{"Name": alias, "Entity": entity, "Type": 0}],
            "Where": [{"Condition": {"Comparison": {
                "ComparisonKind": 2,
                "Left": {"Column": {"Expression": {"SourceRef": {"Source": alias}}, "Property": prop}},
                "Right": {"Literal": {"Value": f"{value}L"}}}}}]}


def vfilter(name, entity, prop, values=None, gte=None):
    body = where_gte(entity, prop, gte) if gte is not None else where_in(entity, prop, values)
    return {"name": name, "field": col(entity, prop), "type": "Advanced" if gte is not None else "Categorical",
            "filter": body, "howCreated": "User"}


# ---------- visuals ----------
def visual(name, vtype, pos, roles=None, filters=(), objects=None, title=None, sort=None):
    x, y, w, h = pos
    v = {"visualType": vtype}
    if roles:
        v["query"] = {"queryState": {r: {"projections": [proj(*f) if isinstance(f, tuple) else proj(f) for f in fs]}
                                     for r, fs in roles.items()}}
        if sort:
            field, direction = sort
            v["query"]["sortDefinition"] = {"sort": [{"field": field, "direction": direction}], "isDefaultSort": False}
    if objects:
        v["objects"] = objects
    vco = {"title": [{"properties": {"show": lit("true"), "text": text(title)}}]} if title else \
          {"title": [{"properties": {"show": lit("false")}}]}
    if title:  # screen readers announce the title as the visual's alt text
        vco["general"] = [{"properties": {"altText": text(title)}}]
    v["visualContainerObjects"] = vco
    v["drillFilterOtherVisuals"] = True
    out = {"$schema": f"{SCHEMA}/visualContainer/2.14.0/schema.json", "name": name,
           "position": {"x": x, "y": y, "z": 0, "height": h, "width": w, "tabOrder": 0}, "visual": v}
    if filters:
        out["filterConfig"] = {"filters": list(filters)}
    return out


def card(name, pos, field, label, filters=(), font=28):
    c = visual(name, "card", pos, {"Values": [(field, label)]}, filters,
               {"labels": [{"properties": {"fontSize": lit(f"{font}D"), "color": color(ACCENT)}}],
                "categoryLabels": [{"properties": {"show": lit("true")}}]})
    c["visual"]["visualContainerObjects"]["general"] = [{"properties": {"altText": text(label)}}]
    return c


def plain(v):
    """No card background or border: for header text that should sit on the page, not in a box."""
    v["visual"]["visualContainerObjects"]["background"] = [{"properties": {"show": lit("false")}}]
    v["visual"]["visualContainerObjects"]["border"] = [{"properties": {"show": lit("false")}}]
    return v


def title_card(name, pos, field):
    return plain(visual(name, "card", pos, {"Values": [field]},
                        objects={"labels": [{"properties": {"fontSize": lit("26D"), "bold": lit("true"),
                                                            "color": color("#0F172A")}}],
                                 "categoryLabels": [{"properties": {"show": lit("false")}}]}))


def navigator(name):
    """Page tabs (Overview / State comparison); the hidden drill-through page is left out automatically."""
    return visual(name, "pageNavigator", (24, 120, 520, 44),
                  objects={"pages": [{"properties": {"showHiddenPages": lit("false")}}]})


def header(prefix, title_visual, subtitle):
    return [title_visual,
            textbox(f"{prefix}_subtitle", (24, 72, 1100, 40), subtitle, size="12pt", bold=False),
            navigator(f"{prefix}_nav"), ai_button(f"{prefix}_ai")]


def ai_button(name):
    """Opens the chatbot in a new tab: Power BI can't embed a Streamlit app, so it links out."""
    label = "Ask the AI about Malaysia's economy →"
    b = visual(name, "actionButton", (1476, 112, 420, 58))
    default = {"id": "default"}
    # "show" is set for the whole button; the values belong to its default (not hovered) state
    b["visual"]["objects"] = {
        "text": [{"properties": {"show": lit("true")}},
                 {"properties": {"text": text(label), "fontColor": color("#FFFFFF"), "bold": lit("true"),
                                 "fontSize": lit("11D")}, "selector": default}],
        "fill": [{"properties": {"show": lit("true")}},
                 {"properties": {"fillColor": color(ACCENT), "transparency": lit("0D")}, "selector": default}],
        "icon": [{"properties": {"show": lit("false")}}]}
    b["visual"]["visualContainerObjects"]["visualLink"] = [
        {"properties": {"show": lit("true"), "type": text("WebUrl"), "webUrl": text(AI_APP)}}]
    b["visual"]["visualContainerObjects"]["general"] = [{"properties": {"altText": text(label)}}]
    return b


def textbox(name, pos, words, size="24pt", bold=True):
    v = visual(name, "textbox", pos)
    style = {"fontSize": size, "fontWeight": "bold"} if bold else {"fontSize": size, "color": SLATE}
    v["visual"]["objects"] = {"general": [{"properties": {"paragraphs": [
        {"textRuns": [{"value": words, "textStyle": style}]}]}}]}
    return v


def footer(page):
    return textbox(f"{page}_footer", (24, 1040, 1872, 36),
                   "Source: OpenDOSM (Department of Statistics Malaysia), consumer price index by state and "
                   "division, Jan 2010 to Sep 2026.", size="10pt", bold=False)


def division_slicer(name, pos):
    return visual(name, "slicer", pos, {"Values": [col("dim_division", "division")]}, objects={
        "data": [{"properties": {"mode": text("Dropdown")}}],
        "selection": [{"properties": {"singleSelect": lit("true")}}],
        "general": [{"properties": {"filter": {"filter": where_in("dim_division", "division", ["Overall"], "d")}}}],
        "header": [{"properties": {"text": text("Spending category")}}]})


def date_slicer(name, pos):
    return visual(name, "slicer", pos, {"Values": [col("Date", "Date")]}, objects={
        "data": [{"properties": {"mode": text("Between")}}],
        "header": [{"properties": {"text": text("Period")}}]})


def color(hex_code):
    return {"solid": {"color": text(hex_code)}}


def bars(reference=None):
    """One accent colour, data labels, and optionally a dashed constant line at a measure's value."""
    objects = {"labels": [{"properties": {"show": lit("true")}}],
               "dataPoint": [{"properties": {"fill": color(ACCENT)}}],
               "valueAxis": [{"properties": {"show": lit("false")}}]}  # values are labelled on the bars
    if reference:
        measure, label = reference
        objects["y1AxisReferenceLine"] = [{"properties": {
            "show": lit("true"), "displayName": text(label), "value": {"expr": measure},
            "lineColor": color(SLATE), "style": text("dashed"), "dataLabelShow": lit("true")},
            "selector": {"id": "1"}}]
    return objects


def grey_series(entity, prop, value):
    """Colour one line of a line chart grey, e.g. the national benchmark."""
    return {"dataPoint": [{"properties": {"fill": color(SLATE)}, "selector": {"data": [{"scopeId": {"Comparison": {
        "ComparisonKind": 0, "Left": col(entity, prop), "Right": {"Literal": {"Value": f"'{value}'"}}}}}]}}]}


STATES_ONLY = lambda n: vfilter(n, "dim_state", "is_state", [True])
OVERALL = lambda n: vfilter(n, "dim_division", "division", ["Overall"])


# ---------- pages ----------
def overview():
    yoy_latest = meas("YoY Latest %")
    return {"name": "overview", "displayName": "Overview"}, [
        *header("ov", title_card("ov_title", (24, 12, 1100, 60), meas("Overview Title")),
                "Year-on-year consumer price inflation across Malaysia's 16 states and territories"),
        division_slicer("ov_division", (1170, 16, 340, 92)),
        date_slicer("ov_period", (1530, 16, 366, 92)),
        card("ov_national", (24, 176, 600, 128), meas("National YoY Latest %"), "National inflation (YoY)"),
        card("ov_top", (660, 176, 600, 128), meas("Highest Inflation State"), "Highest inflation state", font=22),
        card("ov_since2020", (1296, 176, 600, 128), meas("Price Rise Since 2020 %"), "Prices since Jan 2020 (Malaysia)",
             [vfilter("f_malaysia", "dim_state", "state", ["Malaysia"])]),
        visual("ov_states", "barChart", (24, 320, 880, 704),
               {"Category": [col("dim_state", "state")], "Y": [(yoy_latest, "YoY inflation")]},
               [STATES_ONLY("f_states")], bars((meas("National YoY Latest %"), "National")),
               "Inflation by state, latest month (right-click a bar to drill through)", (yoy_latest, "Descending")),
        visual("ov_trend", "lineChart", (928, 320, 968, 704),
               {"Category": [col("Date", "Date")], "Y": [(meas("YoY Inflation %"), "YoY inflation")],
                "Series": [col("dim_state", "state")]},
               [vfilter("f_trend_states", "dim_state", "state",
                        ["Malaysia", "Negeri Sembilan", "W.P. Kuala Lumpur", "Sarawak"])],
               grey_series("dim_state", "state", "Malaysia"),
               title="Inflation over time: national (grey) vs highest, capital and lowest state"),
        footer("ov"),
    ]


def states():
    return {"name": "states", "displayName": "State comparison"}, [
        *header("st", plain(textbox("st_title", (24, 12, 1100, 60), "State comparison", size="26pt")),
                "How each state's inflation has moved year by year, and where it stands now"),
        division_slicer("st_division", (1530, 16, 366, 92)),
        visual("st_heatmap", "pivotTable", (24, 176, 1100, 848),
               {"Rows": [col("dim_state", "state")], "Columns": [col("Date", "Year")],
                "Values": [(meas("YoY Inflation %"), "YoY inflation")]},
               [STATES_ONLY("f_states"), vfilter("f_years", "Date", "Year", gte=2011)],
               {"subTotals": [{"properties": {"rowSubtotals": lit("false"), "columnSubtotals": lit("false")}}],
                # larger text so the 16-year grid fills the visual instead of leaving empty space
                "columnHeaders": [{"properties": {"fontSize": lit("13D")}}],
                "rowHeaders": [{"properties": {"fontSize": lit("13D")}}],
                "values": [{"properties": {"fontSize": lit("13D")}},
                           {"properties": {"backColor": {"solid": {"color": {"expr": {"FillRule": {
                    "Input": meas("YoY Inflation %"),
                    "FillRule": {"linearGradient2": {
                        "min": {"color": {"Literal": {"Value": "'#F0F9FF'"}}},
                        "max": {"color": {"Literal": {"Value": "'#38BDF8'"}}},
                        "nullColoringStrategy": {"strategy": {"Literal": {"Value": "'asZero'"}}}}}}}}}}},
                    "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}],
                                 "metadata": "_Measure.YoY Inflation %"}}]},
               "Average yearly inflation by state (darker = higher)"),
        visual("st_since2020", "barChart", (1148, 176, 748, 416),
               {"Category": [col("dim_state", "state")], "Y": [(meas("Price Rise Since 2020 %"), "Rise since Jan 2020")]},
               [STATES_ONLY("f_states2")], bars(), "Total price rise since January 2020",
               (meas("Price Rise Since 2020 %"), "Descending")),
        visual("st_table", "tableEx", (1148, 608, 748, 416),
               {"Values": [col("dim_state", "state"), (meas("YoY Latest %"), "YoY (latest)"),
                           (meas("Gap vs National (pp)"), "Gap vs national (pp)"),
                           (meas("State Rank"), "Rank")]},
               [STATES_ONLY("f_states3")], {"total": [{"properties": {"totals": lit("false")}}]},
               "Latest month: gap to the national rate", (meas("State Rank"), "Ascending")),
        footer("st"),
    ]


def drill():
    page = {"name": "drill", "displayName": "Category drill-through", "visibility": "HiddenInViewMode",
            # only the clicked state is passed in, so the category filter from Overview doesn't empty this page
            "pageBinding": {"name": "drill_binding", "type": "Drillthrough", "referenceScope": "Default",
                            "acceptsFilterContext": "None",
                            # the parameter is what binds the clicked state to the drill-through filter below
                            "parameters": [{"name": "drill_state_param", "boundFilter": "f_drill_state",
                                            "fieldExpr": col("dim_state", "state")}]},
            "filterConfig": {"filters": [{"name": "f_drill_state", "field": col("dim_state", "state"),
                                          "type": "Categorical", "howCreated": "Drillthrough"}]}}
    back = visual("dr_back", "actionButton", (24, 24, 60, 60))
    back["visual"]["objects"] = {"icon": [{"properties": {"shapeType": text("back")}, "selector": {"id": "default"}}]}
    back["visual"]["visualContainerObjects"]["visualLink"] = [
        {"properties": {"show": lit("true"), "type": text("Back")}}]
    return page, [
        back,
        plain(textbox("dr_title", (100, 12, 1100, 60), "What drives inflation in this state?", size="26pt")),
        textbox("dr_subtitle", (100, 72, 1100, 40),
                "Year-on-year inflation by spending category. Use the back arrow to return to Overview.",
                size="12pt", bold=False),
        card("dr_state", (24, 176, 600, 128), minimum("dim_state", "state"), "State", font=22),
        card("dr_yoy", (660, 176, 600, 128), meas("YoY Latest %"), "Overall inflation (latest month)",
             [OVERALL("f_overall")]),
        card("dr_month", (1296, 176, 600, 128), meas("Latest Month"), "Latest month", font=22),
        visual("dr_divisions", "barChart", (24, 320, 880, 704),
               {"Category": [col("dim_division", "division")], "Y": [(meas("YoY Latest %"), "YoY inflation")]},
               [vfilter("f_no_overall", "dim_division", "division", DIVISIONS)], bars(),
               "Inflation by spending category, latest month", (meas("YoY Latest %"), "Descending")),
        visual("dr_trend", "lineChart", (928, 320, 968, 704),
               {"Category": [col("Date", "Date")], "Y": [(meas("YoY Inflation %"), "YoY inflation")],
                "Series": [col("dim_division", "division")]},
               [vfilter("f_key_divs", "dim_division", "division",
                        ["Food & Non-Alcoholic Beverages", "Transport", "Housing, Water, Electricity & Gas",
                         "Restaurants & Accommodation"])],
               title="Key categories over time"),
        footer("dr"),
    ]


def model_fields():
    """(table, field) pairs that exist in the semantic model, read from the TMDL files."""
    fields = set()
    for f in MODEL.glob("*.tmdl"):
        table = f.stem
        for m in re.finditer(r"^\t(?:column|measure) ('[^']+'|[^\s=]+)", f.read_text(encoding="utf-8"), re.M):
            fields.add((table, m.group(1).strip("'")))
    return fields


def install_theme():
    """Copy theme.json into the report and register it as the custom theme (safe to run repeatedly)."""
    target = REPORT / "StaticResources" / "RegisteredResources" / THEME_NAME
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / "theme.json", target)
    report_file = REPORT / "definition" / "report.json"
    report = json.loads(report_file.read_text(encoding="utf-8"))
    themes = report["themeCollection"]
    themes["customTheme"] = {"name": THEME_NAME, "type": "RegisteredResources",
                             "reportVersionAtImport": themes["baseTheme"]["reportVersionAtImport"]}
    packages = [p for p in report["resourcePackages"] if p["type"] != "RegisteredResources"]
    packages.append({"name": "RegisteredResources", "type": "RegisteredResources",
                     "items": [{"name": THEME_NAME, "path": THEME_NAME, "type": "CustomTheme"}]})
    report["resourcePackages"] = packages
    report_file.write_text(json.dumps(report, indent=2), encoding="utf-8")


def main():
    built = [overview(), states(), drill()]

    # Self-check: every field a visual uses must exist in the model, and names must be unique per page.
    missing = used_fields - model_fields()
    assert not missing, f"fields not in model: {missing}"
    for page, visuals in built:
        names = [v["name"] for v in visuals]
        assert len(names) == len(set(names)), page["name"]

    backup = ROOT / "pages_backup_original"
    if not backup.exists():  # keep the hand-made pages once, in case the generated ones need comparing
        shutil.copytree(PAGES, backup)
    shutil.rmtree(PAGES)
    PAGES.mkdir()
    for page, visuals in built:
        folder = PAGES / page["name"]
        (folder / "visuals").mkdir(parents=True)
        page_json = {"$schema": f"{SCHEMA}/page/2.1.0/schema.json", **page,
                     "displayOption": "FitToPage", "height": 1080, "width": 1920}
        (folder / "page.json").write_text(json.dumps(page_json, indent=2), encoding="utf-8")
        for v in visuals:
            vdir = folder / "visuals" / v["name"]
            vdir.mkdir()
            (vdir / "visual.json").write_text(json.dumps(v, indent=2), encoding="utf-8")
    (PAGES / "pages.json").write_text(json.dumps({
        "$schema": f"{SCHEMA}/pagesMetadata/1.1.0/schema.json",
        "pageOrder": [p["name"] for p, _ in built], "activePageName": "overview"}, indent=2), encoding="utf-8")
    install_theme()
    print("Wrote", ", ".join(f"{p['displayName']} ({len(v)} visuals)" for p, v in built))


if __name__ == "__main__":
    main()
