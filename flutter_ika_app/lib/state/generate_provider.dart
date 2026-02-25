import 'dart:io';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:path_provider/path_provider.dart';
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
    bool clearError = false,
    GenerateResponse? result,
    String? audioUrl,
  }) {
    return GenerateState(
      isLoading: isLoading ?? this.isLoading,
      error: clearError ? null : (error ?? this.error),
      result: result ?? this.result,
      audioUrl: audioUrl ?? this.audioUrl,
    );
  }
}

/// Generate notifier
class GenerateNotifier extends StateNotifier<GenerateState> {
  final IkaApi _api;

  GenerateNotifier(this._api) : super(GenerateState());

  /// Generate content via POST /api/generate (sentence|story|poem|lecture)
  Future<void> generate({
    required String prompt,
    String kind = 'story',
    String length = 'medium',
  }) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final res = await _api.generateApi(
        mode: kind,
        topic: prompt,
        length: length,
        inputLang: 'en',
      );
      state = state.copyWith(
        isLoading: false,
        result: GenerateResponse(
          text: res.text,
          meta: {
            ...res.meta,
            if (res.missingConcepts != null) 'missing_concepts': res.missingConcepts,
          },
        ),
        clearError: true,
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
    state = GenerateState();
  }
}

/// Generate provider
final generateProvider =
    StateNotifierProvider<GenerateNotifier, GenerateState>((ref) {
  final api = ref.watch(ikaApiProvider);
  return GenerateNotifier(api);
});
