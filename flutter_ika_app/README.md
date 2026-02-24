# IKA Language Engine - Flutter MVP

Flutter mobile app for the IKA Language Engine, connecting to a Cloud Run FastAPI backend.

## Features

- **Translate**: English to Ika translation with tense selection
- **Generate**: Create poems, stories, or lectures in Ika
- **Audio**: On-demand audio generation (only when Play is tapped)
- **Library**: Save and manage translation/generation history
- **Firebase Auth**: Anonymous authentication for backend access

## Prerequisites

- Flutter SDK (3.0.0 or higher)
- Firebase project with Authentication enabled
- Backend URL: `https://ika-backend-516421484935.europe-west2.run.app`

## Setup Instructions

### 1. Firebase Configuration

#### Android Setup

1. Go to [Firebase Console](https://console.firebase.google.com/)
2. Select your project (or create a new one)
3. Add Android app:
   - Package name: `com.gmoney.ikaengine`
   - Download `google-services.json`
4. Place `google-services.json` in `android/app/`
5. Update `android/build.gradle`:
   ```gradle
   dependencies {
       classpath 'com.google.gms:google-services:4.4.0'
   }
   ```
6. Update `android/app/build.gradle`:
   ```gradle
   apply plugin: 'com.google.gms.google-services'
   ```

#### iOS Setup

1. In Firebase Console, add iOS app:
   - Bundle ID: `com.gmoney.ikaengine` (or your bundle ID)
   - Download `GoogleService-Info.plist`
2. Place `GoogleService-Info.plist` in `ios/Runner/`
3. Open `ios/Runner.xcworkspace` in Xcode
4. Drag `GoogleService-Info.plist` into the Runner folder in Xcode

### 2. Enable Firebase Authentication

1. In Firebase Console, go to **Authentication**
2. Enable **Anonymous** sign-in method
3. This allows the app to sign in anonymously for backend access

### 3. Configure Backend URL

The backend URL is set in `lib/config/env.dart`:

```dart
static const String baseUrl = 
    'https://ika-backend-516421484935.europe-west2.run.app';
```

Update this if your backend URL changes.

### 4. Install Dependencies

```bash
flutter pub get
```

### 5. Run the App

#### Android

```bash
flutter run
```

Or build APK:

```bash
flutter build apk
```

#### iOS

```bash
flutter run
```

Or build for iOS:

```bash
flutter build ios
```

## Project Structure

```
lib/
├── main.dart                 # App entry point
├── app.dart                  # Main app widget
├── config/
│   └── env.dart             # Configuration (base URL, timeouts)
├── auth/
│   └── firebase_auth_service.dart  # Firebase Auth service
├── api/
│   ├── api_client.dart      # HTTP client with auth
│   ├── ika_api.dart         # API endpoints
│   └── models.dart          # Data models
├── state/
│   ├── auth_provider.dart   # Auth state management
│   ├── translate_provider.dart
│   ├── generate_provider.dart
│   └── library_provider.dart
├── screens/
│   ├── splash_screen.dart   # Initialization screen
│   ├── home_screen.dart      # Main screen with tabs
│   ├── translate_screen.dart
│   ├── generate_screen.dart
│   ├── library_screen.dart
│   └── detail_screen.dart
└── widgets/
    ├── audio_player_widget.dart
    ├── result_card.dart
    ├── meta_expandable.dart
    └── primary_button.dart
```

## Usage

### Translate Screen

1. Enter English text in the input field
2. Select tense (present/past/future/progressive)
3. Tap "Translate" button
4. View Ika translation
5. Tap "Generate Audio" to create audio (on-demand)
6. Use "Play" button to play audio
7. Save to library or copy text

### Generate Screen

1. Select kind: Poem / Story / Lecture
2. Enter topic
3. Select tone and length
4. Tap "Generate" button
5. View generated Ika text
6. Generate and play audio (on-demand)
7. Save to library or copy text

### Library Screen

- View all saved translations and generations
- Tap item to view details
- Play audio if available
- Delete items
- Generate audio for items without audio

## Audio Behavior

**IMPORTANT**: Audio is **on-demand only**:
- Audio is **NEVER** auto-generated
- Audio is generated **ONLY** when user taps "Play Audio" or "Generate Audio"
- Audio URLs are cached locally to avoid regeneration
- Audio is streamed using `just_audio` package

## Error Handling

- **401/403**: Automatically refreshes token and retries once
- **Network timeout**: Shows friendly error message
- **Backend errors**: Displays error message to user
- **Session expired**: Prompts user to re-authenticate

## Local Storage

- Uses **Hive** for local storage
- Stores generation results (translations, poems, stories, lectures)
- Audio URLs are cached per text (SHA256 hash)
- Data persists across app restarts

## Troubleshooting

### Firebase Auth Issues

If you see authentication errors:
1. Verify `google-services.json` (Android) or `GoogleService-Info.plist` (iOS) is in the correct location
2. Check that Anonymous sign-in is enabled in Firebase Console
3. Verify package name/bundle ID matches Firebase configuration

### Backend Connection Issues

If backend calls fail:
1. Check backend URL in `lib/config/env.dart`
2. Verify backend is running and accessible
3. Check network connectivity
4. Verify Firebase Auth token is being generated

### Audio Playback Issues

If audio doesn't play:
1. Check network connectivity
2. Verify audio URL is valid
3. Check device audio settings
4. Try regenerating audio

## Building for Production

### Android

```bash
flutter build apk --release
# or
flutter build appbundle --release
```

### iOS

```bash
flutter build ios --release
```

## Development Notes

- Uses **Riverpod** for state management
- Uses **Dio** for HTTP requests with automatic token injection
- Uses **Hive** for local storage (no SQLite needed)
- Uses **just_audio** for audio playback
- Material Design 3 UI

## License

This project is part of the IKA Language Engine system.
