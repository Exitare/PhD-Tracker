from argparse import ArgumentParser
from src import create_app, start_background_downgrade_process, stop_background_downgrade_process
from src.db import init_db
import os
import atexit
import logging
from src.utils.logging_config import setup_logging
from waitress import serve

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--dev', action='store_true', help='Run the server in development mode')
    parser.add_argument('--port', '-p', type=int, default=5000, help='Port to run the server on')

    args = parser.parse_args()

    if args.dev:
        setup_logging(console_level=logging.DEBUG)
    else:
        setup_logging(console_level=logging.INFO)

        # Initialize database tables (runs once)
    logging.info('[Flask] Initializing database...')
    init_db(dev_mode=args.dev)
    logging.info('[Flask] Database initialized successfully.')

    app = create_app(dev_mode=args.dev)

    # if args dev override PROD environment variable
    if args.dev:
        logging.info("Overriding prod environment variable to 0 for development mode.")
        os.environ["PROD"] = "0"

    # Start background process safely
    if int(os.getenv("RUN_BACKGROUND_TASKS", 0)) == 1:
        start_background_downgrade_process()
        atexit.register(stop_background_downgrade_process)

    logging.info(f"Running server in {'development' if args.dev else 'production'} mode on port {args.port}")
    if args.dev:
        app.run(debug=True, port=args.port)
    else:
        serve(app, host='127.0.0.1', port=args.port)
