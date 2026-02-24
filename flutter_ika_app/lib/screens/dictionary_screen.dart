import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../state/dictionary_provider.dart';
import '../api/models.dart';

/// Dictionary screen: type English, get Ika words
class DictionaryScreen extends ConsumerStatefulWidget {
  const DictionaryScreen({super.key});

  @override
  ConsumerState<DictionaryScreen> createState() => _DictionaryScreenState();
}

class _DictionaryScreenState extends ConsumerState<DictionaryScreen> {
  final TextEditingController _searchController = TextEditingController();
  final FocusNode _focusNode = FocusNode();
  bool _initialLoadDone = false;

  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) {
      if (!_initialLoadDone) {
        _initialLoadDone = true;
        ref.read(dictionaryProvider.notifier).search('');
      }
    });
  }

  @override
  void dispose() {
    _searchController.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  void _search() {
    ref.read(dictionaryProvider.notifier).search(_searchController.text);
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(dictionaryProvider);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    'English → Ika',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          color: Colors.black87,
                          fontWeight: FontWeight.w600,
                        ),
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _searchController,
                    focusNode: _focusNode,
                    decoration: const InputDecoration(
                      hintText: 'Type an English word or leave empty for all',
                      border: OutlineInputBorder(),
                      prefixIcon: Icon(Icons.search),
                    ),
                    textInputAction: TextInputAction.search,
                    onSubmitted: (_) => _search(),
                  ),
                  const SizedBox(height: 12),
                  Row(
                    children: [
                      FilledButton.icon(
                        onPressed: state.isLoading ? null : _search,
                        icon: state.isLoading
                            ? const SizedBox(
                                width: 20,
                                height: 20,
                                child: CircularProgressIndicator(
                                    strokeWidth: 2, color: Colors.white),
                              )
                            : const Icon(Icons.search),
                        label: Text(state.isLoading ? 'Loading...' : 'Look up'),
                      ),
                      const SizedBox(width: 8),
                      OutlinedButton.icon(
                        onPressed: state.isLoading
                            ? null
                            : () {
                                _searchController.clear();
                                ref.read(dictionaryProvider.notifier).search('');
                              },
                        icon: const Icon(Icons.list),
                        label: const Text('Show all'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          if (state.error != null) ...[
            const SizedBox(height: 16),
            Card(
              color: Colors.red[50],
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Text(
                  state.error!,
                  style: TextStyle(color: Colors.red[900]),
                ),
              ),
            ),
          ],
          if (state.entries.isNotEmpty) ...[
            const SizedBox(height: 16),
            Text(
              state.lastQuery == 'all'
                  ? 'All Ika words (${state.entries.length})'
                  : 'Ika words (${state.entries.length})',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                    color: Colors.black87,
                    fontWeight: FontWeight.w600,
                  ),
            ),
            const SizedBox(height: 8),
            SizedBox(
              height: MediaQuery.of(context).size.height * 0.5,
              child: ListView.builder(
                itemCount: state.entries.length,
                itemBuilder: (context, i) =>
                    _EntryCard(entry: state.entries[i]),
              ),
            ),
          ],
          if (!state.isLoading &&
              state.lastQuery.isNotEmpty &&
              state.lastQuery != 'all' &&
              state.entries.isEmpty &&
              state.error == null) ...[
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Text(
                  'No Ika words found for "${state.lastQuery}". Try another word or a shorter prefix.',
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: Colors.grey[700],
                      ),
                ),
              ),
            ),
          ],
        ],
      ),
    );
  }
}

class _EntryCard extends StatelessWidget {
  final DictionaryEntry entry;

  const _EntryCard({required this.entry});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        title: Row(
          children: [
            Expanded(
              child: Text(
                entry.sourceText,
                style: const TextStyle(fontWeight: FontWeight.w500),
              ),
            ),
            Icon(Icons.arrow_forward, size: 18, color: Colors.grey[600]),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                entry.targetText,
                style: TextStyle(
                  fontWeight: FontWeight.w600,
                  color: Theme.of(context).colorScheme.primary,
                ),
              ),
            ),
          ],
        ),
        subtitle: (entry.pos != null || entry.domain != null)
            ? Padding(
                padding: const EdgeInsets.only(top: 4),
                child: Text(
                  [
                    if (entry.pos != null) entry.pos,
                    if (entry.domain != null) entry.domain,
                  ].join(' • '),
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: Colors.grey[600],
                      ),
                ),
              )
            : null,
        trailing: IconButton(
          icon: const Icon(Icons.copy),
          onPressed: () {
            Clipboard.setData(ClipboardData(text: entry.targetText));
            ScaffoldMessenger.of(context).showSnackBar(
              const SnackBar(content: Text('Ika word copied')),
            );
          },
          tooltip: 'Copy Ika word',
        ),
      ),
    );
  }
}
