# desktop_clara

Desktop Clara Flutter UI with a Rust-backed agent core (FFI on Linux).

## Rust backend build

Build the shared library before running the app:

```bash
cd ui/flutter/native/agent_core
cargo build --release
```

If you want to load a different build output, set:

```bash
export AGENT_CORE_LIB=/absolute/path/to/libagent_core.so
```

The Linux CMake build also compiles and bundles `libagent_core.so` automatically.

## Getting Started

This project is a starting point for a Flutter application.

A few resources to get you started if this is your first Flutter project:

- [Lab: Write your first Flutter app](https://docs.flutter.dev/get-started/codelab)
- [Cookbook: Useful Flutter samples](https://docs.flutter.dev/cookbook)

For help getting started with Flutter development, view the
[online documentation](https://docs.flutter.dev/), which offers tutorials,
samples, guidance on mobile development, and a full API reference.
