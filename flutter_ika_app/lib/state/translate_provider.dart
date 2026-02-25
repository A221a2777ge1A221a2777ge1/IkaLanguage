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
    bool clearError = false,
    TranslateResponse? result,
    String? audioUrl,
  }) {
    return TranslateState(
      isLoading: isLoading ?? this.isLoading,
      error: clearError ? null : (error ?? this.error),
      result: result ?? this.result,
      audioUrl: audioUrl ?? this.audioUrl,
    );
  }
}

/// Heuristic: treat as Ika if text contains common Ika diacritics.
const _ikaLikeChars = 'ịẹọụạẹnyinọnwẹkịelebegwọrị';

bool _looksLikeIka(String text) {
  final t = text.trim().toLowerCase();
  if (t.isEmpty) return false;
  for (int i = 0; i < t.length; i++) {
    if (_ikaLikeChars.contains(t[i])) return true;
  }
  return false;
}

/// Translate notifier
class TranslateNotifier extends StateNotifier<TranslateState> {
  final IkaApi _api;

  TranslateNotifier(this._api) : super(TranslateState());

  /// Input language: auto (detect), en, ika
  String _inputLang = 'auto';

  void setInputLang(String lang) {
    _inputLang = lang;
  }

  bool _isIkaInput(String text) {
    if (_inputLang == 'ika') return true;
    if (_inputLang == 'en') return false;
    return _looksLikeIka(text);
  }

  /// Translate text (EN→Ika or Ika→EN using /api/translate)
  Future<void> translate(String text, String tense) async {
    state = state.copyWith(isLoading: true, error: null);
    final trimmed = text.trim();
    if (trimmed.isEmpty) {
      state = state.copyWith(isLoading: false);
      return;
    }

    try {
      if (_isIkaInput(trimmed)) {
        final res = await _api.translateIkaToEn(trimmed);
        final textOut = res.meanings.isNotEmpty
            ? res.meanings.join(', ')
            : (res.suggestions?.isNotEmpty == true
                ? 'Suggestions: ${res.suggestions!.map((s) => s['en']).join(', ')}'
                : 'No English meaning found');
        state = state.copyWith(
          isLoading: false,
          result: TranslateResponse(text: textOut, meta: {
            'direction': 'ika_en',
            'meanings': res.meanings,
            'suggestions': res.suggestions,
          }),
          clearError: true,
        );
      } else {
        final res = await _api.translateEnToIka(trimmed);
        if (res.found && res.candidates.isNotEmpty) {
          final first = res.candidates.first;
          state = state.copyWith(
            isLoading: false,
            result: TranslateResponse(
              text: first.ika,
              meta: {
                'direction': 'en_ika',
                'candidates': res.candidates.map((c) => {'id': c.id, 'ika': c.ika, 'domain': c.domain}).toList(),
                'tense': tense,
              },
            ),
            clearError: true,
          );
        } else {
          final suggestionText = res.suggestions.isNotEmpty
              ? 'Suggestions: ${res.suggestions.take(3).map((s) => s['en']).join(', ')}'
              : 'No Ika translation found';
          state = state.copyWith(
            isLoading: false,
            result: TranslateResponse(text: suggestionText, meta: {'direction': 'en_ika', 'found': false}),
            clearError: true,
          );
        }
      }
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
