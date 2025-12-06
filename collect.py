import os
import json
import subprocess
import re
import sys


def extract_run_number(run_dir_name):
    """Extract run number from directory name like 'run1_20251203_114042' -> '1'"""
    match = re.match(r'run(\d+)_', run_dir_name)
    if match:
        return match.group(1)
    return None


def find_run_directories(base_dir):
    """Find all run directories matching pattern run*_* in base_dir"""
    print(f"[VERBOSE] Searching for run directories in: {base_dir}")
    if not os.path.exists(base_dir):
        print(f"[WARNING] Base directory does not exist: {base_dir}")
        return []
    run_dirs = []
    for item in os.listdir(base_dir):
        item_path = os.path.join(base_dir, item)
        if os.path.isdir(item_path) and re.match(r'run\d+_', item):
            run_dirs.append(item)
            print(f"[VERBOSE] Found run directory: {item}")
    print(f"[VERBOSE] Total run directories found: {len(run_dirs)}")
    return sorted(run_dirs)


def count_coverage(path, port, run_dir, run_number):
    print(f"[VERBOSE] Processing coverage for port {port}, run {run_number}")
    print(f"[VERBOSE]   Service path: {path}")
    print(f"[VERBOSE]   Run directory: {run_dir}")
    class_files = []
    jacoco_command2 = ''
    subdirs = [x[0] for x in os.walk(path)]
    for subdir in subdirs:
        if '/target/classes/' in subdir:
            target_dir = subdir[:subdir.rfind('/target/classes/') + 15]
            if target_dir not in class_files:
                class_files.append(target_dir)
                jacoco_command2 = jacoco_command2 + ' --classfiles ' + target_dir
                print(f"[VERBOSE]   Found target/classes: {target_dir}")
        if '/build/classes/' in subdir:
            target_dir = subdir[:subdir.rfind('/build/classes/') + 14]
            if target_dir not in class_files:
                class_files.append(target_dir)
                jacoco_command2 = jacoco_command2 + ' --classfiles ' + target_dir
                print(f"[VERBOSE]   Found build/classes: {target_dir}")

    jacoco_command2 = jacoco_command2 + ' --csv '
    jacoco_command1 = 'java -jar org.jacoco.cli-0.8.7-nodeps.jar report '
    jacoco_exec_file = os.path.join(run_dir, f"jacoco{port}_run{run_number}.exec")
    jacoco_csv_file = os.path.join(run_dir, f"jacoco{port}_run{run_number}.csv")
    print(f"[VERBOSE]   Exec file: {jacoco_exec_file} (exists: {os.path.exists(jacoco_exec_file)})")
    print(f"[VERBOSE]   CSV file: {jacoco_csv_file}")
    print(f"[VERBOSE]   Running command: {jacoco_command1 + jacoco_exec_file + jacoco_command2 + jacoco_csv_file}")
    result = subprocess.run(jacoco_command1 + jacoco_exec_file + jacoco_command2 + jacoco_csv_file, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[WARNING] JaCoCo command failed with return code {result.returncode}")
        print(f"[WARNING] Error output: {result.stderr}")
    else:
        print(f"[VERBOSE]   Coverage report generated successfully")


def count_requests(file_name, service_name):
    print(f"[VERBOSE]   Processing log file: {file_name}")
    if not os.path.exists(file_name):
        print(f"[WARNING]   Log file does not exist: {file_name}")
        return 0,0,0,0,0,0,0
    print(f"[VERBOSE]   Log file exists, reading...")
    request_total = 0
    request_2xx = 0
    path_2xx = {}
    time_2xx = 0
    req_2xx = 0
    request_4xx = 0
    request_500 = 0
    msg_500 = {}
    executed_operation = 0


    with open("specs/openapi_json/" + service_name + ".json", "r") as _f:
        spec = json.load(_f)


    # Iterate through the API specification and extract the paths
    for m in spec["paths"]:
        endpoint = m
        if len(endpoint) > 1 and endpoint[-1] == '/':
            endpoint = endpoint[:-1]
        if "{" in endpoint:
            temp = endpoint[:endpoint.find("{")]
            if temp not in msg_500:
                msg_500[temp] = []
                path_2xx[temp] = {}
        elif endpoint not in msg_500:
            msg_500[endpoint] = []
            path_2xx[endpoint] = {}

    with open(file_name, "r") as _f:
        lines = _f.readlines()

    current_path = ""
    operation = ""
    time_start = 0
    for k in range(len(lines)):
        if lines[k].strip() == "========REQUEST========":
            request_total = request_total + 1
            operation = lines[k+1].strip()
            current_path = lines[k+2].strip()
            if "?" in current_path:
                current_path = current_path[:current_path.find("?")]
        elif lines[k].strip() == "========RESPONSE========":
            status = int(lines[k+2].strip())

            if time_start == 0:
                time_start = float(lines[k+1].strip())
            if 200 <= status < 300:
                request_2xx = request_2xx + 1
                for path in path_2xx:
                    if path[-1] != '/' and path + "/" in path_2xx and path + "/" in current_path:
                        if operation not in path_2xx[path + "/"]:
                            path_2xx[path + "/"][operation] = float(lines[k+1].strip()) - time_start
                            req_2xx = request_total - 1
                    elif path in current_path:
                        if operation not in path_2xx[path]:
                            path_2xx[path][operation] = float(lines[k+1].strip()) - time_start
                            req_2xx = request_total - 1
            elif 400 <= status < 500:
                request_4xx = request_4xx + 1
            elif status == 500 or status == 502:
                # Let's store the message and check manually -- run new first and figure out supported keywords
                msg = lines[k + 3].strip()
                if "expected a valid value (" in msg:
                    msg = "expected a valid value ("
                elif "was expecting (JSON" in msg:
                    msg = "was expecting (JSON"
                elif "maybe a (non-standard)" in msg:
                    msg = "maybe a (non-standard)"
                elif "Expected space separating root-level values" in msg:
                    msg = "Expected space separating root-level values"
                elif "Unexpected close marker" in msg:
                    msg = "Unexpected close marker"
                elif "Unexpected end-of-input" in msg:
                    msg = "Unexpected end-of-input"
                elif "numeric value: expected digit (0-9)" in msg:
                    msg = "numeric value: expected digit (0-9)"
                elif "numeric value: Leading zeroes not" in msg:
                    msg = "numeric value: Leading zeroes not"
                else:
                    if "not found:" in msg:
                        msg = msg[:msg.find("not found:")]
                    if "meta" in msg:
                        msg = msg[:msg.find("meta")]
                    if "timestamp" in msg:
                        msg = msg[msg.find("status"):]
                    if "For input string" in msg:
                        msg = msg[:msg.find("For input string")]
                    if "path" in msg:
                        msg = msg[:msg.find("path")]
                    if "500," in msg:
                        msg = msg[msg.find("500,"):]
                    if "only regular" in msg:
                        msg = msg[msg.find("only regular"):]
                        msg = msg[:msg.find("at")]
                    if "numeric value:" in msg:
                        msg = msg[msg.find("numeric value:"):]
                        msg = msg[:msg.find("at")]
                    if "expected a valid value" in msg:
                        msg = msg[msg.find("expected a valid value"):]
                        msg = msg[:msg.find(")")]
                    if "was expecting" in msg:
                        msg = msg[msg.find("was expecting"):]
                        msg = msg[:msg.find(")")]
                    if "Expected " in msg:
                        msg = msg[msg.find("Expected"):]
                        msg = msg[:msg.find("at")]
                for path in msg_500:
                    if path[-1] != '/' and path + "/" in msg_500 and path + "/" in current_path:
                        if msg not in msg_500[path + "/"]:
                            print(msg)
                            msg_500[path + "/"].append(msg)
                    elif path in current_path:
                        if msg not in msg_500[path]:
                            print(msg)
                            msg_500[path].append(msg)
    for path in msg_500:
        request_500 += len(msg_500[path])
    for path in path_2xx:
        for op in path_2xx[path]:
            executed_operation += 1
            time_2xx += path_2xx[path][op]
    if executed_operation == 0:
        time_2xx = '-'
        executed_operation = '-'
    else:
        time_2xx = time_2xx / executed_operation
        req_2xx = req_2xx / executed_operation



    print(f"[VERBOSE]   Results: total={request_total}, 2xx={request_2xx}, 4xx={request_4xx}, 500={request_500}, ops={executed_operation}, time_2xx={time_2xx}, req_2xx={req_2xx}")
    return request_total, request_2xx, request_4xx, request_500, executed_operation, time_2xx, req_2xx

# Configuration: Set the base directory containing run directories
# Can be set via command-line argument or modify the default below
if len(sys.argv) > 1:
    BASE_DIR = os.path.abspath(sys.argv[1])
    print(f"[INFO] Using base directory from command line: {BASE_DIR}")
else:
    BASE_DIR = os.path.abspath(".")  # Default to current directory
    print(f"[INFO] Using default base directory (current): {BASE_DIR}")

print(f"[INFO] Starting data collection from: {BASE_DIR}")
print("=" * 80)

a = [0,0,0,0,0,0,0]
b = [0,0,0,0,0,0,0]
c = [0,0,0,0,0,0,0]
d = [0,0,0,0,0,0,0]
e = [0,0,0,0,0,0,0]
ff = [0,0,0,0,0,0,0]
g = [0,0,0,0,0,0,0]
h = [0,0,0,0,0,0,0]
l = [0,0,0,0,0,0,0]

# Find all run directories
print(f"\n[INFO] Searching for run directories...")
run_directories = find_run_directories(BASE_DIR)
if not run_directories:
    print(f"[ERROR] No run directories found in {BASE_DIR}")
    print("[ERROR] Expected directories matching pattern: run*_* (e.g., run1_20251203_114042)")
    sys.exit(1)
print(f"[INFO] Found {len(run_directories)} run directory(ies) to process")
print("=" * 80)

for idx, run_dir_name in enumerate(run_directories, 1):
    run_dir = os.path.join(BASE_DIR, run_dir_name)
    run_number = extract_run_number(run_dir_name)
    if run_number is None:
        print(f"[WARNING] Could not extract run number from {run_dir_name}, skipping...")
        continue
    
    # print(f"\n[INFO] Processing run {idx}/{len(run_directories)}: {run_dir_name} (run number: {run_number})")
    # print(f"[VERBOSE] Full path: {run_dir}")
    # print("-" * 80)
    # print(f"[INFO] Processing FDIC...")
    # log_file = os.path.join(run_dir, f"log-fdic_run{run_number}.txt")
    # t1, t2, t3, t4, t5, t6, t7 = count_requests(log_file, "fdic")
    # a[0] += t1
    # a[1] += t2
    # a[2] += t3
    # a[3] += t4
    # if t7 != 0:
    #     a[4] += t5
    #     a[5] += t6
    #     a[6] += t7
    # print(f"[INFO] FDIC aggregated: total={a[0]}, 2xx={a[1]}, 4xx={a[2]}, 500={a[3]}")
    
    print(f"\n[INFO] Processing Genome-Nexus...")
    log_file = os.path.join(run_dir, f"log-genome-nexus_run{run_number}.txt")
    t1, t2, t3, t4, t5, t6, t7 = count_requests(log_file, "genome-nexus")
    b[0] += t1
    b[1] += t2
    b[2] += t3
    b[3] += t4
    if t7 != 0:
        b[4] += t5
        b[5] += t6
        b[6] += t7
    print(f"[INFO] Genome-Nexus aggregated: total={b[0]}, 2xx={b[1]}, 4xx={b[2]}, 500={b[3]}")
    count_coverage("services/genome-nexus/", "9002", run_dir, run_number)
    # print(f"\n[INFO] Processing Language-tool...")
    # log_file = os.path.join(run_dir, f"log-language-tool_run{run_number}.txt")
    # t1, t2, t3, t4, t5, t6, t7 = count_requests(log_file, "language-tool")
    # c[0] += t1
    # c[1] += t2
    # c[2] += t3
    # c[3] += t4
    # if t7 != 0:
    #     c[4] += t5
    #     c[5] += t6
    #     c[6] += t7
    # print(f"[INFO] Language-tool aggregated: total={c[0]}, 2xx={c[1]}, 4xx={c[2]}, 500={c[3]}")
    # count_coverage("services/emb/cs/rest/original/languagetool", "9003", run_dir, run_number)
    
    # print(f"\n[INFO] Processing OCVN...")
    # log_file = os.path.join(run_dir, f"log-ocvn_run{run_number}.txt")
    # t1, t2, t3, t4, t5, t6, t7 = count_requests(log_file, "ocvn")
    # d[0] += t1
    # d[1] += t2
    # d[2] += t3
    # d[3] += t4
    # if t7 != 0:
    #     d[4] += t5
    #     d[5] += t6
    #     d[6] += t7
    # print(f"[INFO] OCVN aggregated: total={d[0]}, 2xx={d[1]}, 4xx={d[2]}, 500={d[3]}")
    # count_coverage("services/emb/cs/rest-gui/ocvn", "9004", run_dir, run_number)
    
    # print(f"\n[INFO] Processing OhSome...")
    # log_file = os.path.join(run_dir, f"log-ohsome_run{run_number}.txt")
    # t1, t2, t3, t4, t5, t6, t7 = count_requests(log_file, "ohsome")
    # e[0] += t1
    # e[1] += t2
    # e[2] += t3
    # e[3] += t4
    # if t7 != 0:
    #     e[4] += t5
    #     e[5] += t6
    #     e[6] += t7
    # print(f"[INFO] OhSome aggregated: total={e[0]}, 2xx={e[1]}, 4xx={e[2]}, 500={e[3]}")
    
    # print(f"\n[INFO] Processing OMDB...")
    # log_file = os.path.join(run_dir, f"log-omdb_run{run_number}.txt")
    # t1, t2, t3, t4, t5, t6, t7 = count_requests(log_file, "omdb")
    # ff[0] += t1
    # ff[1] += t2
    # ff[2] += t3
    # ff[3] += t4
    # if t7 != 0:
    #     ff[4] += t5
    #     ff[5] += t6
    #     ff[6] += t7
    # print(f"[INFO] OMDB aggregated: total={ff[0]}, 2xx={ff[1]}, 4xx={ff[2]}, 500={ff[3]}")
    
    # print(f"\n[INFO] Processing Rest-countries...")
    # log_file = os.path.join(run_dir, f"log-rest-countries_run{run_number}.txt")
    # t1, t2, t3, t4, t5, t6, t7 = count_requests(log_file, "rest-countries")
    # g[0] += t1
    # g[1] += t2
    # g[2] += t3
    # g[3] += t4
    # if t7 != 0:
    #     g[4] += t5
    #     g[5] += t6
    #     g[6] += t7
    # print(f"[INFO] Rest-countries aggregated: total={g[0]}, 2xx={g[1]}, 4xx={g[2]}, 500={g[3]}")
    
    # print(f"\n[INFO] Processing Spotify...")
    # log_file = os.path.join(run_dir, f"log-spotify_run{run_number}.txt")
    # t1, t2, t3, t4, t5, t6, t7 = count_requests(log_file, "spotify")
    # h[0] += t1
    # h[1] += t2
    # h[2] += t3
    # h[3] += t4
    # if t7 != 0:
    #     h[4] += t5
    #     h[5] += t6
    #     h[6] += t7
    # print(f"[INFO] Spotify aggregated: total={h[0]}, 2xx={h[1]}, 4xx={h[2]}, 500={h[3]}")
    
    # print(f"\n[INFO] Processing YouTube...")
    # log_file = os.path.join(run_dir, f"log-youtube_run{run_number}.txt")
    # t1, t2, t3, t4, t5, t6, t7 = count_requests(log_file, "youtube")
    # l[0] += t1
    # l[1] += t2
    # l[2] += t3
    # l[3] += t4
    # if t7 != 0:
    #     l[4] += t5
    #     l[5] += t6
    #     l[6] += t7
    # print(f"[INFO] YouTube aggregated: total={l[0]}, 2xx={l[1]}, 4xx={l[2]}, 500={l[3]}")
    # count_coverage("services/youtube", "9009", run_dir, run_number)
    
    print(f"[INFO] Completed processing run {run_number}")
    print("=" * 80)
print(f"\n[INFO] Starting coverage aggregation and final results compilation...")
print("=" * 80)

# FDIC results - commented out (not testing FDIC)
# res = str(a[0]) + ',' + str(a[1]) + ',' + str(a[2]) + ',' + str(a[3]) + ',' + str(a[4]) + ',' + str(a[5]) + ',' + str(a[6]) + '\n'
# print(f"[INFO] FDIC final results: {res.strip()}")
res = ""  # Start with empty string for genome-nexus only

print(f"\n[INFO] Aggregating coverage for Genome-Nexus (port 9002)...")
total_branch = 0
covered_branch = 0
total_line = 0
covered_line = 0
total_method = 0
covered_method = 0
for run_dir_name in run_directories:
    run_dir = os.path.join(BASE_DIR, run_dir_name)
    run_number = extract_run_number(run_dir_name)
    if run_number is None:
        continue
    csv_file = os.path.join(run_dir, f"jacoco9002_run{run_number}.csv")
    if os.path.exists(csv_file):
        print(f"[VERBOSE]   Reading coverage CSV: {csv_file}")
        with open(csv_file) as f:
            lines = f.readlines()
            line_count = 0
            for line in lines:
                items = line.split(",")
                if len(items) > 12 and '_COVERED' not in items[6] and '_MISSED' not in items[6]:
                    covered_branch = covered_branch + int(items[6])
                    total_branch = total_branch + int(items[6]) + int(items[5])
                    covered_line = covered_line + int(items[8])
                    total_line = total_line + int(items[8]) + int(items[7])
                    covered_method = covered_method + int(items[12])
                    total_method = total_method + int(items[12]) + int(items[11])
                    line_count += 1
            print(f"[VERBOSE]   Processed {line_count} coverage entries from {csv_file}")
    else:
        print(f"[WARNING]   Coverage CSV not found: {csv_file}")
if total_branch > 0:
    branch_cov = covered_branch / total_branch
    line_cov = covered_line / total_line
    method_cov = covered_method / total_method
    print(f"[INFO] Genome-Nexus coverage: branch={branch_cov:.4f}, line={line_cov:.4f}, method={method_cov:.4f}")
    res = res + str(b[0]) + ',' + str(b[1]) + ',' + str(b[2]) + ',' + str(b[3]) + ',' + str(b[4]) + ',' + str(b[5]) + ',' + str(b[6]) + ',' + str(branch_cov) + ',' + str(line_cov) + ',' + str(method_cov) + '\n'
else:
    print(f"[WARNING] No coverage data found for Genome-Nexus, using zeros")
    res = res + str(b[0]) + ',' + str(b[1]) + ',' + str(b[2]) + ',' + str(b[3]) + ',' + str(b[4]) + ',' + str(b[5]) + ',' + str(b[6]) + ',0,0,0\n'

# Language-tool coverage aggregation - commented out (not testing Language-tool)
# print(f"\n[INFO] Aggregating coverage for Language-tool (port 9003)...")
# total_branch = 0
# covered_branch = 0
# total_line = 0
# covered_line = 0
# total_method = 0
# covered_method = 0
# for run_dir_name in run_directories:
#     run_dir = os.path.join(BASE_DIR, run_dir_name)
#     run_number = extract_run_number(run_dir_name)
#     if run_number is None:
#         continue
#     csv_file = os.path.join(run_dir, f"jacoco9003_run{run_number}.csv")
#     if os.path.exists(csv_file):
#         print(f"[VERBOSE]   Reading coverage CSV: {csv_file}")
#         with open(csv_file) as f:
#             lines = f.readlines()
#             line_count = 0
#             for line in lines:
#                 items = line.split(",")
#                 if len(items) > 12 and '_COVERED' not in items[6] and '_MISSED' not in items[6]:
#                     covered_branch = covered_branch + int(items[6])
#                     total_branch = total_branch + int(items[6]) + int(items[5])
#                     covered_line = covered_line + int(items[8])
#                     total_line = total_line + int(items[8]) + int(items[7])
#                     covered_method = covered_method + int(items[12])
#                     total_method = total_method + int(items[12]) + int(items[11])
#                     line_count += 1
#             print(f"[VERBOSE]   Processed {line_count} coverage entries from {csv_file}")
#     else:
#         print(f"[WARNING]   Coverage CSV not found: {csv_file}")
# if total_branch > 0:
#     branch_cov = covered_branch / total_branch
#     line_cov = covered_line / total_line
#     method_cov = covered_method / total_method
#     print(f"[INFO] Language-tool coverage: branch={branch_cov:.4f}, line={line_cov:.4f}, method={method_cov:.4f}")
#     res = res + str(c[0]) + ',' + str(c[1]) + ',' + str(c[2]) + ',' + str(c[3]) + ',' + str(c[4]) + ',' + str(c[5]) + ',' + str(c[6]) + ',' + str(branch_cov) + ',' + str(line_cov) + ',' + str(method_cov) + '\n'
# else:
#     print(f"[WARNING] No coverage data found for Language-tool, using zeros")
#     res = res + str(c[0]) + ',' + str(c[1]) + ',' + str(c[2]) + ',' + str(c[3]) + ',' + str(c[4]) + ',' + str(c[5]) + ',' + str(c[6]) + ',0,0,0\n'

# OCVN coverage aggregation - commented out (not testing OCVN)
# print(f"\n[INFO] Aggregating coverage for OCVN (port 9004)...")
# total_branch = 0
# covered_branch = 0
# total_line = 0
# covered_line = 0
# total_method = 0
# covered_method = 0
# 
# for run_dir_name in run_directories:
#     run_dir = os.path.join(BASE_DIR, run_dir_name)
#     run_number = extract_run_number(run_dir_name)
#     if run_number is None:
#         continue
#     csv_file = os.path.join(run_dir, f"jacoco9004_run{run_number}.csv")
#     if os.path.exists(csv_file):
#         print(f"[VERBOSE]   Reading coverage CSV: {csv_file}")
#         with open(csv_file) as f:
#             lines = f.readlines()
#             line_count = 0
#             for line in lines:
#                 items = line.split(",")
#                 if len(items) > 12 and '_COVERED' not in items[6] and '_MISSED' not in items[6]:
#                     covered_branch = covered_branch + int(items[6])
#                     total_branch = total_branch + int(items[6]) + int(items[5])
#                     covered_line = covered_line + int(items[8])
#                     total_line = total_line + int(items[8]) + int(items[7])
#                     covered_method = covered_method + int(items[12])
#                     total_method = total_method + int(items[12]) + int(items[11])
#                     line_count += 1
#             print(f"[VERBOSE]   Processed {line_count} coverage entries from {csv_file}")
#     else:
#         print(f"[WARNING]   Coverage CSV not found: {csv_file}")
# if total_branch > 0:
#     branch_cov = covered_branch / total_branch
#     line_cov = covered_line / total_line
#     method_cov = covered_method / total_method
#     print(f"[INFO] OCVN coverage: branch={branch_cov:.4f}, line={line_cov:.4f}, method={method_cov:.4f}")
#     res = res + str(d[0]) + ',' + str(d[1]) + ',' + str(d[2]) + ',' + str(d[3]) + ',' + str(d[4]) + ',' + str(d[5]) + ',' + str(d[6]) + ',' + str(branch_cov) + ',' + str(line_cov) + ',' + str(method_cov) + '\n'
# else:
#     print(f"[WARNING] No coverage data found for OCVN, using zeros")
#     res = res + str(d[0]) + ',' + str(d[1]) + ',' + str(d[2]) + ',' + str(d[3]) + ',' + str(d[4]) + ',' + str(d[5]) + ',' + str(d[6]) + ',0,0,0\n'

# OhSome final results - commented out (not testing OhSome)
# print(f"[INFO] OhSome final results: {str(e[0])},{str(e[1])},{str(e[2])},{str(e[3])},{str(e[4])},{str(e[5])},{str(e[6])}")
# res = res + str(e[0]) + ',' + str(e[1]) + ',' + str(e[2]) + ',' + str(e[3]) + ',' + str(e[4]) + ',' + str(e[5]) + ',' + str(e[6]) + '\n'

# OMDB final results - commented out (not testing OMDB)
# print(f"[INFO] OMDB final results: {str(ff[0])},{str(ff[1])},{str(ff[2])},{str(ff[3])},{str(ff[4])},{str(ff[5])},{str(ff[6])}")
# res = res + str(ff[0]) + ',' + str(ff[1]) + ',' + str(ff[2]) + ',' + str(ff[3]) + ',' + str(ff[4]) + ',' + str(ff[5]) + ',' + str(ff[6]) + '\n'

# Rest-countries final results - commented out (not testing Rest-countries)
# print(f"[INFO] Rest-countries final results: {str(g[0])},{str(g[1])},{str(g[2])},{str(g[3])},{str(g[4])},{str(g[5])},{str(g[6])}")
# res = res + str(g[0]) + ',' + str(g[1]) + ',' + str(g[2]) + ',' + str(g[3]) + ',' + str(g[4]) + ',' + str(g[5]) + ',' + str(g[6]) + '\n'

# Spotify final results - commented out (not testing Spotify)
# print(f"[INFO] Spotify final results: {str(h[0])},{str(h[1])},{str(h[2])},{str(h[3])},{str(h[4])},{str(h[5])},{str(h[6])}")
# res = res + str(h[0]) + ',' + str(h[1]) + ',' + str(h[2]) + ',' + str(h[3]) + ',' + str(h[4]) + ',' + str(h[5]) + ',' + str(h[6]) + '\n'

# YouTube coverage aggregation - commented out (not testing YouTube)
# print(f"\n[INFO] Aggregating coverage for YouTube (port 9009)...")
# total_branch = 0
# covered_branch = 0
# total_line = 0
# covered_line = 0
# total_method = 0
# covered_method = 0
# 
# for run_dir_name in run_directories:
#     run_dir = os.path.join(BASE_DIR, run_dir_name)
#     run_number = extract_run_number(run_dir_name)
#     if run_number is None:
#         continue
#     csv_file = os.path.join(run_dir, f"jacoco9009_run{run_number}.csv")
#     if os.path.exists(csv_file):
#         print(f"[VERBOSE]   Reading coverage CSV: {csv_file}")
#         with open(csv_file) as f:
#             lines = f.readlines()
#             line_count = 0
#             for line in lines:
#                 items = line.split(",")
#                 if len(items) > 12 and '_COVERED' not in items[6] and '_MISSED' not in items[6]:
#                     covered_branch = covered_branch + int(items[6])
#                     total_branch = total_branch + int(items[6]) + int(items[5])
#                     covered_line = covered_line + int(items[8])
#                     total_line = total_line + int(items[8]) + int(items[7])
#                     covered_method = covered_method + int(items[12])
#                     total_method = total_method + int(items[12]) + int(items[11])
#                     line_count += 1
#             print(f"[VERBOSE]   Processed {line_count} coverage entries from {csv_file}")
#     else:
#         print(f"[WARNING]   Coverage CSV not found: {csv_file}")
# if total_branch > 0:
#     branch_cov = covered_branch / total_branch
#     line_cov = covered_line / total_line
#     method_cov = covered_method / total_method
#     print(f"[INFO] YouTube coverage: branch={branch_cov:.4f}, line={line_cov:.4f}, method={method_cov:.4f}")
#     res = res + str(l[0]) + ',' + str(l[1]) + ',' + str(l[2]) + ',' + str(l[3]) + ',' + str(l[4]) + ',' + str(l[5]) + ',' + str(l[6]) + ',' + str(branch_cov) + ',' + str(line_cov) + ',' + str(method_cov) + '\n'
# else:
#     print(f"[WARNING] No coverage data found for YouTube, using zeros")
#     res = res + str(l[0]) + ',' + str(l[1]) + ',' + str(l[2]) + ',' + str(l[3]) + ',' + str(l[4]) + ',' + str(l[5]) + ',' + str(l[6]) + ',0,0,0\n'

print("\n" + "=" * 80)
print("[INFO] Writing final results to res.csv...")
with open("res.csv", "w") as f:
    f.write(res)
print(f"[INFO] Results written to: {os.path.abspath('res.csv')}")
print(f"[INFO] Total lines written: {len(res.split(chr(10)))}")
print("=" * 80)
print("[INFO] Data collection completed successfully!")


