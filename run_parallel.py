#!/usr/bin/env python3
"""
LlamaRestTest Parallel Experiment Runner
Designed for Ubuntu/GCP VMs
"""

import docker
import socket
import random
import threading
import time
import psutil
import sys
import os

DOCKER_PREFIX = "llamaresttest-"

# Initialize Docker client for Ubuntu/Linux
_docker_client = None

def get_docker_client():
    """Get Docker client, handling Linux Docker daemon connection"""
    global _docker_client
    if _docker_client is None:
        try:
            # On Ubuntu/Linux, Docker daemon runs as a service
            # User should be in docker group or use sudo
            _docker_client = docker.from_env()
            # Test connection
            _docker_client.ping()
        except docker.errors.DockerException as e:
            print(f"ERROR: Failed to connect to Docker daemon: {e}")
            print("Make sure:")
            print("  1. Docker daemon is running: sudo systemctl status docker")
            print("  2. Your user is in the docker group: sudo usermod -aG docker $USER")
            print("  3. Or run with sudo: sudo python3 run_parallel.py")
            sys.exit(1)
        except Exception as e:
            print(f"ERROR: Unexpected error connecting to Docker: {e}")
            sys.exit(1)
    return _docker_client

# Check if a TCP port is free
def check_tcp_port(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return not s.connect_ex(('localhost', port)) == 0
    
# Get random free TCP port
def get_random_free_tcp_port():
    remaining_attempts = 1000
    while remaining_attempts > 0:
        candidate_port = random.randrange(10_000, 60_000)
        if check_tcp_port(candidate_port):
            return candidate_port
        remaining_attempts -= 1
    print("ERROR: could not find a free TCP port for the API.")
    sys.exit(1)

# Get available APIs (services)
def get_apis():
    # Use absolute path based on script location or current working directory
    script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
    apis_dir = os.path.join(script_dir, 'apis')
    if not os.path.exists(apis_dir):
        # Fallback to relative path
        apis_dir = './apis'
        if not os.path.exists(apis_dir):
            print(f"ERROR: {apis_dir} directory not found")
            print(f"Current working directory: {os.getcwd()}")
            return []
    apis = [d for d in os.listdir(apis_dir) 
            if os.path.isdir(os.path.join(apis_dir, d)) 
            and os.path.exists(os.path.join(apis_dir, d, 'Dockerfile'))
            and d != 'CUSTOM-API']
    return apis

# Get available tools
def get_tools():
    return ['llamaresttest']  # Only LlamaRestTest for now

# Compute the remaining runs to execute
def compute_remaining_runs(desired_runs):
    remaining_runs = []
    apis = get_apis()
    tools = get_tools()
    for api in apis:
        for tool in tools:
            try:
                base_dir = f"./results/{api}/{tool}"
                subdirs = os.listdir(base_dir)
                count = 0
                for subdir in subdirs:
                    if os.path.exists(f"{base_dir}/{subdir}/completed.txt"):
                        count += 1
                while count < desired_runs:
                    remaining_runs.append({'api': api, 'tool': tool})
                    count += 1
            except:
                for _ in range(desired_runs):
                    remaining_runs.append({'api': api, 'tool': tool})
    return remaining_runs

# Verify Docker images have been built
def check_docker_images(remaining_runs):
    images = set()
    missing_images = []
    for remaining_run in remaining_runs:
        images.add(remaining_run['tool'])
        images.add(remaining_run['api'])
    client = get_docker_client()
    for image in images:
        try:
            client.images.get(DOCKER_PREFIX+image)
        except:
            missing_images.append(image)
    return missing_images

# Filter out runs with missing images
def filter_runs_with_missing_images(remaining_runs, missing_images):
    filtered_remaining_runs = []
    for remaining_run in remaining_runs:
        if remaining_run['tool'] not in missing_images and remaining_run['api'] not in missing_images:
            filtered_remaining_runs.append(remaining_run)
    return filtered_remaining_runs

# Resource requirements for GCP VMs
# Each run needs: 16 CPUs (8 for API + 8 for tool) and 32GB RAM (16GB for API + 16GB for tool)
REQUIRED_RAM = 32 * 1024 * 1024 * 1024      # 32GB per run (16GB API + 16GB tool)
REQUIRED_CPUS = 14  # Need 14 free CPUs before launching (16 will be allocated: 8 API + 8 tool)
CONTAINER_RAM = "16g"  # 16GB per container
CONTAINER_CPUS = 8_000_000_000  # 8 CPUs per container (8 billion nanoseconds = 8 CPUs)

def check_resources(verbose=False):
    available_ram = getattr(psutil.virtual_memory(), 'available')
    total_ram = psutil.virtual_memory().total
    used_ram = total_ram - available_ram
    cpu_percent = psutil.cpu_percent(interval=0.1)
    available_cpus = (1 - (cpu_percent / 100)) * psutil.cpu_count()
    total_cpus = psutil.cpu_count()
    
    if verbose:
        print(f"   [RESOURCE CHECK] RAM: {available_ram / (1024**3):.1f}GB available / {total_ram / (1024**3):.1f}GB total (need {REQUIRED_RAM / (1024**3):.1f}GB)")
        print(f"   [RESOURCE CHECK] CPU: {available_cpus:.1f} available / {total_cpus} total (need {REQUIRED_CPUS:.1f}, using {cpu_percent:.1f}%)")
    
    ram_ok = available_ram > REQUIRED_RAM
    cpu_ok = available_cpus > REQUIRED_CPUS
    
    if verbose and not ram_ok:
        print(f"   [RESOURCE CHECK] ⚠️  RAM insufficient: need {REQUIRED_RAM / (1024**3):.1f}GB, have {available_ram / (1024**3):.1f}GB")
    if verbose and not cpu_ok:
        print(f"   [RESOURCE CHECK] ⚠️  CPU insufficient: need {REQUIRED_CPUS:.1f}, have {available_cpus:.1f}")
    
    return ram_ok and cpu_ok

# Deeper check of resources (10 checks each second)
def deep_check_resources(verbose=False):
    if verbose:
        print(f"   [RESOURCE CHECK] Performing deep resource check (10 samples over 10 seconds)...")
    for i in range(10):
        if check_resources(verbose=(verbose and i == 0)) == False:
            if verbose and i > 0:
                print(f"   [RESOURCE CHECK] Resources insufficient after {i+1} checks")
            return False
        if verbose and i < 9:
            print(f"   [RESOURCE CHECK] Check {i+1}/10 passed, waiting...")
        time.sleep(1)
    if verbose:
        print(f"   [RESOURCE CHECK] ✓ All 10 checks passed - resources available")
    return True

# Execute an experiment run
def launch_run(api, tool, run_count, total_runs):

    attempts = 3
    successfully_completed = False

    while attempts > 0 and not successfully_completed:

        attempts -= 1
        error_occurred = False
        run = 'run-' + time.strftime('%Y%m%d-%H%M%S')
        script_dir = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.getcwd()
        results_path = os.path.join(script_dir, 'results', api, tool, run)
        ports = {'9090/tcp': get_random_free_tcp_port()}
        env = {
            'API': api,
            'TOOL': tool,
            'RUN': run,
            'PORT': ports['9090/tcp']
        }

        os.makedirs(results_path, exist_ok=True, mode=0o777)

        message = 'START' if attempts == 2 else 'RETRY'

        print(f" => [{message}] ({run_count}/{total_runs}) Running {tool} on {api} ({run}) with API on port {ports['9090/tcp']}.")
        with open(f'{results_path}/started.txt', 'a') as f:
            f.write(f'Run started on {time.ctime()}.\n')

        api_container_name = f'{api}_for_{tool}_{run}'
        tool_container_name = f'{tool}_for_{api}_{run}'

        # Verify Docker images have been built
        print(f"   [VERIFY] Checking Docker images...")
        client = get_docker_client()
        try:
            api_image = client.images.get(DOCKER_PREFIX+api)
            tool_image = client.images.get(DOCKER_PREFIX+tool)
            print(f"   [VERIFY] ✓ Found image: {DOCKER_PREFIX}{api} (ID: {api_image.id[:12]})")
            print(f"   [VERIFY] ✓ Found image: {DOCKER_PREFIX}{tool} (ID: {tool_image.id[:12]})")
        except Exception as e:
            print(f" => [ERROR] ({run_count}/{total_runs}) Execution failed for {tool} on {api}. Missing Docker image(s).")
            print(f"   [ERROR] Details: {e}")
            print(f"   [ERROR] Have you built the images? Run: python3 build.py")
            with open(f'{results_path}/errors.txt', 'a') as f:
                f.write(f"Docker image(s) not found for API ({api}) or tool ({tool}).\n{e}\n\n")
            error_occurred = True

        # Start API
        if not error_occurred:
            print(f"   [CONTAINER] Starting API container: {api_container_name}")
            print(f"   [CONTAINER]   Image: {DOCKER_PREFIX}{api}")
            print(f"   [CONTAINER]   Port: {ports['9090/tcp']}")
            print(f"   [CONTAINER]   Resources: {CONTAINER_RAM} RAM, {CONTAINER_CPUS / 1_000_000_000} CPUs")
            try:
                client = get_docker_client()
                results_base = os.path.join(script_dir, 'results')
                api_container = client.containers.run(
                    image=f'{DOCKER_PREFIX}{api}',
                    name=api_container_name,
                    remove=True,
                    environment=env,
                    ports=ports,
                    volumes=[f'{results_base}:/results/'],
                    mem_limit=CONTAINER_RAM,
                    nano_cpus=CONTAINER_CPUS,
                    user='root',
                    detach=True
                    )
                print(f"   [CONTAINER] ✓ API container started (ID: {api_container.id[:12]})")
            except Exception as e:
                print(f"   [CONTAINER] ✗ Failed to start API container: {e}")
                with open(f'{results_path}/errors.txt', 'a') as f:
                    f.write(f"Could not start API ({api}) container.\n{e}\n\n")
                error_occurred = True
        
        # Wait 45 seconds for the API to start
        if not error_occurred:
            print(f"   [WAIT] Waiting 45 seconds for API to initialize...")
            for i in range(9):
                time.sleep(5)
                # Check if container is still running
                try:
                    api_container.reload()
                    status = api_container.status
                    print(f"   [WAIT] {5*(i+1)}s elapsed, API container status: {status}")
                except:
                    print(f"   [WAIT] {5*(i+1)}s elapsed, checking container...")
            print(f"   [WAIT] ✓ API initialization wait complete")
        else:
            time.sleep(2)
        
        # Start tool
        if not error_occurred:
            print(f"   [CONTAINER] Starting tool container: {tool_container_name}")
            print(f"   [CONTAINER]   Image: {DOCKER_PREFIX}{tool}")
            print(f"   [CONTAINER]   Resources: {CONTAINER_RAM} RAM, {CONTAINER_CPUS / 1_000_000_000} CPUs")
            print(f"   [CONTAINER]   Network: host mode")
            try:
                client = get_docker_client()
                tool_container = client.containers.run(
                    image=f'{DOCKER_PREFIX}{tool}',
                    name=tool_container_name,
                    remove=True,
                    environment=env,
                    privileged=True,
                    network_mode='host',
                    mem_limit=CONTAINER_RAM,
                    nano_cpus=CONTAINER_CPUS,
                    detach=True
                    )
                print(f"   [CONTAINER] ✓ Tool container started (ID: {tool_container.id[:12]})")
                time.sleep(1)
            except Exception as e:
                print(f"   [CONTAINER] ✗ Failed to start tool container: {e}")
                print(f"   [CONTAINER] Stopping API container...")
                api_container.stop()
                with open(f'{results_path}/errors.txt', 'a') as f:
                    f.write(f"Could not start tool ({tool}) container.\n{e}\n\n")
                error_occurred = True


        # Perform a health check of containers each minute, for 10 times (10-minute experiment)
        if not error_occurred:
            print(f"   [MONITOR] Starting 10-minute experiment monitoring (health checks every minute)...")
            for minute in range(1, 11):
                time.sleep(60)
                print(f"   [MONITOR] Minute {minute}/10: Checking container health...")
                try:
                    api_container.reload()
                    api_status = api_container.status
                    print(f"   [MONITOR]   API container status: {api_status}")
                    if api_status == 'exited':
                        raise Exception("Container exited")
                # If the container was removed or it exited
                except Exception as e:
                    print(f" => [ERROR] ({run_count}/{total_runs}) API container stopped at minute {minute}.")
                    print(f"   [ERROR] Details: {e}")
                    with open(f'{results_path}/errors.txt', 'a') as f:
                        f.write(f"API container not running at minute {minute}. Aborting.\n{e}\n\n")
                    try:
                        print(f"   [CLEANUP] Stopping tool container...")
                        tool_container.stop()
                    except:
                        pass
                    error_occurred = True
                    break
                try:
                    tool_container.reload()
                    tool_status = tool_container.status
                    print(f"   [MONITOR]   Tool container status: {tool_status}")
                    if tool_status == 'exited':
                        raise Exception("Container exited")
                # If the container was removed or it exited
                except Exception as e:
                    print(f" => [ERROR] ({run_count}/{total_runs}) Tool container stopped at minute {minute}.")
                    print(f"   [ERROR] Details: {e}")
                    with open(f'{results_path}/errors.txt', 'a') as f:
                        f.write(f"Tool container not running at minute {minute}. Aborting.\n{e}\n\n")
                    try:
                        print(f"   [CLEANUP] Stopping API container...")
                        api_container.stop()
                    except:
                        pass
                    error_occurred = True
                    break
                if minute % 5 == 0:
                    print(f"   [MONITOR] ✓ {minute}/10 minutes completed, containers running normally")
        
        # Stop tool container
        if not error_occurred:
            print(f"   [CLEANUP] Stopping tool container...")
            try:
                tool_container.stop()
                print(f"   [CLEANUP] ✓ Tool container stopped")
            except Exception as e:
                print(f"   [CLEANUP] ✗ Error stopping tool container: {e}")
                error_occurred = True
                with open(f'{results_path}/errors.txt', 'a') as f:
                    f.write(f'Could not stop tool ({tool}) container. It possibly crashed.\n{e}\n\n')
                try:
                    api_container.stop()
                except:
                    pass
        
        # Wait 5 seconds to let the API container store the database
        if not error_occurred:
            print(f"   [CLEANUP] Waiting 5 seconds for API to finalize database operations...")
            time.sleep(5)

        # Stop API container
        if not error_occurred:
            print(f"   [CLEANUP] Stopping API container...")
            try:
                api_container.stop()
                print(f"   [CLEANUP] ✓ API container stopped")
            except Exception as e:
                print(f"   [CLEANUP] ✗ Error stopping API container: {e}")
                error_occurred = True
                with open(f'{results_path}/errors.txt', 'a') as f:
                    f.write(f'Could not stop API ({api}) container. It possibly crashed.\n{e}\n\n')

        # Final stages
        if not error_occurred:
            successfully_completed = True
            with open(f'{results_path}/completed.txt', 'a') as f:
                f.write(f'Run completed on {time.ctime()}.\n')
            print(f" => [-END-] ({run_count}/{total_runs}) Run of {tool} on {api} ({run}) completed successfully.")
            print(f"   [RESULTS] Results saved to: {results_path}")
        else:
            time.sleep(2)
            if attempts == 0:
                print(f" => [ERROR] ({run_count}/{total_runs}) Run of {tool} on {api} ({run}) terminated with errors.")
                print(f"   [ERROR] Check error logs in: {results_path}/errors.txt")

# Main
if __name__ == "__main__":
    print("=" * 60)
    print("LlamaRestTest Parallel Experiment Runner")
    print("=" * 60)
    print("Designed for Ubuntu/GCP VMs")
    print("=" * 60)
    
    # Check Docker connection first
    print("[SETUP] Checking Docker connection...")
    try:
        get_docker_client()
        print("[SETUP] ✓ Docker daemon connected")
    except SystemExit:
        sys.exit(1)
    
    print(f"\nSystem resources: {psutil.cpu_count()} CPUs, {psutil.virtual_memory().total / (1024**3):.1f}GB RAM")
    print(f"Resource requirements per run: {REQUIRED_RAM / (1024**3):.1f}GB RAM, {REQUIRED_CPUS} CPUs")
    print(f"Container limits: {CONTAINER_RAM} RAM, {CONTAINER_CPUS / 1_000_000_000} CPUs each")
    print()
    
    # Get number of runs - can be from stdin (piped) or interactive input
    try:
        if not sys.stdin.isatty():
            # Input is piped (e.g., from startup script)
            line = sys.stdin.readline().strip()
            if line:
                desired_runs = int(line)
            else:
                print("ERROR: No input provided. Expected number of runs.")
                sys.exit(1)
        else:
            # Interactive input
            desired_runs = int(input("How many runs per API/tool combination? [1-20]: "))
    except ValueError:
        print("ERROR: Please specify a valid whole number.")
        sys.exit(1)
    except EOFError:
        print("ERROR: No input provided. Expected number of runs.")
        sys.exit(1)
    
    if desired_runs < 1 or desired_runs > 20:
        print(f"ERROR: Number of runs must be in the range 1-20, got {desired_runs}.")
        sys.exit(1)
    
    print(f"[SETUP] Configured for {desired_runs} run(s) per API/tool combination")
    
    print(f"[SETUP] Computing remaining runs...")
    remaining_runs = compute_remaining_runs(desired_runs)
    
    # Uncomment next line to launch a manual subset of runs
    #remaining_runs = [{'api': 'blog', 'tool': 'llamaresttest'}]
    
    print(f"[SETUP] Checking Docker images for {len(remaining_runs)} runs...")
    missing_images = check_docker_images(remaining_runs)
    if len(missing_images) > 0:
        filtered_remaining_runs = filter_runs_with_missing_images(remaining_runs, missing_images)
        print(f"[SETUP] ⚠️  Some Docker images required for the experiment have not been built.")
        print(f"[SETUP] Missing images: {', '.join(missing_images)}")
        print(f"[SETUP] Skipping experiment runs that involve these images.")
        print(f"[SETUP] Only {len(filtered_remaining_runs)} out of {len(remaining_runs)} runs can be launched.")
        remaining_runs = filtered_remaining_runs
    else:
        print(f"[SETUP] ✓ All required Docker images found")
        print(f"[SETUP] Runs planned for execution: {len(remaining_runs)}.")

    total_runs = len(remaining_runs)
    run_count = 0
    
    # Only prompt for confirmation if running interactively
    if sys.stdin.isatty():
        try:
            input("Press ENTER to start the execution of the experiment (or CTRL+C to cancel)...")
        except (EOFError, KeyboardInterrupt):
            print("\nCancelled by user.")
            sys.exit(0)
    else:
        print("[SETUP] Non-interactive mode: starting experiments automatically...")

    while len(remaining_runs) > 0:

        run_count += 1

        # Pick random run
        remaining_run = remaining_runs.pop(random.randrange(len(remaining_runs)))
        print(f"\n[LAUNCH] Preparing to launch run {run_count}/{total_runs}: {remaining_run['tool']} on {remaining_run['api']}")

        # Stop until resources are available
        notify_no_resources = True
        wait_count = 0
        while not deep_check_resources(verbose=(wait_count == 0)):
            if notify_no_resources:
                print(f" => [-WAIT] ({run_count}/{total_runs}) Waiting for system resources to be released...")
                print(f"   [WAIT] Checking current resource availability...")
                check_resources(verbose=True)
                notify_no_resources = False
            wait_count += 1
            if wait_count % 2 == 0:  # Every 60 seconds, show status
                print(f"   [WAIT] Still waiting... ({wait_count * 30}s elapsed)")
                check_resources(verbose=True)
            time.sleep(30)
        
        if wait_count > 0:
            print(f"   [WAIT] ✓ Resources available after {wait_count * 30} seconds")
        
        print(f"[LAUNCH] Starting run {run_count}/{total_runs}...")

        # Launch run in separate thread
        run_thread = threading.Thread(
            target=launch_run,
            args=(remaining_run['api'], remaining_run['tool'], run_count, total_runs)
            )
        run_thread.start()

        # If not last run, wait 60 seconds before launching next
        if len(remaining_runs) > 0:
            time.sleep(60)
    
    print()
    print("=" * 60)
    print("[SUMMARY] All runs have been launched!")
    print(f"[SUMMARY] Total runs launched: {total_runs}")
    print(f"[SUMMARY] Waiting for completion...")
    print(f"[SUMMARY] Monitor progress in: ./results/")
    print(f"[SUMMARY] Each run will create a directory: ./results/<api>/<tool>/run-<timestamp>/")
    print("=" * 60)

