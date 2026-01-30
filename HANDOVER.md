# Nexora Android Hybrid Host - Handover

## Project State
We have successfully transformed the Nexora Ops system into a **Hybrid Android Host**. This capability allows an Android device to run the full Python Backend and serve the Next.js Frontend locally, effectively becoming a portable "Nexus Node".

### Key Components Created
1.  **`nexora_android/`**: The main Flet wrapper project.
    *   `main.py`: The entry point that starts the background Python server and launches the WebView.
    *   `assets/web/`: Contains the **Static Export** of the Next.js frontend (built from `frontend/`).
    *   `backend/`: A copy of the backend logic, patched to skip heavy AI workers on Android.
2.  **Communication Hub & Situational Alerting**:
    *   Dedicated tab for managing emergency recipients by category (Fire, Flood, Intrusion).
    *   Situational logic in `state_manager.py` that selects recipients based on alert context.
3.  **Audio Broadcast System**:
    *   MP3 upload endpoint in `server.py`.
    *   ADB-based audio push and speakerphone playback in `sms_worker.py`.
4.  **`frontend/`**: Updated with `output: 'export'` in `next.config.ts` to support static generation.

## Current Status: Source Ready
The source code is fully prepared and configured. However, the automated APK build process on this machine was halted because the **Android SDK** is missing.

## Next Steps for Developer
To produce the final APK, follow these steps:

1.  **Install Prerequisites**:
    *   **Android Studio**: Install this to get the Android SDK and Command Line Tools. [Download](https://developer.android.com/studio).
    *   **Flutter SDK**: Already installed in `C:\Users\Victo\flutter\3.38.7`. Add `bin` to your PATH.

2.  **Build the APK**:
    Open a terminal in `nexora_android/` and run:
    ```bash
    flet build apk -vv
    ```

3.  **Install on Device**:
    The generic APK will be at `build/app/outputs/flutter-apk/app-release.apk`.

## Architecture Note
-   The backend detects it is running on Android via the `ANDROID_MODE` environment variable (set in `main.py`).
-   **Communication Logic**: The `sms_worker.py` uses ADB commands. For SMS and Audio broadcasts to work on Windows (connected to a phone) or on the Android APK itself, ADB must be available or the device must have permissions.
-   **Situational Context**: The system uses loose matching on the alert "reason" to categorize contacts. For example, a reason containing "fire" triggers contacts in the "fire" category.
-   In this mode, `opencv-python` and `ultralytics` imports are skipped to prevent crashes, as these libraries are not included in the lightweight mobile environment.
