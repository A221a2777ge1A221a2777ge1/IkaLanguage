import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// Firebase Authentication Service
class FirebaseAuthService {
  final FirebaseAuth _auth = FirebaseAuth.instance;
  
  /// Get current user
  User? get currentUser => _auth.currentUser;
  
  /// Sign in anonymously
  Future<UserCredential> signInAnonymously() async {
    try {
      final userCredential = await _auth.signInAnonymously();
      return userCredential;
    } catch (e) {
      throw Exception('Failed to sign in anonymously: $e');
    }
  }
  
  /// Get ID token for API authentication
  Future<String?> getIdToken([bool forceRefresh = false]) async {
    try {
      final user = _auth.currentUser;
      if (user == null) {
        // Try to sign in anonymously first
        await signInAnonymously();
        return await _auth.currentUser?.getIdToken(forceRefresh);
      }
      return await user.getIdToken(forceRefresh);
    } catch (e) {
      throw Exception('Failed to get ID token: $e');
    }
  }
  
  /// Sign out
  Future<void> signOut() async {
    await _auth.signOut();
  }
  
  /// Re-authenticate (sign in again)
  Future<UserCredential> reAuthenticate() async {
    await signOut();
    return await signInAnonymously();
  }
}

/// Provider for Firebase Auth Service
final firebaseAuthServiceProvider = Provider<FirebaseAuthService>((ref) {
  return FirebaseAuthService();
});
