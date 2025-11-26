import docker
import os
import sys

DOCKER_CLIENT = docker.from_env()
DOCKER_PREFIX = "llamaresttest-"

def get_apis():
    """Get list of available APIs with Dockerfiles"""
    apis_dir = './apis'
    if not os.path.exists(apis_dir):
        print(f"ERROR: {apis_dir} directory not found")
        return []
    apis = [d for d in os.listdir(apis_dir) 
            if os.path.isdir(os.path.join(apis_dir, d)) 
            and os.path.exists(os.path.join(apis_dir, d, 'Dockerfile'))
            and d != 'CUSTOM-API']
    return apis

def get_tools():
    """Get list of available tools with Dockerfiles"""
    return ['llamaresttest']

def build_image(name, path, is_api=True):
    """Build a Docker image"""
    image_name = f"{DOCKER_PREFIX}{name}"
    print(f"\n{'='*60}")
    print(f"Building {'API' if is_api else 'Tool'}: {name}")
    print(f"Image name: {image_name}")
    print(f"Context: {path}")
    print(f"{'='*60}\n")
    
    try:
        # Build the image
        image, build_logs = DOCKER_CLIENT.images.build(
            path=path,
            tag=image_name,
            rm=True,
            forcerm=True
        )
        
        # Print build logs
        for log in build_logs:
            if 'stream' in log:
                print(log['stream'], end='')
            elif 'error' in log:
                print(f"ERROR: {log['error']}")
                return False
        
        print(f"\n✓ Successfully built {image_name}\n")
        return True
        
    except Exception as e:
        print(f"\n✗ Failed to build {image_name}")
        print(f"Error: {e}\n")
        return False

def main():
    print("="*60)
    print("LlamaRestTest Docker Image Builder")
    print("="*60)
    print()
    
    # Check if we're in the right directory
    if not os.path.exists('./apis') or not os.path.exists('./tools'):
        print("ERROR: Please run this script from the LlamaRestTest root directory")
        print("Expected structure:")
        print("  ./apis/      - API service Dockerfiles")
        print("  ./tools/     - Tool Dockerfiles")
        sys.exit(1)
    
    # Check if infrastructure exists
    if not os.path.exists('./infrastructure'):
        print("ERROR: ./infrastructure directory not found")
        print("Please copy infrastructure from deeprest-artifact:")
        print("  cp -r ../deeprest-artifact/infrastructure .")
        sys.exit(1)
    
    # Get lists
    apis = get_apis()
    tools = get_tools()
    
    print(f"Found {len(apis)} APIs to build:")
    for api in apis:
        print(f"  - {api}")
    print()
    
    print(f"Found {len(tools)} tools to build:")
    for tool in tools:
        print(f"  - {tool}")
    print()
    
    # Ask what to build
    print("What would you like to build?")
    print("  [1] All images (APIs + Tools)")
    print("  [2] APIs only")
    print("  [3] Tools only")
    print("  [4] Specific API")
    print("  [5] Specific Tool")
    
    try:
        choice = input("\nEnter choice [1-5]: ").strip()
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(0)
    
    success_count = 0
    fail_count = 0
    
    if choice == '1':
        # Build all APIs
        print("\n" + "="*60)
        print("Building all APIs...")
        print("="*60)
        for api in apis:
            if build_image(api, '.', is_api=True):
                success_count += 1
            else:
                fail_count += 1
        
        # Build all tools
        print("\n" + "="*60)
        print("Building all tools...")
        print("="*60)
        for tool in tools:
            if build_image(tool, '.', is_api=False):
                success_count += 1
            else:
                fail_count += 1
    
    elif choice == '2':
        # Build APIs only
        print("\n" + "="*60)
        print("Building all APIs...")
        print("="*60)
        for api in apis:
            if build_image(api, '.', is_api=True):
                success_count += 1
            else:
                fail_count += 1
    
    elif choice == '3':
        # Build tools only
        print("\n" + "="*60)
        print("Building all tools...")
        print("="*60)
        for tool in tools:
            if build_image(tool, '.', is_api=False):
                success_count += 1
            else:
                fail_count += 1
    
    elif choice == '4':
        # Build specific API
        print("\nAvailable APIs:")
        for i, api in enumerate(apis, 1):
            print(f"  [{i}] {api}")
        try:
            api_choice = int(input("\nEnter API number: ").strip())
            if 1 <= api_choice <= len(apis):
                api = apis[api_choice - 1]
                if build_image(api, '.', is_api=True):
                    success_count += 1
                else:
                    fail_count += 1
            else:
                print("Invalid choice")
                sys.exit(1)
        except (ValueError, KeyboardInterrupt):
            print("\nCancelled.")
            sys.exit(0)
    
    elif choice == '5':
        # Build specific tool
        print("\nAvailable tools:")
        for i, tool in enumerate(tools, 1):
            print(f"  [{i}] {tool}")
        try:
            tool_choice = int(input("\nEnter tool number: ").strip())
            if 1 <= tool_choice <= len(tools):
                tool = tools[tool_choice - 1]
                if build_image(tool, '.', is_api=False):
                    success_count += 1
                else:
                    fail_count += 1
            else:
                print("Invalid choice")
                sys.exit(1)
        except (ValueError, KeyboardInterrupt):
            print("\nCancelled.")
            sys.exit(0)
    
    else:
        print("Invalid choice")
        sys.exit(1)
    
    # Summary
    print("\n" + "="*60)
    print("Build Summary")
    print("="*60)
    print(f"✓ Successful: {success_count}")
    print(f"✗ Failed: {fail_count}")
    print(f"Total: {success_count + fail_count}")
    print("="*60)
    
    if fail_count > 0:
        print("\nSome images failed to build. Please check the errors above.")
        sys.exit(1)
    else:
        print("\nAll images built successfully!")
        print("You can now run experiments with: python3 run_parallel.py")

if __name__ == "__main__":
    main()

