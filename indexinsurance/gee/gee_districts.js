/**
 * ============================================================
 *  SACRA — Surkhandarya district-level climate index extraction
 * ============================================================
 *
 *  Purpose:  compute, for each of the 14 districts of Surkhandarya
 *            and for each year 1981-2025:
 *              DSI   — dust-storm index (wind excess over threshold)
 *              DSD   — dust-storm days (count)
 *              WSMAX — seasonal maximum wind speed at 2 m
 *              T2M   — mean air temperature
 *              PREC  — total precipitation
 *              NDVI  — mean NDVI in the pre-stress window (from 2001)
 *
 *  Output:   two Drive exports —
 *              sacra_district_indices.csv   (the panel used by SACRA)
 *              sacra_districts.geojson      (boundaries for the web map)
 *
 *  How to run:
 *    1. Open https://code.earthengine.google.com
 *    2. Paste this whole file into the editor
 *    3. Press "Run"
 *    4. Open the "Tasks" tab on the right, press "RUN" on both tasks
 *    5. Files appear in your Google Drive folder "SACRA"
 *
 *  Author: Alisher Abdullayev
 * ============================================================
 */

// ------------------------------------------------------------
// 0. PARAMETERS  — adjust these, everything else follows
// ------------------------------------------------------------

var YEAR_START = 1981;
var YEAR_END   = 2025;

// Dust-storm season (Afghan wind season in Surkhandarya).
// Change if your station analysis used a different window.
var DUST_MONTH_START = 3;   // March
var DUST_MONTH_END   = 5;   // May

// Wind speed threshold for saltation / dust emission, m/s at 2 m.
// 6.0 is a common bare-soil threshold; recalibrate against your
// station-based dust-storm record.
var WS_THRESHOLD = 6.0;

// Pre-stress window used for the Cultivation Verification Gate (NDVI).
var NDVI_MONTH_START = 3;
var NDVI_MONTH_END   = 4;

// Roughness length for converting 10 m wind to 2 m (cropland).
var Z0 = 0.03;

var DRIVE_FOLDER = 'SACRA';

// ------------------------------------------------------------
// 1. DISTRICT BOUNDARIES
// ------------------------------------------------------------
// FAO GAUL level 2 = district (tuman). Free, built into GEE.

var gaul2 = ee.FeatureCollection('FAO/GAUL/2015/level2');

// -- STEP 1a: find the exact spelling of the region name --------
// GAUL spellings vary. Run this once, read the console, then set
// REGION_NAME below to whatever it actually prints.
var uzRegions = gaul2
  .filter(ee.Filter.eq('ADM0_NAME', 'Uzbekistan'))
  .aggregate_array('ADM1_NAME')
  .distinct();
print('Uzbekistan regions in GAUL (set REGION_NAME from this list):', uzRegions);

var REGION_NAME = 'Surkhandarya';   // <-- adjust after reading the console

var districts = gaul2.filter(ee.Filter.and(
  ee.Filter.eq('ADM0_NAME', 'Uzbekistan'),
  ee.Filter.eq('ADM1_NAME', REGION_NAME)
));

print('Number of districts found (expect 14):', districts.size());
print('District names:', districts.aggregate_array('ADM2_NAME'));
Map.centerObject(districts, 8);
Map.addLayer(districts, {color: '0A1F44'}, 'Surkhandarya districts');

// ------------------------------------------------------------
// 2. WIND -> 2 m, AND THE DUST-STORM INDEX
// ------------------------------------------------------------
// ERA5-Land daily aggregates give u and v at 10 m.
//   WS10 = sqrt(u^2 + v^2)
//   WS2  = WS10 * ln(2/z0) / ln(10/z0)      (logarithmic wind profile)

var logRatio = Math.log(2 / Z0) / Math.log(10 / Z0);   // ~0.723

var era5 = ee.ImageCollection('ECMWF/ERA5_LAND/DAILY_AGGR');

function windSpeed2m(img) {
  var u = img.select('u_component_of_wind_10m');
  var v = img.select('v_component_of_wind_10m');
  var ws10 = u.pow(2).add(v.pow(2)).sqrt();
  return ws10.multiply(logRatio).rename('ws2m')
             .copyProperties(img, ['system:time_start']);
}

/**
 * Build one feature per district per year.
 */
function yearlyIndices(year) {
  year = ee.Number(year);

  var dustStart = ee.Date.fromYMD(year, DUST_MONTH_START, 1);
  var dustEnd   = ee.Date.fromYMD(year, DUST_MONTH_END, 1).advance(1, 'month');

  var daily = era5.filterDate(dustStart, dustEnd).map(windSpeed2m);

  // DSI = sum over days of max(0, ws2m - threshold)      [m/s * days]
  var excess = daily.map(function (img) {
    return img.subtract(WS_THRESHOLD).max(0).rename('excess');
  });
  var dsi = excess.sum().rename('DSI');

  // DSD = number of days with ws2m > threshold
  var dsd = daily.map(function (img) {
    return img.gt(WS_THRESHOLD).rename('day');
  }).sum().rename('DSD');

  // WSMAX = seasonal maximum daily wind speed
  var wsmax = daily.max().rename('WSMAX');

  // Temperature (K -> C) and precipitation (m -> mm) over the same window
  var t2m = era5.filterDate(dustStart, dustEnd)
                .select('temperature_2m').mean()
                .subtract(273.15).rename('T2M');

  var prec = era5.filterDate(dustStart, dustEnd)
                 .select('total_precipitation_sum').sum()
                 .multiply(1000).rename('PREC');

  var stack = dsi.addBands(dsd).addBands(wsmax).addBands(t2m).addBands(prec);

  // MODIS NDVI for the cultivation-verification window (available from 2000)
  var ndviStart = ee.Date.fromYMD(year, NDVI_MONTH_START, 1);
  var ndviEnd   = ee.Date.fromYMD(year, NDVI_MONTH_END, 1).advance(1, 'month');

  var ndviCol = ee.ImageCollection('MODIS/061/MOD13Q1')
                  .filterDate(ndviStart, ndviEnd)
                  .select('NDVI');

  // If the year predates MODIS, fill with a masked constant so the
  // column still exists in the output table.
  var ndvi = ee.Image(ee.Algorithms.If(
    ndviCol.size().gt(0),
    ndviCol.max().multiply(0.0001).rename('NDVI'),
    ee.Image.constant(-9999).rename('NDVI').float()
  ));

  stack = stack.addBands(ndvi);

  var stats = stack.reduceRegions({
    collection: districts,
    reducer: ee.Reducer.mean(),
    scale: 1000,
    tileScale: 4
  });

  return stats.map(function (f) {
    return ee.Feature(null, {
      year:     year,
      district: f.get('ADM2_NAME'),
      region:   f.get('ADM1_NAME'),
      DSI:      f.get('DSI'),
      DSD:      f.get('DSD'),
      WSMAX:    f.get('WSMAX'),
      T2M:      f.get('T2M'),
      PREC:     f.get('PREC'),
      NDVI:     f.get('NDVI')
    });
  });
}

// Build the panel year by year (avoids the element-count limit).
var years = ee.List.sequence(YEAR_START, YEAR_END);
var panel = ee.FeatureCollection(years.map(yearlyIndices)).flatten();

print('Preview of first 5 rows:', panel.limit(5));

// ------------------------------------------------------------
// 3. QUICK VISUAL CHECK — mean DSI per district
// ------------------------------------------------------------

var meanDSI = districts.map(function (d) {
  var name = d.get('ADM2_NAME');
  var rows = panel.filter(ee.Filter.eq('district', name));
  return d.set('meanDSI', rows.aggregate_mean('DSI'));
});

Map.addLayer(
  meanDSI.reduceToImage(['meanDSI'], ee.Reducer.first()),
  {min: 0, max: 60, palette: ['ffffcc', 'fd8d3c', 'b10026']},
  'Mean dust-storm index'
);

// ------------------------------------------------------------
// 4. EXPORTS
// ------------------------------------------------------------

Export.table.toDrive({
  collection: panel,
  description: 'sacra_district_indices',
  folder: DRIVE_FOLDER,
  fileNamePrefix: 'sacra_district_indices',
  fileFormat: 'CSV',
  selectors: ['year', 'district', 'region',
              'DSI', 'DSD', 'WSMAX', 'T2M', 'PREC', 'NDVI']
});

// Simplified boundaries keep the web map light (~200 kB instead of MBs).
var boundaries = districts.map(function (f) {
  return ee.Feature(
    f.geometry().simplify(500),
    {district: f.get('ADM2_NAME'), region: f.get('ADM1_NAME')}
  );
});

Export.table.toDrive({
  collection: boundaries,
  description: 'sacra_districts_geojson',
  folder: DRIVE_FOLDER,
  fileNamePrefix: 'sacra_districts',
  fileFormat: 'GeoJSON'
});

print('Ready. Open the Tasks tab and run both export tasks.');
