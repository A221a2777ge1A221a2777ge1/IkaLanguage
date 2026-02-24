import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../state/library_provider.dart';
import '../widgets/result_card.dart';
import 'detail_screen.dart';

/// Library screen
class LibraryScreen extends ConsumerWidget {
  const LibraryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final libraryState = ref.watch(libraryProvider);

    if (libraryState.isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (libraryState.items.isEmpty) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.library_books, size: 64, color: Colors.grey[400]),
            const SizedBox(height: 16),
            Text(
              'No items in library',
              style: Theme.of(context).textTheme.titleLarge?.copyWith(
                    color: Colors.grey[600],
                  ),
            ),
            const SizedBox(height: 8),
            Text(
              'Save translations or generations to see them here',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Colors.grey[600],
                  ),
            ),
          ],
        ),
      );
    }

    return RefreshIndicator(
      onRefresh: () async {
        // Reload items
        ref.invalidate(libraryProvider);
      },
      child: ListView.builder(
        itemCount: libraryState.items.length,
        itemBuilder: (context, index) {
          final item = libraryState.items[index];
          return ResultCard(
            result: item,
            onTap: () {
              Navigator.of(context).push(
                MaterialPageRoute(
                  builder: (_) => DetailScreen(result: item),
                ),
              );
            },
            onPlayAudio: item.audioUrl != null
                ? () {
                    // Navigate to detail to play audio
                    Navigator.of(context).push(
                      MaterialPageRoute(
                        builder: (_) => DetailScreen(result: item),
                      ),
                    );
                  }
                : null,
          );
        },
      ),
    );
  }
}
