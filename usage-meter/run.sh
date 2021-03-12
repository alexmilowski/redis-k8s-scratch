#!/bin/bash
MY_INTERVAL=${INTERVAL:-300}
trap 'exit 255' TERM
python meter.py --interval $MY_INTERVAL
