import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:just_audio/just_audio.dart';
import '../state/dictionary_provider.dart';
import '../api/models.dart';
import '../services/audio_cache_service.dart';

/// Dictionary screen: type English, get Ika words; Show all; Play/Download audio
class DictionaryScreen extends ConsumerStatefulWidget {
  const DictionaryScreen({super.key});

  @override
  ConsumerState<DictionaryScreen> createState() => _DictionaryScreenState();
}

class _DictionaryScreenState extends ConsumerState<DictionaryScreen> {
  final TextEditingController _searchController = TextEditingController();
  final FocusNode _focusNode = FocusNode();

  @override
  void dispose() {
    _searchController.dispose();
    _focusNode.dispose();
    super.dispose();
  }

  void _search() {
    ref.read(dictionaryProvider.notifier).search(_searchController.text);
  }

  void _showAll() {
    ref.read(dictionaryProvider.notifier).showAll();
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
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _searchController,
                    focusNode: _focusNode,
                    decoration: const InputDecoration(
                      hintText: 'Type an English word (e.g. hello, run, water)',
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
                                child: CircularProgressIndicator(strokeWidth: 2),
                              )
                            : const Icon(Icons.search),
                        label: Text(state.isLoading ? 'Searching...' : 'Look up'),
                      ),
                      const SizedBox(width: 12),
                      OutlinedButton.icon(
                        onPressed: state.isLoading ? null : _showAll,
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
              state.isShowAll ? 'All entries' : 'Ika words',
              style: Theme.of(context).textTheme.titleMedium,
            ),
            const SizedBox(height: 8),
            ...state.entries.map((e) => _EntryCard(entry: e)),
          ],
          if (state.suggestions.isNotEmpty) ...[
            const SizedBox(height: 16),
            Text(
              'Did you mean?',
              style: Theme.of(context).textTheme.titleSmall,
            ),
            const SizedBox(height: 4),
            ...state.suggestions.take(5).map((s) => Card(
                  margin: const EdgeInsets.only(bottom: 6),
                  child: ListTile(
                    title: Text('${s['en']} → ${s['ika']}'),
                    subtitle: s['domain'] != null ? Text(s['domain'].toString()) : null,
                    onTap: () {
                      _searchController.text = s['en']?.toString() ?? '';
                      _search();
                    },
                  ),
                )),
          ],
          if (!state.isLoading &&
              state.lastQuery.isNotEmpty &&
              state.entries.isEmpty &&
              state.error == null &&
              state.suggestions.isEmpty) ...[
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Text(
                  'No Ika words found for "${state.lastQuery}". Try another word or tap "Show all".',
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

class _EntryCard extends ConsumerWidget {
  final DictionaryEntry entry;

  const _EntryCard({required this.entry});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final hasAudio = entry.docId != null && entry.docId!.isNotEmpty;
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
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (hasAudio) _AudioButton(lexiconId: entry.docId!),
            IconButton(
              icon: const Icon(Icons.copy),
              onPressed: () {
                Clipboard.setData(ClipboardData(text: entry.targetText));
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Ika word copied')),
                );
              },
              tooltip: 'Copy Ika word',
            ),
          ],
        ),
      ),
    );
  }
}

class _AudioButton extends ConsumerStatefulWidget {
  final String lexiconId;

  const _AudioButton({required this.lexiconId});

  @override
  ConsumerState<_AudioButton> createState() => _AudioButtonState();
}

class _AudioButtonState extends ConsumerState<_AudioButton> {
  bool _loading = false;
  String? _error;
  AudioPlayer? _player;

  @override
  void dispose() {
    _player?.dispose();
    super.dispose();
  }

  /// Uses AudioCacheService only (GET /api/audio?id=, cache ika_audio_<id>.m4a, play via local just_audio).
  Future<void> _play() async {
    setState(() { _loading = true; _error = null; });
    try {
      final cache = ref.read(audioCacheServiceProvider);
      final path = await cache.getPathForLexiconId(widget.lexiconId);
      _player ??= AudioPlayer();
      await _player!.setFilePath(path);
      await _player!.play();
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _download() async {
    setState(() { _loading = true; _error = null; });
    try {
      final cache = ref.read(audioCacheServiceProvider);
      await cache.getPathForLexiconId(widget.lexiconId);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Audio downloaded and cached')),
        );
      }
    } catch (e) {
      setState(() => _error = e.toString());
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_error != null) {
      return Tooltip(
        message: _error!,
        child: Icon(Icons.error_outline, color: Colors.red[700], size: 22),
      );
    }
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        IconButton(
          icon: _loading
              ? const SizedBox(
                  width: 20,
                  height: 20,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : const Icon(Icons.play_circle_outline),
          onPressed: _loading ? null : _play,
          tooltip: 'Play audio',
        ),
        IconButton(
          icon: const Icon(Icons.download),
          onPressed: _loading ? null : _download,
          tooltip: 'Download audio',
        ),
      ],
    );
  }
}
