#!/bin/bash
echo "Starting Warm Test Suite..."
pytest -v --alluredir=reports/json
allure serve reports/json
