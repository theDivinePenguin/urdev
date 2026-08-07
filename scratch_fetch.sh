#!/bin/bash
set -e
python3 generate.py --location "Mumbai, Maharashtra, India" --yes --endpoints-only
python3 generate.py --location "Jaisalmer, Rajasthan, India" --yes --endpoints-only
