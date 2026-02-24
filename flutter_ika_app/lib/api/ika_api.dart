import 'package:flutter/foundation.dart';
import 'api_client.dart';
import 'models.dart';

/// IKA Language Engine API
class IkaApi {
  final ApiClient _client;

  IkaApi(this._client);

  /// Health check with detailed error reporting
  Future<HealthResponse> healthCheck() async {
    try {
      final response = await _client.get('/health');
      return HealthResponse.fromJson(response.data);
    } on ApiException catch (_) {
      // Re-throw ApiException as-is to preserve URL and status code
      rethrow;
    } catch (e) {
      // Wrap other exceptions
      throw Exception('Health check failed: $e');
    }
  }

  /// Translate text
  Future<TranslateResponse> translate(TranslateRequest request) async {
    final response = await _client.post('/translate', data: request.toJson());
    return TranslateResponse.fromJson(response.data);
  }

  /// Generate story (POST /generate-story)
  Future<GenerateResponse> generateStory(GenerateRequest request) async {
    if (kDebugMode) {
      // ignore: avoid_print
      print('Calling /generate-story …');
    }
    final response = await _client.post('/generate-story', data: request.toJson());
    return GenerateResponse.fromJson(response.data);
  }

  /// Generate audio: POST /generate-audio returns MP3 bytes.
  /// Returns raw MP3 bytes; caller should write to temp file and play with just_audio.
  Future<List<int>> generateAudioBytes(GenerateAudioRequest request) async {
    return _client.postBytes('/generate-audio', data: request.toJson());
  }

  /// Dictionary lookup: English word/prefix → Ika words.
  /// Uses POST /translate with mode: dictionary (returns same entries shape).
  Future<DictionaryResponse> dictionaryLookup(String query) async {
    final response = await _client.post(
      '/translate',
      data: {
        'text': query.trim(),
        'mode': 'dictionary',
        'tense': 'present',
      },
    );
    final data = response.data;
    if (data is! Map<String, dynamic>) {
      throw Exception('Dictionary lookup failed: unexpected response');
    }
    return DictionaryResponse.fromJson(data);
  }
}
