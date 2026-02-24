/// Environment configuration for IKA Language Engine
class Env {
  // Backend base URL
  static const String baseUrl = 
      'https://ika-backend-516421484935.europe-west2.run.app';
  
  // API timeouts
  static const Duration connectTimeout = Duration(seconds: 30);
  static const Duration receiveTimeout = Duration(seconds: 30);
  static const Duration sendTimeout = Duration(seconds: 30);
  
  // Audio cache key prefix
  static const String audioCachePrefix = 'audio_cache_';
}
