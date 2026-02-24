import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import '../api/models.dart';

/// Result card widget for library
class ResultCard extends StatelessWidget {
  final GenerationResult result;
  final VoidCallback? onTap;
  final VoidCallback? onPlayAudio;

  const ResultCard({
    super.key,
    required this.result,
    this.onTap,
    this.onPlayAudio,
  });

  String get _typeLabel {
    switch (result.type) {
      case 'translate':
        return 'Translation';
      case 'poem':
        return 'Poem';
      case 'story':
        return 'Story';
      case 'lecture':
        return 'Lecture';
      default:
        return result.type;
    }
  }

  String get _preview {
    if (result.outputText.length > 50) {
      return '${result.outputText.substring(0, 50)}...';
    }
    return result.outputText;
  }

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Chip(
                    label: Text(_typeLabel),
                    labelStyle: const TextStyle(fontSize: 12),
                  ),
                  const Spacer(),
                  Text(
                    DateFormat('MMM d, y').format(result.createdAt),
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
              const SizedBox(height: 8),
              Text(
                result.type == 'translate' ? result.input : result.input,
                style: Theme.of(context).textTheme.titleSmall,
              ),
              const SizedBox(height: 8),
              Text(
                _preview,
                style: Theme.of(context).textTheme.bodyMedium,
                maxLines: 2,
                overflow: TextOverflow.ellipsis,
              ),
              if (result.audioUrl != null || onPlayAudio != null)
                Padding(
                  padding: const EdgeInsets.only(top: 8.0),
                  child: Row(
                    children: [
                      if (result.audioUrl != null)
                        Icon(Icons.audiotrack, size: 16, color: Colors.green[700]),
                      const SizedBox(width: 4),
                      TextButton.icon(
                        onPressed: onPlayAudio,
                        icon: const Icon(Icons.play_arrow, size: 16),
                        label: const Text('Play'),
                        style: TextButton.styleFrom(
                          padding: const EdgeInsets.symmetric(horizontal: 8),
                        ),
                      ),
                    ],
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }
}
