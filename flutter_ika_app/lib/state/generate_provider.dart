import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../api/ika_api.dart';
import '../api/models.dart';
import 'auth_provider.dart';

/// Generate state
class GenerateState {
  final bool isLoading;
  final String? error;
  final GenerateResponse? result;
  final String? audioUrl; // Cached audio URL

  GenerateState({
    this.isLoading = false,
    this.error,
    this.result,
    this.audioUrl,
  });

  GenerateState copyWith({
    bool? isLoading,
    String? error,
    GenerateResponse? result,
    String? audioUrl,
  }) {
    return GenerateState(
      isLoading: isLoading ?? this.isLoading,
      error: error ?? this.error,
      result: result ?? this.result,
      audioUrl: audioUrl ?? this.audioUrl,
    );
  }
}

/// Generate notifier
class GenerateNotifier extends StateNotifier<GenerateState> {
  final IkaApi _api;

  GenerateNotifier(this._api) : super(GenerateState());

  /// Generate story (calls POST /generate-story)
  Future<void> generate({
    required String prompt,
    String length = 'short',
  }) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final request = GenerateRequest(prompt: prompt, length: length);
      final response = await _api.generateStory(request);
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
      final response = await _api.generateAudio(request);
      if (response == null) {
        return null; // 501 Not Implemented — UI shows friendly message
      }
      state = state.copyWith(audioUrl: response.audioUrl);
      return response.audioUrl;
    } catch (e) {
      state = state.copyWith(error: 'Failed to generate audio: $e');
      return null;
    }
  }

  /// Clear state
  void clear() {
    state = GenerateState();
  }
}

/// Generate provider
final generateProvider =
    StateNotifierProvider<GenerateNotifier, GenerateState>((ref) {
  final api = ref.watch(ikaApiProvider);
  return GenerateNotifier(api);
});
