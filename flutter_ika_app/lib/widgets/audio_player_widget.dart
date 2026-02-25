import 'package:flutter/material.dart';
import 'package:just_audio/just_audio.dart';

/// Self-contained audio player widget for URL or file path.
/// Used by Translate, Generate, and Detail screens (no Riverpod provider).
class AudioPlayerWidget extends StatefulWidget {
  final String? audioUrl;
  final VoidCallback? onGenerateAudio;

  const AudioPlayerWidget({
    super.key,
    this.audioUrl,
    this.onGenerateAudio,
  });

  @override
  State<AudioPlayerWidget> createState() => _AudioPlayerWidgetState();
}

class _AudioPlayerWidgetState extends State<AudioPlayerWidget> {
  final AudioPlayer _player = AudioPlayer();
  bool _isPlaying = false;
  bool _isLoading = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _player.playerStateStream.listen((state) {
      if (mounted) {
        setState(() {
          _isPlaying = state.playing;
          _isLoading = state.processingState == ProcessingState.loading;
        });
      }
    });
  }

  @override
  void dispose() {
    _player.dispose();
    super.dispose();
  }

  Future<void> _playOrPause() async {
    final url = widget.audioUrl;
    if (url == null || url.isEmpty) return;
    try {
      setState(() { _error = null; _isLoading = true; });
      if (_isPlaying) {
        await _player.pause();
      } else {
        if (url.startsWith('http://') || url.startsWith('https://')) {
          await _player.setUrl(url);
        } else {
          await _player.setFilePath(url);
        }
        await _player.play();
      }
    } catch (e) {
      if (mounted) setState(() => _error = 'Failed to play: $e');
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _stop() async {
    await _player.stop();
  }

  @override
  Widget build(BuildContext context) {
    if (widget.audioUrl == null || widget.audioUrl!.isEmpty) {
      return ElevatedButton.icon(
        onPressed: widget.onGenerateAudio,
        icon: const Icon(Icons.play_arrow),
        label: const Text('Generate Audio'),
      );
    }

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            IconButton(
              icon: Icon(_isPlaying ? Icons.pause : Icons.play_arrow),
              onPressed: _isLoading ? null : _playOrPause,
            ),
            IconButton(
              icon: const Icon(Icons.stop),
              onPressed: _isLoading ? null : _stop,
            ),
            if (_isLoading)
              const Padding(
                padding: EdgeInsets.all(8.0),
                child: SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                ),
              ),
          ],
        ),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.all(8.0),
            child: Text(
              _error!,
              style: TextStyle(color: Colors.red[700], fontSize: 12),
            ),
          ),
      ],
    );
  }
}
