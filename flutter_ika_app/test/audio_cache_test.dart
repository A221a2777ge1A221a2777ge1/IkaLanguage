import 'package:flutter_test/flutter_test.dart';
import 'package:ika_language_engine/services/audio_cache_service.dart';

void main() {
  group('Audio cache', () {
    test('lexiconAudioCacheKey produces deterministic filename', () {
      expect(lexiconAudioCacheKey('1'), 'ika_audio_1.m4a');
      expect(lexiconAudioCacheKey('42'), 'ika_audio_42.m4a');
    });
  });
}
