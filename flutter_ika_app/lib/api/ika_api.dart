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

  /// Generate poem (POST /generate-poem)
  Future<GenerateResponse> generatePoem(GenerateRequest request) async {
    final response = await _client.post('/generate-poem', data: request.toJson());
    return GenerateResponse.fromJson(response.data);
  }

  /// Generate lecture (POST /generate-lecture)
  Future<GenerateResponse> generateLecture(GenerateRequest request) async {
    final response = await _client.post('/generate-lecture', data: request.toJson());
    return GenerateResponse.fromJson(response.data);
  }

  /// Naturalize: "Say it like an Ika person" (POST /naturalize)
  Future<NaturalizeResponse> naturalize(NaturalizeRequest request) async {
    final response = await _client.post('/naturalize', data: request.toJson());
    return NaturalizeResponse.fromJson(response.data);
  }

  /// Download audio with auth (for Cloud Run). Returns bytes.
  Future<List<int>> getAudioBytes(String path) async {
    final p = path.startsWith('http') ? Uri.parse(path).path : (path.startsWith('/') ? path : '/$path');
    return _client.getBytes(p);
  }

  /// Generate audio. Returns null if server returns 501 Not Implemented.
  Future<GenerateAudioResponse?> generateAudio(GenerateAudioRequest request) async {
    try {
      final response = await _client.post('/generate-audio', data: request.toJson());
      return GenerateAudioResponse.fromJson(response.data);
    } on ApiException catch (e) {
      if (e.statusCode == 501) {
        return null;
      }
      rethrow;
    }
  }

  /// Dictionary lookup: English word/prefix → Ika words. Empty query returns all (e.g. 675+).
  Future<DictionaryResponse> dictionaryLookup(String query, {int limit = 700}) async {
    final response = await _client.get(
      '/dictionary',
      queryParameters: {'q': query.trim(), 'limit': limit},
    );
    return DictionaryResponse.fromJson(response.data);
  }

  /// Build info from backend (git_sha, dataset_sha256). No auth required.
  Future<Map<String, dynamic>> getBuildInfo() async {
    final response = await _client.get('/build-info');
    return Map<String, dynamic>.from(response.data as Map);
  }
}
