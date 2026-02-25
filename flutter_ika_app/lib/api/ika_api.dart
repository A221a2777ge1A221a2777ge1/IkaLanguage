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
      rethrow;
    } catch (e) {
      throw Exception('Health check failed: $e');
    }
  }

  /// Translate text (legacy POST /translate)
  Future<TranslateResponse> translate(TranslateRequest request) async {
    final response = await _client.post('/translate', data: request.toJson());
    return TranslateResponse.fromJson(response.data);
  }

  /// EN → Ika lookup using local export only (GET /api/translate/en-ika)
  Future<EnIkaLookupResponse> translateEnToIka(String q) async {
    final response = await _client.get(
      '/api/translate/en-ika',
      queryParameters: {'q': q.trim()},
    );
    final data = response.data;
    if (data is! Map<String, dynamic>) {
      throw Exception('Translate en-ika failed: unexpected response');
    }
    return EnIkaLookupResponse.fromJson(data);
  }

  /// Ika → EN lookup (GET /api/translate/ika-en)
  Future<IkaEnLookupResponse> translateIkaToEn(String q) async {
    final response = await _client.get(
      '/api/translate/ika-en',
      queryParameters: {'q': q.trim()},
    );
    final data = response.data;
    if (data is! Map<String, dynamic>) {
      throw Exception('Translate ika-en failed: unexpected response');
    }
    return IkaEnLookupResponse.fromJson(data);
  }

  /// Lexicon audio by id (GET /api/audio?id=). Returns m4a bytes for caching/playback.
  Future<List<int>> getLexiconAudioBytes(String id) async {
    return _client.getBytes('/api/audio', queryParameters: {'id': id});
  }

  /// List dictionary entries (GET /api/dictionary). Optional domain filter.
  Future<DictionaryListResponse> listDictionary({
    String? domain,
    int limit = 500,
  }) async {
    final params = <String, dynamic>{'limit': limit};
    if (domain != null && domain.isNotEmpty) params['domain'] = domain;
    final response = await _client.get('/api/dictionary', queryParameters: params);
    final data = response.data;
    if (data is! Map<String, dynamic>) {
      return DictionaryListResponse(entries: []);
    }
    return DictionaryListResponse.fromJson(data);
  }

  /// Generate content (POST /api/generate). mode: story|poem|lecture|sentence.
  Future<ApiGenerateResponse> generateApi({
    required String mode,
    required String topic,
    String length = 'medium',
    String inputLang = 'en',
  }) async {
    final response = await _client.post(
      '/api/generate',
      data: {
        'mode': mode,
        'topic': topic,
        'length': length,
        'input_lang': inputLang,
      },
    );
    final data = response.data;
    if (data is! Map<String, dynamic>) {
      throw Exception('Generate failed: unexpected response');
    }
    return ApiGenerateResponse.fromJson(data);
  }

  /// Generate story (legacy POST /generate-story)
  Future<GenerateResponse> generateStory(GenerateRequest request) async {
    if (kDebugMode) {
      // ignore: avoid_print
      print('Calling /generate-story …');
    }
    final response = await _client.post('/generate-story', data: request.toJson());
    return GenerateResponse.fromJson(response.data);
  }

  /// Generate audio: POST /generate-audio returns MP3 bytes.
  Future<List<int>> generateAudioBytes(GenerateAudioRequest request) async {
    return _client.postBytes('/generate-audio', data: request.toJson());
  }

  /// Dictionary lookup: uses GET /api/translate/en-ika and maps to entries with audio.
  Future<DictionaryResponse> dictionaryLookup(String query) async {
    final res = await translateEnToIka(query);
    final entries = res.candidates
        .map((c) => DictionaryEntry(
              sourceText: res.query,
              targetText: c.ika,
              domain: c.domain,
              docId: c.id,
              audioUrl: c.audioUrl,
            ))
        .toList();
    return DictionaryResponse(entries: entries);
  }
}
