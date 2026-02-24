import 'package:dio/dio.dart';
import 'package:flutter/foundation.dart';
import '../config/app_config.dart';
import '../auth/firebase_auth_service.dart';

/// API Client with authentication
class ApiClient {
  late final Dio _dio;
  final FirebaseAuthService _authService;

  ApiClient(this._authService) {
    _dio = Dio(BaseOptions(
      baseUrl: AppConfig.baseUrl,
      connectTimeout: AppConfig.connectTimeout,
      receiveTimeout: AppConfig.receiveTimeout,
      sendTimeout: AppConfig.sendTimeout,
    ));
    
    // Add logging interceptor in debug mode
    if (kDebugMode) {
      _dio.interceptors.add(LogInterceptor(
        requestBody: true,
        responseBody: true,
        error: true,
      ));
    }

    // Add interceptor for authentication
    _dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (options, handler) async {
          try {
            final token = await _authService.getIdToken();
            if (token != null) {
              options.headers['Authorization'] = 'Bearer $token';
            }
          } catch (e) {
            // If token fetch fails, continue without it (will get 403)
          }
          handler.next(options);
        },
        onError: (error, handler) async {
          // Handle 401/403 - try to refresh token and retry once
          if (error.response?.statusCode == 401 || 
              error.response?.statusCode == 403) {
            try {
              // Force refresh token
              final newToken = await _authService.getIdToken(true);
              if (newToken != null) {
                // Retry the request
                final opts = error.requestOptions;
                opts.headers['Authorization'] = 'Bearer $newToken';
                final response = await _dio.fetch(opts);
                handler.resolve(response);
                return;
              }
            } catch (e) {
              // Re-authentication needed
              handler.reject(
                DioException(
                  requestOptions: error.requestOptions,
                  error: 'Session expired. Please re-authenticate.',
                  response: error.response,
                ),
              );
              return;
          }
          }
          handler.next(error);
        },
      ),
    );
  }

  /// GET request
  Future<Response> get(String path, {Map<String, dynamic>? queryParameters}) async {
    try {
      if (kDebugMode) {
        debugPrint('API GET: ${AppConfig.baseUrl}$path');
      }
      return await _dio.get(path, queryParameters: queryParameters);
    } on DioException catch (e) {
      if (kDebugMode) {
        debugPrint('API Error GET $path: ${e.type} - ${e.message}');
        debugPrint('Status: ${e.response?.statusCode}');
        debugPrint('Response: ${e.response?.data}');
      }
      throw _handleError(e);
    }
  }

  /// POST request
  Future<Response> post(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
  }) async {
    try {
      if (kDebugMode) {
        debugPrint('API POST: ${AppConfig.baseUrl}$path');
      }
      return await _dio.post(path, data: data, queryParameters: queryParameters);
    } on DioException catch (e) {
      if (kDebugMode) {
        debugPrint('API Error POST $path: ${e.type} - ${e.message}');
        debugPrint('Status: ${e.response?.statusCode}');
        debugPrint('Response: ${e.response?.data}');
      }
      throw _handleError(e);
    }
  }

  /// POST request returning raw bytes (e.g. for /generate-audio MP3).
  Future<List<int>> postBytes(
    String path, {
    dynamic data,
    Map<String, dynamic>? queryParameters,
  }) async {
    try {
      if (kDebugMode) {
        debugPrint('API POST bytes: ${AppConfig.baseUrl}$path');
      }
      final response = await _dio.post<List<int>>(
        path,
        data: data,
        queryParameters: queryParameters,
        options: Options(responseType: ResponseType.bytes),
      );
      final body = response.data;
      if (body == null) {
        throw ApiException(
          message: 'Empty response body',
          url: '${AppConfig.baseUrl}$path',
          statusCode: response.statusCode,
        );
      }
      return body;
    } on DioException catch (e) {
      if (kDebugMode) {
        debugPrint('API Error POST $path: ${e.type} - ${e.message}');
        debugPrint('Status: ${e.response?.statusCode}');
      }
      throw _handleError(e);
    }
  }

  /// Handle errors with detailed information
  ApiException _handleError(DioException error) {
    final requestUrl = '${error.requestOptions.baseUrl}${error.requestOptions.path}';
    final statusCode = error.response?.statusCode;
    
    String message;
    if (error.type == DioExceptionType.connectionTimeout ||
        error.type == DioExceptionType.receiveTimeout ||
        error.type == DioExceptionType.sendTimeout) {
      message = 'Network timeout. Check your connection.';
    } else if (error.type == DioExceptionType.connectionError) {
      message = 'Cannot reach the server. Check internet and that the backend URL is correct.';
    } else if (error.response != null) {
      if (statusCode == 401 || statusCode == 403) {
        message = 'Authentication failed (${statusCode})';
      } else if (statusCode == 404) {
        message = 'Backend not found (404). The server may be down or the app may be using the wrong backend URL.';
      } else if (statusCode == 500) {
        message = 'Server error (${statusCode})';
      } else {
        message = 'HTTP ${statusCode}: ${error.response?.statusMessage ?? 'Unknown'}';
      }
    } else {
      message = 'Network error: ${error.message ?? error.type.toString()}';
    }
    
    return ApiException(
      message: message,
      url: requestUrl,
      statusCode: statusCode,
      dioExceptionType: error.type,
    );
  }
}

/// Detailed API exception with URL and status code
class ApiException implements Exception {
  final String message;
  final String url;
  final int? statusCode;
  final DioExceptionType? dioExceptionType;

  ApiException({
    required this.message,
    required this.url,
    this.statusCode,
    this.dioExceptionType,
  });

  @override
  String toString() {
    final parts = [message];
    if (statusCode != null) {
      parts.add('Status: $statusCode');
    }
    parts.add('URL: $url');
    return parts.join('\n');
  }
}
