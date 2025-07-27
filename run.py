from argparse import ArgumentParser
from src import create_app, start_background_downgrade_process, stop_background_downgrade_process
from src.db import init_db
import os
import atexit
import logging
from src.utils.logging_config import setup_logging
import asyncio

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--dev', action='store_true', help='Run the server in development mode')
    parser.add_argument('--port', '-p', type=int, default=5000, help='Port to run the server on')

    args = parser.parse_args()

    mode: str = os.getenv('MODE', 'dev')

    if args.dev:
        logging.info("Overriding prod environment variable to dev for development mode.")
        os.environ["MODE"] = "dev"
        mode = "dev"

    if mode:
        setup_logging(console_level=logging.DEBUG)
    elif mode == "staging":
        setup_logging(console_level=logging.DEBUG)
    elif mode == "prod":
        setup_logging(console_level=logging.INFO)

        # Initialize database tables (runs once)
    logging.info('[Quart] Initializing database...')
    init_db(mode=mode)
    logging.info('[Quart] Database initialized successfully.')

    app = create_app()

    # if args dev override PROD environment variable


    # Start background process safely
    if int(os.getenv("RUN_BACKGROUND_TASKS", 0)) == 1:
        start_background_downgrade_process()
        atexit.register(stop_background_downgrade_process)

    logging.info(f"Running server in {mode} mode on port {args.port}")
    if mode == "dev":
        logging.info("Running in development mode with debug enabled.")
        app.run(debug=True, port=args.port)
    else:
        # Use Hypercorn instead of Waitress for Quart
        import hypercorn.asyncio
        from hypercorn import Config
        
        config = Config()
        config.bind = [f"0.0.0.0:{args.port}"]
        asyncio.run(hypercorn.asyncio.serve(app, config))
