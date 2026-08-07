#!/bin/bash
set -e
locations=(
  "Kibithu, Arunachal Pradesh, India"
  "Auroville, Tamil Nadu, India"
  "Mumbai Suburban District, Maharashtra, 400051, India"
  "Pokhran, Rajasthan, India"
  "Giethoorn, Netherlands"
  "Hallstatt, Austria"
)

for loc in "${locations[@]}"; do
  echo ">>> Processing $loc"
  python3 generate.py --location "$loc" --yes --endpoints-only
done
echo ">>> All finished!"
