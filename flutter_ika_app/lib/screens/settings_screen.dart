import 'package:flutter/material.dart';
import '../services/audio_cache_service.dart';

/// Settings screen: Clear audio cache, etc.
class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            'Settings',
            style: Theme.of(context).textTheme.titleLarge,
          ),
          const SizedBox(height: 24),
          Card(
            child: ListTile(
              leading: const Icon(Icons.cleaning_services),
              title: const Text('Clear audio cache'),
              subtitle: const Text(
                'Remove downloaded audio files from this device. They will be re-downloaded when you play again.',
              ),
              onTap: () async {
                final confirm = await showDialog<bool>(
                  context: context,
                  builder: (ctx) => AlertDialog(
                    title: const Text('Clear audio cache?'),
                    content: const Text(
                      'This will remove all cached audio from this device. Audio will be downloaded again when you play.',
                    ),
                    actions: [
                      TextButton(
                        onPressed: () => Navigator.pop(ctx, false),
                        child: const Text('Cancel'),
                      ),
                      FilledButton(
                        onPressed: () => Navigator.pop(ctx, true),
                        child: const Text('Clear'),
                      ),
                    ],
                  ),
                );
                if (confirm != true || !context.mounted) return;
                await AudioCacheService().clearCache();
                if (!context.mounted) return;
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(content: Text('Audio cache cleared')),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
