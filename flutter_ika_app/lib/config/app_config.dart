/// App Configuration - Single source of truth for backend URL
class AppConfig {
  /// Backend base URL. Override with --dart-define=BASE_URL=http://10.0.2.2:8080
  /// for Android emulator, or your machine IP for a physical device.
  static String get baseUrl =>
      const String.fromEnvironment(
        'BASE_URL',
        defaultValue: 'https://ika-backend-516421484935.europe-west2.run.app',
      );
  
  // API timeouts
  static const Duration connectTimeout = Duration(seconds: 30);
  static const Duration receiveTimeout = Duration(seconds: 30);
  static const Duration sendTimeout = Duration(seconds: 30);
  
  // Audio cache key prefix
  static const String audioCachePrefix = 'audio_cache_';
  
  /// Check if using HTTP (for cleartext traffic requirement)
  static bool get usesHttp => baseUrl.startsWith('http://');
}
