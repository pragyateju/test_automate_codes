import json
import re
import pandas as pd
from datetime import datetime

# === File Paths ===
TEST_LOG_PATH = "eps_test.log"
REFERENCE_LOG_PATH = "eps_reference.log"
CONFIG_PATH = "eps_config.json"
OUTPUT_PATH = "eps_validation_report.xlsx"

# === Load EPS Config ===
try:
    with open(CONFIG_PATH, "r") as f:
        eps_config = json.load(f)
except FileNotFoundError:
    print(f"Config file not found: {CONFIG_PATH}")
    exit(1)

# === Function to extract the latest TM block ===
def extract_latest_tm_block(log_lines, tm_id):
    blocks = []
    current_block = []
    capture = False

    for line in log_lines:
        if f"Received TM Id:- {tm_id}" in line:
            if current_block:
                blocks.append(current_block)
                current_block = []
            capture = True

        if capture:
            current_block.append(line.strip())

    if current_block:
        blocks.append(current_block)

    return blocks[-1] if blocks else []

# === Function to parse values of specific parameters from block ===
def parse_tm_block(block_lines, params):
    data = {}
    for param in params:
        for line in block_lines:
            if param in line:
                match = re.search(rf"{re.escape(param)}\s*[:=]\s*(.+)", line)
                if match:
                    data[param] = match.group(1).strip()
                    break
    return data

# === Read the log files ===
try:
    with open(TEST_LOG_PATH, "r") as test_file:
        test_lines = test_file.readlines()
    with open(REFERENCE_LOG_PATH, "r") as ref_file:
        ref_lines = ref_file.readlines()
except FileNotFoundError as e:
    print(f" Log file missing: {e}")
    exit(1)

# === Main Comparison Logic ===
results = []

for tm_id, params in eps_config.items():
    test_block = extract_latest_tm_block(test_lines, tm_id)
    ref_block = extract_latest_tm_block(ref_lines, tm_id)

    test_data = parse_tm_block(test_block, params)
    ref_data = parse_tm_block(ref_block, params)

    for param in params:
        test_value = test_data.get(param, "")
        ref_value = ref_data.get(param, "")
        status = "Success" if test_value == ref_value and test_value != "" else "No Success"
        results.append({
            "TM Id": tm_id,
            "Parameter": param,
            "Test Value": test_value,
            "Reference Value": ref_value,
            "Status": status
        })

# === Save to Excel ===
df = pd.DataFrame(results)
df.to_excel(OUTPUT_PATH, index=False)
print(f" Validation report saved to: {OUTPUT_PATH}")

