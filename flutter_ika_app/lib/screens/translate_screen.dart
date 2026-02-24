import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../state/translate_provider.dart';
import '../state/library_provider.dart';
import '../widgets/primary_button.dart';
import '../widgets/audio_player_widget.dart';
import '../widgets/meta_expandable.dart';

/// Translate screen
class TranslateScreen extends ConsumerStatefulWidget {
  const TranslateScreen({super.key});

  @override
  ConsumerState<TranslateScreen> createState() => _TranslateScreenState();
}

class _TranslateScreenState extends ConsumerState<TranslateScreen> {
  final TextEditingController _textController = TextEditingController();
  String _selectedTense = 'present';

  @override
  void dispose() {
    _textController.dispose();
    super.dispose();
  }

  void _translate() {
    final text = _textController.text.trim();
    if (text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Please enter text to translate')),
      );
      return;
    }

    ref.read(translateProvider.notifier).translate(text, _selectedTense);
  }

  Future<void> _generateAudio() async {
    final translateState = ref.read(translateProvider);
    if (translateState.result == null) return;

    // Show loading
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Generating audio...')),
    );

    final audioUrl = await ref.read(translateProvider.notifier).generateAudio();

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
    final translateState = ref.read(translateProvider);
    if (translateState.result == null) return;

    ref.read(libraryProvider.notifier).createFromTranslate(
      input: _textController.text.trim(),
      response: translateState.result!,
      audioUrl: translateState.audioUrl,
    );

    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Saved to library')),
    );
  }

  void _copyText() {
    final translateState = ref.read(translateProvider);
    if (translateState.result == null) return;

    Clipboard.setData(ClipboardData(text: translateState.result!.text));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('Copied to clipboard')),
    );
  }

  @override
  Widget build(BuildContext context) {
    final translateState = ref.watch(translateProvider);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
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
                    'English Text',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 8),
                  TextField(
                    controller: _textController,
                    maxLines: 5,
                    decoration: const InputDecoration(
                      hintText: 'Enter English text to translate...',
                      border: OutlineInputBorder(),
                    ),
                  ),
                  const SizedBox(height: 16),
                  DropdownButtonFormField<String>(
                    value: _selectedTense,
                    decoration: const InputDecoration(
                      labelText: 'Tense',
                      border: OutlineInputBorder(),
                    ),
                    items: const [
                      DropdownMenuItem(value: 'present', child: Text('Present')),
                      DropdownMenuItem(value: 'past', child: Text('Past')),
                      DropdownMenuItem(value: 'future', child: Text('Future')),
                      DropdownMenuItem(value: 'progressive', child: Text('Progressive')),
                    ],
                    onChanged: (value) {
                      setState(() {
                        _selectedTense = value ?? 'present';
                      });
                    },
                  ),
                  const SizedBox(height: 16),
                  PrimaryButton(
                    text: 'Translate',
                    icon: Icons.translate,
                    isLoading: translateState.isLoading,
                    onPressed: _translate,
                  ),
                ],
              ),
            ),
          ),

          // Output section
          if (translateState.error != null)
            Card(
              color: Colors.red[50],
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Text(
                  translateState.error!,
                  style: TextStyle(color: Colors.red[900]),
                ),
              ),
            ),

          if (translateState.result != null) ...[
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
                            'Ika Translation',
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
                      translateState.result!.text,
                      style: Theme.of(context).textTheme.bodyLarge,
                    ),
                    const SizedBox(height: 16),
                    AudioPlayerWidget(
                      audioUrl: translateState.audioUrl,
                      onGenerateAudio: _generateAudio,
                    ),
                  ],
                ),
              ),
            ),
            MetaExpandable(meta: translateState.result!.meta),
          ],
        ],
      ),
    );
  }
}
