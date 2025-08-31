#!/usr/bin/env python3
"""
Docker wrapper for LlamaRestTest - simplified interface for running experiments
"""
import os
import sys
import subprocess
import argparse

def main():
    parser = argparse.ArgumentParser(description='Run LlamaRestTest experiments in Docker')
    parser.add_argument('tool', choices=[
        'arat-rl', 'arat-nlp', 'evomaster', 'resttestgen', 
        'schemathesis', 'llamaresttest', 'llamaresttest-ipd', 
        'llamaresttest-ex', 'tcases'
    ], help='Tool to run')
    parser.add_argument('service', choices=[
        'fdic', 'genome-nexus', 'language-tool', 'ocvn', 
        'ohsome', 'omdb', 'rest-countries', 'spotify', 'youtube'
    ], help='Service to test')
    parser.add_argument('--models-dir', default='./models', 
                       help='Directory containing LlamaREST models (default: ./models)')
    parser.add_argument('--results-dir', default='./results',
                       help='Directory to store results (default: ./results)')
    parser.add_argument('--build', action='store_true',
                       help='Force rebuild of Docker image')
    
    args = parser.parse_args()
    
    # Create directories if they don't exist
    os.makedirs(args.models_dir, exist_ok=True)
    os.makedirs(args.results_dir, exist_ok=True)
    
    # Check if models exist for llama tools
    if 'llama' in args.tool:
        model_files = [f for f in os.listdir(args.models_dir) if f.endswith('.gguf')]
        if not model_files:
            print(f"Warning: No .gguf model files found in {args.models_dir}")
            print("Please download LlamaREST models and place them in the models directory")
    
    # Build image if requested or if it doesn't exist
    if args.build:
        print("Building Docker image...")
        subprocess.run(['docker-compose', 'build'], check=True)
    
    # Start services
    print("Starting services...")
    subprocess.run(['docker-compose', 'up', '-d'], check=True)
    
    # Run the experiment
    print(f"Running {args.tool} on {args.service}...")
    cmd = [
        'docker', 'exec', 'llamaresttest',
        'bash', '-c', 
        f'source venv/bin/activate && python3 run.py {args.tool} {args.service}'
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("Experiment completed successfully!")
        print(f"Results should be available in {args.results_dir}")
    except subprocess.CalledProcessError as e:
        print(f"Experiment failed with exit code {e.returncode}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nExperiment interrupted by user")
        sys.exit(1)
    finally:
        # Collect results
        print("Collecting results...")
        subprocess.run([
            'docker', 'exec', 'llamaresttest',
            'bash', '-c', 'source venv/bin/activate && python3 collect.py'
        ])

if __name__ == '__main__':
    main()