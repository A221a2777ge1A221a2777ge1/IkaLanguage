import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../state/generate_provider.dart';
import '../state/library_provider.dart';
import '../widgets/primary_button.dart';
import '../widgets/audio_player_widget.dart';
import '../widgets/meta_expandable.dart';

/// Generate screen
class GenerateScreen extends ConsumerStatefulWidget {
  const GenerateScreen({super.key});

  @override
  ConsumerState<GenerateScreen> createState() => _GenerateScreenState();
}

class _GenerateScreenState extends ConsumerState<GenerateScreen> {
  final TextEditingController _topicController = TextEditingController();
  String _selectedKind = 'poem';
  String _selectedTone = 'neutral';
  String _selectedLength = 'medium';

  @override
  void dispose() {
    _topicController.dispose();
    super.dispose();
  }

  void _generate() {
    final topic = _topicController.text.trim();
    if (topic.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter a topic')),
      );
      return;
    }

    ref.read(generateProvider.notifier).generate(
      prompt: topic,
      length: _selectedLength,
      kind: _selectedKind,
      tone: _selectedTone,
    );
  }

  Future<void> _generateAudio() async {
    final generateState = ref.read(generateProvider);
    if (generateState.result == null) return;

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Generating audio...')),
    );

    final audioUrl = await ref.read(generateProvider.notifier).generateAudio();

    if (!mounted) return;
    if (audioUrl != null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Audio generated successfully')),
      );
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
            content: Text('Audio generation is not enabled on the server yet.')),
      );
    }
  }

  void _saveToLibrary() {
    final generateState = ref.read(generateProvider);
    if (generateState.result == null) return;

    ref.read(libraryProvider.notifier).createFromGenerate(
      kind: _selectedKind,
      topic: _topicController.text.trim(),
      response: generateState.result!,
      audioUrl: generateState.audioUrl,
    );

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Saved to library')),
    );
  }

  void _copyText() {
    final generateState = ref.read(generateProvider);
    if (generateState.result == null) return;

    Clipboard.setData(ClipboardData(text: generateState.result!.text));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Copied to clipboard')),
    );
  }

  @override
  Widget build(BuildContext context) {
    final generateState = ref.watch(generateProvider);

    final bottomPadding = 16.0 + 56.0 + MediaQuery.of(context).padding.bottom;
    return SingleChildScrollView(
      padding: EdgeInsets.fromLTRB(16.0, 16.0, 16.0, bottomPadding),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Input section
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16.0),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  Text(
                    'Generate Content',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 16),
                  // Kind selector
                  SegmentedButton<String>(
                    segments: const [
                      ButtonSegment(value: 'poem', label: Text('Poem')),
                      ButtonSegment(value: 'story', label: Text('Story')),
                      ButtonSegment(value: 'lecture', label: Text('Lecture')),
                      ButtonSegment(value: 'natural', label: Text('Say it like Ika')),
                    ],
                    selected: {_selectedKind},
                    onSelectionChanged: (Set<String> newSelection) {
                      setState(() {
                        _selectedKind = newSelection.first;
                        if (_selectedKind == 'natural') {
                          if (!['polite', 'casual', 'respectful', 'romantic'].contains(_selectedTone)) {
                            _selectedTone = 'polite';
                          }
                        } else {
                          if (!['neutral', 'formal', 'poetic'].contains(_selectedTone)) {
                            _selectedTone = 'neutral';
                          }
                        }
                      });
                    },
                  ),
                  const SizedBox(height: 16),
                  TextField(
                    controller: _topicController,
                    decoration: InputDecoration(
                      labelText: _selectedKind == 'natural' ? 'Describe what you want to say' : 'Topic',
                      hintText: _selectedKind == 'natural'
                          ? 'e.g. Tell my friend I\'ll be late because of traffic, and I\'m sorry.'
                          : 'Enter topic for generation...',
                      border: const OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 16),
                  Row(
                    children: [
                      Expanded(
                        child: DropdownButtonFormField<String>(
                          value: _selectedKind == 'natural'
                              ? (['polite', 'casual', 'respectful', 'romantic'].contains(_selectedTone) ? _selectedTone : 'polite')
                              : (['neutral', 'formal', 'poetic'].contains(_selectedTone) ? _selectedTone : 'neutral'),
                          decoration: const InputDecoration(
                            labelText: 'Tone',
                            border: OutlineInputBorder(),
                          ),
                          items: _selectedKind == 'natural'
                              ? const [
                                  DropdownMenuItem(value: 'polite', child: Text('Polite')),
                                  DropdownMenuItem(value: 'casual', child: Text('Casual')),
                                  DropdownMenuItem(value: 'respectful', child: Text('Respectful')),
                                  DropdownMenuItem(value: 'romantic', child: Text('Romantic')),
                                ]
                              : const [
                                  DropdownMenuItem(value: 'neutral', child: Text('Neutral')),
                                  DropdownMenuItem(value: 'formal', child: Text('Formal')),
                                  DropdownMenuItem(value: 'poetic', child: Text('Poetic')),
                                ],
                          onChanged: (value) {
                            setState(() {
                              _selectedTone = value ?? (_selectedKind == 'natural' ? 'polite' : 'neutral');
                            });
                          },
                        ),
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: DropdownButtonFormField<String>(
                          value: _selectedLength,
                          decoration: const InputDecoration(
                            labelText: 'Length',
                            border: OutlineInputBorder(),
                          ),
                          items: const [
                            DropdownMenuItem(value: 'short', child: Text('Short')),
                            DropdownMenuItem(value: 'medium', child: Text('Medium')),
                            DropdownMenuItem(value: 'long', child: Text('Long')),
                          ],
                          onChanged: (value) {
                            setState(() {
                              _selectedLength = value ?? 'medium';
                            });
                          },
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 16),
                  PrimaryButton(
                    text: 'Generate',
                    icon: Icons.auto_stories,
                    isLoading: generateState.isLoading,
                    onPressed: _generate,
                  ),
                ],
              ),
            ),
          ),

          // Output section
          if (generateState.error != null)
            Card(
              color: Colors.red[50],
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Text(
                  generateState.error!,
                  style: TextStyle(color: Colors.red[900]),
                ),
              ),
            ),

          if (generateState.result != null) ...[
            const SizedBox(height: 16),
            Card(
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: Text(
                            _selectedKind == 'natural'
                                ? 'Say it like Ika'
                                : 'Generated ${_selectedKind.capitalize()}',
                            style: Theme.of(context).textTheme.titleMedium,
                          ),
                        ),
                        IconButton(
                          icon: const Icon(Icons.copy),
                          onPressed: _copyText,
                          tooltip: 'Copy text',
                        ),
                        IconButton(
                          icon: const Icon(Icons.bookmark_add),
                          onPressed: _saveToLibrary,
                          tooltip: 'Save to library',
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    SelectableText(
                      generateState.result!.text,
                      style: Theme.of(context).textTheme.bodyLarge,
                    ),
                    const SizedBox(height: 16),
                    AudioPlayerWidget(
                      audioUrl: generateState.audioUrl,
                      onGenerateAudio: _generateAudio,
                      cacheHit: generateState.audioCacheHit,
                    ),
                    if (generateState.result!.englishBacktranslation != null &&
                        generateState.result!.englishBacktranslation!.isNotEmpty) ...[
                      const SizedBox(height: 12),
                      ExpansionTile(
                        title: const Text('Show English meaning'),
                        children: [
                          Padding(
                            padding: const EdgeInsets.all(12.0),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.stretch,
                              children: [
                                SelectableText(
                                  generateState.result!.englishBacktranslation!,
                                  style: Theme.of(context).textTheme.bodyMedium,
                                ),
                                if (generateState.result!.notes != null &&
                                    generateState.result!.notes!.isNotEmpty) ...[
                                  const SizedBox(height: 8),
                                  ...generateState.result!.notes!
                                      .map((n) => Padding(
                                            padding: const EdgeInsets.only(bottom: 4.0),
                                            child: Row(
                                              crossAxisAlignment: CrossAxisAlignment.start,
                                              children: [
                                                Icon(Icons.info_outline, size: 16, color: Theme.of(context).colorScheme.primary),
                                                const SizedBox(width: 6),
                                                Expanded(child: Text(n, style: Theme.of(context).textTheme.bodySmall)),
                                              ],
                                            ),
                                          )),
                                ],
                              ],
                            ),
                          ),
                        ],
                      ),
                    ],
                  ],
                ),
              ),
            ),
            if (generateState.result!.meta.isNotEmpty &&
                generateState.result!.englishBacktranslation == null)
              MetaExpandable(meta: generateState.result!.meta),
          ],
        ],
      ),
    );
  }
}

extension StringExtension on String {
  String capitalize() {
    return "${this[0].toUpperCase()}${substring(1)}";
  }
}
