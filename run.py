from argparse import ArgumentParser
from src import create_app
from src.db import init_db

app = create_app()

if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('--dev', action='store_true', help='Run the server in development mode')
    parser.add_argument('--port', '-p', type=int, default=5000, help='Port to run the server on')

    args = parser.parse_args()
    print(f"Running server in {'development' if args.dev else 'production'} mode on port {args.port}")
    init_db()
    app.run(debug=True, port=args.port, host='0.0.0.0')
