# Migration Plan: SOURCE (ika_app) → TARGET (repo root)

## 1. Analysis summary

### Backend (ika_app/backend vs backend)
- **SOURCE** has: app.* imports, dataset + naturalize + generate-story/poem/lecture, local_audio_cache, /audio; **no** build_info, **no** /build-info, health returns only `{"ok": true}`. Dictionary requires min_length=1, limit=25. cloudbuild has no GIT_SHA. Dockerfile has duplicate ENV PORT.
- **TARGET** has: same app.* + build_info.py, /health with build, /build-info, dictionary with optional q and limit=700. Dockerfile correct (single CMD, ${PORT:-8080}). cloudbuild has GIT_SHA=$COMMIT_SHA (only set on trigger, not manual submit).

### Flutter (ika_app/flutter_ika_app vs flutter_ika_app)
- **SOURCE** has: correct 5-tab nav, naturalize, tone in generate, theme/nav visibility fixes, dictionary load-all, audio auth download (getBytes, Ref in player). baseUrl same.
- **TARGET** already has many of these from prior sync; ensure SOURCE versions overwrite so UI/auth/API match SOURCE.

## 2. Files to migrate

### Backend (TARGET = backend/ika-backend)
| Action | File | Why |
|--------|------|-----|
| KEEP | app/build_info.py | Only in TARGET; required for /build-info and fingerprint. |
| KEEP | app/__init__.py | Package marker. |
| MERGE | app/main.py | Keep TARGET version (has build_info, /build-info, dictionary q/limit). Ensure all SOURCE endpoints present—already are. |
| KEEP | Dockerfile | TARGET has correct CMD and no duplicate ENV. |
| EDIT | cloudbuild.yaml | Add substitution _GIT_SHA (default 'unknown'), set GIT_SHA=$_GIT_SHA so manual submit can pass it. |
| COPY | app/*.py (others) | Copy from SOURCE so logic matches: validators, audio_cache, templates_engine, slot_filler, generator, dataset_generator, lexicon_store, pattern_repo, rule_engine, lexicon_repo, firebase_client, tts_engine, local_audio_cache. (All use app.* imports in SOURCE.) |

### Flutter (TARGET = flutter_ika_app)
| Action | Path | Why |
|--------|------|-----|
| COPY | lib/**/*.dart | Overwrite TARGET with SOURCE so theme, nav, naturalize, tone, dictionary load-all, audio getBytes/Ref match SOURCE. |
| KEEP | pubspec.yaml, android/, ios/ | Use TARGET; only copy lib + config if different. |
| SKIP | build/, .dart_tool/, .packages | Build artifacts. |
| SKIP | google-services.json, .env, *.jks | Secrets; keep TARGET versions. |

## 3. Verification
- Backend: `cd backend/ika-backend && pip install -r requirements.txt && python -c "from app.main import app; print('IMPORT OK')"`
- Flutter: `cd flutter_ika_app && flutter pub get && flutter build apk --debug`
- Optional: Flutter calls /build-info to confirm backend reachable.

## 4. Git (TARGET root = CascadeProjects)
- git status → commit all under backend/ika-backend and flutter_ika_app/lib (and app config if changed).
- Message: "Sync correct app updates from ika_app; backend build-info + Flutter UI/API fixes"
- Push origin main.
