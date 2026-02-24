import 'package:firebase_auth/firebase_auth.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../auth/firebase_auth_service.dart';
import '../api/api_client.dart';
import '../api/ika_api.dart';

/// Firebase initialization provider
final firebaseInitializedProvider = FutureProvider<bool>((ref) async {
  await Firebase.initializeApp();
  return true;
});

/// Auth state provider
final authStateProvider = StreamProvider<User?>((ref) {
  return FirebaseAuth.instance.authStateChanges();
});

/// Auth service provider
final authServiceProvider = Provider<FirebaseAuthService>((ref) {
  return FirebaseAuthService();
});

/// API client provider
final apiClientProvider = Provider<ApiClient>((ref) {
  final authService = ref.watch(firebaseAuthServiceProvider);
  return ApiClient(authService);
});

/// IKA API provider
final ikaApiProvider = Provider<IkaApi>((ref) {
  final apiClient = ref.watch(apiClientProvider);
  return IkaApi(apiClient);
});

/// Health check provider with detailed error
final healthCheckProvider = FutureProvider<HealthCheckResult>((ref) async {
  try {
    final api = ref.watch(ikaApiProvider);
    final response = await api.healthCheck();
    return HealthCheckResult(success: response.ok, error: null);
  } catch (e) {
    return HealthCheckResult(success: false, error: e.toString());
  }
});

/// Health check result
class HealthCheckResult {
  final bool success;
  final String? error;

  HealthCheckResult({required this.success, this.error});
}

/// App initialization provider (combines Firebase init + auth + health check)
final appInitializationProvider = FutureProvider<AppInitState>((ref) async {
  // Wait for Firebase initialization
  await ref.watch(firebaseInitializedProvider.future);
  
  // Sign in anonymously
  final authService = ref.watch(firebaseAuthServiceProvider);
  try {
    await authService.signInAnonymously();
  } catch (e) {
    return AppInitState.error('Failed to sign in: $e');
  }
  
  // Check backend health
  final healthCheckResult = await ref.watch(healthCheckProvider.future);
  if (!healthCheckResult.success) {
    final errorMsg = healthCheckResult.error ?? 'Unknown error';
    return AppInitState.error('Health check failed', details: errorMsg);
  }
  
  return AppInitState.success();
});

/// App initialization state
class AppInitState {
  final bool isSuccess;
  final String? error;
  final String? details; // Detailed error information (URL, status code, etc.)

  AppInitState.success() : isSuccess = true, error = null, details = null;
  AppInitState.error(this.error, {this.details}) : isSuccess = false;
}
