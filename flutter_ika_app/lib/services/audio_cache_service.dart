import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:path_provider/path_provider.dart';
import '../api/ika_api.dart';
import '../api/models.dart';
import '../state/auth_provider.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Cache dir: application documents / ika_audio_cache; files named by server filename.

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

  /// Get or create cached audio for Ika text: POST /generate-audio, then GET /audio/{filename}, cache by filename.
  Future<String> getPathForIkaText(String ikaText) async {
    final text = ikaText.trim();
    if (text.isEmpty) throw ArgumentError('Ika text is empty');

    final request = GenerateAudioRequest(text: text);
    final res = await _api.generateAudio(request);
    final filename = res.filename.isNotEmpty ? res.filename : 'audio_${text.hashKey}.mp3';
    final safeName = filename.replaceAll(RegExp(r'[^\w.\-]'), '_');

    final cacheDir = await _getCacheDir();
    final file = File('$cacheDir/$safeName');
    if (await file.exists()) {
      if (kDebugMode) debugPrint('Audio cache hit: $safeName');
      return file.path;
    }

    final bytes = await _api.getAudioByFilename(filename);
    await file.writeAsBytes(bytes);
    if (kDebugMode) debugPrint('Audio cached: $safeName (${bytes.length} bytes)');
    return file.path;
  }

  /// Returns path if already cached (by filename), otherwise null.
  Future<String?> getCachedPathIfExists(String filename) async {
    final safeName = filename.replaceAll(RegExp(r'[^\w.\-]'), '_');
    final cacheDir = await _getCacheDir();
    final file = File('$cacheDir/$safeName');
    if (await file.exists()) return file.path;
    return null;
  }
}

extension on String {
  int get hashKey => hashCode & 0x7FFFFFFF;
}

final audioCacheServiceProvider = Provider<AudioCacheService>((ref) {
  final api = ref.watch(ikaApiProvider);
  return AudioCacheService(api);
});
