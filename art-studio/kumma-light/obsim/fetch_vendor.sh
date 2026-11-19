#!/bin/bash
mkdir -p "$(dirname "$0")/vendor"
curl -sSfL https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js -o "$(dirname "$0")/vendor/three.module.js"
mkdir -p "$(dirname "$0")/vendor/geometries" "$(dirname "$0")/vendor/math" "$(dirname "$0")/vendor/utils"
for f in geometries/ConvexGeometry.js math/ConvexHull.js utils/BufferGeometryUtils.js; do
  curl -sSfL "https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/$f" -o "$(dirname "$0")/vendor/$f"
  sed -i "s#from 'three'#from '../three.module.js'#" "$(dirname "$0")/vendor/$f"
done
