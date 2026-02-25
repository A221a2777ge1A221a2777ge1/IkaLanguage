import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';
import '../api/ika_api.dart';
import '../state/auth_provider.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Cache key for lexicon audio: ika_audio_<id>.m4a
String lexiconAudioCacheKey(String id) => 'ika_audio_$id.m4a';

/// Provides path to cached audio file for lexicon id, or null if not cached.
/// Downloads via GET /api/audio?id= and caches to app temp/doc dir.
class AudioCacheService {
  final IkaApi _api;
  String? _cacheDirPath;

  AudioCacheService(this._api);

  Future<String> _getCacheDir() async {
    if (_cacheDirPath != null) return _cacheDirPath!;
    final dir = await getApplicationDocumentsDirectory();
    final cacheDir = Directory('${dir.path}/ika_audio_cache');
    if (!await cacheDir.exists()) {
      await cacheDir.create(recursive: true);
    }
    _cacheDirPath = cacheDir.path;
    return _cacheDirPath!;
  }

  /// Returns path to audio file (cached or just downloaded). Throws on failure.
  Future<String> getPathForLexiconId(String id) async {
    final cacheDir = await _getCacheDir();
    final file = File('$cacheDir/${lexiconAudioCacheKey(id)}');
    if (await file.exists()) {
      if (kDebugMode) {
        debugPrint('Audio cache hit: $id');
      }
      return file.path;
    }
    final bytes = await _api.getLexiconAudioBytes(id);
    await file.writeAsBytes(bytes);
    if (kDebugMode) {
      debugPrint('Audio cached: $id (${bytes.length} bytes)');
    }
    return file.path;
  }

  /// Returns path if already cached, otherwise null (does not download).
  Future<String?> getCachedPathIfExists(String id) async {
    final cacheDir = await _getCacheDir();
    final file = File('$cacheDir/${lexiconAudioCacheKey(id)}');
    if (await file.exists()) return file.path;
    return null;
  }
}

final audioCacheServiceProvider = Provider<AudioCacheService>((ref) {
  final api = ref.watch(ikaApiProvider);
  return AudioCacheService(api);
});
