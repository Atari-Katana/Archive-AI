# Bifrost Integration

This document outlines the integration of the Bifrost gateway into the Archive-AI project.

## Overview

Bifrost is a high-performance AI gateway that unifies access to over 15 large language model (LLM) providers through a single OpenAI-compatible API. It has been integrated into the Archive-AI project to replace the original keyword-based semantic router, providing a more powerful and flexible way to route user queries to the most appropriate LLM.

## Docker-Compose Integration

Bifrost is configured as a service in the `docker-compose` files, which means it starts automatically with the other services when you run `docker-compose up`.

You can find the service definition for `bifrost` in the following files:
- `docker-compose.yml`
- `docker-compose.prod.yml`
- `docker-compose.cloudflare-fixed.yml`

A typical service definition looks like this:

```yaml
  bifrost:
    image: maximhq/bifrost:latest
    container_name: archive-bifrost
    ports:
      - "8080:8080"
    networks:
      - archive-net
    restart: unless-stopped
```

This configuration uses the official `maximhq/bifrost` Docker image and exposes port 8081, which is the default port for the Bifrost UI and API.

## Configuration

The communication between the `brain` service and the `bifrost` service is configured via the `BIFROST_URL` environment variable.

- **`brain/config.py`**: This file sets the default value for `BIFROST_URL`:
  ```python
  BIFROST_URL = os.getenv("BIFROST_URL", "http://bifrost:8080")
  ```
  The default value `http://bifrost:8080` is used when running inside a Docker container, allowing the `brain` container to communicate with the `bifrost` container using the service name `bifrost` as the hostname.

- **`.env` file**: You can override the default `BIFROST_URL` in the `.env` file. For example, if you are running the `brain` application outside of Docker and want to connect to a Bifrost instance running on your host machine, you would set the following in your `.env` file:
  ```
  BIFROST_URL=http://localhost:8081
  ```

## Managing the Bifrost Service

Since Bifrost is running as a Docker container, you can manage it using standard `docker-compose` commands.

- **Viewing logs:** To view the logs for the Bifrost service, you can run:
  ```bash
  docker-compose logs -f bifrost
  ```

- **Restarting the service:** To restart the Bifrost service, you can run:
  ```bash
  docker-compose restart bifrost
  ```
