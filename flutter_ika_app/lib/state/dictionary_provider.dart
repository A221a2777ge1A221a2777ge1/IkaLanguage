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
  /// When no exact match, suggestions from API (list of {en, ika, id, domain})
  final List<Map<String, dynamic>> suggestions;
  /// true when showing "all" list instead of search results
  final bool isShowAll;

  DictionaryState({
    this.isLoading = false,
    this.error,
    this.entries = const [],
    this.lastQuery = '',
    this.suggestions = const [],
    this.isShowAll = false,
  });

  DictionaryState copyWith({
    bool? isLoading,
    String? error,
    List<DictionaryEntry>? entries,
    String? lastQuery,
    List<Map<String, dynamic>>? suggestions,
    bool? isShowAll,
  }) {
    return DictionaryState(
      isLoading: isLoading ?? this.isLoading,
      error: error,
      entries: entries ?? this.entries,
      lastQuery: lastQuery ?? this.lastQuery,
      suggestions: suggestions ?? this.suggestions,
      isShowAll: isShowAll ?? this.isShowAll,
    );
  }
}

/// Dictionary notifier
class DictionaryNotifier extends StateNotifier<DictionaryState> {
  final IkaApi _api;

  DictionaryNotifier(this._api) : super(DictionaryState());

  Future<void> search(String query) async {
    final q = query.trim();
    if (q.isEmpty) {
      state = state.copyWith(
        entries: [],
        error: null,
        lastQuery: '',
        suggestions: [],
        isShowAll: false,
      );
      return;
    }

    state = state.copyWith(isLoading: true, error: null, lastQuery: q, suggestions: []);

    try {
      final response = await _api.dictionaryLookup(q);
      state = state.copyWith(
        isLoading: false,
        entries: response.entries,
        error: null,
        isShowAll: false,
      );
      if (response.entries.isEmpty) {
        final lookup = await _api.translateEnToIka(q);
        state = state.copyWith(suggestions: lookup.suggestions);
      }
    } catch (e) {
      state = state.copyWith(
        isLoading: false,
        error: e.toString(),
        entries: [],
      );
    }
  }

  Future<void> showAll({String? domain}) async {
    state = state.copyWith(isLoading: true, error: null, isShowAll: true);
    try {
      final response = await _api.listDictionary(domain: domain, limit: 500);
      state = state.copyWith(
        isLoading: false,
        entries: response.entries,
        error: null,
        lastQuery: '',
        suggestions: [],
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
