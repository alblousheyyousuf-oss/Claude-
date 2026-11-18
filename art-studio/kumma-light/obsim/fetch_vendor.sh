#!/bin/bash
mkdir -p "$(dirname "$0")/vendor"
curl -sSfL https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js -o "$(dirname "$0")/vendor/three.module.js"
