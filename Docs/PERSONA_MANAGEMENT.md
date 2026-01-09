# Persona Management System

The Persona Management System allows users to create, store, and switch between different AI personalities. Each persona encapsulates a specific system prompt, backstory, avatar, and voice sample, enabling a highly customizable interaction experience.

## Features

- **Persona Studio**: A user-friendly web interface to create and edit personas.
- **Context Injection**: Automatically updates the AI's system prompt and history based on the active persona.
- **Voice Cloning**: Uses uploaded audio samples to clone the persona's voice for Text-to-Speech (TTS).
- **Persistence**: Personas and the active state are saved locally, surviving system restarts.

## User Guide

### Accessing the Studio
1. Navigate to the Web UI (e.g., `http://localhost:8081/ui/`).
2. Click the **Select Persona** dropdown in the top header.
3. Select **✨ Persona Studio** to open the creation modal.

### Creating a Persona
In the Persona Studio, fill in the following fields:
- **Name**: The display name of the persona (e.g., "Archibald Thornwick").
- **Personality (System Prompt)**: The core instructions that define how the AI behaves (e.g., "You are a Victorian Illustrator...").
- **History / Backstory**: Optional context about the persona's past.
- **Portrait**: Upload an image to serve as the avatar.
- **Voice Sample**: Upload a short audio file (WAV/MP3) of the desired voice. This will be used by the TTS engine.

### Switching Personas
1. Click the **Persona Dropdown**.
2. Select a persona from the list.
3. The system will immediately adopt the new personality. A checkmark `✓` indicates the active persona.

### Editing & Deleting
- **Edit**: Click the Pencil icon `✏️` next to a persona's name.
- **Delete**: Click the Trash icon `🗑️` to remove a persona. *Note: Deleting the active persona reverts the system to Neutral mode.*

## Technical Details

### Data Storage
- **Personas**: Stored in `data/personas.json`.
- **Active State**: Stored in `data/active_persona.json`.
- **Assets**: Images and audio files are stored in `ui/assets/personas/`.

### API Reference

#### Base URL: `/personas`

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | List all personas. |
| `POST` | `/` | Create a new persona. Payload: `{name, personality, ...}` |
| `GET` | `/{id}` | Get details of a specific persona. |
| `PUT` | `/{id}` | Update a persona. |
| `DELETE` | `/{id}` | Delete a persona. |
| `POST` | `/upload` | Upload avatar (`type=image`) or voice (`type=audio`). Returns file path. |
| `POST` | `/activate/{id}` | Set the active persona. |
| `GET` | `/active` | Get the currently active persona. |
| `POST` | `/deactivate` | Revert to neutral mode. |

### Integration Logic

1. **Chat (`/chat`)**:
   - The system checks for an active persona.
   - If found, the `personality` and `history` are prepended to the message history as a `system` message.

2. **Voice (`/voice/synthesize`)**:
   - The system checks if the active persona has a `voice_sample_path`.
   - If yes, it reads the audio file and sends it to the Voice Service (`/synthesize_with_reference`) to generate cloned speech.
   - If no, it uses the default TTS voice.

## Troubleshooting

- **Voice Cloning not working**: Ensure the uploaded audio file is clear and in a supported format (WAV recommended). If the Voice Service is running on a separate machine/container without shared volumes, the file transfer logic ensures the audio data is sent directly.
- **Changes not reflected**: Refresh the Web UI page.
