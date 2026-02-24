import 'dart:io';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';
import '../api/ika_api.dart';
import '../api/models.dart';
import 'auth_provider.dart';

/// Translate state
class TranslateState {
  final bool isLoading;
  final String? error;
  final TranslateResponse? result;
  final String? audioUrl; // Cached audio URL

  TranslateState({
    this.isLoading = false,
    this.error,
    this.result,
    this.audioUrl,
  });

  TranslateState copyWith({
    bool? isLoading,
    String? error,
    TranslateResponse? result,
    String? audioUrl,
  }) {
    return TranslateState(
      isLoading: isLoading ?? this.isLoading,
      error: error ?? this.error,
      result: result ?? this.result,
      audioUrl: audioUrl ?? this.audioUrl,
    );
  }
}

/// Translate notifier
class TranslateNotifier extends StateNotifier<TranslateState> {
  final IkaApi _api;

  TranslateNotifier(this._api) : super(TranslateState());

  /// Translate text
  Future<void> translate(String text, String tense) async {
    state = state.copyWith(isLoading: true, error: null);
    
    try {
      final request = TranslateRequest(text: text, tense: tense);
      final response = await _api.translate(request);
      state = state.copyWith(
        isLoading: false,
        result: response,
        error: null,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  /// Generate audio for current result
  Future<String?> generateAudio() async {
    if (state.result == null || state.result!.text.isEmpty) {
      return null;
    }

    // Check if we already have audio URL for this text
    if (state.audioUrl != null) {
      return state.audioUrl;
    }

    try {
      final request = GenerateAudioRequest(text: state.result!.text);
      final bytes = await _api.generateAudioBytes(request);
      final dir = await getTemporaryDirectory();
      final file = File('${dir.path}/ika_${DateTime.now().millisecondsSinceEpoch}.mp3');
      await file.writeAsBytes(bytes);
      state = state.copyWith(audioUrl: file.path);
      return file.path;
    } catch (e) {
      state = state.copyWith(error: 'Failed to generate audio: $e');
      return null;
    }
  }

  /// Clear state
  void clear() {
    state = TranslateState();
  }
}

/// Translate provider
final translateProvider =
    StateNotifierProvider<TranslateNotifier, TranslateState>((ref) {
  final api = ref.watch(ikaApiProvider);
  return TranslateNotifier(api);
});
