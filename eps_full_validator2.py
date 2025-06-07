import json
import yaml
import pandas as pd
import re
import threading
import pexpect
import datetime
import time

# -------------------------------
# STEP 0: Subsystem Selection
# -------------------------------
subsystems = {
    "1": {
        "name": "EPS",
        "config": "eps_config.json",
        "yaml": "eps_expected.yaml",
        "log": "eps_test.log",
        "test_ids": ["11", "212"]
    }
}

# Simulate selection
choice = "1"
selected = subsystems[choice]

# -------------------------------
# CONFIGURATION
# -------------------------------
config_path = selected["config"]
expected_yaml_path = selected["yaml"]
log_path = selected["log"]
output_excel_path = f"{selected['name'].lower()}_result.xlsx"
mfcc_app_path = "./mfcc_app"
mfcc_log_output = f"{selected['name'].lower()}_mfcc_log.txt"

# -------------------------------
# STEP 1: Print Header
# -------------------------------
now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
print(f"\nProgram started at: {now}")
print(f"Test: {selected['name']} Subsystem Validation\n")

# -------------------------------
# STEP 2: Launch MFCC with pexpect
# -------------------------------
def run_mfcc():
    try:
        print("[+] Launching MFCC app with pexpect...\n")
        child = pexpect.spawn(mfcc_app_path, timeout=60)

        child.expect("Enter the MFCC option:")
        child.sendline("0")

        child.expect("Enter Radio ID:")
        child.sendline("4")

        child.expect("Enter Test Type ID")
        for test_id in selected["test_ids"]:
            child.sendline(test_id)
            time.sleep(1)

        child.expect(pexpect.EOF)
        output = child.before.decode('utf-8', errors='ignore')

        with open(mfcc_log_output, "w") as f:
            f.write(output)

        print("[✓] MFCC interaction complete.\n")

    except Exception as e:
        print(f"[!] MFCC automation failed: {e}")

# -------------------------------
# STEP 3: Start MFCC Automation
# -------------------------------
mfcc_thread = threading.Thread(target=run_mfcc)
mfcc_thread.start()
mfcc_thread.join()

# -------------------------------
# STEP 4: Load Inputs
# -------------------------------
with open(config_path) as f:
    tm_config = json.load(f)

with open(expected_yaml_path) as f:
    expected_values = yaml.safe_load(f)

with open(log_path) as f:
    log_lines = f.readlines()

# -------------------------------
# STEP 5: Create TM ID → Parameter Map
# -------------------------------
param_to_tmid = {}
for tmid, params in tm_config.items():
    for param in params:
        key = param.strip()
        if key:
            param_to_tmid[key] = tmid

# -------------------------------
# STEP 6: Parse Log and Validate
# -------------------------------
log_text = " ".join(log_lines)
results = []

for param, expected in expected_values.items():
    cleaned_param = param.strip()
    pattern = re.compile(rf"{re.escape(cleaned_param)}.*?([-+]?[0-9]*\.?[0-9]+)")
    match = pattern.search(log_text)

    if match:
        actual = float(match.group(1))
        status = "MATCHED" if expected["min"] <= actual <= expected["max"] else "MISMATCH"
        results.append({
            "Parameter": cleaned_param,
            "TM_ID": param_to_tmid.get(cleaned_param, "Unknown"),
            "Present": "Yes",
            "Actual Value": actual,
            "Expected Min": expected["min"],
            "Expected Max": expected["max"],
            "Status": status
        })
    else:
        results.append({
            "Parameter": cleaned_param,
            "TM_ID": param_to_tmid.get(cleaned_param, "Unknown"),
            "Present": "No",
            "Actual Value": None,
            "Expected Min": expected["min"],
            "Expected Max": expected["max"],
            "Status": "NOT PRESENT"
        })

# -------------------------------
# STEP 7: Save Results
# -------------------------------
df = pd.DataFrame(results)
df.to_excel(output_excel_path, index=False)

print(f"[✓] Validation complete. Results saved to {output_excel_path}")

