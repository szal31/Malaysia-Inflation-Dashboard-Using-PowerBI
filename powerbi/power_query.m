// Power Query (M) for the three tables.
// 1. Home > Transform data > Manage Parameters > New: name DataFolder, type Text,
//    value = full path to data\clean\ WITH a trailing backslash, e.g. C:\Project\01-malaysia-inflation-powerbi\data\clean\
// 2. For each query below: Home > New Source > Blank Query > Advanced Editor > paste > rename the query.
// Types are set explicitly so division_code stays text ("01", not 1) and the relationship works.

// ---- Query name: fact_cpi ----
let
    Source  = Csv.Document(File.Contents(DataFolder & "fact_cpi.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    // first 12 months of each series have no YoY value; make them null, not errors
    Blanks  = Table.ReplaceValue(Headers, "", null, Replacer.ReplaceValue, {"inflation_yoy", "inflation_mom"}),
    Typed   = Table.TransformColumnTypes(Blanks, {
                {"state", type text}, {"date", type date}, {"division_code", type text},
                {"cpi_index", type number}, {"inflation_yoy", type number}, {"inflation_mom", type number}}, "en-US")
in
    Typed

// ---- Query name: dim_state ----
let
    Source  = Csv.Document(File.Contents(DataFolder & "dim_state.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed   = Table.TransformColumnTypes(Headers, {
                {"state", type text}, {"region", type text}, {"map_location", type text}, {"is_state", type logical}}, "en-US")
in
    Typed

// ---- Query name: dim_division ----
let
    Source  = Csv.Document(File.Contents(DataFolder & "dim_division.csv"), [Delimiter = ",", Encoding = 65001, QuoteStyle = QuoteStyle.Csv]),
    Headers = Table.PromoteHeaders(Source, [PromoteAllScalars = true]),
    Typed   = Table.TransformColumnTypes(Headers, {
                {"division_code", type text}, {"division", type text}, {"sort_order", Int64.Type}}, "en-US")
in
    Typed
