import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../api/ika_api.dart';
import '../api/models.dart';
import 'auth_provider.dart';

/// Dictionary state
class DictionaryState {
  final bool isLoading;
  final String? error;
  final List<DictionaryEntry> entries;
  final String lastQuery;

  DictionaryState({
    this.isLoading = false,
    this.error,
    this.entries = const [],
    this.lastQuery = '',
  });

  DictionaryState copyWith({
    bool? isLoading,
    String? error,
    List<DictionaryEntry>? entries,
    String? lastQuery,
  }) {
    return DictionaryState(
      isLoading: isLoading ?? this.isLoading,
      error: error,
      entries: entries ?? this.entries,
      lastQuery: lastQuery ?? this.lastQuery,
    );
  }
}

/// Dictionary notifier
class DictionaryNotifier extends StateNotifier<DictionaryState> {
  final IkaApi _api;

  DictionaryNotifier(this._api) : super(DictionaryState());

  /// Search by prefix, or load all words when query is empty (up to 700).
  Future<void> search(String query) async {
    final q = query.trim();
    state = state.copyWith(isLoading: true, error: null, lastQuery: q.isEmpty ? 'all' : q);

    try {
      final response = q.isEmpty
          ? await _api.dictionaryLookup('', limit: 700)
          : await _api.dictionaryLookup(q, limit: 200);
      state = state.copyWith(
        isLoading: false,
        entries: response.entries,
        error: null,
      );
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
        entries: [],
      );
    }
  }

  void clear() {
    state = DictionaryState();
  }
}

final dictionaryProvider =
    StateNotifierProvider<DictionaryNotifier, DictionaryState>((ref) {
  final api = ref.watch(ikaApiProvider);
  return DictionaryNotifier(api);
});
