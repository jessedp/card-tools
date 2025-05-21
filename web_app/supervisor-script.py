#!/usr/bin/env python3
import os
import sys
import time
import signal
import subprocess
import argparse
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('supervisor')

# Path to the main application
SCRIPT_DIR = Path(__file__).parent
WEB_APP_PATH = SCRIPT_DIR / "web" / "app.py"

class Supervisor:
    def __init__(self):
        self.process = None
        self.should_run = True
        
    def start(self):
        """Start the web server process."""
        if self.process is not None and self.process.poll() is None:
            logger.info("Process is already running")
            return
        
        logger.info("Starting web server...")
        self.process = subprocess.Popen(
            [sys.executable, str(WEB_APP_PATH)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True
        )
        
        # Log process output
        self._log_output()
        
    def stop(self):
        """Stop the web server process."""
        if self.process is None or self.process.poll() is not None:
            logger.info("No process is running")
            return
        
        logger.info("Stopping web server...")
        self.should_run = False
        
        # Try to terminate gracefully first
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning("Process did not terminate gracefully, forcing...")
            self.process.kill()
        
        logger.info("Web server stopped")
        self.process = None
    
    def restart(self):
        """Restart the web server process."""
        logger.info("Restarting web server...")
        self.stop()
        time.sleep(1)
        self.start()
    
    def _log_output(self):
        """Log the output from the process."""
        def read_output():
            while self.should_run and self.process and self.process.poll() is None:
                line = self.process.stdout.readline()
                if line:
                    logger.info(f"APP: {line.strip()}")
                else:
                    break
        
        # Start output logging in another thread
        import threading
        threading.Thread(target=read_output, daemon=True).start()

def signal_handler(sig, frame):
    """Handle termination signals."""
    logger.info(f"Received signal {sig}, shutting down...")
    if supervisor:
        supervisor.stop()
    sys.exit(0)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Web Server Supervisor')
    parser.add_argument('action', choices=['start', 'stop', 'restart', 'status'],
                      help='Action to perform on the web server')
    
    args = parser.parse_args()
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create supervisor instance
    supervisor = Supervisor()
    
    # Execute requested action
    if args.action == 'start':
        supervisor.start()
        try:
            # Keep the script running
            while supervisor.should_run:
                time.sleep(1)
                # Check if process died unexpectedly
                if supervisor.process and supervisor.process.poll() is not None:
                    logger.error("Web server process died unexpectedly, restarting...")
                    supervisor.start()
        except KeyboardInterrupt:
            supervisor.stop()
    
    elif args.action == 'stop':
        supervisor.stop()
    
    elif args.action == 'restart':
        supervisor.restart()
    
    elif args.action == 'status':
        if supervisor.process is None:
            logger.info("Web server is not running")
        elif supervisor.process.poll() is None:
            logger.info("Web server is running")
        else:
            logger.info(f"Web server stopped with exit code {supervisor.process.returncode}")
