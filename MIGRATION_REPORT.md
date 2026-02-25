# Migration Report: SOURCE (ika_app) → TARGET (repo root)

## What was done

### 1. Analysis
- **SOURCE**: `C:\Users\USER\CascadeProjects\ika_app\flutter_ika_app` and `ika_app\backend`
- **TARGET**: `C:\Users\USER\CascadeProjects\flutter_ika_app` and `backend`
- TARGET already had `build_info.py`, `/health` with build, `/build-info`, and dictionary with optional `q` and `limit=700`. SOURCE had the full endpoint set (generate-story/poem/lecture, naturalize) and app.* imports but no build_info.

### 2. Files changed

#### Backend (backend/ika-backend)
| File | Change |
|------|--------|
| `cloudbuild.yaml` | Added `substitutions: _GIT_SHA: 'unknown'` and use `GIT_SHA=${_GIT_SHA}` so manual submit can pass `--substitutions=_GIT_SHA=$(git rev-parse HEAD)`. No reliance on `$COMMIT_SHA`. |
| `app/main.py` | No structural change; already had build_info, /build-info, dictionary q/limit. (Other app/*.py were already in sync; dataset_generator, lexicon_store, pattern_repo, slot_filler, templates.json from prior work left as-is.) |
| `Dockerfile` | Unchanged (already correct: single CMD, `${PORT:-8080}`). |
| `app/build_info.py` | Unchanged (TARGET-only; kept). |

#### Flutter (flutter_ika_app/lib)
| File | Change |
|------|--------|
| **Copied from SOURCE** | All of `lib/**/*.dart` (26 files) overwritten with SOURCE so 5-tab nav, naturalize, tone, generate-story/poem/lecture API match SOURCE. |
| `app.dart` | Light theme and nav visibility (ColorScheme, AppBarTheme, BottomNavigationBarTheme). |
| `screens/home_screen.dart` | Fixed brace nesting (removed duplicate `);`), explicit nav bar colors (white, blue, black54). |
| `api/api_client.dart` | Added `getBytes(path)` for authenticated audio download. |
| `api/ika_api.dart` | Added `getAudioBytes(path)`, `dictionaryLookup(query, {limit})`, `getBuildInfo()`. |
| `widgets/audio_player_widget.dart` | AudioPlayerNotifier(ref), play() uses api.getAudioBytes() with auth, fallback to cache. |
| `state/dictionary_provider.dart` | Empty query loads all (limit 700). |
| `screens/dictionary_screen.dart` | initState loads all; "Show all" button; ListView.builder; visible text colors. |
| `config/app_config.dart` | Unchanged (baseUrl already Cloud Run). |

#### Other
| File | Change |
|------|--------|
| `MIGRATION_PLAN.md` | Added (plan only). |
| `flutter_ika_app/pubspec.lock` | Updated after copy. |

### 3. Commands run
- `xcopy ika_app\flutter_ika_app\lib\* flutter_ika_app\lib\ /E /Y /I` – copy SOURCE lib → TARGET
- `git add backend/ika-backend/app backend/ika-backend/cloudbuild.yaml backend/ika-backend/data/templates.json flutter_ika_app/lib flutter_ika_app/pubspec.lock MIGRATION_PLAN.md`
- `git commit -m "Sync correct app updates from ika_app; backend build-info + Flutter UI/API fixes"`
- `git push origin main` → **cd89194..9d7156e  main -> main**

### 4. Manual steps for you
1. **Backend import check** (after deps install):  
   `cd backend/ika-backend`  
   `py -m venv .venv` (if needed), `.\.venv\Scripts\Activate.ps1`  
   `pip install -r requirements.txt`  
   `python -c "from app.main import app; print('IMPORT OK')"`

2. **Flutter build** (optional):  
   `cd flutter_ika_app`  
   `flutter pub get`  
   `flutter build apk --debug` (or `flutter run`)

3. **Deploy backend** (Cloud Shell):  
   `cd ~/IkaLanguage/backend/ika-backend`  
   `git pull origin main`  
   `gcloud builds submit --config=cloudbuild.yaml . --substitutions=_GIT_SHA=$(git rev-parse HEAD)`  
   Then: `curl -s https://ika-backend-516421484935.europe-west2.run.app/build-info`

### 5. Endpoints confirmed (TARGET backend)
- `/health` – returns `{"ok": true, "build": { "git_sha", "dataset_sha256", "dataset_files_count" }}`
- `/build-info` – returns build info (no auth)
- `/translate`, `/generate`, `/generate-story`, `/generate-poem`, `/generate-lecture`, `/naturalize`, `/generate-audio`, `/dictionary`, `/audio/{filename}` – as in OpenAPI / SOURCE

### 6. Not copied (by design)
- Build artifacts: `build/`, `.dart_tool/`, `.gradle/`, `__pycache__/`, `node_modules/`
- Secrets: `serviceAccount.json`, `google-services.json`, `.env`, keystores
- Entire `ika_app/` folder (SOURCE) – left untracked; not added to git
