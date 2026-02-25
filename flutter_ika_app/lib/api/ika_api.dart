import 'package:flutter/foundation.dart';
import 'api_client.dart';
import 'models.dart';

/// IKA Language Engine API (Cloud Run; no /api/ prefix)
class IkaApi {
  final ApiClient _client;

  IkaApi(this._client);

  /// GET /health
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

  /// POST /translate — body: { text, mode: rule_based|en_to_ika|ika_to_en|auto, tense }
  /// Response: { text, meanings?, candidates?, found? } — pass through as text + meta
  Future<TranslateResponse> translate(TranslateRequest request) async {
    final response = await _client.post('/translate', data: request.toJson());
    final data = response.data;
    if (data is! Map<String, dynamic>) {
      throw Exception('Translate failed: unexpected response');
    }
    final text = data['text'] ?? '';
    final meta = Map<String, dynamic>.from(data)..remove('text');
    return TranslateResponse(text: text, meta: meta);
  }

  /// GET /dictionary?q=&limit= — returns entries with source_text, target_text, pos?, domain?, doc_id?
  Future<DictionaryListResponse> listDictionary({
    String? q,
    int limit = 200,
    int offset = 0,
  }) async {
    final params = <String, dynamic>{'limit': limit};
    if (offset > 0) params['offset'] = offset;
    if (q != null && q.isNotEmpty) params['q'] = q;
    final response = await _client.get('/dictionary', queryParameters: params);
    final data = response.data;
    if (data is! Map<String, dynamic>) {
      return DictionaryListResponse(entries: []);
    }
    return DictionaryListResponse.fromJson(data);
  }

  /// POST /generate — body: kind, topic, tone, length
  Future<GenerateResponse> generate({
    required String kind,
    required String topic,
    String tone = 'neutral',
    String length = 'medium',
  }) async {
    final response = await _client.post('/generate', data: {
      'kind': kind,
      'topic': topic,
      'tone': tone,
      'length': length,
    });
    final data = response.data;
    if (data is! Map<String, dynamic>) {
      throw Exception('Generate failed: unexpected response');
    }
    return GenerateResponse.fromJson(data);
  }

  /// POST /generate-story (body: prompt, length)
  Future<GenerateResponse> generateStory(GenerateRequest request) async {
    if (kDebugMode) {
      // ignore: avoid_print
      print('Calling /generate-story …');
    }
    final response = await _client.post('/generate-story', data: request.toJson());
    return GenerateResponse.fromJson(response.data);
  }

  /// POST /generate-poem
  Future<GenerateResponse> generatePoem(GenerateRequest request) async {
    final response = await _client.post('/generate-poem', data: request.toJson());
    return GenerateResponse.fromJson(response.data);
  }

  /// POST /generate-lecture
  Future<GenerateResponse> generateLecture(GenerateRequest request) async {
    final response = await _client.post('/generate-lecture', data: request.toJson());
    return GenerateResponse.fromJson(response.data);
  }

  /// POST /naturalize — body: intent_text, tone, length
  Future<GenerateResponse> naturalize({
    required String intentText,
    String tone = 'neutral',
    String length = 'medium',
  }) async {
    final response = await _client.post('/naturalize', data: {
      'intent_text': intentText,
      'tone': tone,
      'length': length,
    });
    final data = response.data;
    if (data is! Map<String, dynamic>) {
      throw Exception('Naturalize failed: unexpected response');
    }
    return GenerateResponse.fromJson(data);
  }

  /// POST /generate-audio — returns JSON { audio_url, filename }; then use getAudioByFilename to download
  Future<GenerateAudioResponse> generateAudio(GenerateAudioRequest request) async {
    final response = await _client.post('/generate-audio', data: request.toJson());
    final data = response.data;
    if (data is! Map<String, dynamic>) {
      throw Exception('Generate audio failed: unexpected response');
    }
    return GenerateAudioResponse.fromJson(data);
  }

  /// GET /audio/{filename} — download audio bytes (cache by filename)
  Future<List<int>> getAudioByFilename(String filename) async {
    final path = '/audio/${Uri.encodeComponent(filename)}';
    return _client.getBytes(path);
  }

  /// Dictionary lookup: GET /dictionary?q=query&limit=25; map to DictionaryResponse
  Future<DictionaryResponse> dictionaryLookup(String query) async {
    final res = await listDictionary(q: query.trim(), limit: 25);
    return DictionaryResponse(entries: res.entries);
  }
}
