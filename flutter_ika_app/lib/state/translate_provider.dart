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

  /// Translate text (EN→Ika or Ika→EN via POST /translate)
  Future<void> translate(String text, String tense) async {
    state = state.copyWith(isLoading: true, error: null);
    final trimmed = text.trim();
    if (trimmed.isEmpty) {
      state = state.copyWith(isLoading: false);
      return;
    }

    try {
      final mode = _isIkaInput(trimmed) ? 'ika_to_en' : 'en_to_ika';
      final res = await _api.translate(TranslateRequest(
        text: trimmed,
        tense: tense,
        mode: mode,
      ));
      final meta = res.meta;
      if (mode == 'ika_to_en') {
        final meanings = meta['meanings'] is List ? List<String>.from(meta['meanings'] as List) : <String>[];
        final suggestions = meta['suggestions'] as List?;
        final textOut = res.text.isNotEmpty
            ? res.text
            : (meanings.isNotEmpty
                ? meanings.join(', ')
                : (suggestions != null && suggestions.isNotEmpty
                    ? 'Suggestions: ${suggestions.take(3).map((s) => (s is Map ? s['en'] : s).toString()).join(', ')}'
                    : 'No English meaning found'));
        state = state.copyWith(
          isLoading: false,
          result: TranslateResponse(
            text: textOut,
            meta: {'direction': 'ika_en', 'meanings': meanings, 'suggestions': suggestions ?? []},
          ),
          clearError: true,
        );
      } else {
        final found = meta['found'] == true;
        final candidates = meta['candidates'] is List ? meta['candidates'] as List : <dynamic>[];
        final hasResult = (found && candidates.isNotEmpty) || res.text.isNotEmpty;
        if (hasResult) {
          final ika = res.text.isNotEmpty
              ? res.text
              : (candidates.isNotEmpty
                  ? (candidates.first is Map
                      ? ((candidates.first as Map)['ika'] ?? (candidates.first as Map)['target_text'] ?? res.text)
                      : res.text)
                  : res.text);
          state = state.copyWith(
            isLoading: false,
            result: TranslateResponse(
              text: ika.toString(),
              meta: {
                'direction': 'en_ika',
                'candidates': candidates,
                'tense': tense,
              },
            ),
            clearError: true,
          );
        } else {
          final suggestionText = res.text.isNotEmpty
              ? res.text
              : (meta['suggestions'] is List && (meta['suggestions'] as List).isNotEmpty
                  ? 'Suggestions: ${(meta['suggestions'] as List).take(3).map((s) => (s is Map ? s['en'] : s).toString()).join(', ')}'
                  : 'No Ika translation found');
          state = state.copyWith(
            isLoading: false,
            result: TranslateResponse(
              text: suggestionText,
              meta: {'direction': 'en_ika', 'found': false},
            ),
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
    state = TranslateState();
  }
}

/// Translate provider
final translateProvider =
    StateNotifierProvider<TranslateNotifier, TranslateState>((ref) {
  final api = ref.watch(ikaApiProvider);
  return TranslateNotifier(api);
});
