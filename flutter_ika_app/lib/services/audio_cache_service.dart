import 'dart:io';
import 'package:flutter_cache_manager/flutter_cache_manager.dart';
import '../config/app_config.dart';

/// Downloads and caches audio files from the backend. Playback uses the local file.
class AudioCacheService {
  static final AudioCacheService _instance = AudioCacheService._();
  factory AudioCacheService() => _instance;

  AudioCacheService._();

  static const _cacheKey = 'ika_audio_cache';

  /// Default cache manager with long TTL (30 days) for audio.
  static CacheManager get _cacheManager => DefaultCacheManager();

  /// Resolve relative path (e.g. /audio/abc.mp3) to full URL.
  String fullUrl(String audioUrl) {
    if (audioUrl.startsWith('http')) return audioUrl;
    final base = AppConfig.baseUrl.replaceFirst(RegExp(r'/$'), '');
    final path = audioUrl.startsWith('/') ? audioUrl : '/$audioUrl';
    return '$base$path';
  }

  /// Download (or get from cache) and return local file for playback.
  /// Use this when you have the audio_url from POST /generate-audio.
  Future<File> getFileForUrl(String audioUrl) async {
    final url = fullUrl(audioUrl);
    final file = await _cacheManager.getSingleFile(url);
    return file;
  }

  /// Clear all cached audio files.
  Future<void> clearCache() async {
    await _cacheManager.emptyCache();
  }
}
