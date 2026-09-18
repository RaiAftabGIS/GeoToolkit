# from geotoolkit.core import SimpleGeoFile
# from geotoolkit.utils import list_files
# files=list_files("geotoolkit/examples")
# print(files)

# geo=SimpleGeoFile()

# geo.load("geotoolkit/examples/sample.geojson")
# print("Total features:", geo.count_features())
# print("Feature types:", geo.features_type())
# print(geo.get_bounding_box())
# print("Filtered features:")
# print(geo.filter_by_property("city", "Lahore"))
//==============================================================
// ASE - LST / PERT / SUHII ANALYSIS
// LAHORE METROPOLITAN REGION
// CLEANED & CONSOLIDATED VERSION
//==============================================================


//==============================================================
// SECTION 1
// USER INPUTS
//==============================================================

var studyArea = table.geometry();

Map.centerObject(studyArea, 10);
Map.setOptions("SATELLITE");

Map.addLayer(
  studyArea,
  {color: 'red'},
  'Study Area'
);


//--------------------------------------------------------------
// Study Years
//--------------------------------------------------------------

var years = ee.List.sequence(2005, 2026);


//--------------------------------------------------------------
// Summer Season
//--------------------------------------------------------------

var startMonth = 5;
var endMonth = 6;


//--------------------------------------------------------------
// ASE Parameters
//--------------------------------------------------------------

var BUFFER_RATIO = 0.5;
var NUMBER_OF_BUFFERS = 20;
var ET = 50;
var PERT = 0.02;
var SUA_SIZE = 6.5;


//--------------------------------------------------------------
// Export Folder
//--------------------------------------------------------------

var exportFolder = 'ASE_Lahore';


//==============================================================
// SECTION 2
// LOAD DATASETS
//==============================================================

var modis = ee.ImageCollection('MODIS/061/MOD11A2');

var evi = ee.ImageCollection('MODIS/061/MOD13Q1');

var worldCover = ee.ImageCollection('ESA/WorldCover/v200');

var dem = ee.Image('USGS/SRTMGL1_003');

var water = ee.Image('JRC/GSW1_4/GlobalSurfaceWater');


//==============================================================
// SECTION 3
// PREPARE DATASETS
//==============================================================

//--------------------------------------------------------------
// DEM
//--------------------------------------------------------------

dem = dem.clip(studyArea);


//--------------------------------------------------------------
// Water Mask
//--------------------------------------------------------------

var occurrence = water.select('occurrence');

var waterMask = occurrence.lt(50);


//--------------------------------------------------------------
// Built-up
//--------------------------------------------------------------

var landcover = worldCover
  .first()
  .select('Map')
  .clip(studyArea);

var builtup = landcover
  .eq(50)
  .focal_max(1)
  .focal_min(1);


//==============================================================
// SECTION 4
// MODIS LST
//==============================================================

function getSummerLST(year) {

  var start = ee.Date.fromYMD(
    year,
    startMonth,
    1
  );

  var end = ee.Date.fromYMD(
    year,
    endMonth,
    30
  );

  return modis
    .filterDate(start, end)
    .filterBounds(studyArea)
    .select('LST_Day_1km')
    .mean()
    .multiply(0.02)
    .subtract(273.15)
    .clip(studyArea);
}


//--------------------------------------------------------------
// LST Visualization
//--------------------------------------------------------------

var LST_VIS = {
  min: 20,
  max: 50,
  palette: [
    '040274',
    '2c7bb6',
    'abd9e9',
    'ffffbf',
    'fdae61',
    'd7191c'
  ]
};


//--------------------------------------------------------------
// Year-wise Summer LST
//--------------------------------------------------------------

var summerLSTCollection = ee.ImageCollection.fromImages(
  years.map(function(year) {

    year = ee.Number(year);

    return getSummerLST(year)
      .rename('LST')
      .set('Year', year);

  })
);


//==============================================================
// SECTION 5
// BASIC QUALITY CHECK
//==============================================================

print('Study Area', studyArea);
print('Year-wise Summer LST Collection', summerLSTCollection);
print('Built-up Layer', builtup);
print('DEM', dem);
print('Water Mask', waterMask);


//==============================================================
// SECTION 6
// FINAL CENTRAL URBAN AREA (CUA)
//==============================================================

//--------------------------------------------------------------
// GHSL Built Surface
//--------------------------------------------------------------

var ghsl = ee.ImageCollection(
  'JRC/GHSL/P2023A/GHS_BUILT_S'
)
.first()
.select('built_surface')
.clip(studyArea);


//--------------------------------------------------------------
// GHSL Statistics
//--------------------------------------------------------------

print(
  'GHSL Statistics',
  ghsl.reduceRegion({
    reducer: ee.Reducer.minMax(),
    geometry: studyArea,
    scale: 100,
    maxPixels: 1e13
  })
);


//--------------------------------------------------------------
// Initial Urban Mask
//--------------------------------------------------------------

var urbanMask = ghsl
  .gt(3000)
  .selfMask();


//--------------------------------------------------------------
// Morphological Cleaning
//--------------------------------------------------------------

urbanMask = urbanMask
  .focalMax({
    radius: 150,
    units: 'meters'
  })
  .focalMin({
    radius: 150,
    units: 'meters'
  });


//--------------------------------------------------------------
// Fill Small Gaps
//--------------------------------------------------------------

urbanMask = urbanMask.focalMode({
  radius: 100,
  units: 'meters'
});


//--------------------------------------------------------------
// Remove Small Patches
//--------------------------------------------------------------

var connected = urbanMask.connectedPixelCount({
  maxSize: 1000,
  eightConnected: true
});

urbanMask = urbanMask.updateMask(
  connected.gte(100)
);


//--------------------------------------------------------------
// Display Clean Urban Mask
//--------------------------------------------------------------

Map.addLayer(
  urbanMask,
  {palette: ['red']},
  'Clean Urban Mask'
);


//--------------------------------------------------------------
// Convert to Polygon
//--------------------------------------------------------------

var urbanVectors = urbanMask.reduceToVectors({
  geometry: studyArea,
  scale: 30,
  geometryType: 'polygon',
  eightConnected: true,
  reducer: ee.Reducer.countEvery(),
  maxPixels: 1e13,
  tileScale: 4
});


//--------------------------------------------------------------
// Calculate Polygon Area
//--------------------------------------------------------------

urbanVectors = urbanVectors.map(function(feature) {

  return feature.set({
    Area: feature.geometry().area({
      maxError: 10
    })
  });

});


//--------------------------------------------------------------
// Largest Polygon = CUA
//--------------------------------------------------------------

var centralUrban = ee.Feature(
  urbanVectors
    .sort('Area', false)
    .first()
);


//--------------------------------------------------------------
// Simplify CUA Geometry
//--------------------------------------------------------------

var CUA_Geometry = centralUrban
  .geometry()
  .simplify({
    maxError: 30
  });


//--------------------------------------------------------------
// Display CUA
//--------------------------------------------------------------

Map.addLayer(
  CUA_Geometry,
  {color: 'blue'},
  'Final CUA'
);


//--------------------------------------------------------------
// CUA Area
//--------------------------------------------------------------

var CUA_Area_km2 = CUA_Geometry
  .area({
    maxError: 10
  })
  .divide(1e6);

print(
  'Final CUA Area (km²)',
  CUA_Area_km2
);


//==============================================================
// SECTION 7
// CENTRAL URBAN LST
//==============================================================

function calculateUrbanLST(year) {

  var lst = getSummerLST(year);

  var stats = lst.reduceRegion({
    reducer: ee.Reducer.mean(),
    geometry: CUA_Geometry,
    scale: 1000,
    maxPixels: 1e13,
    bestEffort: true
  });

  return ee.Feature(null, {
    Year: year,
    Urban_LST: stats.get('LST_Day_1km')
  });

}


var urbanLST = ee.FeatureCollection(
  years.map(calculateUrbanLST)
);

print('Urban LST', urbanLST);


//--------------------------------------------------------------
// Export Urban LST
//--------------------------------------------------------------

Export.table.toDrive({
  collection: urbanLST,
  description: 'Urban_LST_2005_2026',
  folder: exportFolder,
  fileFormat: 'CSV'
});


//==============================================================
// SECTION 8
// AUTOMATIC BUFFER GENERATION
//==============================================================

var BUFFER_STEP = 1000;

var TOTAL_BUFFERS = 20;

var bufferCollection = ee.FeatureCollection([]);

var previousBuffer = CUA_Geometry;


for (var i = 1; i <= TOTAL_BUFFERS; i++) {

  var currentBuffer = CUA_Geometry.buffer({
    distance: i * BUFFER_STEP,
    maxError: 10
  });

  var ring = currentBuffer
    .difference({
      right: previousBuffer,
      maxError: 10
    })
    .intersection({
      right: studyArea,
      maxError: 10
    });

  ring = ee.Feature(ring).set({
    Buffer_ID: i,
    Distance_m: i * BUFFER_STEP
  });

  bufferCollection = bufferCollection.merge(
    ee.FeatureCollection([ring])
  );

  previousBuffer = currentBuffer;
}


Map.addLayer(
  bufferCollection,
  {color: 'yellow'},
  '20 Buffer Rings'
);

print(
  'Buffer Collection',
  bufferCollection
);

//==============================================================
// SECTION 9
// YEAR-WISE BUFFER LST
//==============================================================

function calculateBufferLST(year) {

  var lst = getSummerLST(year);

  return bufferCollection.map(function(feature) {

    var stats = lst.reduceRegion({

      reducer: ee.Reducer.mean(),

      geometry: feature.geometry(),

      scale: 1000,

      bestEffort: true,

      maxPixels: 1e13

    });

    return feature.set({

      Year: year,

      Mean_LST:
        stats.get('LST_Day_1km')

    });

  });

}


//--------------------------------------------------------------
// Year-wise Buffer LST
//--------------------------------------------------------------

var bufferLST = ee.FeatureCollection(
  years.map(function(year) {

    return calculateBufferLST(
      ee.Number(year)
    );

  })
).flatten();


print(
  'Year-wise Buffer LST',
  bufferLST
);


//--------------------------------------------------------------
// Year-wise Buffer Profile
//--------------------------------------------------------------

var bufferProfile = bufferLST
  .map(function(feature) {

    return ee.Feature(null, {

      Year:
        feature.get('Year'),

      Buffer_ID:
        feature.get('Buffer_ID'),

      Distance_m:
        feature.get('Distance_m'),

      Mean_LST:
        feature.get('Mean_LST')

    });

  })
  .sort('Distance_m');

print(
  'Year-wise Buffer Profile',
  bufferProfile
);
//==============================================================
// SECTION 10
// YEAR-WISE BUFFER LST CHART
//==============================================================

var lstChart = ui.Chart.feature.groups({

  features: bufferProfile,

  xProperty: 'Distance_m',

  yProperty: 'Mean_LST',

  seriesProperty: 'Year'

})
.setChartType('LineChart')
.setOptions({

  title: 'ASE Buffer LST Profile (2005–2026)',

  hAxis: {
    title: 'Distance from CUA (m)'
  },

  vAxis: {
    title: 'Mean LST (°C)'
  },

  lineWidth: 2,

  pointSize: 3,

  legend: {
    position: 'right'
  }

});

print(lstChart);
//==============================================================
// SECTION 11
// YEAR-WISE SUMMER EVI
//==============================================================

function getSummerEVI(year) {

  var start = ee.Date.fromYMD(
    year,
    startMonth,
    1
  );

  var end = ee.Date.fromYMD(
    year,
    endMonth,
    30
  );

  return evi
    .filterDate(start, end)
    .filterBounds(studyArea)
    .select('EVI')
    .mean()
    .multiply(0.0001)
    .clip(studyArea);

}


//--------------------------------------------------------------
// Year-wise Summer EVI
//--------------------------------------------------------------

var summerEVICollection = ee.ImageCollection.fromImages(

  years.map(function(year) {

    year = ee.Number(year);

    return getSummerEVI(year)
      .rename('EVI')
      .set('Year', year);

  })

);


//--------------------------------------------------------------
// Buffer-wise Yearly EVI
//--------------------------------------------------------------

function calculateBufferEVI(year) {

  var eviYear = getSummerEVI(year);

  return bufferCollection.map(function(feature) {

    var stat = eviYear.reduceRegion({

      reducer: ee.Reducer.mean(),

      geometry: feature.geometry(),

      scale: 250,

      maxPixels: 1e13,

      bestEffort: true

    });

    return feature.set({

      Year: year,

      Mean_EVI: stat.get('EVI')

    });

  });

}


//--------------------------------------------------------------
// All Years Buffer EVI
//--------------------------------------------------------------

var bufferEVI = ee.FeatureCollection(

  years.map(function(year) {

    return calculateBufferEVI(
      ee.Number(year)
    );

  })

).flatten();


print(
  'Year-wise Buffer EVI',
  bufferEVI
);

//==============================================================
// SECTION 12
// ELEVATION VALIDATION
//==============================================================

var bufferElevation = bufferCollection.map(function(feature) {

  var stat = dem.reduceRegion({

    reducer: ee.Reducer.mean(),

    geometry: feature.geometry(),

    scale: 30,

    maxPixels: 1e13

  });

  return feature.set({
    Mean_Elevation: stat.get('elevation')
  });

});

print(
  'Buffer Elevation',
  bufferElevation
);


Map.addLayer(
  dem,
  {
    min: 150,
    max: 300,
    palette: [
      'blue',
      'cyan',
      'green',
      'yellow',
      'orange',
      'red'
    ]
  },
  'DEM'
);


print(
  'DEM Statistics',
  dem.reduceRegion({
    reducer: ee.Reducer.minMax(),
    geometry: studyArea,
    scale: 30,
    maxPixels: 1e13
  })
);


//==============================================================
// SECTION 13
// ELEVATION THRESHOLD (ET)
//==============================================================

var cuaElevation = dem.reduceRegion({

  reducer: ee.Reducer.mean(),

  geometry: CUA_Geometry,

  scale: 30,

  maxPixels: 1e13

});

var meanCUAElevation = ee.Number(
  cuaElevation.get('elevation')
);

print(
  'CUA Mean Elevation',
  meanCUAElevation
);


var elevationCheck = bufferElevation.map(
  function(feature) {

    var elev = ee.Number(
      feature.get('Mean_Elevation')
    );

    var diff = elev
      .subtract(meanCUAElevation)
      .abs();

    return feature.set({

      Elevation_Difference: diff,

      ET_Pass: diff.lte(ET)

    });

  }
);

print(
  'Elevation Threshold Check',
  elevationCheck
);


//==============================================================
// SECTION 14
// YEAR-WISE PERTURBATION THRESHOLD
//==============================================================

function calculatePERT(year) {

  var cuaEVI = getSummerEVI(year);

  //------------------------------------------------------------
  // CUA Mean EVI
  //------------------------------------------------------------

  var cuaEVIStat = cuaEVI.reduceRegion({

    reducer: ee.Reducer.mean(),

    geometry: CUA_Geometry,

    scale: 250,

    maxPixels: 1e13,

    bestEffort: true

  });

  var meanCUAEVI = ee.Number(
    cuaEVIStat.get('EVI')
  );


  //------------------------------------------------------------
  // Buffer-wise PERT Check
  //------------------------------------------------------------

  return elevationCheck.map(
    function(feature) {

      var stat = cuaEVI.reduceRegion({

        reducer: ee.Reducer.mean(),

        geometry: feature.geometry(),

        scale: 250,

        maxPixels: 1e13,

        bestEffort: true

      });

      var eviValue = ee.Number(
        stat.get('EVI')
      );

      var diff = eviValue
        .subtract(meanCUAEVI)
        .abs();

      return feature.set({

        Year: year,

        Mean_EVI: eviValue,

        CUA_Mean_EVI: meanCUAEVI,

        PERT_Difference: diff,

        PERT_Pass: diff.lte(PERT)

      });

    }
  );

}


//--------------------------------------------------------------
// Year-wise PERT
//--------------------------------------------------------------

var perturbationCheck = ee.FeatureCollection(

  years.map(function(year) {

    return calculatePERT(
      ee.Number(year)
    );

  })

).flatten();


print(
  'Year-wise PERT Check',
  perturbationCheck
);


//==============================================================
// SECTION 15
// YEAR-WISE VALID BUFFER LST PROFILE
//==============================================================

//--------------------------------------------------------------
// ET-valid buffer IDs
//--------------------------------------------------------------

var validBufferIDs = elevationCheck
  .filter(ee.Filter.eq('ET_Pass', 1))
  .aggregate_array('Buffer_ID');

print(
  'Valid Buffer IDs',
  validBufferIDs
);


//--------------------------------------------------------------
// Year-wise valid LST buffers
//--------------------------------------------------------------

var validLSTBuffers = bufferLST
  .filter(
    ee.Filter.inList(
      'Buffer_ID',
      validBufferIDs
    )
  );

print(
  'Year-wise Valid LST Buffers',
  validLSTBuffers
);

print(
  'Number of Valid LST Buffers',
  validLSTBuffers.size()
);

//==============================================================
// SECTION 16
// YEAR-WISE CUA + BUFFER LST SEQUENCE
//==============================================================

function calculateLSTSequence(year) {

  //------------------------------------------------------------
  // CUA LST
  //------------------------------------------------------------

  var cuaLSTStat = getSummerLST(year).reduceRegion({

    reducer: ee.Reducer.mean(),

    geometry: CUA_Geometry,

    scale: 1000,

    maxPixels: 1e13,

    tileScale: 4

  });

  var T0 = ee.Number(
    cuaLSTStat.get('LST_Day_1km')
  );


  //------------------------------------------------------------
  // Year-specific valid buffer LST
  //------------------------------------------------------------

  var yearBuffers = validLSTBuffers
    .filter(
      ee.Filter.eq('Year', year)
    )
    .sort('Buffer_ID');


  var bufferLSTValues =
    yearBuffers.aggregate_array('Mean_LST');


  //------------------------------------------------------------
  // Complete LST sequence
  //------------------------------------------------------------

  var T = ee.List([T0]).cat(
    ee.List(bufferLSTValues)
  );


  //------------------------------------------------------------
  // Tmax / Tmin / PERT
  //------------------------------------------------------------

  var Tmax = ee.Number(
    T.reduce(ee.Reducer.max())
  );

  var Tmin = ee.Number(
    T.reduce(ee.Reducer.min())
  );

  var deltaTThreshold = Tmax
    .subtract(Tmin)
    .multiply(PERT);


  return ee.Feature(null, {

    Year: year,

    T0: T0,

    Tmax: Tmax,

    Tmin: Tmin,

    PERT_Threshold: deltaTThreshold,

    LST_Count: T.size()

  });

}


//--------------------------------------------------------------
// Year-wise LST / PERT summary
//--------------------------------------------------------------

var yearlyLSTSummary = ee.FeatureCollection(

  years.map(function(year) {

    return calculateLSTSequence(
      ee.Number(year)
    );

  })

);


print(
  'Year-wise LST / PERT Summary',
  yearlyLSTSummary
);
//==============================================================
// SECTION 17
// YEAR-WISE ASE LST PROFILE
//==============================================================

function createLSTProfile(year) {

  //------------------------------------------------------------
  // Year-specific buffers
  //------------------------------------------------------------

  var yearBuffers = validLSTBuffers
    .filter(
      ee.Filter.eq('Year', year)
    )
    .sort('Buffer_ID');


  //------------------------------------------------------------
  // CUA LST
  //------------------------------------------------------------

  var cuaLSTStat = getSummerLST(year).reduceRegion({

    reducer: ee.Reducer.mean(),

    geometry: CUA_Geometry,

    scale: 1000,

    maxPixels: 1e13,

    tileScale: 4

  });

  var T0 = ee.Number(
    cuaLSTStat.get('LST_Day_1km')
  );


  //------------------------------------------------------------
  // Buffer LST values
  //------------------------------------------------------------

  var bufferLSTValues =
    yearBuffers.aggregate_array('Mean_LST');


  //------------------------------------------------------------
  // Complete LST sequence
  //------------------------------------------------------------

  var T = ee.List([T0]).cat(
    ee.List(bufferLSTValues)
  );


  //------------------------------------------------------------
  // Distances
  //------------------------------------------------------------

  var profileDistances = ee.List([0]).cat(
    yearBuffers.aggregate_array('Distance_m')
  );


  //------------------------------------------------------------
  // Buffer IDs
  //------------------------------------------------------------

  var profileIDs = ee.List(['CUA']).cat(
    yearBuffers.aggregate_array('Buffer_ID')
  );


  //------------------------------------------------------------
  // Create profile
  //------------------------------------------------------------

  return ee.FeatureCollection(

    ee.List.sequence(
      0,
      T.size().subtract(1)
    )
    .map(function(i) {

      i = ee.Number(i);

      return ee.Feature(null, {

        Year: year,

        Position: i,

        Buffer_ID: profileIDs.get(i),

        Distance_m: profileDistances.get(i),

        LST: T.get(i)

      });

    })

  );

}


//--------------------------------------------------------------
// All-year ASE LST profiles
//--------------------------------------------------------------

var lstProfile = ee.FeatureCollection(

  years.map(function(year) {

    return createLSTProfile(
      ee.Number(year)
    );

  })

).flatten();


print(
  'Year-wise ASE LST Profile',
  lstProfile
);

print(
  'Profile Observation Count',
  lstProfile.size()
);
//==============================================================
// SECTION 18
// YEAR-WISE CUBIC LST PROFILE FIT
//==============================================================

function fitCubicLST(year) {

  //------------------------------------------------------------
  // Select one year
  //------------------------------------------------------------

  var yearProfile = lstProfile
    .filter(
      ee.Filter.eq('Year', year)
    );


  //------------------------------------------------------------
  // Prepare regression variables
  //------------------------------------------------------------

  var profileForFit = yearProfile.map(
    function(feature) {

      var x = ee.Number(
        feature.get('Distance_m')
      ).divide(1000);

      return feature.set({

        X: x,

        X2: x.multiply(x),

        X3: x.multiply(x).multiply(x),

        constant: 1

      });

    }
  );


  //------------------------------------------------------------
  // Cubic Regression
  //------------------------------------------------------------

  var regression = profileForFit.reduceColumns({

    reducer: ee.Reducer.linearRegression(4, 1),

    selectors: [
      'constant',
      'X',
      'X2',
      'X3',
      'LST'
    ]

  });


  var coefficients = ee.Array(
    regression.get('coefficients')
  );


  //------------------------------------------------------------
  // Regression coefficients
  //------------------------------------------------------------

  var c0 = ee.Number(
    coefficients.get([0, 0])
  );

  var c1 = ee.Number(
    coefficients.get([1, 0])
  );

  var c2 = ee.Number(
    coefficients.get([2, 0])
  );

  var c3 = ee.Number(
    coefficients.get([3, 0])
  );


  //------------------------------------------------------------
  // Calculate fitted LST
  //------------------------------------------------------------

  var fittedProfile = profileForFit.map(
    function(feature) {

      var x = ee.Number(
        feature.get('X')
      );

      var fittedLST = c0
        .add(c1.multiply(x))
        .add(c2.multiply(x.pow(2)))
        .add(c3.multiply(x.pow(3)));

      return feature.set({

        Fitted_LST: fittedLST

      });

    }
  );


  return fittedProfile;
}


//--------------------------------------------------------------
// Year-wise fitted profiles
//--------------------------------------------------------------

var fittedProfile = ee.FeatureCollection(

  years.map(function(year) {

    return fitCubicLST(
      ee.Number(year)
    );

  })

).flatten();


print(
  'Year-wise Fitted LST Profile',
  fittedProfile
);

print(
  'Fitted Profile Count',
  fittedProfile.size()
);
//==============================================================
// SECTION 19
// YEAR-WISE FITTED LST GRADIENT
//==============================================================

function calculateFittedDeltaT(year) {

  var yearProfile = fittedProfile
    .filter(
      ee.Filter.eq('Year', year)
    )
    .sort('Distance_m');


  var fittedLST = yearProfile
    .aggregate_array('Fitted_LST');


  var fittedDeltaT = ee.List.sequence(
    1,
    fittedLST.size().subtract(1)
  )
  .map(function(i) {

    i = ee.Number(i);

    var current = ee.Number(
      fittedLST.get(i)
    );

    var previous = ee.Number(
      fittedLST.get(i.subtract(1))
    );

    return current.subtract(previous);

  });


  var fittedAbsDeltaT = fittedDeltaT.map(
    function(value) {

      return ee.Number(value).abs();

    }
  );


  return ee.FeatureCollection(

    ee.List.sequence(
      0,
      fittedDeltaT.size().subtract(1)
    )
    .map(function(i) {

      i = ee.Number(i);

      return ee.Feature(null, {

        Year: year,

        Position: i.add(1),

        Fitted_Delta_T:
          fittedDeltaT.get(i),

        Absolute_Delta_T:
          fittedAbsDeltaT.get(i)

      });

    })

  );

}


//--------------------------------------------------------------
// All-year fitted gradients
//--------------------------------------------------------------

var fittedGradientProfile =
  ee.FeatureCollection(

    years.map(function(year) {

      return calculateFittedDeltaT(
        ee.Number(year)
      );

    })

  ).flatten();


print(
  'Year-wise Fitted Gradient Profile',
  fittedGradientProfile
);

print(
  'Fitted Gradient Count',
  fittedGradientProfile.size()
);
//==============================================================
// SECTION 20
// YEAR-WISE FINAL PERT THRESHOLD
//==============================================================

var PERT_THRESHOLD = yearlyLSTSummary.map(
  function(feature) {

    return ee.Feature(null, {

      Year: feature.get('Year'),

      PERT_Threshold:
        feature.get('PERT_Threshold')

    });

  }
);


print(
  'Year-wise FINAL PERT THRESHOLD',
  PERT_THRESHOLD
);


//==============================================================
// SECTION 21
// YEAR-WISE PERT CROSSING DIAGNOSTIC
//==============================================================

function calculatePERTDiagnostic(year) {

  //------------------------------------------------------------
  // Year-specific fitted gradient
  //------------------------------------------------------------

  var yearGradient =
    fittedGradientProfile
      .filter(
        ee.Filter.eq('Year', year)
      )
      .sort('Position');


  var deltaTList =
    yearGradient.aggregate_array(
      'Fitted_Delta_T'
    );


  var absDeltaTList =
    yearGradient.aggregate_array(
      'Absolute_Delta_T'
    );


  //------------------------------------------------------------
  // Year-specific PERT threshold
  //------------------------------------------------------------

  var PERT_THRESHOLD_YEAR =
    ee.Number(
      yearlyLSTSummary
        .filter(
          ee.Filter.eq('Year', year)
        )
        .first()
        .get('PERT_Threshold')
    );


  //------------------------------------------------------------
  // PERT crossing diagnostic
  //------------------------------------------------------------

  return ee.FeatureCollection(

    ee.List.sequence(
      0,
      deltaTList.size().subtract(2)
    )
    .map(function(i) {

      i = ee.Number(i);

      var d1 = ee.Number(
        deltaTList.get(i)
      );

      var d2 = ee.Number(
        deltaTList.get(
          i.add(1)
        )
      );

      var abs1 = ee.Number(
        absDeltaTList.get(i)
      );

      var abs2 = ee.Number(
        absDeltaTList.get(
          i.add(1)
        )
      );


      var aboveFlag = ee.Number(
        ee.Algorithms.If(
          abs1.gt(PERT_THRESHOLD_YEAR),
          1,
          0
        )
      );


      var belowNextFlag = ee.Number(
        ee.Algorithms.If(
          abs2.lte(PERT_THRESHOLD_YEAR),
          1,
          0
        )
      );


      return ee.Feature(null, {

        Year: year,

        Position: i.add(1),

        Delta_T_1: d1,

        Absolute_Delta_T_1: abs1,

        Delta_T_2: d2,

        Absolute_Delta_T_2: abs2,

        PERT: PERT_THRESHOLD_YEAR,

        Above_Flag: aboveFlag,

        Next_Below_Flag: belowNextFlag

      });

    })

  );

}


//--------------------------------------------------------------
// All-year PERT diagnostics
//--------------------------------------------------------------

var numericPERTDiagnostic =
  ee.FeatureCollection(

    years.map(function(year) {

      return calculatePERTDiagnostic(
        ee.Number(year)
      );

    })

  ).flatten();


print(
  'Year-wise Numeric PERT Diagnostic',
  numericPERTDiagnostic
);


//--------------------------------------------------------------
// Crossing Candidates
//--------------------------------------------------------------

var crossingCandidates =
  numericPERTDiagnostic.filter(
    ee.Filter.and(

      ee.Filter.eq(
        'Above_Flag',
        1
      ),

      ee.Filter.eq(
        'Next_Below_Flag',
        1
      )

    )
  );


print(
  'Year-wise ASE PERT Crossing Candidates',
  crossingCandidates
);

print(
  'Number of Year-wise ASE PERT Crossing Candidates',
  crossingCandidates.size()
);
//==============================================================
// SECTION 22
// YEAR-WISE FINAL PERT PROFILE
//==============================================================

function createPERTProfile(year) {

  //------------------------------------------------------------
  // Year-specific fitted gradient
  //------------------------------------------------------------

  var yearGradient =
    fittedGradientProfile
      .filter(
        ee.Filter.eq('Year', year)
      )
      .sort('Position');


  //------------------------------------------------------------
  // Year-specific LST profile
  //------------------------------------------------------------

  var yearProfile =
    lstProfile
      .filter(
        ee.Filter.eq('Year', year)
      )
      .sort('Position');


  //------------------------------------------------------------
  // Distances
  //------------------------------------------------------------

  var distances =
    yearProfile.aggregate_array(
      'Distance_m'
    );


  //------------------------------------------------------------
  // Absolute Delta T
  //------------------------------------------------------------

  var absDeltaT =
    yearGradient.aggregate_array(
      'Absolute_Delta_T'
    );


  //------------------------------------------------------------
  // Year-specific PERT threshold
  //------------------------------------------------------------

  var PERT_THRESHOLD_YEAR =
    ee.Number(
      yearlyLSTSummary
        .filter(
          ee.Filter.eq('Year', year)
        )
        .first()
        .get('PERT_Threshold')
    );


  //------------------------------------------------------------
  // Create PERT profile
  //------------------------------------------------------------

  return ee.FeatureCollection(

    ee.List.sequence(
      0,
      absDeltaT.size().subtract(1)
    )
    .map(function(i) {

      i = ee.Number(i);

      return ee.Feature(null, {

        Year: year,

        Position: i.add(1),

        Distance_m:
          distances.get(i.add(1)),

        Absolute_Delta_T:
          absDeltaT.get(i),

        PERT_Threshold:
          PERT_THRESHOLD_YEAR,

        PERT_Pass:
          ee.Number(
            absDeltaT.get(i)
          ).gte(
            PERT_THRESHOLD_YEAR
          )

      });

    })

  );

}


//--------------------------------------------------------------
// All-year PERT profiles
//--------------------------------------------------------------

var pertProfile =
  ee.FeatureCollection(

    years.map(function(year) {

      return createPERTProfile(
        ee.Number(year)
      );

    })

  ).flatten();


print(
  'Year-wise FINAL PERT PROFILE',
  pertProfile
);


//==============================================================
// YEAR-WISE PERT CHART
//==============================================================

var finalPERTChart =
  ui.Chart.feature.groups({

    features: pertProfile,

    xProperty: 'Distance_m',

    yProperty: 'Absolute_Delta_T',

    seriesProperty: 'Year'

  })
  .setChartType('LineChart')
  .setOptions({

    title: 'Year-wise ASE PERT Analysis',

    hAxis: {
      title: 'Distance from CUA (m)'
    },

    vAxis: {
      title: 'Absolute Delta T (°C)'
    },

    lineWidth: 2,

    pointSize: 3,

    legend: {
      position: 'right'
    }

  });


print(
  'YEAR-WISE ASE PERT CHART',
  finalPERTChart
);
//==============================================================
// SECTION 23
// YEAR-WISE FINAL PERT CROSSING DISTANCES
//==============================================================

function calculateCrossingDistances(year) {

  var yearCrossings =
    crossingCandidates
      .filter(
        ee.Filter.eq('Year', year)
      )
      .sort('Position');


  var crossingPositions =
    yearCrossings.aggregate_array(
      'Position'
    );


  var crossingCount =
    yearCrossings.size();


  //------------------------------------------------------------
  // First crossing
  //------------------------------------------------------------

  var firstCrossingPosition =
    ee.Algorithms.If(

      crossingCount.gte(1),

      ee.Number(
        crossingPositions.get(0)
      ),

      null

    );


  //------------------------------------------------------------
  // Second crossing
  //------------------------------------------------------------

  var secondCrossingPosition =
    ee.Algorithms.If(

      crossingCount.gte(2),

      ee.Number(
        crossingPositions.get(1)
      ),

      null

    );


  //------------------------------------------------------------
  // Convert to distance
  //------------------------------------------------------------

  var firstCrossingDistance =
    ee.Algorithms.If(

      crossingCount.gte(1),

      ee.Number(
        firstCrossingPosition
      ).multiply(1000),

      null

    );


  var secondCrossingDistance =
    ee.Algorithms.If(

      crossingCount.gte(2),

      ee.Number(
        secondCrossingPosition
      ).multiply(1000),

      null

    );


  return ee.Feature(null, {

    Year: year,

    Crossing_Count:
      crossingCount,

    First_Crossing_Position:
      firstCrossingPosition,

    First_Crossing_Distance_m:
      firstCrossingDistance,

    First_Crossing_Distance_km:
      ee.Algorithms.If(
        crossingCount.gte(1),
        ee.Number(firstCrossingDistance)
          .divide(1000),
        null
      ),

    Second_Crossing_Position:
      secondCrossingPosition,

    Second_Crossing_Distance_m:
      secondCrossingDistance,

    Second_Crossing_Distance_km:
      ee.Algorithms.If(
        crossingCount.gte(2),
        ee.Number(secondCrossingDistance)
          .divide(1000),
        null
      )

  });

}


//--------------------------------------------------------------
// All-year crossing distances
//--------------------------------------------------------------

var yearlyCrossingDistances =
  ee.FeatureCollection(

    years.map(function(year) {

      return calculateCrossingDistances(
        ee.Number(year)
      );

    })

  );


print(
  'Year-wise PERT Crossing Distances',
  yearlyCrossingDistances
);

//==============================================================
// SECTION 24
// YEAR-WISE ASE BACKGROUND / RURAL REFERENCE AREA
//==============================================================

function calculateBRA(year) {

  //------------------------------------------------------------
  // Get year-specific crossing
  //------------------------------------------------------------

  var yearCrossing =
    yearlyCrossingDistances
      .filter(
        ee.Filter.eq('Year', year)
      )
      .first();

  var crossingCount =
    ee.Number(
      yearCrossing.get('Crossing_Count')
    );

  var hasBRA =
    crossingCount.gte(1);


  //------------------------------------------------------------
  // Safe BRA distance
  //------------------------------------------------------------

  var BRA_DISTANCE =
    ee.Number(
      ee.Algorithms.If(
        hasBRA,
        yearCrossing.get('First_Crossing_Distance_m'),
        0
      )
    );


  //------------------------------------------------------------
  // Create BRA geometry
  //------------------------------------------------------------

  var BRA_Outer =
    CUA_Geometry.buffer({
      distance: BRA_DISTANCE,
      maxError: 100
    });

  var BRA_Geometry =
    BRA_Outer.difference({
      right: CUA_Geometry,
      maxError: 100
    });


  //------------------------------------------------------------
  // BRA Area
  //------------------------------------------------------------

  var BRA_Area_km2 =
    ee.Algorithms.If(
      hasBRA,
      BRA_Geometry
        .area({
          maxError: 100
        })
        .divide(1e6),
      null
    );


  //------------------------------------------------------------
  // Second crossing
  //------------------------------------------------------------

  var secondCrossingDistance =
    ee.Algorithms.If(
      crossingCount.gte(2),
      yearCrossing.get(
        'Second_Crossing_Distance_m'
      ),
      null
    );


  //------------------------------------------------------------
  // Final BRA feature
  //------------------------------------------------------------

  return ee.Feature(null, {

    Year: year,

    Crossing_Count:
      crossingCount,

    CUA_Area_km2:
      CUA_Area_km2,

    BRA_Available:
      hasBRA,

    BRA_Distance_m:
      ee.Algorithms.If(
        hasBRA,
        BRA_DISTANCE,
        null
      ),

    BRA_Distance_km:
      ee.Algorithms.If(
        hasBRA,
        BRA_DISTANCE.divide(1000),
        null
      ),

    BRA_Area_km2:
      BRA_Area_km2,

    Second_Crossing_Distance_m:
      secondCrossingDistance,

    Second_Crossing_Distance_km:
      ee.Algorithms.If(
        crossingCount.gte(2),
        ee.Number(secondCrossingDistance)
          .divide(1000),
        null
      )

  });

}


//--------------------------------------------------------------
// Year-wise BRA summary
//--------------------------------------------------------------

var yearlyBRASummary =
  ee.FeatureCollection(

    years.map(function(year) {

      return calculateBRA(
        ee.Number(year)
      );

    })

  );


print(
  'Year-wise ASE BRA Summary',
  yearlyBRASummary
);
//==============================================================
// SECTION 25
// YEAR-WISE ASE LST PROFILE CHART
//==============================================================

var finalLSTChart =
  ui.Chart.feature.groups({

    features: fittedProfile,

    xProperty: 'Distance_m',

    yProperty: 'LST',

    seriesProperty: 'Year'

  })
  .setChartType('LineChart')
  .setOptions({

    title:
      'ASE LST Profile - Actual LST (2005–2026)',

    hAxis: {
      title:
        'Distance from CUA (m)'
    },

    vAxis: {
      title:
        'LST (°C)'
    },

    lineWidth: 2,

    pointSize: 3,

    legend: {
      position: 'right'
    }

  });


print(
  'YEAR-WISE ASE LST PROFILE',
  finalLSTChart
);

//==============================================================
// SECTION 26
// YEAR-WISE ASE BRA LST + SUHII
//==============================================================

function calculateSUHII(year) {

  //------------------------------------------------------------
  // Year-specific BRA
  //------------------------------------------------------------

  var yearBRA =
    yearlyBRASummary
      .filter(
        ee.Filter.eq('Year', year)
      )
      .first();


  var hasBRA =
  ee.Number(
    yearBRA.get('BRA_Available')
  ).eq(1);


  //------------------------------------------------------------
  // Safe BRA distance
  //------------------------------------------------------------

  var BRA_DISTANCE =
    ee.Number(
      ee.Algorithms.If(
        hasBRA,
        yearBRA.get('BRA_Distance_m'),
        0
      )
    );


  //------------------------------------------------------------
  // BRA Geometry
  //------------------------------------------------------------

  var BRA_Geometry =
    CUA_Geometry
      .buffer({
        distance: BRA_DISTANCE,
        maxError: 100
      })
      .difference({
        right: CUA_Geometry,
        maxError: 100
      });


  //------------------------------------------------------------
  // Year-specific LST
  //------------------------------------------------------------

  var yearLST =
    getSummerLST(year);


  //------------------------------------------------------------
  // BRA Mean LST
  //------------------------------------------------------------

  var BRA_LST_Stats =
    yearLST.reduceRegion({

      reducer: ee.Reducer.mean(),

      geometry: BRA_Geometry,

      scale: 1000,

      maxPixels: 1e13,

      tileScale: 4

    });


  var BRA_Mean_LST =
    ee.Algorithms.If(
      hasBRA,
      BRA_LST_Stats.get('LST_Day_1km'),
      null
    );


  //------------------------------------------------------------
  // CUA Mean LST
  //------------------------------------------------------------

  var CUA_LST_Stats =
    yearLST.reduceRegion({

      reducer: ee.Reducer.mean(),

      geometry: CUA_Geometry,

      scale: 1000,

      maxPixels: 1e13,

      tileScale: 4

    });


  var CUA_Mean_LST =
    CUA_LST_Stats.get(
      'LST_Day_1km'
    );


  //------------------------------------------------------------
  // SUHII
  //------------------------------------------------------------

  var ASE_SUHII_Final =
    ee.Algorithms.If(
      hasBRA,
      ee.Number(CUA_Mean_LST)
        .subtract(
          ee.Number(BRA_Mean_LST)
        ),
      null
    );


  //------------------------------------------------------------
  // Final feature
  //------------------------------------------------------------

  return ee.Feature(null, {

    Year: year,

    BRA_Available:
      hasBRA,

    CUA_Mean_LST:
      CUA_Mean_LST,

    BRA_Mean_LST:
      BRA_Mean_LST,

    SUHII:
      ASE_SUHII_Final,

    BRA_Distance_m:
      ee.Algorithms.If(
        hasBRA,
        BRA_DISTANCE,
        null
      ),

    BRA_Distance_km:
      ee.Algorithms.If(
        hasBRA,
        BRA_DISTANCE.divide(1000),
        null
      )

  });

}


//--------------------------------------------------------------
// Year-wise SUHII
//--------------------------------------------------------------

var yearlySUHII =
  ee.FeatureCollection(

    years.map(function(year) {

      return calculateSUHII(
        ee.Number(year)
      );

    })

  );


print(
  'Year-wise ASE SUHII',
  yearlySUHII
);
//==============================================================
// SECTION 27
// FINAL MULTI-YEAR SUHII TABLE
//==============================================================

var finalSUHII =
  yearlySUHII.select([
    'Year',
    'CUA_Mean_LST',
    'BRA_Mean_LST',
    'SUHII',
    'BRA_Distance_m',
    'BRA_Distance_km'
  ]);

print(
  '===== FINAL MULTI-YEAR SUHII TABLE =====',
  finalSUHII
);

print(
  'Years',
  finalSUHII.aggregate_array('Year')
);

print(
  'CUA LST',
  finalSUHII.aggregate_array('CUA_Mean_LST')
);

print(
  'BRA LST',
  finalSUHII.aggregate_array('BRA_Mean_LST')
);

print(
  'SUHII',
  finalSUHII.aggregate_array('SUHII')
);

//==============================================================
// SECTION 28
// SUHII TREND
//==============================================================

var suhiiChart =
  ui.Chart.feature.byFeature(
    finalSUHII,
    'Year',
    'SUHII'
  )
  .setChartType('LineChart')
  .setOptions({

    title:
      'ASE SUHII Trend (2005–2026)',

    hAxis: {
      title:
        'Year'
    },

    vAxis: {
      title:
        'SUHII (°C)'
    },

    lineWidth: 3,

    pointSize: 6,

    legend: {
      position: 'none'
    }

  });

print(
  'FINAL ASE SUHII TREND',
  suhiiChart
);
///==============================================================
// SECTION 29
// CUA vs BRA LST
//==============================================================

var finalCUABRAChart =
  ui.Chart.feature.byFeature(

    finalSUHII,

    'Year',

    [
      'CUA_Mean_LST',
      'BRA_Mean_LST'
    ]

  )
  .setChartType('LineChart')
  .setOptions({

    title:
      'CUA and BRA LST Comparison (2005–2026)',

    hAxis: {
      title:
        'Year'
    },

    vAxis: {
      title:
        'Mean LST (°C)'
    },

    lineWidth: 3,

    pointSize: 6,

    legend: {
      position: 'top'
    },

    chartArea: {
      left: 75,
      right: 30,
      top: 50,
      bottom: 65
    }

  });

print(
  'FINAL CUA vs BRA LST GRAPH',
  finalCUABRAChart
);
//==============================================================
// SECTION 30
// LST SPATIAL MAPS
//==============================================================

var mapYears = [
  2005,
  2009,
  2011,
  2015,
  2019,
  2022,
  2026
];


//--------------------------------------------------------------
// Year-wise LST Maps
//--------------------------------------------------------------

mapYears.forEach(function(year) {

  Map.addLayer(

    getSummerLST(year),

    LST_VIS,

    'LST ' + year

  );

});


//--------------------------------------------------------------
// CUA Boundary
//--------------------------------------------------------------

Map.addLayer(
  CUA_Geometry,
  {color: 'red'},
  'CUA Boundary'
);


//--------------------------------------------------------------
// Example BRA Boundary
// First year with valid BRA
//--------------------------------------------------------------

var validExampleBRA =
  yearlyBRASummary
    .filter(
      ee.Filter.eq(
        'BRA_Available',
        true
      )
    )
    .first();

var exampleYear =
  validExampleBRA.get(
    'Year'
  );

var exampleBRA_Distance =
  ee.Number(
    validExampleBRA.get(
      'BRA_Distance_m'
    )
  );

var exampleBRA_Geometry =
  CUA_Geometry
    .buffer({
      distance:
        exampleBRA_Distance,
      maxError: 100
    })
    .difference({
      right:
        CUA_Geometry,
      maxError: 100
    });

Map.addLayer(
  exampleBRA_Geometry,
  {color: 'yellow'},
  'BRA Boundary - Example Year'
);


//--------------------------------------------------------------
// Map Center
//--------------------------------------------------------------

Map.centerObject(
  studyArea,
  9
);

//==============================================================
// SECTION 31
// LST MAP EXPORTS
//==============================================================

mapYears.forEach(function(year) {

  Export.image.toDrive({

    image:
      getSummerLST(year),

    description:
      'ASE_LST_' + year,

    folder:
      'ASE_Final_LST_Maps',

    fileNamePrefix:
      'ASE_LST_' + year,

    region:
      studyArea,

    scale:
      1000,

    maxPixels:
      1e13,

    fileFormat:
      'GeoTIFF'

  });

});


print(
  '===== FINAL LST MAP YEARS =====',
  mapYears
);

print(
  'Number of LST Maps Generated',
  mapYears.length
);

//==============================================================
// SECTION 32
// YEAR-WISE CUA + BRA VECTOR EXPORT
//==============================================================


//--------------------------------------------------------------
// CUA Feature — Fixed for all years
//--------------------------------------------------------------

var CUA_Feature =
  ee.Feature(
    CUA_Geometry,
    {
      Zone: 'CUA',

      Area_km2:
        CUA_Geometry
          .area(1)
          .divide(1e6)
    }
  );


//--------------------------------------------------------------
// Only years with valid BRA
//--------------------------------------------------------------

var validBRASummary =
  yearlyBRASummary.filter(
    ee.Filter.eq(
      'BRA_Available',
      true
    )
  );


//--------------------------------------------------------------
// Year-wise BRA Features
//--------------------------------------------------------------

var yearlyBRAFeatures =
  ee.FeatureCollection(

    validBRASummary.map(
      function(yearSummary) {

        var year =
          yearSummary.get('Year');


        var BRA_DISTANCE =
          ee.Number(
            yearSummary.get(
              'BRA_Distance_m'
            )
          );


        var BRA_Geometry =
          CUA_Geometry
            .buffer({
              distance: BRA_DISTANCE,
              maxError: 100
            })
            .difference({
              right: CUA_Geometry,
              maxError: 100
            });


        return ee.Feature(
          BRA_Geometry,
          {
            Zone: 'BRA',

            Year: year,

            Area_km2:
              BRA_Geometry
                .area(1)
                .divide(1e6),

            Distance_km:
              BRA_DISTANCE
                .divide(1000)
          }
        );

      }
    )

  );


print(
  '===== YEAR-WISE ASE BRA GEOMETRY =====',
  yearlyBRAFeatures
);


//--------------------------------------------------------------
// Export Fixed CUA
//--------------------------------------------------------------

Export.table.toDrive({

  collection:
    ee.FeatureCollection([
      CUA_Feature
    ]),

  description:
    'ASE_CUA_Boundary',

  folder:
    'ASE_Final_Vector',

  fileNamePrefix:
    'ASE_CUA_Boundary',

  fileFormat:
    'SHP'

});


//--------------------------------------------------------------
// Export Year-wise BRA
//--------------------------------------------------------------

Export.table.toDrive({

  collection:
    yearlyBRAFeatures,

  description:
    'ASE_BRA_Boundaries_2005_2026',

  folder:
    'ASE_Final_Vector',

  fileNamePrefix:
    'ASE_BRA_Boundaries_2005_2026',

  fileFormat:
    'SHP'

});


//--------------------------------------------------------------
// Export CUA + all valid Year-wise BRA
//--------------------------------------------------------------

var allASEZones =
  ee.FeatureCollection([
    CUA_Feature
  ])
  .merge(
    yearlyBRAFeatures
  );


print(
  '===== FINAL YEAR-WISE ASE ZONES =====',
  allASEZones
);


Export.table.toDrive({

  collection:
    allASEZones,

  description:
    'ASE_CUA_BRA_Zones_2005_2026',

  folder:
    'ASE_Final_Vector',

  fileNamePrefix:
    'ASE_CUA_BRA_Zones_2005_2026',

  fileFormat:
    'SHP'

});
//==============================================================
// SECTION 33
// FINAL INTEGRATED ASE TABLE
//==============================================================

function createASEFinalTable(year) {

  var yearFittedProfile =
    fittedProfile
      .filter(
        ee.Filter.eq(
          'Year',
          year
        )
      )
      .sort('Distance_m');


  var yearPERTProfile =
    pertProfile
      .filter(
        ee.Filter.eq(
          'Year',
          year
        )
      )
      .sort('Position');


  var fittedList =
    yearFittedProfile.toList(
      yearFittedProfile.size()
    );

  var pertList =
    yearPERTProfile.toList(
      yearPERTProfile.size()
    );


  return ee.FeatureCollection(

    ee.List.sequence(
      0,
      yearPERTProfile.size().subtract(1)
    )
    .map(function(i) {

      i = ee.Number(i);


      var pertRow =
        ee.Feature(
          pertList.get(i)
        );


      // PERT Position 1 corresponds
      // to fittedProfile Position 1
      var profileRow =
        ee.Feature(
          fittedList.get(
            i.add(1)
          )
        );


      var absoluteDeltaT =
        ee.Number(
          pertRow.get(
            'Absolute_Delta_T'
          )
        );


      var pertThreshold =
        ee.Number(
          pertRow.get(
            'PERT_Threshold'
          )
        );


      return ee.Feature(null, {

        Year:
          year,

        Position:
          pertRow.get(
            'Position'
          ),

        Distance_m:
          pertRow.get(
            'Distance_m'
          ),

        Distance_km:
          ee.Number(
            pertRow.get(
              'Distance_m'
            )
          ).divide(1000),

        Actual_LST:
          profileRow.get(
            'LST'
          ),

        Fitted_LST:
          profileRow.get(
            'Fitted_LST'
          ),

        Absolute_Delta_T:
          absoluteDeltaT,

        PERT_Threshold:
          pertThreshold,

        Difference_from_PERT:
          absoluteDeltaT.subtract(
            pertThreshold
          ),

        Above_PERT:
          absoluteDeltaT.gte(
            pertThreshold
          )

      });

    })

  );

}


//--------------------------------------------------------------
// Build final table for all years
//--------------------------------------------------------------

var ASE_Final_Table =
  ee.FeatureCollection(

    years.map(function(year) {

      return createASEFinalTable(
        ee.Number(year)
      );

    })

  ).flatten();


print(
  '===== FINAL YEAR-WISE ASE INTEGRATED TABLE =====',
  ASE_Final_Table
);

print(
  'Final ASE Table Rows',
  ASE_Final_Table.size()
);

//==============================================================
// SECTION 34
// SUHII STATISTICAL SUMMARY
//==============================================================

// Only years with valid SUHII
var validSUHII =
  finalSUHII.filter(
    ee.Filter.notNull([
      'SUHII'
    ])
  );


//--------------------------------------------------------------
// SUHII VALUES
//--------------------------------------------------------------

var suhiValues =
  validSUHII.aggregate_array(
    'SUHII'
  );


//--------------------------------------------------------------
// MINIMUM SUHII
//--------------------------------------------------------------

var suhiMin =
  ee.Number(
    suhiValues.reduce(
      ee.Reducer.min()
    )
  );


//--------------------------------------------------------------
// MAXIMUM SUHII
//--------------------------------------------------------------

var suhiMax =
  ee.Number(
    suhiValues.reduce(
      ee.Reducer.max()
    )
  );


//--------------------------------------------------------------
// MEAN SUHII
//--------------------------------------------------------------

var suhiMean =
  ee.Number(
    suhiValues.reduce(
      ee.Reducer.mean()
    )
  );


//--------------------------------------------------------------
// FIRST VALID SUHII
//--------------------------------------------------------------

var firstSUHII =
  ee.Number(
    validSUHII
      .sort('Year')
      .first()
      .get('SUHII')
  );


//--------------------------------------------------------------
// LAST VALID SUHII
//--------------------------------------------------------------

var lastSUHII =
  ee.Number(
    validSUHII
      .sort('Year', false)
      .first()
      .get('SUHII')
  );


//--------------------------------------------------------------
// SUHII CHANGE
//--------------------------------------------------------------

var suhiChange =
  lastSUHII.subtract(
    firstSUHII
  );


//--------------------------------------------------------------
// STATISTICAL SUMMARY
//--------------------------------------------------------------

var SUHII_Statistical_Summary =
  ee.FeatureCollection([

    ee.Feature(null, {

      Parameter:
        'Minimum SUHII',

      Value:
        suhiMin,

      Unit:
        'Celsius'

    }),

    ee.Feature(null, {

      Parameter:
        'Maximum SUHII',

      Value:
        suhiMax,

      Unit:
        'Celsius'

    }),

    ee.Feature(null, {

      Parameter:
        'Mean SUHII',

      Value:
        suhiMean,

      Unit:
        'Celsius'

    }),

    ee.Feature(null, {

      Parameter:
        'SUHII Change (First-Last Valid Year)',

      Value:
        suhiChange,

      Unit:
        'Celsius'

    })

  ]);


//--------------------------------------------------------------
// PRINT RESULTS
//--------------------------------------------------------------

print(
  '===== FINAL SUHII STATISTICAL SUMMARY =====',
  SUHII_Statistical_Summary
);

print(
  'Valid SUHII Years',
  validSUHII.aggregate_array('Year')
);

print(
  'Minimum SUHII',
  suhiMin
);

print(
  'Maximum SUHII',
  suhiMax
);

print(
  'Mean SUHII',
  suhiMean
);

print(
  'SUHII Change (First-Last Valid Year)',
  suhiChange
);
 //==============================================================
// SECTION 35
// FINAL YEAR-WISE RESULTS SUMMARY
//==============================================================

var ASE_Final_Summary =
  yearlyBRASummary.map(function(braFeature) {

    var year =
      braFeature.get('Year');


    var suhiiFeature =
      finalSUHII
        .filter(
          ee.Filter.eq(
            'Year',
            year
          )
        )
        .first();


    var lstSummary =
      yearlyLSTSummary
        .filter(
          ee.Filter.eq(
            'Year',
            year
          )
        )
        .first();


    var crossingSummary =
      yearlyCrossingDistances
        .filter(
          ee.Filter.eq(
            'Year',
            year
          )
        )
        .first();


    return ee.Feature(null, {

      Year:
        year,

      //----------------------------------------------------------
      // CUA
      //----------------------------------------------------------

      CUA_Area_km2:
        braFeature.get(
          'CUA_Area_km2'
        ),


      //----------------------------------------------------------
      // BRA
      //----------------------------------------------------------

      BRA_Available:
        braFeature.get(
          'BRA_Available'
        ),

      BRA_Area_km2:
        braFeature.get(
          'BRA_Area_km2'
        ),

      BRA_Distance_km:
        braFeature.get(
          'BRA_Distance_km'
        ),


      //----------------------------------------------------------
      // PERT
      //----------------------------------------------------------

      PERT_Threshold:
        lstSummary.get(
          'PERT_Threshold'
        ),


      //----------------------------------------------------------
      // PERT CROSSINGS
      //----------------------------------------------------------

      Crossing_Count:
        crossingSummary.get(
          'Crossing_Count'
        ),

      First_Crossing_Distance_km:
        crossingSummary.get(
          'First_Crossing_Distance_km'
        ),

      Second_Crossing_Distance_km:
        crossingSummary.get(
          'Second_Crossing_Distance_km'
        ),


      //----------------------------------------------------------
      // LST
      //----------------------------------------------------------

      CUA_Mean_LST:
        suhiiFeature.get(
          'CUA_Mean_LST'
        ),

      BRA_Mean_LST:
        suhiiFeature.get(
          'BRA_Mean_LST'
        ),


      //----------------------------------------------------------
      // SUHII
      //----------------------------------------------------------

      SUHII:
        suhiiFeature.get(
          'SUHII'
        )

    });

  });


print(
  '================================================'
);

print(
  'FINAL YEAR-WISE ASE RESULTS SUMMARY'
);

print(
  '================================================'
);

print(
  ASE_Final_Summary
);

//==============================================================
// SECTION 36
// ALL FINAL EXPORTS
//==============================================================


//--------------------------------------------------------------
// Multi-Year SUHII
//--------------------------------------------------------------

Export.table.toDrive({

  collection:
    finalSUHII,

  description:
    'ASE_Final_MultiYear_SUHII_Table',

  folder:
    'ASE_Final_Results',

  fileNamePrefix:
    'ASE_Final_MultiYear_SUHII_Table',

  fileFormat:
    'CSV'

});


//--------------------------------------------------------------
// LST Profile
//--------------------------------------------------------------

Export.table.toDrive({

  collection:
    fittedProfile,

  description:
    'ASE_Final_LST_Profile_2005_2026',

  folder:
    'ASE_Final_Results',

  fileNamePrefix:
    'ASE_Final_LST_Profile_2005_2026',

  fileFormat:
    'CSV'

});


//--------------------------------------------------------------
// PERT Profile
//--------------------------------------------------------------

Export.table.toDrive({

  collection:
    pertProfile,

  description:
    'ASE_Final_PERT_Profile_2005_2026',

  folder:
    'ASE_Final_Results',

  fileNamePrefix:
    'ASE_Final_PERT_Profile_2005_2026',

  fileFormat:
    'CSV'

});


//--------------------------------------------------------------
// Raw LST Profile
//--------------------------------------------------------------

Export.table.toDrive({

  collection:
    lstProfile,

  description:
    'ASE_Raw_LST_Profile_2005_2026',

  folder:
    'ASE_Final_Results',

  fileNamePrefix:
    'ASE_Raw_LST_Profile_2005_2026',

  fileFormat:
    'CSV'

});


//--------------------------------------------------------------
// Integrated ASE Table
//--------------------------------------------------------------

Export.table.toDrive({

  collection:
    ASE_Final_Table,

  description:
    'ASE_Final_Integrated_Table_2005_2026',

  folder:
    'ASE_Final_Results',

  fileNamePrefix:
    'ASE_Final_Integrated_Table_2005_2026',

  fileFormat:
    'CSV'

});


//--------------------------------------------------------------
// PERT Diagnostic
//--------------------------------------------------------------

Export.table.toDrive({

  collection:
    numericPERTDiagnostic,

  description:
    'ASE_Final_PERT_Diagnostic_2005_2026',

  folder:
    'ASE_Final_Results',

  fileNamePrefix:
    'ASE_Final_PERT_Diagnostic_2005_2026',

  fileFormat:
    'CSV'

});


//--------------------------------------------------------------
// Year-wise PERT Crossing Distances
//--------------------------------------------------------------

Export.table.toDrive({

  collection:
    yearlyCrossingDistances,

  description:
    'ASE_Final_PERT_Crossing_Distances_2005_2026',

  folder:
    'ASE_Final_Results',

  fileNamePrefix:
    'ASE_Final_PERT_Crossing_Distances_2005_2026',

  fileFormat:
    'CSV'

});


//--------------------------------------------------------------
// Year-wise BRA Summary
//--------------------------------------------------------------

Export.table.toDrive({

  collection:
    yearlyBRASummary,

  description:
    'ASE_Final_BRA_Summary_2005_2026',

  folder:
    'ASE_Final_Results',

  fileNamePrefix:
    'ASE_Final_BRA_Summary_2005_2026',

  fileFormat:
    'CSV'

});


//--------------------------------------------------------------
// Statistical Summary
//--------------------------------------------------------------

Export.table.toDrive({

  collection:
    SUHII_Statistical_Summary,

  description:
    'ASE_Final_SUHII_Statistical_Summary',

  folder:
    'ASE_Final_Results',

  fileNamePrefix:
    'ASE_Final_SUHII_Statistical_Summary',

  fileFormat:
    'CSV'

});


//--------------------------------------------------------------
// Final Year-wise Summary
//--------------------------------------------------------------

Export.table.toDrive({

  collection:
    ASE_Final_Summary,

  description:
    'ASE_Final_Results_Summary_2005_2026',

  folder:
    'ASE_Final_Results',

  fileNamePrefix:
    'ASE_Final_Results_Summary_2005_2026',

  fileFormat:
    'CSV'

});


//==============================================================
// FINAL MESSAGE
//==============================================================

print(
  '================================================'
);

print(
  '===== ASE ANALYSIS COMPLETE ====='
);

print(
  '================================================'
);

print(
  'Final SUHII Years',
  finalSUHII.aggregate_array('Year')
);

print(
  'CUA Area (km²)',
  CUA_Area_km2
);

print(
  'Year-wise BRA Summary',
  yearlyBRASummary
);

print(
  'Year-wise PERT Threshold',
  PERT_THRESHOLD
);

print(
  'Minimum SUHII',
  suhiMin
);

print(
  'Maximum SUHII',
  suhiMax
);

print(
  'Mean SUHII',
  suhiMean
);

print(
  'SUHII Change 2005-2026',
  suhiChange
);

print(
  '===== YEAR-WISE FINAL SUMMARY =====',
  ASE_Final_Summary
);