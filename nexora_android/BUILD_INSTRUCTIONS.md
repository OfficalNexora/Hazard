# How to Build the Nexora Android APK

The project files in this directory are fully prepared. However, building an Android APK requires downloading the Flutter SDK and Android SDK (~2GB+), which takes too long to do automatically.

## 1. Prerequisites
-   **Nexus Hybrid Host** project ready (this folder).
-   **Android SDK**: The automated build failed to install the Android SDK. You must install **Android Studio** or the **Android Command Line Tools**.
    -   Download: [https://developer.android.com/studio](https://developer.android.com/studio)
    -   Install it and open it once to complete the SDK setup.
    -   Accept all licenses.

## 2. Build Command
Open a terminal in this directory (`nexora_android`) and run:

```powershell
flet build apk --vv
```

## 3. First Run Process (What to expect)
1.  **Flutter SDK Download**: The first time you run this, it will ask to download the Flutter SDK. Type `y` and press Enter.
2.  **Android SDK**: It might also ask to accept Android SDK licenses. Type `y` if prompted.
3.  **Compilation**: Once tools are installed, it will compile `app-release.apk`.
4.  **Output**: The verified APK will be in `build/app/outputs/flutter-apk/app-release.apk`.

## 4. Install on Phone
1.  Transfer the `.apk` to your phone.
2.  Enable "Install from Unknown Sources".
3.  Install via File Manager.
