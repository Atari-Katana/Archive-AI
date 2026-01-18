# Multi-stage build for Archive-AI Rust Services

# --- Builder Stage ---
FROM rust:1.83-slim-bookworm as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y pkg-config libssl-dev && rm -rf /var/lib/apt/lists/*

# Copy workspace definition
COPY Cargo.toml Cargo.lock ./

# Create dummy crates to cache dependencies
RUN mkdir -p crates/shared/src && \
    mkdir -p crates/brain/src && \
    mkdir -p crates/librarian/src && \
    echo "fn main() {}" > crates/brain/src/main.rs && \
    echo "fn main() {}" > crates/librarian/src/main.rs && \
    echo "pub fn hello() {}" > crates/shared/src/lib.rs && \
    # Create dummy Cargo.tomls if they are not copied yet? 
    # Actually, we should copy the crates directories structure first.
    # But to cache deps, we need Cargo.tomls. 
    # Let's copy the real Cargo.tomls
    mkdir -p crates/shared && mkdir -p crates/brain && mkdir -p crates/librarian

COPY crates/shared/Cargo.toml crates/shared/
COPY crates/brain/Cargo.toml crates/brain/
COPY crates/librarian/Cargo.toml crates/librarian/

# Build dependencies only
RUN cargo build --release

# Now copy the real source code
COPY crates crates

# Touch main files to force rebuild of the crates themselves (dependencies are cached)
RUN touch crates/brain/src/main.rs && \
    touch crates/librarian/src/main.rs && \
    touch crates/shared/src/lib.rs

# Build the real binaries
RUN cargo build --release

# --- Runtime Stage (Brain) ---
FROM debian:bookworm-slim as brain-rs

WORKDIR /app
RUN apt-get update && apt-get install -y ca-certificates libssl3 && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/target/release/brain /app/brain
CMD ["/app/brain"]

# --- Runtime Stage (Librarian) ---
FROM debian:bookworm-slim as librarian-rs

WORKDIR /app
RUN apt-get update && apt-get install -y ca-certificates libssl3 && rm -rf /var/lib/apt/lists/*

COPY --from=builder /app/target/release/librarian /app/librarian
CMD ["/app/librarian"]
