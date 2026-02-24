import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:hive_flutter/hive_flutter.dart';
import 'package:uuid/uuid.dart';
import '../api/models.dart';

/// Library state
class LibraryState {
  final List<GenerationResult> items;
  final bool isLoading;

  LibraryState({
    this.items = const [],
    this.isLoading = false,
  });

  LibraryState copyWith({
    List<GenerationResult>? items,
    bool? isLoading,
  }) {
    return LibraryState(
      items: items ?? this.items,
      isLoading: isLoading ?? this.isLoading,
    );
  }
}

/// Library notifier
class LibraryNotifier extends StateNotifier<LibraryState> {
  static const String _boxName = 'generation_results';

  LibraryNotifier() : super(LibraryState()) {
    _loadItems();
  }

  /// Load items from Hive
  Future<void> _loadItems() async {
    state = state.copyWith(isLoading: true);
    try {
      final box = await Hive.openBox<Map>(_boxName);
      final items = box.values
          .map((json) => GenerationResult.fromJson(Map<String, dynamic>.from(json)))
          .toList()
        ..sort((a, b) => b.createdAt.compareTo(a.createdAt)); // Newest first
      state = state.copyWith(items: items, isLoading: false);
    } catch (e) {
      state = state.copyWith(isLoading: false);
    }
  }

  /// Save item to library
  Future<void> saveItem(GenerationResult item) async {
    try {
      final box = await Hive.openBox<Map>(_boxName);
      await box.put(item.id, item.toJson());
      await _loadItems();
    } catch (e) {
      // Handle error
    }
  }

  /// Delete item
  Future<void> deleteItem(String id) async {
    try {
      final box = await Hive.openBox<Map>(_boxName);
      await box.delete(id);
      await _loadItems();
    } catch (e) {
      // Handle error
    }
  }

  /// Update item audio URL
  Future<void> updateItemAudioUrl(String id, String audioUrl) async {
    try {
      final box = await Hive.openBox<Map>(_boxName);
      final itemJson = box.get(id);
      if (itemJson != null) {
        final item = GenerationResult.fromJson(Map<String, dynamic>.from(itemJson));
        item.audioUrl = audioUrl;
        await box.put(id, item.toJson());
        await _loadItems();
      }
    } catch (e) {
      // Handle error
    }
  }

  /// Create result from translate
  Future<GenerationResult> createFromTranslate({
    required String input,
    required TranslateResponse response,
    String? audioUrl,
  }) async {
    final result = GenerationResult(
      id: const Uuid().v4(),
      type: 'translate',
      input: input,
      outputText: response.text,
      meta: response.meta,
      createdAt: DateTime.now(),
      audioUrl: audioUrl,
    );
    await saveItem(result);
    return result;
  }

  /// Create result from generate
  Future<GenerationResult> createFromGenerate({
    required String kind,
    required String topic,
    required GenerateResponse response,
    String? audioUrl,
  }) async {
    final result = GenerationResult(
      id: const Uuid().v4(),
      type: kind,
      input: topic,
      outputText: response.text,
      meta: response.meta,
      createdAt: DateTime.now(),
      audioUrl: audioUrl,
    );
    await saveItem(result);
    return result;
  }
}

/// Library provider
final libraryProvider =
    StateNotifierProvider<LibraryNotifier, LibraryState>((ref) {
  return LibraryNotifier();
});
