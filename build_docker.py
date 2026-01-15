#!/usr/bin/env python3
"""
Build script for Headless Music Player Docker image.
- Builds frontend (npm install + npm run build)
- Copies assets to backend
- Creates Docker image
- Optionally deploys (stops old container, runs new, cleans old images)
"""

import subprocess
import shutil
import sys
from pathlib import Path

# Configuration
PROJECT_ROOT = Path(__file__).parent
FRONTEND_DIR = PROJECT_ROOT / "frontend"
BACKEND_DIR = PROJECT_ROOT / "backend"
DOCKER_IMAGE_NAME = "headless-music-player"
DOCKER_TAG = "latest"
CONTAINER_NAME = "music-player"

# Persistent data directories (created alongside the script)
DATA_DIRS = {
    "music": PROJECT_ROOT / "music",        # Music files
    "config": PROJECT_ROOT / "config",      # State/settings persistence
    "cache": PROJECT_ROOT / "cache",        # Cover art cache
    "playlists": PROJECT_ROOT / "playlists" # User playlists
}


def run_command(cmd, cwd=None, description="", capture=False):
    """Run a shell command and handle errors."""
    print(f"\n{'='*50}")
    print(f"▶ {description}")
    print(f"  Command: {' '.join(cmd)}")
    print(f"{'='*50}")
    
    if capture:
        result = subprocess.run(
            cmd, cwd=cwd, 
            shell=True if sys.platform == "win32" else False,
            capture_output=True, text=True
        )
    else:
        result = subprocess.run(cmd, cwd=cwd, shell=True if sys.platform == "win32" else False)
    
    if result.returncode != 0 and not capture:
        print(f"✗ Failed: {description}")
        sys.exit(1)
    
    print(f"✓ Complete: {description}")
    return result


def ensure_data_dirs():
    """Create all persistent data directories if they don't exist."""
    print("\n📂 Ensuring data directories exist...")
    paths = {}
    for name, path in DATA_DIRS.items():
        path.mkdir(exist_ok=True)
        abs_path = path.resolve()
        paths[name] = abs_path
        print(f"  ✓ {name}: {abs_path}")
    return paths


def build_frontend():
    """Build the frontend with npm."""
    print("\n📦 Building Frontend...")
    
    # npm install
    run_command(
        ["npm", "install"],
        cwd=FRONTEND_DIR,
        description="Installing npm dependencies"
    )
    
    # npm run build
    run_command(
        ["npm", "run", "build"],
        cwd=FRONTEND_DIR,
        description="Building frontend (Vite)"
    )


def copy_assets():
    """Copy built frontend assets to backend."""
    print("\n📁 Copying Assets to Backend...")
    
    src_dist = FRONTEND_DIR / "dist"
    dest_assets = BACKEND_DIR / "assets"
    dest_templates = BACKEND_DIR / "templates"
    
    # Ensure source exists
    if not src_dist.exists():
        print(f"✗ Build output not found at {src_dist}")
        sys.exit(1)
    
    # Clean and copy assets folder
    if dest_assets.exists():
        shutil.rmtree(dest_assets)
    shutil.copytree(src_dist / "assets", dest_assets / "assets")
    print(f"  ✓ Copied assets to {dest_assets}")
    
    # Copy index.html to templates
    dest_templates.mkdir(exist_ok=True)
    shutil.copy(src_dist / "index.html", dest_templates / "index.html")
    print(f"  ✓ Copied index.html to {dest_templates}")


def build_docker():
    """Build the Docker image."""
    print("\n🐳 Building Docker Image...")
    
    run_command(
        ["docker", "build", "-t", f"{DOCKER_IMAGE_NAME}:{DOCKER_TAG}", "."],
        cwd=PROJECT_ROOT,
        description=f"Building Docker image: {DOCKER_IMAGE_NAME}:{DOCKER_TAG}"
    )


def stop_old_container():
    """Stop and remove the old container if running."""
    print("\n🛑 Stopping old container...")
    
    # Check if container exists
    result = subprocess.run(
        ["docker", "ps", "-a", "-q", "-f", f"name={CONTAINER_NAME}"],
        capture_output=True, text=True
    )
    
    if result.stdout.strip():
        # Stop container
        subprocess.run(["docker", "stop", CONTAINER_NAME], capture_output=True)
        print(f"  ✓ Stopped container: {CONTAINER_NAME}")
        
        # Remove container
        subprocess.run(["docker", "rm", CONTAINER_NAME], capture_output=True)
        print(f"  ✓ Removed container: {CONTAINER_NAME}")
    else:
        print(f"  ℹ No existing container named '{CONTAINER_NAME}' found")


def cleanup_old_images():
    """Remove old/dangling images to free up space on RPi."""
    print("\n🧹 Cleaning up old Docker images...")
    
    # Remove dangling images (old builds replaced by new :latest)
    result = subprocess.run(
        ["docker", "images", "-q", "-f", "dangling=true"],
        capture_output=True, text=True
    )
    
    if result.stdout.strip():
        dangling_ids = result.stdout.strip().split('\n')
        for img_id in dangling_ids:
            subprocess.run(["docker", "rmi", img_id], capture_output=True)
        print(f"  ✓ Removed {len(dangling_ids)} dangling image(s)")
    else:
        print("  ℹ No dangling images to remove")
    
    # Also prune unused build cache
    subprocess.run(["docker", "builder", "prune", "-f"], capture_output=True)
    print("  ✓ Pruned build cache")


def deploy_container(paths):
    """Deploy the new container with all volume mounts."""
    print("\n🚀 Deploying new container...")
    
    cmd = [
        "docker", "run", "-d",
        "--name", CONTAINER_NAME,
        "--restart", "unless-stopped",
        "--device", "/dev/snd",
        "--group-add", "audio",
        "-e", "SDL_AUDIODRIVER=alsa",
        # Volume mounts for persistence
        "-v", f"{paths['music']}:/app/music",
        "-v", f"{paths['config']}:/app/config",
        "-v", f"{paths['cache']}:/app/cache",
        "-v", f"{paths['playlists']}:/app/playlists",
        "-p", "8000:8000",
        f"{DOCKER_IMAGE_NAME}:{DOCKER_TAG}"
    ]
    
    run_command(cmd, description=f"Starting container: {CONTAINER_NAME}")
    
    print(f"\n  📂 Mounted volumes:")
    print(f"     🎵 Music:     {paths['music']} → /app/music")
    print(f"     ⚙️  Config:    {paths['config']} → /app/config")
    print(f"     🖼️  Cache:     {paths['cache']} → /app/cache")
    print(f"     📋 Playlists: {paths['playlists']} → /app/playlists")
    print(f"\n  🌐 Access at: http://<raspberry-pi-ip>:8000")


def main():
    print("=" * 60)
    print("🎵 Headless Music Player - Docker Build Script")
    print("=" * 60)
    
    # Ensure all data directories exist
    paths = ensure_data_dirs()
    
    # Step 1: Build frontend
    build_frontend()
    
    # Step 2: Copy assets
    copy_assets()
    
    # Step 3: Build Docker image
    build_docker()
    
    print("\n" + "=" * 60)
    print("✅ Build Complete!")
    print("=" * 60)
    
    # Ask user if they want to deploy
    print("\n" + "-" * 60)
    response = input("🚀 Do you want to deploy now? (y/n): ").strip().lower()
    
    if response == 'y' or response == 'yes':
        # Stop old container
        stop_old_container()
        
        # Clean up old images to save space
        cleanup_old_images()
        
        # Deploy new container
        deploy_container(paths)
        
        print("\n" + "=" * 60)
        print("✅ Deployment Complete!")
        print("=" * 60)
        print("\n📝 State (volume, repeat mode, queue) will persist across restarts.")
    else:
        print("\n⏭ Skipping deployment.")
        print(f"\nTo deploy manually:")
        print(f"  docker run -d \\")
        print(f"    --name {CONTAINER_NAME} \\")
        print(f"    --restart unless-stopped \\")
        print(f"    --device /dev/snd \\")
        print(f"    --group-add audio \\")
        print(f"    -e SDL_AUDIODRIVER=alsa \\")
        print(f"    -v {paths['music']}:/app/music \\")
        print(f"    -v {paths['config']}:/app/config \\")
        print(f"    -v {paths['cache']}:/app/cache \\")
        print(f"    -v {paths['playlists']}:/app/playlists \\")
        print(f"    -p 8000:8000 \\")
        print(f"    {DOCKER_IMAGE_NAME}:{DOCKER_TAG}")


if __name__ == "__main__":
    main()
