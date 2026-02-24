import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import '../api/models.dart';
import '../state/auth_provider.dart';
import '../state/library_provider.dart';
import '../widgets/audio_player_widget.dart';
import '../widgets/meta_expandable.dart';

/// Detail screen for library item
class DetailScreen extends ConsumerStatefulWidget {
  final GenerationResult result;

  const DetailScreen({
    super.key,
    required this.result,
  });

  @override
  ConsumerState<DetailScreen> createState() => _DetailScreenState();
}

class _DetailScreenState extends ConsumerState<DetailScreen> {
  String? _audioUrl;
  bool _isGeneratingAudio = false;

  @override
  void initState() {
    super.initState();
    _audioUrl = widget.result.audioUrl;
  }

  Future<void> _generateAudio() async {
    if (_isGeneratingAudio) return;

    setState(() {
      _isGeneratingAudio = true;
    });

    try {
      final api = ref.read(ikaApiProvider);
      final request = GenerateAudioRequest(text: widget.result.outputText);
      final response = await api.generateAudio(request);

      setState(() {
        _isGeneratingAudio = false;
      });

      if (response == null) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
                content: Text('Audio generation is not enabled on the server yet.')),
          );
        }
        return;
      }

      setState(() {
        _audioUrl = response.audioUrl;
      });

      ref.read(libraryProvider.notifier).updateItemAudioUrl(
        widget.result.id,
        response.audioUrl,
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text('Audio generated successfully')),
        );
      }
    } catch (e) {
      setState(() {
        _isGeneratingAudio = false;
      });
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed to generate audio: $e')),
        );
      }
    }
  }

  void _copyText() {
    Clipboard.setData(ClipboardData(text: widget.result.outputText));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Copied to clipboard')),
    );
  }

  void _shareText() {
    // Basic share - can be enhanced with share_plus package
    Clipboard.setData(ClipboardData(text: widget.result.outputText));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Copied to clipboard (share)')),
    );
  }

  void _deleteItem() {
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Delete Item'),
        content: const Text('Are you sure you want to delete this item?'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('Cancel'),
          ),
          TextButton(
            onPressed: () {
              ref.read(libraryProvider.notifier).deleteItem(widget.result.id);
              Navigator.of(context).pop();
              Navigator.of(context).pop(); // Go back to library
            },
            child: const Text('Delete'),
          ),
        ],
      ),
    );
  }

  String get _typeLabel {
    switch (widget.result.type) {
      case 'translate':
        return 'Translation';
      case 'poem':
        return 'Poem';
      case 'story':
        return 'Story';
      case 'lecture':
        return 'Lecture';
      default:
        return widget.result.type;
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_typeLabel),
        actions: [
          IconButton(
            icon: const Icon(Icons.copy),
            onPressed: _copyText,
            tooltip: 'Copy',
          ),
          IconButton(
            icon: const Icon(Icons.share),
            onPressed: _shareText,
            tooltip: 'Share',
          ),
          IconButton(
            icon: const Icon(Icons.delete),
            onPressed: _deleteItem,
            tooltip: 'Delete',
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // Header info
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Input',
                      style: Theme.of(context).textTheme.titleSmall,
                    ),
                    const SizedBox(height: 4),
                    Text(
                      widget.result.input,
                      style: Theme.of(context).textTheme.bodyLarge,
                    ),
                    const SizedBox(height: 16),
                    Text(
                      'Created: ${DateFormat('MMM d, y • h:mm a').format(widget.result.createdAt)}',
                      style: Theme.of(context).textTheme.bodySmall,
                    ),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 16),

            // Output text
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Ika Text',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 8),
                    SelectableText(
                      widget.result.outputText,
                      style: Theme.of(context).textTheme.bodyLarge,
                    ),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 16),

            // Audio player
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Audio',
                      style: Theme.of(context).textTheme.titleMedium,
                    ),
                    const SizedBox(height: 8),
                    if (_isGeneratingAudio)
                      const Center(
                        child: Padding(
                          padding: EdgeInsets.all(16.0),
                          child: Column(
                            children: [
                              CircularProgressIndicator(),
                              SizedBox(height: 8),
                              Text('Generating audio...'),
                            ],
                          ),
                        ),
                      )
                    else
                      AudioPlayerWidget(
                        audioUrl: _audioUrl,
                        onGenerateAudio: _generateAudio,
                      ),
                  ],
                ),
              ),
            ),

            // Metadata
            MetaExpandable(meta: widget.result.meta),
          ],
        ),
      ),
    );
  }
}
