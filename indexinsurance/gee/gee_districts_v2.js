/**
 * ============================================================
 *  SACRA — GEE skripti v2: kunlik shamol jadvali
 * ============================================================
 *
 *  v1 dagi xato: kunlik O'RTACHA shamol va vektor o'rtachalash
 *  chang-bo'ron cho'qqilarini yo'qotgan -> DSI deyarli nol.
 *
 *  v2: SOATLIK ERA5-Land ma'lumotidan har kun uchun
 *      WS10_MAX  = max_h sqrt(u_h^2 + v_h^2)    (skalyar, 10 m)
 *      WS10_MEAN = mean_h sqrt(u_h^2 + v_h^2)
 *      TMAX      = kunlik maksimal harorat, C
 *      PREC      = kunlik yog'in, mm
 *
 *  Indeks (DSI) endi bu yerda EMAS, Python konveyerida
 *  hisoblanadi — chegarani GEE'ni qayta ishlatmasdan
 *  o'zgartirish mumkin.
 *
 *  ISHGA TUSHIRISH:
 *    1. Hammasini nusxalab, code.earthengine.google.com ga joylang
 *    2. Run
 *    3. Tasks -> 5 ta vazifa chiqadi -> har birida RUN
 *    4. Drive'dagi SACRA papkasida 5 ta CSV paydo bo'ladi
 *
 *  Har vazifa 30-90 daqiqa olishi mumkin (soatlik ma'lumot katta).
 * ============================================================
 */

// ---------------- PARAMETRLAR ----------------

// Fevral-iyun: chang-bo'ron mavsumi + kalibrlash uchun zaxira oylar
var MONTH_START = 2;
var MONTH_END   = 6;

// Vazifalar o'n yilliklarga bo'lingan — bitta ulkan vazifa
// GEE vaqt chegarasiga urilishi mumkin.
var CHUNKS = [
  [1981, 1989],
  [1990, 1999],
  [2000, 2009],
  [2010, 2019],
  [2020, 2025]
];

var DRIVE_FOLDER = 'SACRA';

// ---------------- TUMANLAR ----------------

var districts = ee.FeatureCollection('FAO/GAUL/2015/level2')
  .filter(ee.Filter.and(
    ee.Filter.eq('ADM0_NAME', 'Uzbekistan'),
    ee.Filter.eq('ADM1_NAME', 'Surkhandarya')
  ));

print('Birliklar soni (15 kutiladi):', districts.size());

// ---------------- MA'LUMOT MANBALARI ----------------

var hourly = ee.ImageCollection('ECMWF/ERA5_LAND/HOURLY')
  .select(['u_component_of_wind_10m', 'v_component_of_wind_10m']);

var dailyAgg = ee.ImageCollection('ECMWF/ERA5_LAND/DAILY_AGGR')
  .select(['temperature_2m_max', 'total_precipitation_sum']);

// Har soat uchun SKALYAR tezlik: avval tezlik, keyin agregatsiya.
// (v1 da teskarisi qilingan edi — bu asosiy xato edi.)
function hourlySpeed(img) {
  var u = img.select('u_component_of_wind_10m');
  var v = img.select('v_component_of_wind_10m');
  return u.pow(2).add(v.pow(2)).sqrt().rename('ws');
}

// ---------------- BITTA KUN ----------------

function oneDay(dateMillis) {
  var d0 = ee.Date(dateMillis);
  var d1 = d0.advance(1, 'day');

  var speeds = hourly.filterDate(d0, d1).map(hourlySpeed);
  var wsMax  = speeds.max().rename('WS10_MAX');
  var wsMean = speeds.mean().rename('WS10_MEAN');

  var agg  = ee.Image(dailyAgg.filterDate(d0, d1).first());
  var tmax = agg.select('temperature_2m_max').subtract(273.15).rename('TMAX');
  var prec = agg.select('total_precipitation_sum').multiply(1000).rename('PREC');

  var stack = wsMax.addBands(wsMean).addBands(tmax).addBands(prec);

  var stats = stack.reduceRegions({
    collection: districts,
    reducer: ee.Reducer.mean(),
    scale: 1000,
    tileScale: 4
  });

  var dateStr = d0.format('YYYY-MM-dd');
  var year = d0.get('year');

  return stats.map(function (f) {
    return ee.Feature(null, {
      date: dateStr,
      year: year,
      district: f.get('ADM2_NAME'),
      WS10_MAX: f.get('WS10_MAX'),
      WS10_MEAN: f.get('WS10_MEAN'),
      TMAX: f.get('TMAX'),
      PREC: f.get('PREC')
    });
  });
}

// ---------------- BITTA YIL ----------------

function oneYear(y) {
  y = ee.Number(y);
  var start = ee.Date.fromYMD(y, MONTH_START, 1);
  var end   = ee.Date.fromYMD(y, MONTH_END, 1).advance(1, 'month');
  var nDays = end.difference(start, 'day');
  var days  = ee.List.sequence(0, nDays.subtract(1)).map(function (k) {
    return start.advance(k, 'day').millis();
  });
  return ee.FeatureCollection(days.map(oneDay)).flatten();
}

// ---------------- TEKSHIRUV: bitta kun ----------------

var test = oneDay(ee.Date('2018-04-15').millis());
print('Sinov: 2018-04-15 (Termiz hududida WS10_MAX 5-12 m/s kutiladi):', test);

// ---------------- EKSPORT ----------------

CHUNKS.forEach(function (c) {
  var y0 = c[0], y1 = c[1];
  var fc = ee.FeatureCollection(
    ee.List.sequence(y0, y1).map(oneYear)
  ).flatten();

  Export.table.toDrive({
    collection: fc,
    description: 'sacra_daily_' + y0 + '_' + y1,
    folder: DRIVE_FOLDER,
    fileNamePrefix: 'sacra_daily_' + y0 + '_' + y1,
    fileFormat: 'CSV',
    selectors: ['date', 'year', 'district',
                'WS10_MAX', 'WS10_MEAN', 'TMAX', 'PREC']
  });
});

print('Tayyor. Tasks yorlig\'ida 5 ta vazifa — har birida RUN bosing.');
