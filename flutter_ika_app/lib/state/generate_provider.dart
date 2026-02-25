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

  /// Generate content via POST /generate or /generate-story, /generate-poem, /generate-lecture
  Future<void> generate({
    required String prompt,
    String kind = 'story',
    String length = 'medium',
  }) async {
    state = state.copyWith(isLoading: true, error: null);
    try {
      final GenerateResponse res;
      final req = GenerateRequest(prompt: prompt, length: length);
      switch (kind) {
        case 'story':
          res = await _api.generateStory(req);
          break;
        case 'poem':
          res = await _api.generatePoem(req);
          break;
        case 'lecture':
          res = await _api.generateLecture(req);
          break;
        default:
          res = await _api.generate(
            kind: kind,
            topic: prompt,
            tone: 'neutral',
            length: length,
          );
      }
      state = state.copyWith(
        isLoading: false,
        result: res,
        clearError: true,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
      );
    }
  }

  /// Generate audio for current result (POST /generate-audio then GET /audio/{filename})
  Future<String?> generateAudio() async {
    if (state.result == null || state.result!.text.isEmpty) {
      return null;
    }

    if (state.audioUrl != null) {
      return state.audioUrl;
    }

    try {
      final request = GenerateAudioRequest(text: state.result!.text);
      final res = await _api.generateAudio(request);
      final bytes = await _api.getAudioByFilename(res.filename);
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
