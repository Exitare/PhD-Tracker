from argparse import ArgumentParser
from src import create_app, start_background_downgrade_process, stop_background_downgrade_process
from src.db import init_db
import os
import atexit

app = create_app()

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--dev', action='store_true', help='Run the server in development mode')
    parser.add_argument('--port', '-p', type=int, default=5000, help='Port to run the server on')

    args = parser.parse_args()
    print("Initializing database...")
    init_db()

    # Start background process safely
    if int(os.getenv("RUN_BACKGROUND_TASKS", 0)) == 1:
        start_background_downgrade_process()
        atexit.register(stop_background_downgrade_process)

    print(f"Running server in {'development' if args.dev else 'production'} mode on port {args.port}")
    app.run(debug=True, port=args.port)
