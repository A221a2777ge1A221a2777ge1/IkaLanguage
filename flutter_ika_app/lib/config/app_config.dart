/// App Configuration - Single source of truth for backend URL
class AppConfig {
  // Backend base URL - change this to switch between environments.
  // If you see "Backend not found (404)", ensure this URL matches your
  // deployed Cloud Run service (or use a local URL for development).
  // Production (default):
  static const String baseUrl = 
      'https://ika-backend-516421484935.europe-west2.run.app';
  
  // Local development (uncomment and set your local IP):
  // static const String baseUrl = 'http://192.168.1.100:8080';
  
  // API timeouts
  static const Duration connectTimeout = Duration(seconds: 30);
  static const Duration receiveTimeout = Duration(seconds: 30);
  static const Duration sendTimeout = Duration(seconds: 30);
  
  // Audio cache key prefix
  static const String audioCachePrefix = 'audio_cache_';
  
  /// Check if using HTTP (for cleartext traffic requirement)
  static bool get usesHttp => baseUrl.startsWith('http://');
}
