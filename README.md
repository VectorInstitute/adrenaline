# adrenaline

TBD

## Getting Started

Docker is used for development and production.

1. Clone the repository:

```bash
git clone git@github.com:VectorInstitute/adrenaline.git
```

### Production

To deploy the production application:

```bash
docker compose --env-file .env.production -f docker-compose.yml build
docker compose --env-file .env.production -f docker-compose.yml up
```

### Development

To launch the application for development:

```bash
docker compose --env-file .env.development -f docker-compose.dev.yml build
docker compose --env-file .env.development -f docker-compose.dev.yml up
```

Open your browser and visit `http://localhost:<port>` to see the application.
The port can be modified in the respective `.env` files.


## System Architecture

TODO

## Project Structure

This project is divided into two main directories: `frontend` for the Next.js application and `backend` for the FastAPI server.

### Frontend (Next.js)

### Backend (FastAPI)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the Apache 2.0 license.

## Acknowledgements

- [Vector Institute](https://vectorinstitute.ai/)
